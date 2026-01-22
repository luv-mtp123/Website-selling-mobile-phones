import os
import requests
import json
import time

# --- CẤU HÌNH ---
# Sử dụng os.environ.get để lấy key an toàn từ file .env hoặc biến môi trường
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def get_gemini_suggestions(product_name):
    """
    Hàm gọi Google Gemini API để gợi ý phụ kiện.
    Sử dụng REST API thông qua thư viện requests.
    Tự động retry nếu gặp lỗi quá tải (429).
    """
    # 1. Kiểm tra Key (Lấy lại từ os.environ phòng trường hợp chưa load kịp lúc import)
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return "⚠️ Lỗi: Chưa cấu hình GEMINI_API_KEY trong file .env"

    # 2. Cấu hình Endpoint
    # Chuyển sang 'gemini-2.5-flash' vì 'gemini-2.0-flash' bị giới hạn quota (429).
    # Nếu vẫn lỗi, bạn có thể thử 'gemini-flash-latest'
    target_model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    # 3. Tạo nội dung gửi đi (Prompt)
    prompt = (
        f"Tôi đang xem điện thoại {product_name}. "
        "Hãy đóng vai chuyên gia, gợi ý 3 phụ kiện cần thiết nhất (như ốp lưng, sạc, tai nghe...). "
        "Giải thích ngắn gọn 1 dòng lý do nên mua. Định dạng: Gạch đầu dòng, tiếng Việt. "
        "Không cần chào hỏi, đi thẳng vào vấn đề."
    )

    # Cấu trúc JSON theo chuẩn Gemini API
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    # 4. Gửi yêu cầu (Có cơ chế Retry)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                try:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    return text
                except (KeyError, IndexError):
                    return "Gemini không trả về nội dung hợp lệ."

            elif response.status_code == 429:
                # Lỗi quá tải (Rate Limit) -> Chờ và thử lại
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # Chờ 2s, 4s...
                    continue
                else:
                    return "⚠️ Hệ thống đang bận (Quá giới hạn request). Vui lòng thử lại sau."

            elif response.status_code == 404:
                # Nếu vẫn lỗi 404 model, thử list lại (như logic cũ nhưng rút gọn)
                return f"Lỗi Model (404): Không tìm thấy '{target_model}'. Hãy kiểm tra lại API Key hoặc đổi model."

            elif response.status_code == 400:
                return "Lỗi yêu cầu (400): Kiểm tra lại dữ liệu gửi đi."
            elif response.status_code == 403:
                return "Lỗi quyền truy cập (403): API Key sai hoặc bị chặn."
            else:
                return f"Lỗi kết nối Gemini (Mã {response.status_code}): {response.text}"

        except Exception as e:
            return f"Lỗi kết nối mạng: {str(e)}"

    return "Lỗi không xác định."