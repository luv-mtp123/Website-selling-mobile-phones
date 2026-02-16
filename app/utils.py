import os
import requests
import json
import time
import re
import hashlib
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer
# [FIX] Import or_ từ sqlalchemy để dùng cho tìm kiếm
from sqlalchemy import or_
# --- IMPORT MODEL ĐỂ AI ĐỌC DỮ LIỆU ---
from app.extensions import db
from app.models import AICache

# Lưu ý: Product được import lazy bên trong hàm để tránh circular import


# --- CẤU HÌNH ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# --- FILE VALIDATION UTILS ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def validate_image_file(file):
    """
    Kiểm tra file upload:
    1. Có tên file không?
    2. Đuôi file hợp lệ không?
    3. Kích thước file < 2MB không? (Kiểm tra length con trỏ file)
    Trả về: (True, None) hoặc (False, "Lỗi cụ thể")
    """
    if file.filename == '':
        return False, "Chưa chọn file."

    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
        return False, "Định dạng file không hỗ trợ. Chỉ nhận: JPG, PNG, WEBP."

    # Kiểm tra kích thước (seek đến cuối để lấy size, sau đó seek về đầu)
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)

    if file_length > 2 * 1024 * 1024:  # 2MB
        return False, "File quá lớn! Vui lòng chọn ảnh dưới 2MB."

    return True, None


def get_serializer(secret_key):
    return URLSafeTimedSerializer(secret_key)


def send_reset_email_simulation(to_email, token):
    reset_link = url_for('auth.reset_password', token=token, _external=True)
    print("=" * 30)
    print(f"EMAIL MOCK SENDING TO: {to_email}")
    print(f"LINK RESET: {reset_link}")
    print("=" * 30)
    return reset_link


# --- AI CORE FUNCTIONS ---

def call_gemini_api(prompt, system_instruction=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Lỗi: Chưa cấu hình GEMINI_API_KEY")
        return None

    target_model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,  # Giảm nhiệt độ để AI tập trung vào chính xác, bớt sáng tạo
            "maxOutputTokens": 4000  # Tăng token để bảng so sánh không bị cắt giữa chừng
        }
    }

    if system_instruction:
        data["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)  # Tăng timeout lên 30s
        if response.status_code == 200:
            result = response.json()
            try:
                return result['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                return None
        else:
            print(f"Gemini Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Network Error: {str(e)}")
        return None


def build_product_context(user_query):
    """
    RAG LITE: Tìm sản phẩm trong DB khớp với query để nạp kiến thức cho AI.
    """
    from app.models import Product

    user_query = user_query.lower()

    # Logic tìm kiếm mờ
    products = Product.query.filter(
        or_(
            Product.name.ilike(f"%{user_query}%"),
            Product.brand.ilike(f"%{user_query}%"),
            Product.category.ilike(f"%{user_query}%")
        ),
        Product.is_active == True
    ).limit(6).all()

    # Nếu không tìm thấy chính xác, thử tìm theo từ đơn
    if not products:
        words = user_query.split()
        for word in words:
            if len(word) > 2:
                found = Product.query.filter(Product.name.ilike(f"%{word}%"), Product.is_active == True).limit(3).all()
                products.extend(found)
                if len(products) >= 3: break

    # Loại bỏ trùng lặp
    products = list({p.id: p for p in products}.values())

    if not products:
        return "Hiện tại hệ thống không tìm thấy sản phẩm nào khớp chính xác với yêu cầu này trong kho."

    # Tạo bảng dữ liệu ngữ cảnh
    context_text = "--- DANH SÁCH SẢN PHẨM CÓ SẴN TẠI SHOP ---\n"
    for p in products:
        price = "{:,.0f} đ".format(p.sale_price if p.is_sale else p.price)
        status = f"Sẵn hàng ({p.stock_quantity})" if p.stock_quantity > 0 else "Tạm hết"
        is_sale = "🔥 Đang giảm giá!" if p.is_sale else ""

        context_text += f"ID: {p.id} | Tên: {p.name} | Giá: {price} | Tình trạng: {status} {is_sale}\n"
        if p.description:
            clean_desc = p.description.replace('\n', ' ').strip()[:80]
            context_text += f"   Mô tả: {clean_desc}...\n"

    context_text += "--------------------------------------------"
    return context_text


def generate_chatbot_response(user_msg):
    """
    Hàm xử lý tập trung cho Chatbot
    """
    product_context = build_product_context(user_msg)

    system_instruction = (
        "Bạn là Trợ lý ảo AI của 'MobileStore' trong dịp Tết Bính Ngọ 2026. 🐍🌸\n"
        "TÍNH CÁCH: Thân thiện, vui vẻ, nhiệt tình, hay dùng emoji Tết (🧧, 🌸, 💰).\n"
        "NHIỆM VỤ:\n"
        "1. Tư vấn bán hàng dựa trên dữ liệu được cung cấp.\n"
        "2. Nếu có giá tiền, hãy in đậm (ví dụ: **10.000.000 đ**).\n"
        "3. Luôn gợi ý khách mua thêm phụ kiện hoặc chốt đơn nếu khách tỏ ý thích.\n"
        "4. Nếu khách hỏi ngoài lề, hãy khéo léo lái về mua điện thoại chơi Tết.\n"
        "GIỚI HẠN: Trả lời ngắn gọn dưới 100 từ."
    )

    final_prompt = (
        f"Câu hỏi của khách: '{user_msg}'\n\n"
        f"Dữ liệu kho hàng thực tế:\n{product_context}\n\n"
        "Hãy trả lời khách hàng ngay:"
    )

    response = call_gemini_api(final_prompt, system_instruction)
    return response if response else "Hệ thống AI đang quá tải vì khách sắm Tết đông quá! Bạn đợi xíu nha 🧧"


# --- [FIXED] SMART SEARCH INTENT ---
def analyze_search_intents(query):
    """
    Phân tích ý định tìm kiếm của người dùng thành JSON.
    """
    prompt = (
        f"Phân tích câu tìm kiếm: '{query}'. \n"
        "Nhiệm vụ: Trích xuất thông tin để lọc sản phẩm trong Database.\n"
        "Quy tắc quan trọng:\n"
        "1. 'keyword': Phải là từ khóa CỐT LÕI ngắn gọn nhất có trong tên sản phẩm. Ví dụ: 'ốp lưng iphone' -> keyword: 'ốp lưng'. Đừng lấy cả cụm 'ốp lưng iphone'.\n"
        "2. 'category': Bắt buộc là 'phone' hoặc 'accessory' hoặc null. Nếu tìm 'ốp', 'sạc', 'tai nghe', 'cáp' -> category='accessory'.\n"
        "3. 'brand': Tên hãng (Apple, Samsung...) nếu có.\n"
        "\n"
        "Trả về JSON duy nhất (không markdown):\n"
        "{\n"
        "  'brand': 'Tên hãng hoặc null',\n"
        "  'category': 'phone' hoặc 'accessory' hoặc null,\n"
        "  'keyword': 'Từ khóa ngắn gọn (ví dụ: ốp, sạc, tai nghe, iphone 15) hoặc null',\n"
        "  'min_price': số tiền (int) hoặc null,\n"
        "  'max_price': số tiền (int) hoặc null,\n"
        "  'sort': 'price_asc' (rẻ nhất), 'price_desc' (đắt nhất) hoặc null\n"
        "}\n"
    )
    response_text = call_gemini_api(prompt)
    if not response_text: return None

    try:
        # Làm sạch chuỗi JSON (xóa ```json và ``` nếu có)
        clean_text = re.sub(r"```json|```", "", response_text).strip()
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        return None


def get_comparison_result(p1_name, p1_price, p1_desc, p2_name, p2_price, p2_desc):
    # [FIX] Prompt chặt chẽ hơn để tránh AI trả về lời dẫn chuyện
    prompt = (
        f"Đóng vai chuyên gia công nghệ. So sánh 2 sản phẩm: {p1_name} ({p1_price}đ) và {p2_name} ({p2_price}đ). \n"
        "YÊU CẦU ĐẦU RA (Output Requirement): \n"
        "1. CHỈ TRẢ VỀ MÃ HTML (HTML Code Only). KHÔNG ĐƯỢC có lời chào, lời dẫn (như 'Chắc chắn rồi', 'Dưới đây là...').\n"
        "2. Cấu trúc HTML:\n"
        "   - Một thẻ <h3> tiêu đề.\n"
        "   - Một bảng <table class='table table-bordered table-striped table-hover'> so sánh: Màn hình, Camera, Pin, Hiệu năng, Giá.\n"
        "   - Một thẻ <div class='alert alert-success mt-3'> chứa kết luận ngắn gọn: Ai nên mua máy nào.\n"
        "3. Không sử dụng markdown code block (```html)."
    )
    result = call_gemini_api(prompt)

    if not result: return None

    # Làm sạch triệt để: Xóa markdown code block và khoảng trắng thừa
    clean_html = re.sub(r"```html|```", "", result).strip()
    return clean_html