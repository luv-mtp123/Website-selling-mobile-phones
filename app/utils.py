import os
import requests
import json
import time
import re
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer

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

def call_gemini_api(prompt):
    """Hàm gọi API chung"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    target_model = "gemini-2.5-flash"
    # [FIXED] Sửa lại URL chuẩn (bỏ các ký tự thừa do lỗi copy paste cũ)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}

    # Thêm hướng dẫn hệ thống để AI trả lời ngắn gọn, đúng trọng tâm
    system_instruction = "Bạn là trợ lý ảo chuyên về điện thoại của MobileStore. Trả lời ngắn gọn, thân thiện, format HTML nếu cần."

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": 0.1,  # Giảm nhiệt độ để AI trả lời chính xác
            "maxOutputTokens": 2000  # Tăng token để bảng so sánh dài không bị cắt
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
    """
    prompt = (
        f"Phân tích query: '{query}'. "
        "Trả về 1 JSON duy nhất. Cấu trúc bắt buộc:\n"
        "{\n"
        "  \"brand\": \"Apple\" | \"Samsung\" | \"Xiaomi\" | \"Oppo\" | null,\n"
        "  \"min_price\": int (VNĐ) | null,\n"
        "  \"max_price\": int (VNĐ) | null,\n"
        "  \"sort\": \"price_asc\" | \"price_desc\" | null\n"
        "}\n"
        "Lưu ý: 'dưới 10 triệu' -> max_price: 10000000. 'trên 5 củ' -> min_price: 5000000."
    )

    response_text = call_gemini_api(prompt)
    if not response_text: return None

    # print(f"DEBUG AI Raw: {response_text}")

    try:
        # 1. Thử làm sạch Markdown
        clean_text = re.sub(r"```json|```", "", response_text).strip()

        # 2. Dùng Regex tìm chuỗi JSON nằm giữa dấu { và } ngoài cùng
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match:
            clean_json = match.group(0)
            data = json.loads(clean_json)
            return data

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
        "Chỉ trả về HTML, không markdown, không lời dẫn thừa."
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