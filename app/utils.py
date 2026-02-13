import os
import requests
import json
import time
import re
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer
# [FIX] Import or_ từ sqlalchemy để dùng cho tìm kiếm
from sqlalchemy import or_
# --- IMPORT MODEL ĐỂ AI ĐỌC DỮ LIỆU ---
from app.extensions import db
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


# --- PASSWORD RESET UTILS ---
def get_serializer(secret_key):
    return URLSafeTimedSerializer(secret_key)


def send_reset_email_simulation(to_email, token):
    """
    Giả lập gửi email. Trong thực tế sẽ dùng SMTP.
    Ở đây sẽ in ra Console và trả về link để test.
    """
    reset_link = url_for('auth.reset_password', token=token, _external=True)
    print("=" * 30)
    print(f"EMAIL MOCK SENDING TO: {to_email}")
    print(f"LINK RESET: {reset_link}")
    print("=" * 30)
    return reset_link

# --- AI CORE FUNCTIONS ---

def call_gemini_api(prompt, system_instruction=None):
    """Hàm gọi API Gemini cơ bản"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Lỗi: Chưa cấu hình GEMINI_API_KEY")
        return None

    # Sử dụng model flash để phản hồi nhanh cho Chatbot
    target_model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    # Cấu trúc payload chuẩn
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7, # Tăng nhẹ sự sáng tạo cho lời thoại tự nhiên
            "maxOutputTokens": 1000
        }
    }

    # Thêm System Instruction nếu có (Giúp định hình nhân cách AI tốt hơn)
    if system_instruction:
        data["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
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


# --- [NEW] RAG: TẠO NGỮ CẢNH DỮ LIỆU CHO AI ---
def build_product_context(user_query):
    """
    RAG LITE: Tìm sản phẩm trong DB khớp với query để nạp kiến thức cho AI.
    [OPTIMIZED] Trả về định dạng rõ ràng hơn để AI dễ đọc.
    """
    from app.models import Product

    user_query = user_query.lower()

    # Logic tìm kiếm mờ (Fuzzy search simulation)
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

    # [OPTIMIZED] Tạo bảng dữ liệu ngữ cảnh
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
    [NEW] Hàm xử lý tập trung cho Chatbot
    Kết hợp RAG + Persona + Prompt Engineering
    """
    # 1. Lấy ngữ cảnh dữ liệu
    product_context = build_product_context(user_msg)

    # 2. Xây dựng System Persona (Nhân cách)
    system_instruction = (
        "Bạn là Trợ lý ảo AI của 'MobileStore' trong dịp Tết Bính Ngọ 2026. 🐍🌸\n"
        "TÍNH CÁCH: Thân thiện, vui vẻ, nhiệt tình, hay dùng emoji Tết (🧧, 🌸, 💰).\n"
        "NHIỆM VỤ:\n"
        "1. Tư vấn bán hàng dựa trên dữ liệu được cung cấp.\n"
        "2. Nếu có giá tiền, hãy in đậm (ví dụ: **10.000.000 đ**).\n"
        "3. Luôn gợi ý khách mua thêm phụ kiện hoặc chốt đơn nếu khách tỏ ý thích.\n"
        "4. Nếu khách hỏi ngoài lề (thời tiết, chính trị...), hãy khéo léo lái về mua điện thoại chơi Tết.\n"
        "GIỚI HẠN: Trả lời ngắn gọn dưới 100 từ. Không bịa đặt thông tin sản phẩm không có trong ngữ cảnh."
    )

    # 3. Tạo User Prompt kèm Context
    final_prompt = (
        f"Câu hỏi của khách: '{user_msg}'\n\n"
        f"Dữ liệu kho hàng thực tế:\n{product_context}\n\n"
        "Hãy trả lời khách hàng ngay:"
    )

    # 4. Gọi AI
    response = call_gemini_api(final_prompt, system_instruction)
    return response if response else "Hệ thống AI đang quá tải vì khách sắm Tết đông quá! Bạn đợi xíu nha 🧧"


def get_gemini_suggestions(product_name):
    prompt = (
        f"Gợi ý 3 phụ kiện cần thiết nhất cho {product_name}. "
        "Trả về định dạng HTML <ul><li>...</li></ul> ngắn gọn."
    )
    return call_gemini_api(prompt)

def analyze_search_intents(query):
    # Prompt cũ của bạn vẫn ổn
    prompt = (
        f"Phân tích query: '{query}'. Trả về JSON {{brand, category, keyword, min_price, max_price, sort}}."
    )
    response_text = call_gemini_api(prompt)
    if not response_text: return None
    try:
        clean_text = re.sub(r"```json|```", "", response_text).strip()
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return None
    except: return None

def get_comparison_result(p1_name, p1_price, p1_desc, p2_name, p2_price, p2_desc):
    prompt = (
        f"So sánh 2 điện thoại: {p1_name} ({p1_price}đ) và {p2_name} ({p2_price}đ). "
        "Tạo bảng HTML class='table table-bordered' so sánh: Màn hình, Camera, Pin, Hiệu năng. "
        "Kết luận ngắn gọn ai nên mua máy nào."
    )
    result = call_gemini_api(prompt)
    return re.sub(r"```html|```", "", result).strip() if result else None