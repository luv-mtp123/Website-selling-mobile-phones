import os
import json
import re
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
        """Hàm sinh Vector nhúng sử dụng model Google mới nhất."""
        model = 'models/text-embedding-004'
        embeddings = []
        for text in input:
            try:
                # Gọi API Google để lấy vector (768 chiều)
                res = genai.embed_content(model=model, content=text, task_type="retrieval_document")
                embeddings.append(res['embedding'])
            except Exception as e:
                ### ---> [ĐÃ SỬA CHỖ NÀY: Bắt lỗi API Hết Quota để không tạo Vector rác, giúp App nhảy qua SQL an toàn] <--- ###
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


# --- [NEW] VECTOR SEARCH FUNCTIONS ---

def search_vector_db(query_text, n_results=5, metadata_filters=None):
    """
    Tìm kiếm bằng Vector Database CÓ KẾT HỢP BỘ LỌC (Metadata Filtering).
    metadata_filters format ChromaDB: {"category": "phone"} hoặc {"$and": [{"category": "phone"}, {"brand": "Apple"}]}
    """
    if not product_collection or not GEMINI_API_KEY:
        return []

    try:
        query_params = {
            "query_texts": [query_text],
            "n_results": n_results
        }

        # Thêm bộ lọc nếu có để ép VectorDB không bị nhầm lẫn ĐT và Phụ kiện
        if metadata_filters:
            query_params["where"] = metadata_filters

        results = product_collection.query(**query_params)

        if results['ids'] and len(results['ids']) > 0:
            return results['ids'][0]
        return []
    except Exception as e:
        ### ---> [ĐÃ SỬA CHỖ NÀY: Nếu gọi Vector lỗi do hết API, in log và trả về rỗng để kích hoạt SQL Fallback] <--- ###
        print(f"⚠️ Vector Search Skipped: {e}")
        return []


def sync_product_to_vector_db(product):
    """
    Đồng bộ 1 sản phẩm vào Vector DB.
    Cần gọi hàm này khi Add/Edit sản phẩm trong Admin.
    """
    if not product_collection: return

    # Tạo nội dung ngữ nghĩa phong phú (Rich Semantic Content)
    # Kết hợp Tên, Hãng, Loại, Mô tả và Giá để AI hiểu toàn diện
    semantic_text = f"Sản phẩm: {product.name}. Hãng: {product.brand}. Loại: {product.category}. Mô tả chi tiết: {product.description}. Mức giá khoảng: {product.price} đồng."

    # Upsert (Update hoặc Insert) vào ChromaDB
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


# =========================================================================
# ---> [NEW ALGORITHM: THUẬT TOÁN ĐIỂM TƯƠNG ĐỒNG SẢN PHẨM] <---
# =========================================================================
def get_similar_products(current_product, limit=4):
    """
    Thuật toán Gợi ý Sản phẩm Tương tự (Content-Based Filtering Local).
    Chạy nội bộ 100% bằng toán học và logic, không phụ thuộc vào AI bên ngoài.

    Quy tắc chấm điểm (Scoring):
    - Cùng danh mục (Bắt buộc lọc từ đầu).
    - Cùng hãng (Brand): +50 điểm (Ưu tiên cao nhất).
    - Khoảng giá (Price): +10 đến +30 điểm (Giá càng sát điểm càng cao).
    - Tên sản phẩm: +5 điểm cho mỗi từ khóa trùng lặp.
    """
    from app.models import Product

    # 1. Lọc các ứng viên tiềm năng (Cùng loại, đang mở bán, trừ máy hiện tại)
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

    # 2. Vòng lặp chấm điểm tương đồng
    for p in candidates:
        score = 0
        candidate_price = p.sale_price if p.is_sale else p.price

        # Tiêu chí 1: Cùng hãng (Brand Match)
        if p.brand.lower() == current_product.brand.lower():
            score += 50

        # Tiêu chí 2: Độ lệch giá (Price Proximity)
        max_price = max(target_price, 1)
        price_diff_ratio = abs(candidate_price - target_price) / max_price

        if price_diff_ratio <= 0.1:  # Lệch giá dưới 10%
            score += 30
        elif price_diff_ratio <= 0.2:  # Lệch giá dưới 20%
            score += 20
        elif price_diff_ratio <= 0.3:  # Lệch giá dưới 30%
            score += 10

        # Tiêu chí 3: Trùng lặp từ khóa tên (Keyword Overlap)
        candidate_words = set(p.name.lower().split())
        common_words = target_words.intersection(candidate_words)
        score += len(common_words) * 5

        scored_products.append((score, p))

    # 3. Sắp xếp theo điểm số giảm dần
    scored_products.sort(key=lambda x: x[0], reverse=True)

    # 4. Trích xuất ra danh sách object (Bỏ điểm số đi)
    similar_products = [item[1] for item in scored_products[:limit]]

    return similar_products


# =========================================================================


# --- AI CORE FUNCTIONS (UPDATED) ---

def call_gemini_api(prompt, system_instruction=None):
    """
    Hàm lõi giao tiếp trực tiếp với Google Gemini API.
    Bao gồm việc gắn System Instruction để ép khuôn tính cách và xử lý lỗi kết nối.
    """
    if not GEMINI_API_KEY: return None
    # Dùng SDK Google Generative AI thay vì requests thủ công
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
    # Sử dụng intent parsing để lấy category trước khi search DB
    ai_data = local_analyze_intent(user_query)
    filter_dict = {}
    if ai_data and ai_data.get('category'):
        filter_dict["category"] = ai_data['category']

    # Vector search có lọc category
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
    # [UPDATED] Context giờ đây được lấy thông minh hơn nhờ Vector Search
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


# [FIXED & UPGRADED] Cải thiện hàm phân tích ý định tìm kiếm
def analyze_search_intents(query):
    """
    Hệ thống trích xuất dữ liệu (Entity Extraction) bằng LLM.
    Bóc tách câu nói tự nhiên của người dùng thành cấu trúc JSON chuẩn mực gồm (Brand, Price, Category).
    """
    # Cập nhật Prompt khắt khe hơn để phân biệt Điện thoại và Phụ kiện
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

    # 1. Tách Brand
    brands = {'iphone': 'Apple', 'apple': 'Apple', 'samsung': 'Samsung', 'oppo': 'Oppo', 'xiaomi': 'Xiaomi',
              'vivo': 'Vivo'}
    for k, v in brands.items():
        if k in query:
            data['brand'] = v
            query = query.replace(k, '')  # Gỡ tên hãng khỏi query để làm sạch

    # 2. Phân loại Category
    accessory_kws = ['ốp', 'sạc', 'tai nghe', 'cáp', 'kính', 'cường lực', 'giá đỡ', 'loa', 'dây đeo', 'airpods']
    phone_kws = ['điện thoại', 'máy', 'smartphone', 'phone']
    if any(x in query for x in accessory_kws):
        data['category'] = 'accessory'
    elif any(x in query for x in phone_kws):
        data['category'] = 'phone'

    # 3. Tách Giá (Price) và gỡ chữ ra khỏi query
    ### ---> [ĐÃ SỬA CHỖ NÀY: Bắt giá tiền thông minh hơn, không cần phải gõ chữ "dưới", lấy thẳng con số gắn với triệu/củ] <--- ###
    price_match = re.search(r'(\d+)\s*(triệu|củ)', query)
    if price_match:
        val = int(price_match.group(1))
        if val < 1000: data['max_price'] = val * 1000000
        query = re.sub(r'\d+\s*(triệu|củ)', '', query)  # Xóa phần giá khỏi text

    # 4. Làm sạch Keyword (Loại bỏ toàn bộ stop_words đàm thoại để Database đọc được chữ chính)
    stop_words = ['tôi', 'muốn', 'mua', 'tìm', 'cho', 'cần', 'dưới', 'khoảng', 'điện', 'thoại', 'máy', 'tốt', 'đẹp',
                  'giá', 'chơi', 'game', 'chụp', 'ảnh', 'rẻ']
    words = query.split()
    kw_words = [w for w in words if w not in stop_words]

    data['keyword'] = " ".join(kw_words).strip()
    return data


# ==============================================================================================
# ---> [ĐÃ SỬA CHỖ NÀY: Nâng cấp System Instruction ép buộc AI phân tích sâu sắc cho TỪNG máy] <---
# ==============================================================================================
def get_comparison_result(p1_id, p1_name, p1_price, p1_desc, p1_img,
                          p2_id, p2_name, p2_price, p2_desc, p2_img,
                          p3_id=None, p3_name=None, p3_price=None, p3_desc=None, p3_img=None,
                          p4_id=None, p4_name=None, p4_price=None, p4_desc=None, p4_img=None):
    """
    Sử dụng AI tạo bảng HTML đối chiếu thông số đa sản phẩm (tối đa 4) theo cấu trúc chuẩn CellphoneS.
    Bảng có Header bám dính (Sticky Header) chứa Hình ảnh, Giá và Nút "Mua Ngay".
    Đưa ra lời khuyên khách quan (Pros/Cons) hỗ trợ người dùng ra quyết định.
    """
    system_instruction = (
        "Bạn là chuyên gia bán hàng công nghệ cấp cao kiêm Frontend Developer. "
        "Nhiệm vụ của bạn là sinh ra bảng so sánh HTML CỰC KỲ CHÍNH XÁC cấu trúc để render giao diện, "
        "sau đó BẮT BUỘC phải viết bài phân tích tư vấn RẤT CHUYÊN SÂU, CHI TIẾT bên dưới bảng."
    )

    products_info = f"Sản phẩm 1: ID={p1_id}, Tên={p1_name}, Giá={p1_price}, Ảnh={p1_img}, Cấu hình={p1_desc}\n"
    products_info += f"Sản phẩm 2: ID={p2_id}, Tên={p2_name}, Giá={p2_price}, Ảnh={p2_img}, Cấu hình={p2_desc}\n"

    num_cols = 2
    headers_html = f"""
         + `<th>` 1: `<h5 class="fw-bold text-danger mb-0">SO SÁNH</h5>` (width: 15%)
         + `<th>` 2: `<div class="text-center"><img src="{p1_img}" style="max-height:140px; object-fit:contain;" class="mb-2"><br><span class="fw-bold fs-6 text-dark">{p1_name}</span><br><span class="text-danger fw-bold fs-6">{p1_price}</span><br><form action="/cart/add/{p1_id}" method="POST" class="mt-2"><button type="submit" class="btn btn-danger btn-sm rounded-pill px-3 fw-bold shadow-sm">MUA NGAY</button></form></div>`
         + `<th>` 3: `<div class="text-center"><img src="{p2_img}" style="max-height:140px; object-fit:contain;" class="mb-2"><br><span class="fw-bold fs-6 text-dark">{p2_name}</span><br><span class="text-danger fw-bold fs-6">{p2_price}</span><br><form action="/cart/add/{p2_id}" method="POST" class="mt-2"><button type="submit" class="btn btn-danger btn-sm rounded-pill px-3 fw-bold shadow-sm">MUA NGAY</button></form></div>`"""

    # Tạo logic ép AI viết Lời khuyên động theo số lượng máy
    advice_html = f"""
    - Bước 4: Tạo phần tư vấn RẤT CHUYÊN SÂU dưới bảng bằng thẻ `<div class="alert alert-info mt-4 rounded-4 shadow-sm border-0 p-4">`.
       Bên trong div, tạo tiêu đề `<h5 class="fw-bold text-primary mb-3"><i class="fas fa-robot me-2"></i>TƯ VẤN CHUYÊN SÂU TỪ CHUYÊN GIA AI</h5>`.
       BẮT BUỘC viết 2-3 đoạn văn phân tích CHI TIẾT về điểm mạnh, điểm yếu, sự khác biệt cốt lõi (Camera, Hiệu năng, Pin, Thiết kế) giữa {num_cols} sản phẩm. Thể hiện bạn là chuyên gia công nghệ am hiểu sâu sắc.
       Cuối cùng, tạo danh sách `<ul>` với class `mt-3` chỉ rõ đối tượng phù hợp cho TỪNG MÁY:
         + `<li>Nên mua <b>{p1_name}</b> nếu bạn... (nêu rõ lý do)</li>`
         + `<li>Nên mua <b>{p2_name}</b> nếu bạn... (nêu rõ lý do)</li>`"""

    if p3_id:
        num_cols = 3
        products_info += f"Sản phẩm 3: ID={p3_id}, Tên={p3_name}, Giá={p3_price}, Ảnh={p3_img}, Cấu hình={p3_desc}\n"
        headers_html += f"""\n         + `<th>` 4: `<div class="text-center"><img src="{p3_img}" style="max-height:140px; object-fit:contain;" class="mb-2"><br><span class="fw-bold fs-6 text-dark">{p3_name}</span><br><span class="text-danger fw-bold fs-6">{p3_price}</span><br><form action="/cart/add/{p3_id}" method="POST" class="mt-2"><button type="submit" class="btn btn-danger btn-sm rounded-pill px-3 fw-bold shadow-sm">MUA NGAY</button></form></div>`"""
        advice_html += f"\n         + `<li>Nên mua <b>{p3_name}</b> nếu bạn... (nêu rõ lý do)</li>`"

    if p4_id:
        num_cols = 4
        products_info += f"Sản phẩm 4: ID={p4_id}, Tên={p4_name}, Giá={p4_price}, Ảnh={p4_img}, Cấu hình={p4_desc}\n"
        headers_html += f"""\n         + `<th>` 5: `<div class="text-center"><img src="{p4_img}" style="max-height:140px; object-fit:contain;" class="mb-2"><br><span class="fw-bold fs-6 text-dark">{p4_name}</span><br><span class="text-danger fw-bold fs-6">{p4_price}</span><br><form action="/cart/add/{p4_id}" method="POST" class="mt-2"><button type="submit" class="btn btn-danger btn-sm rounded-pill px-3 fw-bold shadow-sm">MUA NGAY</button></form></div>`"""
        advice_html += f"\n         + `<li>Nên mua <b>{p4_name}</b> nếu bạn... (nêu rõ lý do)</li>`"

    # Đóng thẻ div cho phần tư vấn
    advice_html += "\n       Đóng thẻ `</div>`."

    prompt = f"""
    Tạo mã HTML so sánh các sản phẩm phong cách CellphoneS:
    {products_info}

    Yêu cầu ĐỊNH DẠNG HTML BẮT BUỘC TỪNG DÒNG CHỮ:
    - Bước 1: Tạo bảng `<table class="table table-bordered table-striped table-compare align-middle">`
    - Bước 2: Tạo Header Bám dính: `<thead class="compare-thead bg-white">`
       Trong thead, tạo 1 thẻ `<tr>` chứa các thẻ `<th>`:
{headers_html}
    - Bước 3: Tạo `<tbody>`.
       Chia nhóm thông số bằng thẻ: `<tr class="table-light"><td colspan="{num_cols + 1}" class="fw-bold text-uppercase text-secondary ps-3 py-2">TÊN NHÓM</td></tr>` (Các nhóm: MÀN HÌNH, VI XỬ LÝ, BỘ NHỚ, CAMERA SAU, CAMERA TRƯỚC, PIN & SẠC, THIẾT KẾ).
       Liệt kê chi tiết từng dòng `<tr><td>Tên thông số</td><td class="text-center fw-medium">Giá trị 1</td><td class="text-center fw-medium">Giá trị 2</td>...</tr>`. Tự bổ sung kiến thức kỹ thuật nếu cấu hình bị thiếu.
{advice_html}

    CHỈ TRẢ VỀ HTML, KHÔNG KÈM TEXT HAY MARKDOWN BLOCK NÀO KHÁC.
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