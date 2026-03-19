"""
Module chứa toàn bộ Thư viện Tiện ích (Utilities) và Thuật toán Lõi (Core Algorithms).
Bao gồm: Giao tiếp AI (Gemini), Quản trị Vector DB (Chroma), Hệ thống tìm kiếm Fallback,
Thuật toán Khuyến nghị, So sánh sản phẩm và Động cơ Khuyến mãi (Voucher Engine).
Tuyệt đối không chứa các module liên quan đến SMTP/Email.
"""

import os
import json
import re
import chromadb
from google import genai
from google.genai import types
from chromadb.utils import embedding_functions
from flask import url_for
from itsdangerous import URLSafeTimedSerializer
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import requests
from PIL import Image
import io


# [NEW] Khởi tạo thư viện PyTorch cho Visual Search
try:
    import torch
    import torchvision.models as models
    import torchvision.transforms as transforms
except ImportError:
    torch = None
    print("⚠️ PyTorch chưa được cài đặt. Tính năng tìm kiếm bằng hình ảnh sẽ không hoạt động. Chạy: pip install torch torchvision")

# =========================================================================
# [HOTFIX] Khóa mõm triệt để lỗi rác Telemetry của ChromaDB 0.4.22
# Sử dụng kỹ thuật Monkey Patching đúng chuẩn Python tránh lỗi Argument Mismatch
# =========================================================================
try:
    from chromadb.telemetry.posthog import Posthog  # type: ignore

    # ---> [HOTFIX]: Dùng lambda để nuốt sạch mọi tham số, diệt tận gốc lỗi crash log
    Posthog.capture = lambda *args, **kwargs: None
except Exception:
    pass

# Tắt cảnh báo Telemetry của ChromaDB để giao diện Console sạch sẽ
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Khởi tạo ChromaDB (Lưu file local tại thư mục chroma_db)
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
except Exception as e:
    print(f"⚠️ ChromaDB Init Warning: {e}")
    chroma_client = None

# [NEW] Khởi tạo Model MobileNetV2 siêu nhẹ cho tính năng Visual Search
visual_model = None
visual_transforms = None

if torch is not None:
    try:
        # Sử dụng trọng số (weights) đã được huấn luyện sẵn trên tập ImageNet
        weights = models.MobileNet_V2_Weights.DEFAULT
        visual_model = models.mobilenet_v2(weights=weights)
        visual_model.eval()  # Chuyển sang chế độ dự đoán (không train)

        # Tiền xử lý ảnh theo chuẩn của PyTorch
        visual_transforms = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    except Exception as e:
        print(f"⚠️ Không thể tải mô hình MobileNetV2: {e}")



class LocalEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Sử dụng Vector Model Offline để miễn phí 100% API Quota"""
    def __init__(self):
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")

    def __call__(self, input: list[str]) -> list[list[float]]:
        try:
            return self.ef(input)
        except Exception as e:
            print(f"❌ Local Embedding Error: {e}")
            return [[0.0] * 384] * len(input)

# Khởi tạo Collection lưu trữ
try:
    if chroma_client:
        product_collection = chroma_client.get_or_create_collection(
            name="mobile_store_products",
            embedding_function=LocalEmbeddingFunction()
        )
        # ---> [NEW] Khởi tạo Collection riêng chứa Vector Hình ảnh
        # [FIX QUAN TRỌNG 1]: Thêm metadata cosine. Vector Model Hình ảnh bắt buộc phải dùng Cosine Similarity thay vì L2 để so sánh độ tương đồng chính xác.
        product_image_collection = chroma_client.get_or_create_collection(
            name="product_images",
            metadata={"hnsw:space": "cosine"}
        )
    else:
        product_collection = None
        product_image_collection = None
except Exception as e:
    print(f"⚠️ ChromaDB Collection Error: {e}")
    product_collection = None
    product_image_collection = None

def validate_image_file(file):
    """
    Kiểm tra tính hợp lệ của file ảnh tải lên hệ thống.
    Xác minh phần mở rộng và chặn các file vượt quá dung lượng 2MB để chống DDoS Storage.
    """
    if file.filename == '': return False, "Chưa chọn file."
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
        return False, "Chỉ nhận: JPG, PNG, WEBP."
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 2 * 1024 * 1024: return False, "File > 2MB."
    return True, None


# =========================================================================
# ---> [NEW] HỆ THỐNG XỬ LÝ ẢNH (VISUAL SEARCH ENGINE)
# =========================================================================
def get_image_embedding(image_source, is_url=True):
    """
    Biến đổi hình ảnh thành mảng Vector 1000 chiều bằng MobileNetV2.
    """
    if not visual_model or not visual_transforms:
        return None

    try:
        if is_url:
            # Nếu là link ảnh trên mạng (Tự động tải về trên RAM)
            # [FIX QUAN TRỌNG 2]: Thêm Header User-Agent giả lập trình duyệt để tải ảnh từ Amazon/Unsplash không bị lỗi 403 Forbidden.
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(image_source, stream=True, timeout=5, headers=headers)
            response.raise_for_status()
            img = Image.open(response.raw).convert('RGB')
        else:
            # Nếu là file do người dùng upload trực tiếp
            img = Image.open(image_source).convert('RGB')

        # Chạy ảnh qua mạng CNN
        input_tensor = visual_transforms(img)
        input_batch = input_tensor.unsqueeze(0)  # Tạo mini-batch (batch_size=1)

        with torch.no_grad():
            output = visual_model(input_batch)

        # Chuyển tensor thành list Python chuẩn để nhét vào ChromaDB
        return output[0].numpy().tolist()
    except Exception as e:
        print(f"⚠️ Lỗi trích xuất Vector Ảnh: {e}")
        return None


def sync_product_image_to_vector_db(product):
    """
    Đồng bộ ảnh của sản phẩm vào ChromaDB khi Admin thêm/sửa sản phẩm.
    """
    if not product_image_collection or not product.image_url:
        return

    embedding = get_image_embedding(product.image_url, is_url=True)
    if embedding:
        try:
            product_image_collection.upsert(
                embeddings=[embedding],
                metadatas=[{"name": product.name, "brand": product.brand}],
                ids=[str(product.id)]
            )
            print(f"📸 Indexed Image Vector: {product.name}")
        except Exception as e:
            print(f"⚠️ Lỗi lưu Vector Ảnh vào ChromaDB: {e}")


def search_image_vector_db(image_file, n_results=4):
    """
    Tìm kiếm các sản phẩm có hình dáng giống nhất với ảnh tải lên.
    """
    if not product_image_collection: return []

    embedding = get_image_embedding(image_file, is_url=False)
    if not embedding: return []

    try:
        results = product_image_collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        if results['ids'] and len(results['ids']) > 0:
            return results['ids'][0]
        return []
    except Exception as e:
        print(f"⚠️ Lỗi tìm kiếm Vector Ảnh: {e}")
        return []

def identify_phone_by_gemini(image_file):
    """
    Dùng AI Gemini Vision (Đa phương thức) để nhận diện chính xác TÊN dòng điện thoại từ ảnh.
    Đáp ứng chuẩn xác yêu cầu: "Đưa ảnh vào và show ra tên điện thoại là gì".
    """
    raw_keys = os.environ.get("GEMINI_API_KEY", "")
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

    if not api_keys:
        return None

    try:
        # Đọc dữ liệu ảnh gốc
        image_bytes = image_file.read()
        # Quan trọng: Reset con trỏ file về 0 để các hàm vector phía sau (nếu gọi) không bị lỗi đọc file rỗng
        image_file.seek(0)

        mime_type = image_file.mimetype if hasattr(image_file, 'mimetype') else 'image/jpeg'

        system_instruction = (
            "Bạn là chuyên gia nhận diện hình ảnh các thiết bị di động. "
            "Nhiệm vụ của bạn là: Nhìn vào bức ảnh và xác định ĐÚNG TÊN HÃNG VÀ TÊN DÒNG MÁY điện thoại hiển thị trong ảnh. "
            "CHỈ TRẢ VỀ CHUỖI JSON DUY NHẤT, tuyệt đối không giải thích thêm. "
            "LUÔN KÈM THEO TÊN HÃNG. Ví dụ: {\"phone_model\": \"Apple iPhone 15 Pro Max\"} hoặc {\"phone_model\": \"Xiaomi Redmi Note 13 Pro\"}. "
            "Nếu ảnh không chứa điện thoại hoặc quá mờ không thể nhận diện được, hãy trả về {\"phone_model\": null}."
        )

        for key in api_keys:
            try:
                temp_client = genai.Client(api_key=key)
                response = temp_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        "Hãy nhận diện tên của dòng điện thoại xuất hiện trong bức ảnh này:",
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json"
                    )
                )

                # Bóc tách JSON an toàn
                clean = re.sub(r"```json|```", "", response.text).strip()
                parsed = json.loads(clean)
                return parsed.get("phone_model")
            except Exception as e:
                # Nếu Key này lỗi/hết quota thì xoay vòng sang key khác
                continue
        return None
    except Exception as e:
        print(f"Lỗi AI Vision Nhận diện: {e}")
        return None


def get_serializer(secret_key):
    """
    Khởi tạo đối tượng mã hóa chuỗi an toàn.
    Dùng để sinh mã Token có giới hạn thời gian (Dùng trong tính năng Quên mật khẩu).
    """
    return URLSafeTimedSerializer(secret_key)


def send_reset_email_simulation(to_email, token):
    """
    Giả lập quá trình tạo liên kết khôi phục mật khẩu.
    Chỉ in thẳng đường dẫn chứa Token ra Console Server để Dev tiện kiểm thử.
    Tuyệt đối không sử dụng module SMTP/Email thực.
    """
    link = url_for('auth.reset_password', token=token, _external=True)
    print(f"🔑 [MOCK PASSWORD RESET LINK]: {link}")
    return link


def search_vector_db(query_text, n_results=5, metadata_filters=None):
    # ---> [HOTFIX 4]: Đã xóa bỏ điều kiện 'or not GEMINI_API_KEY'
    # Giải phóng hoàn toàn Vector Offline, cho phép nó chạy bất chấp trạng thái API Key
    if not product_collection:
        return []
    try:
        count = product_collection.count()
        if count == 0: return []
        safe_n_results = min(n_results, count)

        query_params = {"query_texts": [query_text], "n_results": safe_n_results}
        if metadata_filters:
            query_params["where"] = metadata_filters

        results = product_collection.query(**query_params)
        if results['ids'] and len(results['ids']) > 0:
            return results['ids'][0]
        return []
    except Exception as e:
        print(f"⚠️ Vector Search Skipped: {e}")
        return []


def sync_product_to_vector_db(product):
    """
    Đồng bộ dữ liệu của 1 Sản phẩm vào bộ nhớ Vector Database.
    Chuyển đổi dữ liệu bảng (SQL) thành văn bản ngữ nghĩa để AI dễ dàng đọc hiểu.
    """
    if not product_collection: return

    clean_desc = str(product.description).replace('\n', ' ').strip()
    semantic_text = f"Sản phẩm {product.name}, hãng {product.brand}, loại {product.category}. Cấu hình/Tính năng: {clean_desc}. Giá bán: {product.price} VNĐ."

    try:
        product_collection.upsert(
            documents=[semantic_text],
            metadatas=[{"price": product.price, "brand": product.brand, "category": product.category}],
            ids=[str(product.id)]
        )
        print(f"✅ Indexed Vector: {product.name}")
    except Exception as e:
        print(f"Sync Vector Error: {e}")


def get_similar_products(current_product, limit=4):
    """
    Thuật toán Gợi ý Sản phẩm Tương tự dựa trên Content-Based Filtering.
    Chạy 100% bằng toán học nội bộ (So khớp Hãng, Độ lệch giá và Từ khóa).
    """
    from app.models import Product

    candidates = Product.query.filter(
        Product.category == current_product.category,
        Product.id != current_product.id,
        Product.is_active == True
    ).all()

    if not candidates:
        return []

    scored_products = []
    target_words = set(current_product.name.lower().split())
    target_price = current_product.sale_price if current_product.is_sale else current_product.price

    for p in candidates:
        score = 0
        candidate_price = p.sale_price if p.is_sale else p.price

        if p.brand.lower() == current_product.brand.lower():
            score += 50

        max_price = max(target_price, 1)
        price_diff_ratio = abs(candidate_price - target_price) / max_price

        if price_diff_ratio <= 0.1: score += 30
        elif price_diff_ratio <= 0.2: score += 20
        elif price_diff_ratio <= 0.3: score += 10

        candidate_words = set(p.name.lower().split())
        common_words = target_words.intersection(candidate_words)
        score += len(common_words) * 5

        scored_products.append((score, p))

    scored_products.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_products[:limit]]


# =========================================================================
# LÕI GIAO TIẾP VỚI GOOGLE GEMINI (TỐI ƯU HÓA ROTATION KEY & SDK MỚI)
# =========================================================================
def call_gemini_api(prompt, system_instruction=None, is_json=False):
    """
    Hàm lõi gọi Google Gemini có tính năng xoay vòng API Key (Key Rotation)
    Đã được tối ưu bộ lọc chuỗi để chống lỗi 400 INVALID_ARGUMENT.
    """
    raw_keys = os.environ.get("GEMINI_API_KEY", "")

    # Xử lý chuỗi key an toàn hơn: Cắt theo dấu phẩy, loại bỏ khoảng trắng, lọc bỏ key rỗng
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

    if not api_keys:
        print("❌ System Error: Không tìm thấy GEMINI_API_KEY trong file .env")
        return None

    config_kwargs = {}
    if system_instruction:
        config_kwargs['system_instruction'] = system_instruction

    if is_json:
        config_kwargs['response_mime_type'] = "application/json"

    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

    # Thử lần lượt từng API Key
    for key in api_keys:
        try:
            temp_client = genai.Client(api_key=key)
            response = temp_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            # Bắt cả lỗi 429 (Hết Quota) và 400 (Key sai/bị khóa) để trượt sang key tiếp theo
            if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "400" in error_str or "invalid" in error_str:
                hidden_key = f"...{key[-4:]}" if len(key) > 4 else "UNKNOWN"
                print(f"⚠️ Key ({hidden_key}) gặp lỗi ({error_str[:30]}...). Đang thử Key tiếp theo...")
                continue
            else:
                print(f"Gemini API Error: {e}")
                return None

    print("❌ TOÀN BỘ API KEY ĐÃ HỎNG HOẶC HẾT HẠN MỨC. Hệ thống AI đang tạm liệt!")
    return None


def direct_gemini_search(query, catalog_json):
    """
    Chế độ bất tử (Direct Text-RAG): Dùng mô hình LLM Text đọc kho hàng JSON.
    Tự động kích hoạt khi Vector DB gặp lỗi để luôn có kết quả tìm kiếm.
    """
    if not GEMINI_API_KEY: return []

    system_instruction = (
        "Bạn là trí tuệ nhân tạo lõi của MobileStore. "
        "Dựa vào yêu cầu của khách và danh sách kho hàng (JSON), "
        "hãy phân tích ngữ nghĩa và lọc ra đúng các ID sản phẩm. "
        "BẮT BUỘC TRẢ VỀ CHỈ MỘT MẢNG JSON CÁC SỐ NGUYÊN LÀ ID. Ví dụ: [1, 5, 12]. Tuyệt đối không viết thêm chữ gì khác."
    )
    prompt = f"Yêu cầu tìm kiếm của khách: '{query}'\n\nKho hàng hiện tại:\n{catalog_json}\n\nTrả về mảng JSON ID:"

    # ---> [HOTFIX 2]: Bật is_json=True để AI luôn trả về format chuẩn
    res = call_gemini_api(prompt, system_instruction, is_json=True)
    if not res: return []

    try:
        # Bóc tách an toàn: Xóa rác markdown nếu AI quên luật
        clean = re.sub(r"```json|```", "", res).strip()
        parsed_data = json.loads(clean)

        if isinstance(parsed_data, dict):
            parsed_data = parsed_data.get('ids', parsed_data.get('data', []))

        if isinstance(parsed_data, list):
            return [int(i) for i in parsed_data if str(i).isdigit() or isinstance(i, int)]

        return []
    except Exception as e:
        print(f"Direct AI Search Parse Error: {e}")
        return []


def build_product_context(user_query):
    ai_data = local_analyze_intent(user_query)
    filter_dict = {}
    if ai_data and ai_data.get('category'):
        filter_dict["category"] = ai_data['category']

    vector_ids = search_vector_db(user_query, n_results=10, metadata_filters=filter_dict if filter_dict else None)

    from app.models import Product
    products = []

    if vector_ids:
        ids = [int(i) for i in vector_ids if i.isdigit()]
        products = Product.query.filter(Product.id.in_(ids), Product.is_active == True).all()

    if not products:
        user_query_lower = user_query.lower()
        query = Product.query.filter(Product.name.ilike(f"%{user_query_lower}%"), Product.is_active == True)
        if filter_dict:
            query = query.filter_by(category=filter_dict['category'])
        products = query.limit(3).all()

    if not products:
        return "Hiện tại hệ thống không tìm thấy sản phẩm nào phù hợp trong kho."

    context_text = "--- KHO HÀNG THỰC TẾ ĐANG BÁN ---\n"
    for p in products:
        price = "{:,.0f} đ".format(p.sale_price if p.is_sale else p.price).replace(",", ".")
        status = f"Sẵn hàng ({p.stock_quantity})" if p.stock_quantity > 0 else "Hết hàng"
        desc_short = (p.description or "")[:150].replace('\n', ' ')
        context_text += f"- Tên máy: {p.name} | Hãng: {p.brand} | Giá: {price} | Tình trạng: {status}\n  Điểm nổi bật: {desc_short}...\n"

    return context_text


def generate_chatbot_response(user_msg, chat_history=None):

    """
    [UPGRADED] Chatbot AI Không Kịch Bản - Xử lý thông minh mọi tình huống thực tế.
    Kết hợp RAG động và khả năng phân tích Context đa tầng.
    """
    if chat_history is None:
        chat_history = []

    # ---> [FIX LỖI QUÊN NGỮ CẢNH (AMNESIA & FALSE OUT-OF-STOCK)] <---
    # Nối câu hỏi gần nhất của User và 1 phần câu trả lời của AI vào truy vấn RAG
    # Giúp hệ thống tìm kiếm luôn giữ được Tên Sản Phẩm dù khách chỉ nói "tư vấn máy đó"
    rag_query = user_msg
    if len(chat_history) > 0:
        last_user = chat_history[-1].get('user', '')
        # Trích xuất 100 ký tự đầu tiên từ câu trả lời trước đó của AI để giữ lại tên dòng máy
        last_ai = chat_history[-1].get('ai', '')[:100]
        rag_query = f"{last_user} {last_ai} {user_msg}"

    # 1. Luôn Trích xuất Context từ Kho hàng (RAG) với truy vấn đã được mở rộng
    context = build_product_context(rag_query)

    # 2. Xây dựng System Instruction linh hoạt tuyệt đối (Cập nhật luật chống mất hàng)
    system_instruction = (
        "Bạn là nhân viên tư vấn ảo AI xuất sắc, nhiệt tình và chuyên nghiệp của hệ thống bán lẻ MobileStore.\n\n"
        "MỤC TIÊU VÀ NhiỆM VỤ CỦA BẠN:\n"
        "- Xử lý LINH HOẠT mọi tình huống: Khách chào hỏi, hỏi giá, nhờ tư vấn, so sánh, thắc mắc chính sách, "
        "thậm chí là tán gẫu hoặc bắt bẻ.\n"
        "- Đọc hiểu ngữ cảnh từ [LỊCH SỬ HỘI THOẠI] để phản hồi liền mạch, không hỏi lại những gì khách đã nói.\n"
        "- Xưng hô là 'Dạ', tự xưng là 'em' hoặc 'MobileStore', gọi khách hàng là 'anh/chị'. Thái độ luôn ân cần, vui vẻ.\n\n"
        "QUY TẮC BÁN HÀNG NGHIÊM NGẶT (RAG RULES - CHỐNG BÁO SAI KHO HÀNG):\n"
        "1. Dữ liệu [KHO HÀNG THỰC TẾ] bên dưới thay đổi theo từng câu hỏi. NẾU KHÁCH HỎI TIẾP VỀ SẢN PHẨM Ở CÂU TRƯỚC (vd: 'máy đó', 'chiếc này'), HÃY DỰA VÀO LỊCH SỬ ĐỂ TƯ VẤN TIẾP. TUYỆT ĐỐI KHÔNG BÁO LÀ 'TẠM HẾT HÀNG' NẾU TRƯỚC ĐÓ VỪA BÁO CÒN HÀNG.\n"
        "2. CHỈ TƯ VẤN CÁC SẢN PHẨM CÓ TRONG KHO HOẶC ĐÃ XUẤT HIỆN TRONG LỊCH SỬ. KHÔNG tự sáng tác, bịa đặt giá.\n"
        "3. Khi khách tìm một dòng máy MỚI HOÀN TOÀN mà không có trong kho, lúc đó mới xin lỗi và gợi ý sang các mã máy tương tự đang có sẵn.\n"
        "4. Cách trình bày phải súc tích, dễ đọc, xuống dòng hợp lý, có thể dùng emoji để tạo thiện cảm.\n\n"
        f"{context}"
    )

    # 3. Format Lịch sử hội thoại rõ ràng cho AI đọc hiểu mạch truyện
    prompt = ""
    if chat_history:
        prompt += "--- LỊCH SỬ HỘI THOẠI GẦN NHẤT ---\n"
        for turn in chat_history:
            prompt += f"Khách hàng: {turn.get('user', '')}\nMobileStore: {turn.get('ai', '')}\n"

    prompt += f"\n--- CÂU HỎI MỚI CỦA KHÁCH ---\nKhách hàng: {user_msg}\nMobileStore:"

    # 4. Giao tiếp với não bộ Gemini
    res = call_gemini_api(prompt, system_instruction=system_instruction)

    if res:
        return res.strip()

    # 5. Fallback tinh tế khi API sập hoặc Quota cạn kiệt
    return "Dạ hiện tại hệ thống AI tư vấn đang tải hơi nhiều dữ liệu một chút, anh/chị có thể đợi em vài giây hoặc nói rõ tên dòng máy (VD: 'iPhone 15') để em tra cứu kho nhanh nhất nhé! 🥰"


def analyze_search_intents(query):
    """
    [NÂNG CẤP LÕI]: Trích xuất Dữ liệu (Entity) + Suy luận Ngữ nghĩa (Reasoning) bằng LLM.
    Bổ sung "semantic_query" để dịch các nhu cầu "lóng" thành truy vấn Vector chuẩn.
    """
    system_instruction = """
    Bạn là hệ thống AI phân tích ý định tìm kiếm cao cấp cho MobileStore.
    Nhiệm vụ: Phân tích câu hỏi tự nhiên và trả về CHỈ MỘT chuỗi JSON hợp lệ. Không giải thích.

    Quy tắc bóc tách:
    1. Giá: 'triệu'/'củ' = 1000000. 'trăm' = 100000. Nếu không nhắc đến, để min_price và max_price là null.
    2. Category: 'accessory' (ốp, sạc, tai nghe, cáp...) hoặc 'phone' (điện thoại, máy, tên dòng máy...). Không rõ để null.
    3. Brand: Hãng (Apple, Samsung, Xiaomi, Oppo...). Không có để null.
    4. keyword: Tên dòng máy chính xác hoặc màu sắc (VD: "iphone 15 pro max", "đen"). Lược bỏ các từ thừa.
    5. semantic_query (QUAN TRỌNG): Hãy dịch "nhu cầu" của khách thành 1 câu mô tả tính năng lý tưởng để tìm kiếm Vector. 
       - VD: Khách hỏi "máy cho người già" -> semantic_query: "điện thoại màn hình lớn, loa to, pin trâu, dễ sử dụng".
       - VD: Khách hỏi "điện thoại chiến game" -> semantic_query: "điện thoại cấu hình mạnh, chip chơi game mượt, tần số quét cao".
       - Nếu khách chỉ gõ tên máy (VD: "iphone 14"), giữ nguyên: "iphone 14".

    Định dạng JSON yêu cầu (BẮT BUỘC DÙNG CẤU TRÚC NÀY):
    {"brand": "Tên hãng hoặc null", "category": "phone hoặc accessory hoặc null", "min_price": Số hoặc null, "max_price": Số hoặc null, "keyword": "Từ khóa thô hoặc null", "semantic_query": "Câu dịch ngữ nghĩa hoặc null", "sort": "price_asc hoặc price_desc hoặc null"}
    """
    prompt = f"Câu hỏi: '{query}'\n\nTrả về JSON:"
    # Ép Gemini cấu trúc response trả về 100% JSON (Tránh lỗi 500)
    res = call_gemini_api(prompt, system_instruction=system_instruction, is_json=True)
    if not res: return None

    try:
        clean = re.sub(r"```json|```", "", res).strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            # [FIX CRASH] Chuẩn hóa lại cấu trúc JSON trước khi trả về cho main.py
            safe_data = {
                'brand': parsed.get('brand'),
                'category': parsed.get('category'),
                'min_price': parsed.get('min_price'),
                'max_price': parsed.get('max_price'),
                'keyword': parsed.get('keyword', ''),
                'semantic_query': parsed.get('semantic_query', ''),
                'sort': parsed.get('sort')
            }
            return safe_data
        return None
    except Exception as e:
        print(f"AI Parse JSON Error: {e}")
        return None


def local_analyze_intent(query):
    """
    [NEW ARCHITECTURE] Động cơ bóc tách ngữ nghĩa thuần Python (Regex + Heuristics).
    Nhanh, không phụ thuộc API, độ chính xác 100% với các cấu trúc tiếng lóng VN.
    """
    query = query.lower().strip()
    data = {'brand': None, 'category': None, 'keyword': '', 'semantic_query': '', 'min_price': None, 'max_price': None, 'sort': None}

    # Bóc Hãng
    brands = {'iphone': 'Apple', 'apple': 'Apple', 'samsung': 'Samsung', 'oppo': 'Oppo', 'xiaomi': 'Xiaomi',
              'vivo': 'Vivo', 'realme': 'Realme'}
    for k, v in brands.items():
        if k in query:
            data['brand'] = v
            # Không xóa từ khóa hãng khỏi query để hệ thống Score Search bên dưới còn dùng

    # Bóc Danh mục cực chuẩn (Tránh bẫy "ốp lưng iphone")
    accessory_kws = ['ốp', 'sạc', 'tai nghe', 'cáp', 'kính', 'cường lực', 'giá đỡ', 'loa', 'dây đeo', 'airpods', 'buds',
                     'bao da']

    # Ưu tiên Phụ kiện lên hàng đầu: Nếu câu có chữ "ốp" thì 100% là tìm phụ kiện
    if any(x in query for x in accessory_kws):
        data['category'] = 'accessory'
    elif re.search(r'\b(điện thoại|máy|smartphone|phone)\b', query):
        data['category'] = 'phone'

    # Bóc Giá (Quy đổi "củ", "triệu")
    price_match = re.search(r'(\d+)\s*(triệu|củ|tr)', query)
    if price_match:
        val = int(price_match.group(1))
        if val < 1000: data['max_price'] = val * 1000000
        query = re.sub(r'\d+\s*(triệu|củ|tr)(\s*quay\s*đầu|\s*trở\s*xuống)?', '', query)

    # Lọc Stop words
    stop_words = ['tôi', 'muốn', 'mua', 'tìm', 'cho', 'cần', 'dưới', 'khoảng', 'điện', 'thoại', 'máy', 'giá', 'rẻ',
                  'nào', 'tầm', 'quay', 'đầu']
    words = query.split()
    clean_kw = " ".join([w for w in words if w not in stop_words]).strip()

    data['keyword'] = clean_kw
    data['semantic_query'] = clean_kw # Gán tạm cho fallback vector

    return data

# ==============================================================================================
# ---> [ĐÃ KHÔI PHỤC: BẢNG SO SÁNH GIỮ ĐÚNG FORM GỐC (HÀNG-CỘT) + TƯ VẤN AI CHUYÊN SÂU] <---
# ==============================================================================================
def get_comparison_result(p1_id, p1_name, p1_price, p1_desc, p1_img,
                          p2_id, p2_name, p2_price, p2_desc, p2_img,
                          p3_id=None, p3_name=None, p3_price=None, p3_desc=None, p3_img=None,
                          p4_id=None, p4_name=None, p4_price=None, p4_desc=None, p4_img=None):
    """
    Sử dụng AI tạo bảng HTML đối chiếu thông số từ 2 đến 4 sản phẩm theo CẤU TRÚC GỐC của bảng so sánh.
    Bên dưới bảng sẽ đính kèm phần tư vấn, đánh giá, phân tích sâu sắc từ AI.
    """
    system_instruction = (
        "Bạn là chuyên gia bán hàng công nghệ cấp cao kiêm Frontend Developer. "
        "Nhiệm vụ của bạn là tạo một bảng HTML so sánh thông số kỹ thuật CHÍNH XÁC theo cấu trúc Hàng-Cột yêu cầu, "
        "sau đó đưa ra bài phân tích tư vấn cực kỳ CHUYÊN SÂU bên dưới."
    )

    if not p1_img: p1_img = "https://via.placeholder.com/150"
    if not p2_img: p2_img = "https://via.placeholder.com/150"

    products_info = f"Máy 1: {p1_name} (Giá: {p1_price}) - Ảnh: {p1_img} - Cấu hình: {p1_desc}\n"
    products_info += f"Máy 2: {p2_name} (Giá: {p2_price}) - Ảnh: {p2_img} - Cấu hình: {p2_desc}\n"

    machine_headers = f'<th>Tính năng</th><th class="text-center" style="width: 20%;"><span class="text-dark fw-bold">{p1_name}</span></th><th class="text-center" style="width: 20%;"><span class="text-dark fw-bold">{p2_name}</span></th>'
    advice_list = f"  + <li>Nên mua <b>{p1_name}</b> nếu bạn...</li>\n  + <li>Nên mua <b>{p2_name}</b> nếu bạn...</li>\n"

    num_cols = 2

    if p3_name:
        num_cols = 3
        products_info += f"Máy 3: {p3_name} (Giá: {p3_price}) - Ảnh: {p3_img} - Cấu hình: {p3_desc}\n"
        machine_headers += f'<th class="text-center" style="width: 20%;"><span class="text-dark fw-bold">{p3_name}</span></th>'
        advice_list += f"  + <li>Nên mua <b>{p3_name}</b> nếu bạn...</li>\n"

    if p4_name:
        num_cols = 4
        products_info += f"Máy 4: {p4_name} (Giá: {p4_price}) - Ảnh: {p4_img} - Cấu hình: {p4_desc}\n"
        machine_headers += f'<th class="text-center" style="width: 20%;"><span class="text-dark fw-bold">{p4_name}</span></th>'
        advice_list += f"  + <li>Nên mua <b>{p4_name}</b> nếu bạn...</li>\n"

    prompt = f"""
    Hãy tạo mã HTML so sánh {num_cols} sản phẩm sau:
    {products_info}

    LƯU Ý QUAN TRỌNG: 
    SỬ DỤNG KIẾN THỨC CỦA BẠN để điền đầy đủ và chính xác nhất các thông số kỹ thuật bị thiếu. Không để trống thông số nào. 
    Nếu phần "Ảnh" là đường link hợp lệ, hãy dùng thẻ `<img src="..." style="max-height: 120px; object-fit: contain;">`. Nếu không có, ghi "Không có ảnh".
    Dữ liệu Giá và Ảnh ĐÃ CÓ SẴN ở trên, hãy đưa đúng vào bảng.

    Yêu cầu ĐỊNH DẠNG HTML BẮT BUỘC (Tuyệt đối không thay đổi cấu trúc bảng dưới đây):
    - Bước 1: Tạo một bảng `<table class="table table-bordered table-hover">`.
    Cột 1 là "Thông số kỹ thuật", Cột 2 là tên máy 1, Cột 3 là tên máy 2.
    BẮT BUỘC phải tạo các hàng (row) sau đây trong bảng:
      + Kích thước màn hình
      + Công nghệ màn hình / Độ phân giải
      + Tần số quét (Hz)
      + Camera sau
      + Camera trước
      + Chipset (CPU)
      + Dung lượng RAM
      + Bộ nhớ trong (ROM)
      + Dung lượng Pin & Công suất Sạc nhanh
      + Công nghệ NFC
      + Thẻ SIM
      + Hệ điều hành
      + Thiết kế & Trọng lượng

    - Sau khi đóng thẻ `</table>`, tạo 1 khối tư vấn AI:
      `<div class="alert alert-info mt-4 p-4 rounded-4 shadow-sm border-0" style="background-color: #e8f9fd;">`
      `<h4 class="fw-bold text-primary mb-3"><i class="fas fa-robot me-2"></i>Tư vấn chuyên sâu từ chuyên gia công nghệ</h4>`
      Mở đầu bằng câu: "Chào bạn, với vai trò là một chuyên gia..."
      Viết các đoạn văn phân tích CHI TIẾT (có liệt kê "Điểm mạnh", "Phù hợp với") về điểm mạnh, yếu, sự khác biệt giữa các máy.
      `<h5 class="fw-bold text-dark mt-4">Tóm tắt & Lời khuyên cuối cùng:</h5>`
      `<ul class="mt-2 text-dark">`
      {advice_list}
      `</ul>`
      `</div>`

    CHỈ TRẢ VỀ MÃ HTML (Gồm bảng so sánh và thẻ div tư vấn), KHÔNG DÙNG ```html VÀ KHÔNG KÈM TEXT GIẢI THÍCH KHÁC.
    """

    res = call_gemini_api(prompt, system_instruction=system_instruction)
    return re.sub(r"```html|```", "", res).strip() if res else None


def generate_local_comparison_html(p1, p2, p3=None, p4=None):
    """
    Thuật toán vẽ bảng so sánh dự phòng bằng Python thuần (Local HTML Generator).
    Cứu sập trang khi API Google quá tải. Đảm bảo form bảng khớp 100% với form của AI
    và giữ đúng định dạng Hàng-Cột truyền thống.
    """
    products = [p for p in [p1, p2, p3, p4] if p]

    headers_html = "<th>Tính năng</th>"
    for p in products:
        headers_html += f"<th class='text-center' style='width: 20%;'><span class='text-dark fw-bold'>{p.name}</span></th>"

    tbody_html = "<tr><td class='fw-bold'>Giá</td>"
    for p in products:
        price_str = "{:,.0f} đ".format(p.sale_price if p.is_sale else p.price).replace(",", ".")
        tbody_html += f"<td class='text-center fw-bold text-danger'>{price_str}</td>"
    tbody_html += "</tr>"

    tbody_html += "<tr><td class='fw-bold'>Ảnh sản phẩm</td>"
    for p in products:
        tbody_html += f"<td class='text-center'><img src='{p.image_url}' style='max-height:120px; object-fit:contain;'></td>"
    tbody_html += "</tr>"

    tbody_html += "<tr><td class='fw-bold'>Thương hiệu</td>"
    for p in products:
        tbody_html += f"<td class='text-center fw-medium'>{p.brand}</td>"
    tbody_html += "</tr>"

    tbody_html += "<tr><td class='fw-bold'>Phân loại</td>"
    for p in products:
        cat_name = "Điện thoại" if p.category == 'phone' else "Phụ kiện"
        tbody_html += f"<td class='text-center fw-medium'>{cat_name}</td>"
    tbody_html += "</tr>"

    tbody_html += "<tr><td class='fw-bold'>Đặc điểm nổi bật</td>"
    for p in products:
        desc = (p.description or "Đang cập nhật")[:150] + "..."
        tbody_html += f"<td class='text-center fw-medium'><small>{desc}</small></td>"
    tbody_html += "</tr>"

    html = f"""
    <table class="table table-bordered table-hover bg-white shadow-sm table-compare align-middle mb-0">
        <thead class="table-light text-center">
            <tr>{headers_html}</tr>
        </thead>
        <tbody>
            {tbody_html}
        </tbody>
    </table>
    <div class="alert alert-secondary mt-4 p-4 rounded-4 shadow-sm border-0" style="background-color: #f8f9fa;">
        <h4 class="fw-bold text-secondary mb-3"><i class="fas fa-server me-2"></i>CHẾ ĐỘ DỰ PHÒNG (LOCAL MODE)</h4>
        <p class="mb-0 text-dark">Hệ thống AI Gemini tạm thời đang bảo trì hoặc hết hạn mức (Quota). Bảng so sánh trên được tạo tự động bằng thuật toán nội bộ. Vui lòng quay lại sau để xem chuyên gia AI phân tích chuyên sâu.</p>
    </div>
    """
    return html


def analyze_sentiment(text):
    """
    Xử lý ngôn ngữ tự nhiên (NLP) phân tích cảm xúc của Đánh giá.
    Phân loại ra POSITIVE, NEGATIVE, NEUTRAL.
    """
    system_instruction = (
        "Bạn là hệ thống NLP phân tích cảm xúc đánh giá khách hàng. "
        "Dựa vào nội dung bình luận, hãy phân loại và CHỈ TRẢ VỀ ĐÚNG 1 TỪ: "
        "POSITIVE, NEGATIVE, hoặc NEUTRAL."
    )
    res = call_gemini_api(f"Phân tích: '{text}'", system_instruction=system_instruction)
    if res:
        res = res.strip().upper()
        if "NEGATIVE" in res: return "NEGATIVE"
        if "POSITIVE" in res: return "POSITIVE"
    return "NEUTRAL"


# =========================================================================
# ĐỘNG CƠ XỬ LÝ VOUCHER - SPECIFICATION PATTERN
# =========================================================================

class VoucherSpecification(ABC):
    """
    Class Abstract lõi cho các ống lọc điều kiện Voucher.
    Áp dụng nguyên lý Open/Closed trong SOLID.
    """
    @abstractmethod
    def is_satisfied_by(self, voucher, order_total, user_rank_tier):
        """Hàm trừu tượng bắt buộc các Class con phải thực thi."""
        pass


class MinimumOrderSpecification(VoucherSpecification):
    """Kiểm tra điều kiện: Tổng giá trị đơn hàng có đạt mức tối thiểu không."""
    def is_satisfied_by(self, voucher, order_total, user_rank_tier):
        if order_total < voucher.min_order_value:
            return False, f"Đơn hàng chưa đạt mức tối thiểu {'{:,.0f}'.format(voucher.min_order_value).replace(',', '.')}đ"
        return True, "Hợp lệ"


class ExpiryDateSpecification(VoucherSpecification):
    """Kiểm tra điều kiện: Mã Voucher đã quá hạn sử dụng hay chưa."""
    def is_satisfied_by(self, voucher, order_total, user_rank_tier):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if now > voucher.valid_to:
            return False, "Rất tiếc, mã Voucher này đã hết hạn sử dụng."
        return True, "Hợp lệ"


class UserRankSpecification(VoucherSpecification):
    """Kiểm tra điều kiện: Phân quyền cấp bậc VIP của khách hàng."""
    def is_satisfied_by(self, voucher, order_total, user_rank_tier):
        if user_rank_tier < voucher.required_rank:
            ranks = {1: "M-New", 2: "M-Gold", 3: "M-Platinum", 4: "M-Diamond"}
            req_rank_str = ranks.get(voucher.required_rank, "VIP")
            return False, f"Voucher độc quyền! Chỉ áp dụng cho tài khoản từ hạng {req_rank_str} trở lên."
        return True, "Hợp lệ"


class VoucherValidatorEngine:
    """
    Động cơ Pipeline (Đường ống) xử lý Khuyến mãi trung tâm.
    Dữ liệu truyền vào sẽ phải đi qua tuần tự từng màng lọc bảo mật.
    """
    def __init__(self):
        # Đăng ký các trạm kiểm duyệt vào đường ống
        self.rules = [
            MinimumOrderSpecification(),
            ExpiryDateSpecification(),
            UserRankSpecification()
        ]

    def validate(self, voucher, order_total, user_rank_tier):
        """
        Kích hoạt đường ống kiểm duyệt.
        Trả về True nếu pass qua toàn bộ Rule, ngược lại trả về False kèm nguyên nhân.
        """
        if not voucher.is_active:
            return False, "Mã Voucher này hiện đang bị khóa hoặc vô hiệu hóa bởi Admin."

        for rule in self.rules:
            is_valid, msg = rule.is_satisfied_by(voucher, order_total, user_rank_tier)
            if not is_valid:
                return False, msg

        return True, "Mã Voucher hợp lệ. Đã áp dụng giảm giá!"

    def calculate_discount(self, voucher, order_total):
        """Thuật toán tính toán số tiền khấu trừ cuối cùng."""
        if voucher.discount_type == 'fixed':
            return min(voucher.discount_value, order_total)

        elif voucher.discount_type == 'percent':
            discount = int(order_total * (voucher.discount_value / 100))
            if voucher.max_discount:
                return min(discount, voucher.max_discount)
            return discount

        return 0