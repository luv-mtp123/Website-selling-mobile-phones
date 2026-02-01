#### **📱 MobileStore - Siêu Thị Điện Thoại Thông Minh Tích Hợp AI**



###### Chào mừng bạn đến với MobileStore! Đây là một dự án thương mại điện tử hiện đại, được xây dựng bằng Python Flask và tích hợp sức mạnh của Google Gemini AI để mang lại trải nghiệm mua sắm thông minh chưa từng có.



##### ✨ Tính Năng Nổi Bật



###### 🤖 Trí Tuệ Nhân Tạo (Gemini AI Integration)



Dự án tích hợp sâu Gemini AI để hỗ trợ người dùng:



###### 🔍 Tìm Kiếm Thông Minh (Smart Search):



Hiểu ngôn ngữ tự nhiên.



Ví dụ: Nhập "Điện thoại Samsung dưới 20 triệu chụp ảnh đẹp" -> Hệ thống tự động lọc Hãng: Samsung, Giá: < 20tr.



⚖️ So Sánh Sản Phẩm (AI Comparison):



Chọn 2 sản phẩm bất kỳ để AI phân tích.



Tự động kẻ bảng so sánh thông số, hiệu năng, pin và đưa ra lời khuyên "Nên mua máy nào?".



###### 💡 Gợi Ý Phụ Kiện:



Khi xem chi tiết điện thoại, AI sẽ tự động gợi ý 3 phụ kiện "chuẩn bài" nhất kèm lý do thuyết phục.



###### 🛍️ Trải Nghiệm Mua Sắm \& Thanh Toán



Giỏ Hàng (Cart): Thêm, sửa, xóa sản phẩm, tự động tính tổng tiền.



Đặt Hàng (Checkout): Form điền thông tin giao hàng và lưu lịch sử đơn hàng vào cơ sở dữ liệu.



Lịch Sử Mua Hàng: Người dùng có thể xem lại các đơn hàng đã đặt trong trang Dashboard.



###### 🔐 Hệ Thống Tài Khoản \& Bảo Mật



Đăng Nhập Google (OAuth): Hỗ trợ đăng nhập/đăng ký nhanh bằng tài khoản Google.



Xác thực truyền thống: Đăng ký/Đăng nhập bằng mật khẩu (được mã hóa an toàn).



Phân Quyền:



User: Mua hàng, xem lịch sử.



Admin: Truy cập trang quản trị riêng biệt.



###### 🎨 Giao Diện \& Tiện Ích Khác



Giao Diện Tết: Hiệu ứng hoa rơi và câu đối đỏ đón xuân.



Chatbot: Trợ lý ảo trả lời các câu hỏi thường gặp (địa chỉ, bảo hành, giờ làm việc...).



Responsive: Giao diện đẹp mắt trên cả máy tính và điện thoại.



###### 🛠 Yêu Cầu Cài Đặt



Trước khi chạy, hãy đảm bảo máy bạn đã cài:



Python (3.10 trở lên).



PIP (Trình quản lý thư viện).



Các thư viện chính sử dụng:



Flask: Web Framework.



Flask-SQLAlchemy: Quản lý cơ sở dữ liệu.



Flask-Login: Quản lý phiên đăng nhập.



Authlib: Xử lý đăng nhập Google.



requests: Gọi API Gemini.



###### 🚀 Hướng Dẫn Chạy (4 Bước)



###### Bước 1: Cài đặt thư viện



Mở Terminal tại thư mục dự án và chạy:



pip install -r requirements.txt





###### Bước 2: Cấu hình Môi trường (.env)



Tạo file .env (nếu chưa có) và điền các thông tin sau:



\# Key bảo mật cho Flask Session

SECRET\_KEY=chuoi-bi-mat-bao-mat-flask-123



\# API Key của Google Gemini (Lấy tại aistudio.google.com)

GEMINI\_API\_KEY=AIzaSyD-....



\# Cấu hình Google Login (Lấy tại console.cloud.google.com)

\# Redirect URI: \[http://127.0.0.1:5000/authorize/google](http://127.0.0.1:5000/authorize/google)

GOOGLE\_CLIENT\_ID=dien\_client\_id\_cua\_ban

GOOGLE\_CLIENT\_SECRET=dien\_client\_secret\_cua\_ban





###### Bước 3: Khởi tạo Database



Nếu bạn muốn reset dữ liệu mới nhất (bao gồm sản phẩm mẫu), hãy xóa file mobilestore.db cũ đi. Khi chạy app, hệ thống sẽ tự tạo lại.



###### Bước 4: Chạy Website



Gõ lệnh sau vào Terminal:



python app.py





👉 Truy cập: http://127.0.0.1:5000



🔑 Tài Khoản Demo (Seed Data)



Khi khởi chạy lần đầu, hệ thống tự động tạo sẵn:



Vai trò



Username



Password



Admin



admin



123456



Khách



khach



123456



##### 📂 Cấu Trúc Thư Mục



MobileStore/

├── app.py                # File điều hành CHÍNH (Routes, Logic)

├── utils.py              # Xử lý kết nối AI (Gemini, Smart Search)

├── models.py             # Định nghĩa Database (User, Product, Order)

├── extensions.py         # Khởi tạo db, login\_manager

├── requirements.txt      # Danh sách thư viện

├── .env                  # Chứa API Key (Bảo mật)

├── mobilestore.db        # File dữ liệu SQLite

└── templates/            # Giao diện HTML (Jinja2)

&nbsp;   ├── base.html         # Khung sườn chung (Menu, Footer, Chatbot, Tết)

&nbsp;   ├── home.html         # Trang chủ + Smart Search

&nbsp;   ├── detail.html       # Chi tiết sản phẩm + Gợi ý AI

&nbsp;   ├── compare.html      # So sánh sản phẩm AI

&nbsp;   ├── cart.html         # Giỏ hàng

&nbsp;   ├── checkout.html     # Thanh toán

&nbsp;   ├── login.html        # Đăng nhập (Form + Google)

&nbsp;   ├── register.html     # Đăng ký

&nbsp;   ├── dashboard.html    # Trang cá nhân \& Lịch sử đơn hàng

&nbsp;   └── admin\_dashboard.html # Trang quản trị



##### 

##### 📝 Ghi chú

##### 

Nếu gặp lỗi redirect\_uri\_mismatch khi đăng nhập Google, hãy vào Google Cloud Console thêm URI: http://127.0.0.1:5000/authorize/google.



Nếu gặp lỗi kết nối AI, hãy kiểm tra lại GEMINI\_API\_KEY trong file .env.



#### Chúc bạn có trải nghiệm tuyệt vời với MobileStore! 🚀

