import sys
import os

# =========================================================================
# Ép Terminal của Windows đọc được Emoji UTF-8 (Giống file __init__.py)
# =========================================================================
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# =========================================================================

try:
    from waitress import serve
except ImportError:
    print("❌ THIẾU THƯ VIỆN WAITRESS!")
    print("Vui lòng chạy lệnh sau để cài đặt: py -m pip install waitress")
    sys.exit(1)

# =========================================================================
# ---> [NEW] Tích hợp thẳng lõi khởi tạo từ wsgi.py cũ vào đây <---
# =========================================================================
from app import create_app, initialize_database

# Khởi tạo ứng dụng Flask đóng vai trò là Entry Point cho máy chủ Production
app = create_app()

# Đảm bảo Database và các bảng dữ liệu được tạo sẵn sàng trước khi nhận request
with app.app_context():
    initialize_database()


# =========================================================================


def start_production_server():
    """
    Hệ thống khởi động máy chủ WSGI trên Windows sử dụng Waitress.
    Waitress là giải pháp thay thế hoàn hảo cho Gunicorn trên nền tảng Windows.
    Hỗ trợ xử lý đa luồng (Multi-threading) để chịu tải cao.
    """
    print("=" * 65)
    print("🚀 BẮT ĐẦU KHỞI CHẠY MÁY CHỦ PRODUCTION (WINDOWS EXCLUSIVE) 🚀")
    print("=" * 65)
    print("⚙️ Đang sử dụng Engine: Waitress WSGI Server")
    print("🌐 Chế độ: Mạng nội bộ (0.0.0.0)")
    print("🌍 Cổng (Port): 5000")
    print("🚦 Luồng xử lý (Threads): 6")
    print("-" * 65)
    print("👉 Hướng dẫn: Mở trình duyệt và truy cập http://127.0.0.1:5000")
    print("💡 Nhấn [CTRL + C] để dừng máy chủ an toàn.")
    print("=" * 65)

    try:
        # Chạy server với 6 luồng (threads) để xử lý nhiều người truy cập cùng lúc
        serve(app, host='0.0.0.0', port=5000, threads=6)
    except KeyboardInterrupt:
        print("\n🛑 Đã nhận lệnh dừng từ quản trị viên. Đang tắt máy chủ...")
    except Exception as e:
        print(f"\n❌ Đã xảy ra lỗi nghiêm trọng khi chạy Server: {e}")


if __name__ == "__main__":
    start_production_server()