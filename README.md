## **📱 MobileStore - Siêu Thị Điện Thoại Thông Minh Tích Hợp AI (Phiên Bản Tết 2024)**



##### Chào mừng bạn đến với MobileStore! Đây là dự án thương mại điện tử hiện đại được xây dựng bằng Python Flask, tích hợp sâu Google Gemini AI để mang lại trải nghiệm mua sắm thông minh.

##### 

##### Phiên bản này đã được nâng cấp toàn diện về giao diện (Theme Tết), tính năng quản trị (CRUD) và tối ưu hóa logic AI.

##### 

### ✨ Các Tính Năng Mới Cập Nhật (What's New)

##### 

#### 🌸 Giao Diện Tết Giáp Thìn:

###### 

##### Trang chủ được khoác áo mới với Banner Tết, hiệu ứng hoa rơi và màu sắc may mắn.

##### 

##### Hệ thống câu đối và badge "Lì Xì" cho sản phẩm.

##### 

#### 🤖 Chatbot Hybrid (Thông Minh Hơn):

##### 

##### Cơ chế lai (Hybrid): Sử dụng từ khóa (Rule-based) để trả lời siêu tốc các câu hỏi thường gặp (địa chỉ, bảo hành) + Gemini AI để xử lý các câu hỏi tư vấn phức tạp.

##### 

##### Hoạt động mượt mà, không bị lag và tiết kiệm token AI.

##### 

#### 🔧 Quản Trị Admin Nâng Cao:

##### 

##### Đã tách biệt giao diện: Danh sách sản phẩm (admin\_dashboard.html) và Sửa sản phẩm (admin\_edit.html).

##### 

##### Admin có thể Thêm, Xóa, và Sửa chi tiết thông tin sản phẩm (Giá, Sale, Mô tả...).

##### 

#### 🔍 AI Smart Search \& Compare (Đã Sửa Lỗi):

##### 

##### Sử dụng Regex để trích xuất dữ liệu JSON từ AI chính xác hơn, khắc phục lỗi tìm kiếm trước đây.

##### 

##### Bảng so sánh sản phẩm được render ra HTML đẹp mắt thay vì Markdown thô.

##### 

#### 🚀 Tính Năng Chi Tiết

##### 

#### 1\. Trí Tuệ Nhân Tạo (Gemini AI Integration)

##### 

##### Tìm Kiếm Thông Minh (Smart Search): Hiểu ngôn ngữ tự nhiên.

##### 

##### Ví dụ: "Điện thoại Samsung dưới 20 triệu chụp ảnh đẹp" -> Hệ thống tự động lọc Hãng Samsung, Giá < 20tr.

##### 

##### So Sánh Sản Phẩm (AI Comparison): Kẻ bảng so sánh thông số, hiệu năng, pin giữa 2 máy bất kỳ và đưa ra lời khuyên mua sắm.

##### 

##### Gợi Ý Phụ Kiện: AI tự động đề xuất phụ kiện phù hợp khi xem chi tiết sản phẩm.

##### 

#### 2\. Người Dùng (User)

##### 

##### Đăng Nhập/Đăng Ký: Hỗ trợ Google OAuth và tài khoản thường.

##### 

##### Giỏ Hàng \& Thanh Toán: Thêm/sửa/xóa sản phẩm, tính tổng tiền, đặt hàng (lưu vào DB).

##### 

##### Lịch Sử Đơn Hàng: Xem lại các đơn hàng đã mua trong Dashboard cá nhân.

##### 

#### 3\. Quản Trị Viên (Admin)



##### Truy cập /admin để xem thống kê tổng quan (Sản phẩm, User, Đơn hàng).

##### 

##### Quản lý toàn bộ danh sách sản phẩm (CRUD).

##### 

### 🛠 Cài Đặt \& Chạy Dự Án

##### 

#### Bước 1: Cài đặt thư viện

##### 

##### Mở Terminal tại thư mục dự án và chạy:

##### 

##### pip install -r requirements.txt

##### 

##### 

#### Bước 2: Cấu hình Môi trường (.env)

##### 

##### Tạo file .env và điền các thông tin sau (Nếu chưa có, hãy copy từ file cũ):

##### 

##### SECRET\_KEY=chuoi-bi-mat-bao-mat-flask-123

##### GEMINI\_API\_KEY=Dien\_API\_Key\_Gemini\_Cua\_Ban\_Vao\_Day

##### GOOGLE\_CLIENT\_ID=Dien\_Client\_ID\_Google

##### GOOGLE\_CLIENT\_SECRET=Dien\_Client\_Secret\_Google

##### 

##### 

#### Bước 3: Khởi tạo Database (Quan Trọng)

##### 

##### Nếu bạn gặp lỗi hiển thị hoặc muốn nạp lại dữ liệu mẫu (Sản phẩm mới, User mẫu):

##### 

##### Xóa file mobilestore.db hiện có trong thư mục.

##### 

##### Chạy lại ứng dụng, hệ thống sẽ tự động tạo lại DB mới chuẩn xác.

##### 

#### Bước 4: Chạy Website

##### 

##### python app.py

##### 

##### 

##### 👉 Truy cập: http://127.0.0.1:5000

##### 

##### 📂 Cấu Trúc Thư Mục Mới Nhất

##### 

##### MobileStore/

##### ├── app.py                # Logic chính (Đã cập nhật fix lỗi trùng lặp \& init DB)

##### ├── utils.py              # Logic AI (Đã cập nhật Regex parsing)

##### ├── models.py             # Database Models

##### ├── extensions.py         # Config mở rộng

##### ├── requirements.txt      # Thư viện

##### ├── .env                  # Biến môi trường

##### ├── mobilestore.db        # Database SQLite

##### └── templates/            # Giao diện HTML

##### &nbsp;   ├── base.html         # Layout chung + Hiệu ứng Tết + Chatbot UI

##### &nbsp;   ├── home.html         # Trang chủ + Smart Search + Banner Tết

##### &nbsp;   ├── detail.html       # Chi tiết sản phẩm

##### &nbsp;   ├── compare.html      # So sánh AI (Giao diện VS mới)

##### &nbsp;   ├── cart.html         # Giỏ hàng

##### &nbsp;   ├── checkout.html     # Thanh toán

##### &nbsp;   ├── login.html        # Đăng nhập

##### &nbsp;   ├── register.html     # Đăng ký

##### &nbsp;   ├── dashboard.html    # Trang cá nhân user

##### &nbsp;   ├── admin\_dashboard.html # Admin: Thống kê \& Danh sách (Đã tách code sửa)

##### &nbsp;   └── admin\_edit.html      # Admin: Form sửa sản phẩm (Mới)

##### 

##### 

#### 🔑 Tài Khoản Demo (Seed Data)

##### 

##### Khi khởi chạy lần đầu (sau khi xóa DB cũ), hệ thống tạo sẵn:

##### 

##### Vai trò

##### 

##### Username

##### 

##### Password

##### 

##### Admin

##### 

##### admin

##### 

##### 123456

##### 

##### Khách

##### 

##### khach

##### 

##### 123456

##### 

#### 📝 Ghi Chú Khắc Phục Lỗi (Troubleshooting)

##### 

##### Lỗi TemplateSyntaxError: Encountered unknown tag 'endblock':

##### 

##### Do file HTML bị thiếu thẻ mở {% block content %}. Code mới nhất đã fix lỗi này.

##### 

##### Lỗi View function mapping is overwriting...:

##### 

##### Do trùng tên hàm trong app.py. File app.py hiện tại đã được dọn dẹp sạch sẽ.

##### 

##### Lỗi 'product' is undefined khi vào Admin:

##### 

##### Do code sửa sản phẩm nằm chung với trang danh sách. Đã tách ra thành admin\_edit.html.

##### 

##### Trang chủ không hiện sản phẩm:

##### 

##### Hãy xóa file .db và chạy lại python app.py để hàm initialize\_database() nạp dữ liệu.

##### 

### Chúc bạn có trải nghiệm tuyệt vời với MobileStore phiên bản Tết! 🌸🧧

