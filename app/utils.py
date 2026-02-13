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
from app.models import Product

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

def call_gemini_api(prompt, system_instruction=None):
    """Hàm gọi API Gemini cơ bản"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    target_model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    if not system_instruction:
        system_instruction = "Bạn là trợ lý ảo của MobileStore. Trả lời ngắn gọn, thân thiện."

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": 0.3,
            # [FIX] Tăng maxOutputTokens lên 4000 để tránh bị cắt cụt HTML khi bảng quá dài
            "maxOutputTokens": 4000
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
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
    Tìm các sản phẩm trong DB khớp với câu hỏi của user
    để nạp kiến thức cho AI.
    """
    # [FIX] Lazy Import: Import Product TẠI ĐÂY để tránh lỗi Circular Import
    # Khi hàm này được gọi, app đã khởi tạo xong nên không bị lỗi vòng lặp
    from app.models import Product

    user_query = user_query.lower()

    # 1. Tìm kiếm cơ bản: Tên hoặc Hãng chứa từ khóa (dùng ilike cho không phân biệt hoa thường)
    products = Product.query.filter(
        or_(
            Product.name.ilike(f"%{user_query}%"),
            Product.brand.ilike(f"%{user_query}%")
        ),
        Product.is_active == True
    ).limit(5).all()

    # 2. Nếu không tìm thấy, thử tách từ khóa (VD: "ip 15" -> tìm "15")
    if not products:
        words = user_query.split()
        for word in words:
            if len(word) > 2:  # Bỏ qua từ quá ngắn
                found = Product.query.filter(Product.name.ilike(f"%{word}%"), Product.is_active == True).limit(3).all()
                products.extend(found)
                if products: break  # Tìm thấy thì dừng để tiết kiệm

    # 3. Tạo đoạn văn bản ngữ cảnh
    if not products:
        return "Không tìm thấy sản phẩm cụ thể nào trong kho dữ liệu khớp với câu hỏi."

    context_text = "DỮ LIỆU CỬA HÀNG HIỆN TẠI (Sử dụng thông tin này để trả lời):\n"
    for p in products:
        price_str = "{:,.0f} đ".format(p.sale_price if p.is_sale else p.price)
        status = f"Sẵn hàng (SL: {p.stock_quantity})" if p.stock_quantity > 0 else "HẾT HÀNG"
        context_text += f"- Tên: {p.name} | Hãng: {p.brand} | Giá: {price_str} | Trạng thái: {status}\n"
        if p.description:
            # Lấy 50 ký tự đầu của mô tả để tiết kiệm token
            short_desc = p.description[:50] + "..." if len(p.description) > 50 else p.description
            context_text += f"  Mô tả: {short_desc}\n"

    return context_text


def get_gemini_suggestions(product_name):
    """Gợi ý phụ kiện"""
    prompt = (
        f"Tôi đang xem điện thoại {product_name}. "
        "Hãy gợi ý 3 phụ kiện cần thiết nhất (chỉ tên phụ kiện và lý do ngắn 5 từ). "
        "Trả về định dạng HTML danh sách không thứ tự <ul><li>...</li></ul>. Không thêm lời dẫn."
    )
    return call_gemini_api(prompt)


def analyze_search_intents(query):
    """
    SMART SEARCH: Phân tích intent người dùng
    [UPDATE v3] Thêm trường 'keyword' để lọc tên sản phẩm chính xác hơn
    """
    # Đảm bảo biến prompt được định nghĩa trước khi gọi API
    prompt = (
        f"Phân tích query tìm kiếm: '{query}'.\n"
        "Nhiệm vụ: Trích xuất thông tin lọc Database.\n"
        "Trả về JSON duy nhất (không Markdown). Cấu trúc:\n"
        "{\n"
        "  \"brand\": \"Apple\" | \"Samsung\" | \"Xiaomi\" | \"Oppo\" | null,\n"
        "  \"category\": \"phone\" | \"accessory\" | null,\n"
        "  \"keyword\": string | null,\n"
        "  \"min_price\": int | null,\n"
        "  \"max_price\": int | null,\n"
        "  \"sort\": \"price_asc\" | \"price_desc\" | null\n"
        "}\n"
        "QUY TẮC:\n"
        "1. 'điện thoại' -> category: 'phone'.\n"
        "2. 'sạc', 'cáp', 'tai nghe', 'ốp', 'kính', 'loa' -> category: 'accessory'.\n"
        "3. keyword: Là từ khóa quan trọng nhất để tìm trong tên sản phẩm. \n"
        "   - Ví dụ: 'ốp lưng iphone' -> keyword: 'ốp'.\n"
        "   - Ví dụ: 'sạc samsung' -> keyword: 'sạc'.\n"
        "   - Ví dụ: 'tai nghe' -> keyword: 'tai nghe'.\n"
        "   - Nếu user tìm chung chung 'điện thoại samsung' -> keyword: null."
    )

    response_text = call_gemini_api(prompt)
    if not response_text: return None

    try:
        clean_text = re.sub(r"```json|```", "", response_text).strip()
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        return None


def get_comparison_result(p1_name, p1_price, p1_desc, p2_name, p2_price, p2_desc):
    """
    AI COMPARISON: Trả về bảng HTML trực tiếp để hiển thị đẹp hơn
    [FIXED] Xử lý lỗi API trả về None và lọc sạch Markdown
    """
    prompt = (
        f"So sánh 2 điện thoại:\n"
        f"1. {p1_name} ({p1_price}đ)\n"
        f"2. {p2_name} ({p2_price}đ)\n"
        "Hãy tạo một bảng HTML (sử dụng class='table table-bordered table-striped') so sánh các tiêu chí: "
        "Màn hình, Camera, Hiệu năng, Pin, Đáng mua hơn?. "
        "Cột 1: Tiêu chí, Cột 2: {p1_name}, Cột 3: {p2_name}. "
        "Cuối cùng thêm 1 đoạn văn ngắn kết luận <b>Ai nên mua máy nào</b>. "
        "Chỉ trả về HTML hợp lệ, ĐẢM BẢO ĐÓNG TẤT CẢ CÁC THẺ (</table>, </div>). Không markdown, không lời dẫn thừa."
    )

    result = call_gemini_api(prompt)

    if result:
        # Lọc bỏ ```html và ``` ở đầu/cuối nếu có để tránh lỗi hiển thị
        clean_html = re.sub(r"```html|```", "", result).strip()
        return clean_html
    else:
        # Trả về thông báo lỗi HTML đẹp mắt thay vì None
        return (
            "<div class='alert alert-warning text-center'>"
            "<i class='fas fa-exclamation-triangle fa-2x mb-2 text-warning'></i><br>"
            "<strong>Hệ thống AI đang quá tải hoặc mất kết nối.</strong><br>"
            "Vui lòng thử lại sau vài phút."
            "</div>"
        )