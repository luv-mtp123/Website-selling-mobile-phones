from app import create_app, initialize_database

# Khởi tạo ứng dụng Flask đóng vai trò là Entry Point cho máy chủ Production
app = create_app()

# Đảm bảo Database và các bảng dữ liệu được tạo sẵn sàng trước khi nhận request
# Điều này giúp tránh lỗi "no such table" khi chạy Gunicorn hoặc py wsgi.py trực tiếp
with app.app_context():
    initialize_database()

if __name__ == "__main__":
    app.run()