import os
from app import create_app, initialize_database

# Khởi tạo ứng dụng Flask từ app/__init__.py
app = create_app()

if __name__ == '__main__':
    # Kích hoạt Context của ứng dụng để thao tác với Database
    with app.app_context():
        pass
        # initialize_database()

    # Chạy server ở chế độ an toàn (Production Ready Standard)
    print("🚀 Server đang chạy tại: http://127.0.0.1:5000")

    # ---> [PATCHED]: Không gán cứng debug=True để tránh cảnh báo bảo mật.
    # Hệ thống sẽ lấy giá trị từ biến môi trường, mặc định là False.
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

    app.run(debug=is_debug, port=5000)