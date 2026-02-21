import os
import json
import re
import requests
import chromadb
import google.generativeai as genai
from chromadb.utils import embedding_functions
from flask import url_for
from itsdangerous import URLSafeTimedSerializer

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
        model = 'models/embedding-001'
        embeddings = []
        for text in input:
            try:
                # Gọi API Google để lấy vector (768 chiều)
                res = genai.embed_content(model=model, content=text, task_type="retrieval_document")
                embeddings.append(res['embedding'])
            except:
                # Fallback vector rỗng nếu lỗi (để không crash app)
                embeddings.append([0.0] * 768)
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
    if file.filename == '': return False, "Chưa chọn file."
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
        return False, "Chỉ nhận: JPG, PNG, WEBP."
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 2 * 1024 * 1024: return False, "File > 2MB."
    return True, None


def get_serializer(secret_key):
    return URLSafeTimedSerializer(secret_key)


def send_reset_email_simulation(to_email, token):
    link = url_for('auth.reset_password', token=token, _external=True)
    print(f"EMAIL MOCK: {link}")
    return link


# --- [NEW] VECTOR SEARCH FUNCTIONS ---

def search_vector_db(query_text, n_results=5):
    """
    Tìm kiếm ngữ nghĩa bằng Vector Database.
    Input: Câu hỏi tự nhiên (VD: 'máy nào chụp ảnh đẹp')
    Output: Danh sách ID sản phẩm phù hợp nhất.
    """
    if not product_collection or not GEMINI_API_KEY:
        return []

    try:
        results = product_collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        # Chroma trả về dict of lists, cần lấy list IDs đầu tiên
        # results['ids'][0] chứa danh sách ID tìm thấy
        found_ids = results['ids'][0]
        return found_ids  # Trả về list ID (dạng string)
    except Exception as e:
        print(f"Vector Search Error: {e}")
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


# --- AI CORE FUNCTIONS (UPDATED) ---

def call_gemini_api(prompt, system_instruction=None):
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


def build_product_context(user_query):
    """
    TRUE RAG FLOW:
    1. Vector Search (Tìm ý hiểu)
    2. Fallback Keyword Search (Tìm chính xác)
    3. Query DB lấy dữ liệu realtime (Tồn kho, Giá mới)
    """
    from app.models import Product

    # Bước 1: Tìm ID sản phẩm bằng Vector Search (Semantic)
    # Ví dụ: "máy pin trâu" -> Vector DB trả về ID của Samsung M34, iPhone 15 Plus
    vector_ids = search_vector_db(user_query)

    products = []
    if vector_ids:
        # Chuyển ID string về int để query SQL
        ids = [int(i) for i in vector_ids if i.isdigit()]
        # Fetch từ DB để đảm bảo lấy đúng Tồn kho/Giá hiện tại (tránh dữ liệu vector bị cũ)
        products = Product.query.filter(Product.id.in_(ids), Product.is_active == True).all()

    # Bước 2: Fallback - Nếu Vector không ra, dùng tìm kiếm từ khóa LIKE (SQL)
    if not products:
        user_query_lower = user_query.lower()
        products = Product.query.filter(
            Product.name.ilike(f"%{user_query_lower}%"),
            Product.is_active == True
        ).limit(3).all()

    if not products:
        return "Hiện tại hệ thống không tìm thấy sản phẩm nào phù hợp trong kho."

    # Bước 3: Format dữ liệu để trả về cho AI (Context Window)
    context_text = "--- KHO HÀNG THỰC TẾ (Đã lọc theo nhu cầu) ---\n"
    for p in products:
        price = "{:,.0f} đ".format(p.sale_price if p.is_sale else p.price).replace(",", ".")
        status = f"Sẵn hàng ({p.stock_quantity})" if p.stock_quantity > 0 else "Hết hàng"

        # Chỉ lấy 150 ký tự mô tả để tiết kiệm token
        desc_short = (p.description or "")[:150].replace('\n', ' ')

        context_text += f"- ID:{p.id} | {p.name} ({p.brand}) | Giá: {price} | Tình trạng: {status}\n"
        context_text += f"  Chi tiết: {desc_short}...\n"

    return context_text


def generate_chatbot_response(user_msg, chat_history=[]):
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
    system_instruction = """
    Bạn là hệ thống trích xuất dữ liệu tìm kiếm cho Website bán điện thoại MobileStore.
    Nhiệm vụ: Phân tích câu hỏi của khách và trả về CHỈ MỘT chuỗi JSON hợp lệ. Không giải thích thêm.

    Quy tắc quy đổi tiền: 'triệu' hoặc 'củ' = 1,000,000 VNĐ. 'trăm' = 100,000 VNĐ.

    Định dạng JSON yêu cầu (Nếu không xác định được trường nào thì để giá trị là null):
    {
        "brand": "Tên hãng viết hoa chữ đầu (ví dụ: Apple, Samsung, Xiaomi, Oppo, Vivo...)",
        "category": "Điền 'phone' nếu tìm điện thoại. Điền 'accessory' nếu tìm ốp lưng, sạc, cáp, tai nghe.",
        "min_price": Số nguyên (ví dụ: 5000000),
        "max_price": Số nguyên (ví dụ: 10000000),
        "keyword": "Đặc điểm kỹ thuật hoặc dòng máy (ví dụ: 'pro max', 'pin', 'camera'). KHÔNG lấy nguyên văn từ lóng như 'pin trâu', 'chụp ảnh đẹp' mà hãy dịch thành thuật ngữ 'pin', 'camera'.",
        "sort": "Điền 'price_asc' nếu muốn tìm rẻ nhất. Điền 'price_desc' nếu muốn tìm đắt nhất/cao cấp nhất."
    }

    === VÍ DỤ MẪU ===
    Input: "tìm điện thoại samsung dưới 10 củ pin trâu"
    Output: {"brand": "Samsung", "category": "phone", "min_price": null, "max_price": 10000000, "keyword": "pin", "sort": null}

    Input: "ốp lưng iphone rẻ nhất"
    Output: {"brand": "Apple", "category": "accessory", "min_price": null, "max_price": null, "keyword": "ốp lưng", "sort": "price_asc"}

    Input: "điện thoại tầm 5 đến 7 triệu chụp ảnh đẹp"
    Output: {"brand": null, "category": "phone", "min_price": 5000000, "max_price": 7000000, "keyword": "camera", "sort": null}
    """

    prompt = f"Câu hỏi của khách: '{query}'\n\nTrả về JSON:"

    # Truyền system_instruction vào API
    res = call_gemini_api(prompt, system_instruction=system_instruction)
    if not res: return None

    try:
        # Làm sạch kết quả trả về để đảm bảo parse được JSON
        clean = re.sub(r"```json|```", "", res).strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"AI Parse JSON Error: {e} - Raw text: {res}")
        return None


def local_analyze_intent(query):
    # Hàm này vẫn giữ nguyên như phiên bản cũ để làm fallback
    query = query.lower()
    data = {'brand': None, 'category': None, 'keyword': query, 'min_price': None, 'max_price': None, 'sort': None}
    brands = {'iphone': 'Apple', 'samsung': 'Samsung', 'oppo': 'Oppo', 'xiaomi': 'Xiaomi'}
    for k, v in brands.items():
        if k in query: data['brand'] = v
    if any(x in query for x in ['ốp', 'sạc', 'tai nghe']):
        data['category'] = 'accessory'
    elif any(x in query for x in ['điện thoại', 'máy']):
        data['category'] = 'phone'
    if 'dưới' in query and 'triệu' in query:
        nums = re.findall(r'\d+', query)
        if nums: data['max_price'] = int(nums[0]) * 1000000
    return data


def get_comparison_result(p1_name, p1_price, p1_desc, p2_name, p2_price, p2_desc):
    prompt = f"Tạo bảng HTML so sánh chi tiết: {p1_name} ({p1_price}) vs {p2_name} ({p2_price}). Chỉ trả về code HTML."
    res = call_gemini_api(prompt)
    return re.sub(r"```html|```", "", res).strip() if res else None