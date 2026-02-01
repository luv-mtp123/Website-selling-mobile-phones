import os
import requests
import json
import time
import re

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def call_gemini_api(prompt):
    """Hàm gọi API chung để tái sử dụng"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ Lỗi: Chưa cấu hình GEMINI_API_KEY"

    target_model = "gemini-2.5-flash"

    # [QUAN TRỌNG] Đây là dòng đã sửa. KHÔNG được có dấu [] hay () bao quanh link
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        # Tăng timeout lên 30s để AI kịp suy nghĩ
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
        "Hãy đóng vai chuyên gia, gợi ý 3 phụ kiện cần thiết nhất. "
        "Giải thích ngắn gọn 1 dòng lý do. Định dạng: Gạch đầu dòng, tiếng Việt."
    )
    return call_gemini_api(prompt) or "Hiện tại chưa có gợi ý."


def analyze_search_intents(query):
    """
    SMART SEARCH: Phân tích câu tìm kiếm tự nhiên thành JSON bộ lọc.
    """
    prompt = (
        f"Phân tích câu tìm kiếm: '{query}' từ người dùng muốn mua điện thoại. "
        "Hãy trích xuất các tiêu chí lọc và trả về định dạng JSON thuần túy (không markdown, không giải thích). "
        "Các trường JSON cần lấy (nếu không có thì để null): "
        "- brand: (Apple, Samsung, Xiaomi, Google, Oppo... hoặc null) "
        "- min_price: (số nguyên hoặc null) "
        "- max_price: (số nguyên hoặc null) "
        "- sort: ('price_asc' nếu tìm giá rẻ/thấp, 'price_desc' nếu tìm giá cao/xịn, hoặc null) "
        "Ví dụ: 'điện thoại giá rẻ dưới 5 triệu' -> {\"max_price\": 5000000, \"sort\": \"price_asc\", \"brand\": null}"
    )

    response_text = call_gemini_api(prompt)
    if not response_text: return None

    try:
        # Làm sạch chuỗi JSON phòng trường hợp AI trả về markdown code block
        clean_json = re.sub(r"```json|```", "", response_text).strip()
        return json.loads(clean_json)
    except json.JSONDecodeError:
        return None


def get_comparison_result(p1_name, p1_price, p1_desc, p2_name, p2_price, p2_desc):
    """
    AI COMPARISON: So sánh 2 sản phẩm và trả về Markdown
    """
    prompt = (
        f"So sánh chi tiết 2 điện thoại sau:\n"
        f"1. {p1_name} (Giá: {p1_price} đ) - Đặc điểm: {p1_desc}\n"
        f"2. {p2_name} (Giá: {p2_price} đ) - Đặc điểm: {p2_desc}\n\n"
        "Yêu cầu:\n"
        "- Kẻ bảng so sánh (định dạng Markdown) về: Hiệu năng, Camera, Pin, và Giá trị/Giá tiền.\n"
        "- Đưa ra kết luận ngắn gọn: Ai nên mua máy nào?\n"
        "- Giọng văn khách quan, chuyên gia công nghệ."
    )
    return call_gemini_api(prompt) or "Hệ thống đang bận, vui lòng thử lại sau."