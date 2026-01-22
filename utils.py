import os
import requests

# --- CẤU HÌNH API KEY ---
# Bạn hãy điền Key của bạn vào dòng dưới đây (thay thế YOUR_API_KEY_HERE)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBzgG9EqVSyVzJnI-cXf2IegFXfMb7LkH0")


def get_gemini_suggestions(product_name):
    """
    Hàm gọi AI Gemini để lấy gợi ý phụ kiện.
    Sử dụng thư viện 'requests' để tránh lỗi tương thích trên Python 3.14.
    """
    # 1. Kiểm tra Key
    if not GEMINI_API_KEY or "AIzaSyBzgG9EqVSyVzJnI-cXf2IegFXfMb7LkH0" in GEMINI_API_KEY:
        return "⚠️ Chưa có API Key. Hãy mở file utils.py để điền Key nhé!"

    # 2. Cấu hình gửi đi
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    # Câu lệnh cho AI (Prompt)
    prompt = (
        f"Tôi đang mua điện thoại {product_name}. "
        "Hãy đóng vai chuyên gia, gợi ý ngắn gọn 3 món phụ kiện cần thiết nhất (ốp lưng, sạc...) "
        "và lý do nên mua. Trả lời bằng tiếng Việt, định dạng gạch đầu dòng."
    )

    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    # 3. Gửi yêu cầu
    try:
        response = requests.post(url, headers=headers, json=data, timeout=5)

        if response.status_code == 200:
            result = response.json()
            try:
                # Lấy nội dung trả về
                text = result['candidates'][0]['content']['parts'][0]['text']
                return text
            except (KeyError, IndexError):
                return "AI không trả về nội dung hợp lệ."
        else:
            return f"Lỗi kết nối AI (Mã {response.status_code})."

    except Exception as e:
        return "Đang gặp sự cố kết nối với AI."