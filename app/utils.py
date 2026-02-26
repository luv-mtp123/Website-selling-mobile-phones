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
import google.generativeai as genai
from chromadb.utils import embedding_functions
from flask import url_for
from itsdangerous import URLSafeTimedSerializer
from abc import ABC, abstractmethod
from datetime import datetime, timezone

# Tắt cảnh báo Telemetry của ChromaDB để giao diện Console sạch sẽ
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# --- CẤU HÌNH TRUE RAG (VECTOR DB) ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Khởi tạo ChromaDB (Lưu file local tại thư mục chroma_db)
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
except Exception as e:
    print(f"⚠️ ChromaDB Init Warning: {e}")
    chroma_client = None


class GeminiEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """
    Hàm sinh Vector nhúng (Embedding) sử dụng model Text-Embedding mới nhất của Google.
    Chuyển đổi ngôn ngữ tự nhiên thành mảng số thực đa chiều (768 chiều).
    """
    def __call__(self, input: list[str]) -> list[list[float]]:
        """Thực thi gọi API Google để lấy chuỗi Vector."""
        model = 'models/text-embedding-004'
        embeddings = []
        for text in input:
            try:
                res = genai.embed_content(model=model, content=text, task_type="retrieval_document")
                embeddings.append(res['embedding'])
            except Exception as e:
                print(f"❌ Embedding API Error (Quota?): {e}")
                raise ValueError("API Hết Quota hoặc Lỗi")
        return embeddings


# Khởi tạo Collection lưu trữ
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
    """
    Tìm kiếm ngữ nghĩa bằng Vector Database kết hợp Metadata Filtering.
    Giúp AI hiểu các khái niệm phức tạp (như 'pin trâu') và lọc chuẩn danh mục.
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


def call_gemini_api(prompt, system_instruction=None):
    """
    Hàm lõi gọi giao thức tới Google Gemini API.
    Xử lý thiết lập System Instruction để ép khuôn tính cách và hành vi AI.
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
    Hệ thống Retrieval-Augmented Generation (RAG).
    Trích xuất dữ liệu thực từ CSDL dựa trên câu hỏi để làm bối cảnh cho Chatbot.
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
        context_text += f"- ID:{p.id} | {p.name} ({p.brand}) | Giá: {price} | Tình trạng: {status}\n  Chi tiết: {desc_short}...\n"

    return context_text


def generate_chatbot_response(user_msg, chat_history=None):
    """
    Module xử lý thông minh của Chatbot CSKH.
    Ghép nối lịch sử trò chuyện (Memory) và bối cảnh kho hàng (RAG) để trả lời.
    Tích hợp Bộ nhớ đệm (AI Cache) để tăng tốc độ phản hồi và tiết kiệm Quota.
    """
    import hashlib
    from app.extensions import db
    from app.models import AICache

    if chat_history is None:
        chat_history = []

    product_context = build_product_context(user_msg)

    history_text = ""
    if chat_history:
        history_text = "\n--- LỊCH SỬ HỘI THOẠI ---\n"
        for turn in chat_history:
            history_text += f"User: {turn['user']}\nAI: {turn['ai']}\n"

    system_instruction = (
        "Bạn là Chuyên gia tư vấn công nghệ AI của MobileStore. "
        "Hãy tư vấn dựa trên danh sách 'KHO HÀNG THỰC TẾ' được cung cấp. "
        "Nếu sản phẩm khách hỏi không có trong kho, hãy lịch sự báo hết hàng và gợi ý sản phẩm tương tự."
    )
    final_prompt = f"{history_text}\nKhách hàng hỏi: '{user_msg}'\n\n{product_context}\n\nAI trả lời:"

    # =========================================================================
    # ---> [NEW: Kích hoạt AI Cache - Băm Prompt để kiểm tra DB] <---
    # =========================================================================
    # Băm toàn bộ final_prompt (chứa tồn kho thực tế) thay vì chỉ user_msg
    # để AI không bị "học vẹt" khi sản phẩm bất ngờ Hết Hàng.
    cache_key_content = f"chatbot_{final_prompt}"
    key = hashlib.md5(cache_key_content.encode('utf-8')).hexdigest()

    cached = AICache.query.filter_by(prompt_hash=key).first()
    if cached:
        return cached.response_text
    # =========================================================================

    response_text = call_gemini_api(final_prompt, system_instruction)

    # ---> [NEW: Lưu kết quả vào DB để dùng cho lần sau] <---
    if response_text:
        try:
            # Kiểm tra chống Race Condition (Trùng lặp insert)
            if not AICache.query.filter_by(prompt_hash=key).first():
                db.session.add(AICache(prompt_hash=key, response_text=response_text))
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Chatbot Cache Error: {e}")

    return response_text


def analyze_search_intents(query):
    """
    Hệ thống trích xuất dữ liệu (Entity Extraction) bằng LLM.
    Bóc tách câu nói tự nhiên thành JSON cấu trúc (Hãng, Giá, Loại).
    """
    system_instruction = """
    Bạn là hệ thống trích xuất dữ liệu tìm kiếm cho Website MobileStore.
    Nhiệm vụ: Phân tích câu hỏi của khách và trả về CHỈ MỘT chuỗi JSON hợp lệ. Không giải thích.

    Quy tắc:
    1. Giá: 'triệu' hoặc 'củ' = 1,000,000. 'trăm' = 100,000.
    2. Category: 
       - BẮT BUỘC ĐIỀN 'accessory' nếu truy vấn chứa: ốp, sạc, tai nghe, cáp, kính, cường lực, giá đỡ...
       - BẮT BUỘC ĐIỀN 'phone' nếu truy vấn là tên dòng máy hoặc chứa từ 'điện thoại', 'máy'.

    Định dạng JSON yêu cầu:
    {"brand": "Apple/Samsung...", "category": "phone/accessory", "min_price": Số, "max_price": Số, "keyword": "Từ khóa", "sort": "price_asc/price_desc"}
    """
    prompt = f"Câu hỏi: '{query}'\n\nTrả về JSON:"
    res = call_gemini_api(prompt, system_instruction=system_instruction)
    if not res: return None

    try:
        clean = re.sub(r"```json|```", "", res).strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match: return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"AI Parse JSON Error: {e}")
        return None


def local_analyze_intent(query):
    """
    Thuật toán phân tích dự phòng (Local Fallback Mode).
    Áp dụng Regular Expressions (Regex) để trích xuất ý định khi Google AI lỗi.
    """
    query = query.lower()
    data = {'brand': None, 'category': None, 'keyword': '', 'min_price': None, 'max_price': None, 'sort': None}

    brands = {'iphone': 'Apple', 'apple': 'Apple', 'samsung': 'Samsung', 'oppo': 'Oppo', 'xiaomi': 'Xiaomi', 'vivo': 'Vivo'}
    for k, v in brands.items():
        if k in query:
            data['brand'] = v
            query = query.replace(k, '')

    accessory_kws = ['ốp', 'sạc', 'tai nghe', 'cáp', 'kính', 'cường lực', 'giá đỡ', 'loa', 'dây đeo', 'airpods']
    phone_kws = ['điện thoại', 'máy', 'smartphone', 'phone']
    if any(x in query for x in accessory_kws): data['category'] = 'accessory'
    elif any(x in query for x in phone_kws): data['category'] = 'phone'

    price_match = re.search(r'(\d+)\s*(triệu|củ)', query)
    if price_match:
        val = int(price_match.group(1))
        if val < 1000: data['max_price'] = val * 1000000
        query = re.sub(r'\d+\s*(triệu|củ)', '', query)

    stop_words = ['tôi', 'muốn', 'mua', 'tìm', 'cho', 'cần', 'dưới', 'khoảng', 'điện', 'thoại', 'máy', 'tốt', 'đẹp', 'giá', 'chơi', 'game', 'chụp', 'ảnh', 'rẻ']
    words = query.split()
    data['keyword'] = " ".join([w for w in words if w not in stop_words]).strip()
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