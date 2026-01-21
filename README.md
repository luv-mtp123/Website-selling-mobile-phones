Website-selling-mobile-phones

Hướng Dẫn Chạy Dự Án Mobile Shop (Django)
===

# 

# Dự án này được tạo tự động bởi script. Dưới đây là các bước để chạy trang web trên máy tính của bạn.

# 

# Yêu cầu hệ thống

# 

# Đã cài đặt Python (phiên bản 3.8 trở lên).

# 

# Các bước thực hiện

# 

# Bước 1: Tạo dự án

# 

# Chạy file script tạo dự án bạn vừa tải về:

# 

# python setup\_project.py

# 

# 

# Sau khi chạy xong, bạn sẽ thấy thư mục mobile\_shop.

# 

# Bước 2: Cài đặt thư viện

# 

# Mở terminal (CMD/PowerShell) tại thư mục mobile\_shop vừa tạo và chạy lệnh:

# 

# cd mobile\_shop

# pip install -r requirements.txt

# 

# 

# Bước 3: Khởi tạo Database (Migration)

# 

# Tạo bảng dữ liệu trong SQLite:

# 

# python manage.py makemigrations

# python manage.py migrate

# 

# 

# Bước 4: Tạo dữ liệu mẫu (Seed Data)

# 

# Tôi đã chuẩn bị sẵn script để tạo User Admin và một vài điện thoại mẫu. Chạy lệnh:

# 

# python seed\_data.py

# 

# 

# Tài khoản Admin mặc định:

# 

# User: admin

# 

# Pass: admin123

# 

# Bước 5: Chạy Server

# 

# Khởi động website:

# 

# python manage.py runserver

# 

# 

# Truy cập trình duyệt tại địa chỉ: https://www.google.com/search?q=http://127.0.0.1:8000

# 

# Các tính năng đã tích hợp

# 

# AI Search Simulation:

# 

# Thử tìm từ khóa "iPhone" -> Hệ thống sẽ hiển thị kết quả tìm kiếm VÀ đề xuất thêm "Củ sạc", "Ốp lưng" (Logic đề xuất nằm trong views.py).

# 

# Thử tìm "Samsung" -> Đề xuất các hãng Android khác.

# 

# Phân quyền (Role):

# 

# Khách: Xem trang chủ, tìm kiếm.

# 

# Admin/User đăng nhập: Truy cập được trang Dashboard (/dashboard/) để Thêm/Sửa/Xóa sản phẩm.

# 

# Giao diện:

# 

# Sử dụng Tailwind CSS (CDN) nên không cần cài đặt nodejs/npm.

# 

# Responsive trên mobile.

