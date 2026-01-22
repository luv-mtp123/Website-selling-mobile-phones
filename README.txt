📱 MobileStore - Website Bán Điện Thoại Tích Hợp AI

	Chào mừng bạn đến với dự án MobileStore! Đây là một website thương mại điện tử bán điện thoại di động được xây dựng bằng Python Flask, tích hợp trí tuệ nhân tạo Google Gemini để tự động gợi ý phụ kiện phù hợp cho từng dòng máy.

✨ Tính Năng Nổi Bật :

- Mua sắm thông minh:

- Tìm kiếm sản phẩm theo tên.

- Lọc theo thương hiệu (Apple, Samsung, Xiaomi...).

- Sắp xếp theo giá (Tăng/Giảm dần).

🤖 Trợ lý ảo AI (Gemini):

- Tự động phân tích tên điện thoại bạn đang xem.

- Gợi ý 3 món phụ kiện "chuẩn bài" nhất (ốp lưng, sạc nhanh...) kèm lý do thuyết phục.

- Hoạt động mượt mà trên mọi phiên bản Python (kể cả 3.14 mới nhất).

Hệ thống tài khoản:

Đăng ký / Đăng nhập / Đăng xuất.

Phân quyền: Khách hàng (User) và Quản trị viên (Admin).

Cập nhật thông tin cá nhân.

Quản trị (Admin Dashboard):

Thêm mới sản phẩm (kèm link ảnh).

Xóa sản phẩm.

Xem thống kê số lượng người dùng và sản phẩm.

🛠 Yêu Cầu Cài Đặt

Trước khi chạy, hãy đảm bảo máy bạn đã cài:

Python (Khuyên dùng bản 3.10 trở lên, dự án này hỗ trợ cả Python 3.14).

PIP (Trình quản lý thư viện Python).

Các thư viện cần thiết:

Dự án sử dụng các thư viện nhẹ và phổ biến:

Flask (Web Framework)

Flask-SQLAlchemy (Cơ sở dữ liệu)

Flask-Login (Quản lý đăng nhập)

requests (Gọi API Google Gemini)

🚀 Hướng Dẫn Chạy (3 Bước Đơn Giản)

Bước 1: Cài đặt thư viện

Mở Terminal (hoặc CMD/PowerShell) tại thư mục dự án và chạy lệnh:

	pip install -r requirements.txt


(Nếu chưa có file requirements.txt, hãy tạo nó với nội dung: Flask, Flask-SQLAlchemy, Flask-Login, requests, werkzeug).

Bước 2: Kiểm tra cấu hình AI

Mở file utils.py, đảm bảo biến GEMINI_API_KEY đã được điền mã Key của bạn.
(Hiện tại trong code đã tích hợp sẵn Key hoạt động tốt).

Bước 3: Khởi chạy Website

Gõ lệnh sau vào Terminal:

	python app.py


Sau đó mở trình duyệt và truy cập: 👉 http://127.0.0.1:5000

Lưu ý: Nếu bạn muốn reset dữ liệu (ví dụ ảnh bị lỗi), hãy XÓA file mobilestore.db đi rồi chạy lại lệnh trên. Hệ thống sẽ tự động tạo lại dữ liệu mới sạch sẽ.

🔑 Tài Khoản Mặc Định (Seed Data)

Khi chạy lần đầu, hệ thống tự động tạo 2 tài khoản mẫu để bạn test:

Vai trò

Tên đăng nhập

Mật khẩu

Quản trị viên (Admin)

admin

123456

Khách hàng (User)

khach

123456

📂 Cấu Trúc Thư Mục

Để bạn dễ dàng chỉnh sửa code:

MobileStore/
├── app.py                # File CHÍNH (Chạy file này)
├── utils.py              # Xử lý kết nối AI Gemini
├── models.py             # Định nghĩa bảng User, Product
├── extensions.py         # Khởi tạo db, login_manager
├── requirements.txt      # Danh sách thư viện
├── mobilestore.db        # File dữ liệu (Tự sinh ra)
└── templates/            # Giao diện HTML
    ├── base.html         # Khung sườn chung (Menu, Footer)
    ├── home.html         # Trang chủ
    ├── detail.html       # Chi tiết sản phẩm (+ Gợi ý AI)
    ├── login.html        # Đăng nhập
    ├── register.html     # Đăng ký
    ├── dashboard.html    # Trang cá nhân của khách hàng
    ├── admin_dashborad.html   #File dành cho Admin để xem thống kê và quản lý (thêm/xóa) sản phẩm.

Chúc bạn có trải nghiệm thú vị với MobileStore! 🚀