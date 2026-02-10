from app import create_app, initialize_database

# Khởi tạo ứng dụng Flask từ app/__init__.py
app = create_app()

if __name__ == '__main__':
    # Kích hoạt Context của ứng dụng để thao tác với Database
    with app.app_context():
        # Tạo bảng và dữ liệu mẫu (Admin, Sản phẩm...) nếu chưa có
        initialize_database()

    # Chạy server ở chế độ Debug
    print("🚀 Server đang chạy tại: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)