import os
import json
import re
import requests
import chromadb
import google.generativeai as genai
from chromadb.utils import embedding_functions
from flask import url_for
from itsdangerous import URLSafeTimedSerializer

### ---> [ĐÃ SỬA CHỖ NÀY: Tắt cảnh báo Telemetry của ChromaDB] <--- ###
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# --- [NEW] CẤU HÌNH TRUE RAG (VECTOR DB) ---
# Sử dụng Google Generative AI Embeddings
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Khởi tạo ChromaDB (Lưu file local tại thư mục chroma_db)
# PersistentClient giúp dữ liệu không bị mất khi restart server
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
except Exception as e:
    print(f"⚠️ ChromaDB Init Warning: {e}")
    chroma_client = None


# Hàm tạo Embedding dùng Gemini (Wrapper cho ChromaDB)
class GeminiEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __call__(self, input: list[str]) -> list[list[float]]:
        model = 'models/text-embedding-004'
        embeddings = []
        for text in input:
            try:
                # Gọi API Google để lấy vector (768 chiều)
                res = genai.embed_content(model=model, content=text, task_type="retrieval_document")
                embeddings.append(res['embedding'])
            except Exception as e:
                print(f"❌ Embedding API Error (Quota?): {e}")
                raise ValueError("API Hết Quota hoặc Lỗi")
        return embeddings


# Tạo hoặc lấy Collection (Bảng lưu vector)
try:
    if chroma_client and GEMINI_API_KEY:
        product_collection = chroma_client.get_or_create_collection(
            name="mobile_store_products",
            embedding_function=GeminiEmbeddingFunction()
        )
    else:
        product_collection = None
except Exception as e:
    print(f"⚠️ ChromaDB Collection Error: {e}")
    product_collection = None


# ---------------------------------------------------------

def validate_image_file(file):
    """
    Kiểm tra tính hợp lệ của file ảnh tải lên.
    Xác minh phần mở rộng (JPG, PNG, WEBP) và dung lượng (<2MB) để ngăn chặn mã độc.
    """
    if file.filename == '': return False, "Chưa chọn file."
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
        return False, "Chỉ nhận: JPG, PNG, WEBP."
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 2 * 1024 * 1024: return False, "File > 2MB."
    return True, None


def get_serializer(secret_key):
    """
    Khởi tạo đối tượng mã hóa chuỗi (Serializer).
    Dùng để tạo các mã Token bảo mật có thời hạn (như Reset Password).
    """
    return URLSafeTimedSerializer(secret_key)


def send_reset_email_simulation(to_email, token):
    """
    Giả lập quá trình gửi Email khôi phục mật khẩu.
    Sẽ in thẳng đường link (chứa token) ra màn hình Console để Dev dễ dàng Test.
    """
    link = url_for('auth.reset_password', token=token, _external=True)
    print(f"EMAIL MOCK: {link}")
    return link


# --- VECTOR SEARCH FUNCTIONS ---

def search_vector_db(query_text, n_results=5, metadata_filters=None):
    """
    Tìm kiếm bằng Vector Database CÓ KẾT HỢP BỘ LỌC (Metadata Filtering).
    """
    if not product_collection or not GEMINI_API_KEY:
        return []

    try:
        query_params = {
            "query_texts": [query_text],
            "n_results": n_results
        }

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
    Đồng bộ thông tin sản phẩm mới/cập nhật từ SQLite sang ChromaDB.
    Chuyển đổi văn bản miêu tả thành Vector nhúng (Embeddings) để phục vụ cho Semantic Search.
    """
    if not product_collection: return

    semantic_text = f"Sản phẩm: {product.name}. Hãng: {product.brand}. Loại: {product.category}. Mô tả chi tiết: {product.description}. Mức giá khoảng: {product.price} đồng."

    try:
        product_collection.upsert(
            documents=[semantic_text],
            metadatas=[{
                "price": product.price,
                "brand": product.brand,
                "category": product.category
            }],
            ids=[str(product.id)]
        )
        print(f"✅ Indexed Vector: {product.name}")
    except Exception as e:
        print(f"Sync Vector Error: {e}")


# --- AI CORE FUNCTIONS ---

def call_gemini_api(prompt, system_instruction=None):
    """
    Hàm lõi giao tiếp trực tiếp với Google Gemini API.
    Bao gồm việc gắn System Instruction để ép khuôn tính cách và xử lý lỗi kết nối.
    """
    if not GEMINI_API_KEY: return None
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

### ---> [ĐÃ SỬA CHỖ NÀY: BỔ SUNG LÕI TÌM KIẾM TEXT-RAG ĐỂ VƯỢT QUA LỖI VECTOR 404] <--- ###
def direct_gemini_search(query, catalog_json):
    """
    Dùng mô hình Text (đang hoạt động tốt) đọc toàn bộ kho hàng và nhặt ID ra.
    Khắc phục triệt để lỗi Embedding 404.
    """
    if not GEMINI_API_KEY: return []

    system_instruction = (
        "Bạn là trí tuệ nhân tạo lõi của MobileStore. "
        "Dựa vào yêu cầu của khách và danh sách kho hàng (JSON), "
        "hãy phân tích ngữ nghĩa (VD: 'củ/quy đầu' = triệu, 'pin trâu' = pin lớn, 'chụp đêm' = camera xịn, 'chơi game' = chip mạnh) "
        "và lọc ra đúng các ID sản phẩm phù hợp nhất với nhu cầu."
        "BẮT BUỘC TRẢ VỀ CHỈ MỘT MẢNG JSON CÁC SỐ NGUYÊN LÀ ID. Ví dụ: [1, 5, 12]. Tuyệt đối không viết thêm chữ gì khác."
    )
    prompt = f"Yêu cầu tìm kiếm của khách: '{query}'\n\nKho hàng hiện tại:\n{catalog_json}\n\nTrả về mảng JSON ID:"

    res = call_gemini_api(prompt, system_instruction)
    if not res: return []

    try:
        clean = re.sub(r"```json|```", "", res).strip()
        match = re.search(r"\[.*\]", clean, re.DOTALL)
        if match:
            ids = json.loads(match.group(0))
            return [int(i) for i in ids]
        return []
    except Exception as e:
        print(f"Direct AI Search Parse Error: {e}")
        return []


def build_product_context(user_query):
    """
    Thu thập tự động dữ liệu kho hàng xung quanh chủ đề mà người dùng đang hỏi (RAG).
    Nạp dữ liệu này làm "Ngữ cảnh - Context" để Chatbot trả lời thông minh không bị ảo giác.
    """
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

    context_text = "--- KHO HÀNG THỰC TẾ (Đã lọc theo nhu cầu) ---\n"
    for p in products:
        price = "{:,.0f} đ".format(p.sale_price if p.is_sale else p.price).replace(",", ".")
        status = f"Sẵn hàng ({p.stock_quantity})" if p.stock_quantity > 0 else "Hết hàng"
        desc_short = (p.description or "")[:150].replace('\n', ' ')
        context_text += f"- ID:{p.id} | {p.name} ({p.brand}) | Giá: {price} | Tình trạng: {status}\n"
        context_text += f"  Chi tiết: {desc_short}...\n"

    return context_text


def generate_chatbot_response(user_msg, chat_history=[]):
    """
    Module xử lý lõi của AI Tư vấn bán hàng.
    Được tích hợp bộ nhớ Session để hiểu các đại từ nhân xưng (Nó, Cái đó) từ lịch sử chat.
    """
    product_context = build_product_context(user_msg)

    history_text = ""
    if chat_history:
        history_text = "\n--- LỊCH SỬ HỘI THOẠI ---\n"
        for turn in chat_history:
            history_text += f"User: {turn['user']}\nAI: {turn['ai']}\n"

    system_instruction = (
        "Bạn là Chuyên gia tư vấn công nghệ AI của MobileStore. "
        "Hãy tư vấn dựa trên danh sách 'KHO HÀNG THỰC TẾ' được cung cấp. "
        "Nếu sản phẩm khách hỏi không có trong kho (context), hãy lịch sự báo hết hàng và gợi ý sản phẩm tương tự trong danh sách."
    )

    final_prompt = f"{history_text}\nKhách hàng hỏi: '{user_msg}'\n\n{product_context}\n\nAI trả lời:"

    return call_gemini_api(final_prompt, system_instruction)


def analyze_search_intents(query):
    """
    Hệ thống trích xuất dữ liệu (Entity Extraction) bằng LLM.
    Bóc tách câu nói tự nhiên của người dùng thành cấu trúc JSON chuẩn mực gồm (Brand, Price, Category).
    """
    system_instruction = """
    Bạn là hệ thống trích xuất dữ liệu tìm kiếm cho Website bán điện thoại MobileStore.
    Nhiệm vụ: Phân tích câu hỏi của khách và trả về CHỈ MỘT chuỗi JSON hợp lệ. Không giải thích thêm.

    Quy tắc:
    1. Giá: 'triệu' hoặc 'củ' = 1,000,000. 'trăm' = 100,000.
    2. Category: 
       - BẮT BUỘC ĐIỀN 'accessory' nếu truy vấn chứa: ốp, sạc, tai nghe, cáp, kính, cường lực, giá đỡ, loa, dây đeo, airpods, buds...
       - BẮT BUỘC ĐIỀN 'phone' nếu truy vấn là tên dòng máy (ví dụ: 'iphone 15', 's24 ultra', 'redmi note 13') hoặc chứa từ 'điện thoại', 'máy'.
       - KHÔNG được nhầm lẫn. Ví dụ: "ốp lưng iphone 15" -> accessory. "iphone 15" -> phone.

    Định dạng JSON yêu cầu (Nếu không xác định được, để null):
    {
        "brand": "Apple, Samsung, Xiaomi, Oppo, Vivo, Asus, Google, Realme...",
        "category": "phone hoặc accessory",
        "min_price": Số nguyên,
        "max_price": Số nguyên,
        "keyword": "Từ khóa chính (Bỏ các từ: tìm, mua, điện thoại, giá rẻ...)",
        "sort": "price_asc hoặc price_desc hoặc null"
    }

    === VÍ DỤ MẪU ===
    Input: "ốp lưng iphone 15 pro max"
    Output: {"brand": "Apple", "category": "accessory", "min_price": null, "max_price": null, "keyword": "ốp lưng iphone 15 pro max", "sort": null}

    Input: "tìm s24 ultra"
    Output: {"brand": "Samsung", "category": "phone", "min_price": null, "max_price": null, "keyword": "s24 ultra", "sort": null}

    Input: "cáp sạc"
    Output: {"brand": null, "category": "accessory", "min_price": null, "max_price": null, "keyword": "cáp sạc", "sort": null}
    """

    prompt = f"Câu hỏi của khách: '{query}'\n\nTrả về JSON:"
    res = call_gemini_api(prompt, system_instruction=system_instruction)
    if not res: return None

    try:
        clean = re.sub(r"```json|```", "", res).strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"AI Parse JSON Error: {e} - Raw text: {res}")
        return None


def local_analyze_intent(query):
    """
    Thuật toán Fallback dự phòng (Offline Mode).
    Sử dụng Regex kết hợp Python thuần để đọc hiểu ý định nếu như API của Google AI bị sập.
    """
    query = query.lower()
    data = {'brand': None, 'category': None, 'keyword': '', 'min_price': None, 'max_price': None, 'sort': None}

    brands = {'iphone': 'Apple', 'apple': 'Apple', 'samsung': 'Samsung', 'oppo': 'Oppo', 'xiaomi': 'Xiaomi',
              'vivo': 'Vivo'}
    for k, v in brands.items():
        if k in query:
            data['brand'] = v
            query = query.replace(k, '')

    accessory_kws = ['ốp', 'sạc', 'tai nghe', 'cáp', 'kính', 'cường lực', 'giá đỡ', 'loa', 'dây đeo', 'airpods']
    phone_kws = ['điện thoại', 'máy', 'smartphone', 'phone']
    if any(x in query for x in accessory_kws):
        data['category'] = 'accessory'
    elif any(x in query for x in phone_kws):
        data['category'] = 'phone'

    price_match = re.search(r'(\d+)\s*(triệu|củ)', query)
    if price_match:
        val = int(price_match.group(1))
        if val < 1000: data['max_price'] = val * 1000000
        query = re.sub(r'\d+\s*(triệu|củ)', '', query)

    stop_words = ['tôi', 'muốn', 'mua', 'tìm', 'cho', 'cần', 'dưới', 'khoảng', 'điện', 'thoại', 'máy', 'tốt', 'đẹp',
                  'giá', 'chơi', 'game', 'chụp', 'ảnh', 'rẻ']
    words = query.split()
    kw_words = [w for w in words if w not in stop_words]

    data['keyword'] = " ".join(kw_words).strip()
    return data


def get_comparison_result(p1_name, p1_price, p1_desc, p2_name, p2_price, p2_desc):
    """
    Sử dụng AI tạo bảng HTML đối chiếu trực tiếp thông số 2 sản phẩm.
    Đưa ra lời khuyên khách quan (Pros/Cons) hỗ trợ người dùng ra quyết định mua hàng.
    """
    system_instruction = (
        "Bạn là chuyên gia bán hàng công nghệ cấp cao. "
        "Nhiệm vụ của bạn là so sánh thông số, sau đó BẮT BUỘC phải đưa ra lời khuyên "
        "để khách hàng biết mình nên chọn máy nào."
    )

    prompt = f"""
    Hãy tạo mã HTML so sánh 2 sản phẩm:
    1. {p1_name} (Giá: {p1_price}) - Thông tin: {p1_desc}
    2. {p2_name} (Giá: {p2_price}) - Thông tin: {p2_desc}

    LƯU Ý QUAN TRỌNG: 
    Nếu phần "Thông tin cung cấp" bên trên bị thiếu thông số, hãy SỬ DỤNG KIẾN THỨC CỦA BẠN về 2 dòng điện thoại này để điền bổ sung cho đầy đủ và chính xác nhất. Không được để trống quá nhiều.

    Yêu cầu ĐỊNH DẠNG HTML BẮT BUỘC:
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

    - Bước 2: Dưới bảng, thêm một thẻ `<div class="alert alert-info mt-4" style="border-radius: 10px;">`.
    - Trong thẻ div này, tạo tiêu đề `<h5 class="fw-bold text-primary">💡 TƯ VẤN TỪ CHUYÊN GIA AI</h5>`.
    - Viết 1-2 đoạn văn phân tích chuyên sâu về sự khác biệt lớn nhất giữa 2 máy.
    - Thêm danh sách `<ul>` chỉ rõ:
      + <li>Nên mua <b>{p1_name}</b> nếu bạn...</li>
      + <li>Nên mua <b>{p2_name}</b> nếu bạn...</li>

    CHỈ TRẢ VỀ MÃ HTML CỦA BẢNG VÀ PHẦN TƯ VẤN, KHÔNG GIẢI THÍCH THÊM BẤT CỨ ĐIỀU GÌ.
    """

    res = call_gemini_api(prompt, system_instruction=system_instruction)
    return re.sub(r"```html|```", "", res).strip() if res else None


def analyze_sentiment(text):
    """
    Sử dụng AI phân tích cảm xúc của đoạn đánh giá.
    Chỉ trả về 1 trong 3 trạng thái: POSITIVE, NEGATIVE, NEUTRAL.
    """
    system_instruction = (
        "Bạn là hệ thống NLP phân tích cảm xúc đánh giá khách hàng về điện thoại/phụ kiện. "
        "Dựa vào nội dung bình luận, hãy phân loại và CHỈ TRẢ VỀ ĐÚNG 1 TỪ DUY NHẤT bằng tiếng Anh: "
        "POSITIVE (khen ngợi, tốt), NEGATIVE (chê bai, máy lỗi, giật lag, thái độ tệ), hoặc NEUTRAL (bình thường, trung lập)."
    )
    prompt = f"Phân tích bình luận sau: '{text}'"

    res = call_gemini_api(prompt, system_instruction=system_instruction)
    if res:
        res = res.strip().upper()
        if "NEGATIVE" in res: return "NEGATIVE"
        if "POSITIVE" in res: return "POSITIVE"
    return "NEUTRAL"