# **📱 MobileStore - Siêu Thị Điện Thoại Thông Minh Tích Hợp AI (Phiên Bản Tết 2026 - Modular MVC)**

# 

#### **Chào mừng bạn đến với MobileStore! Đây là dự án thương mại điện tử hiện đại được xây dựng bằng Python Flask, tích hợp sâu Google Gemini AI.**

#### 

#### **Phiên bản này đã được Tái cấu trúc (Refactor) toàn diện sang mô hình Modular MVC và cập nhật giao diện Tết Bính Ngọ 2026.**

# 

# **🚀 Các Cập Nhật Mới Nhất (Latest Updates)**

# 

## **1. 🛠️ Fix Lỗi Logic \& Bảo Mật (Critical Fixes)**

# 

### **✅ Quản Lý Database Chuyên Nghiệp (Flask-Migrate) (MỚI)**

# 

#### **Nâng cấp: Tích hợp Flask-Migrate để quản lý thay đổi cấu trúc Database mà không cần xóa dữ liệu cũ.**

#### 

#### **Lệnh hỗ trợ: flask db init, flask db migrate, flask db upgrade.**

# 

### **✅ Fix Lỗi API Chatbot (CSRF Error):**

# 

#### **Vấn đề: API Chatbot gặp lỗi 400 Bad Request do bị chặn bởi cơ chế bảo vệ CSRF khi gọi từ AJAX.**

#### 

#### **Giải pháp: Sử dụng decorator @csrf.exempt cho endpoint /api/chatbot để cho phép giao tiếp API mượt mà mà vẫn giữ bảo mật cho các form khác.**

# 

### **✅ Fix Lỗi AI Smart Search (Bộ lọc thông minh):**

# 

#### **Vấn đề: Trước đây tìm kiếm "ốp lưng", "sạc" vẫn hiển thị cả điện thoại do AI chỉ lọc theo Hãng.**

#### 

#### **Giải pháp:**

#### 

#### **Prompt Engineering: Bắt buộc AI phân loại rõ ràng category: 'phone' hoặc category: 'accessory' dựa trên từ khóa.**

#### 

#### **Trích xuất Keyword: AI tự động lấy từ khóa chính (VD: "ốp", "tai nghe") để lọc chính xác tên sản phẩm.**

#### 

#### **Cache Versioning: Đổi key cache để xóa bỏ các kết quả phân tích cũ sai lệch.**

# 

### **✅ Fix Lỗi Giá Giỏ Hàng (Pricing Logic Security):**

# 

#### **Vấn đề: Giá sản phẩm lưu trong session. Nếu Admin tăng giá khi khách đang mua, khách vẫn thanh toán giá cũ.**

#### 

#### **Giải pháp: Tại bước thanh toán (checkout), hệ thống truy vấn lại giá thực tế từ Database để tính tổng tiền.**

# 

### **✅ Fix Lỗi Toàn Vẹn Dữ Liệu (Cascade Delete):**

# 

#### **Giải pháp: Thêm cấu hình cascade="all, delete-orphan" vào Model. Khi xóa sản phẩm, toàn bộ bình luận liên quan sẽ tự động được dọn dẹp.**

# 

### **✅ Tối ưu Cấu trúc Database (SQLAlchemy 2.0):**

# 

#### **Cập nhật: Thay thế cú pháp Model.query.get bằng db.session.get() giúp tối ưu hiệu suất và loại bỏ cảnh báo (LegacyAPIWarning).**

# 

### **✅ Fix Lỗi Xung Đột Thời Gian (Timezone TypeError):**

# 

#### **Giải pháp: Đồng bộ toàn bộ dữ liệu thời gian về dạng naive UTC (.replace(tzinfo=None)) để tương thích hoàn toàn với SQLite.**

# 

## **2. ✨ Tính Năng Mới: Bình Luận \& Đánh Giá (Reviews)**

# 

### **⭐ Hệ thống đánh giá 5 sao: Cho phép người dùng đăng nhập gửi đánh giá chất lượng sản phẩm.**

# 

### **💬 Bình luận thời gian thực: Hiển thị danh sách bình luận mới nhất kèm Avatar và tên người dùng.**

# 

## **3. 🎨 Nâng Cấp Giao Diện (UI/UX Optimization)**

# 

### **🏠 Trang Chủ (Homepage) - Giao diện Tết:**

# 

#### **Banner Tết Bính Ngọ: Banner tĩnh khổ lớn với hiệu ứng zoom nhẹ sang trọng.**

#### 

#### **Flash Sale: Khu vực khuyến mãi với đồng hồ đếm ngược (Countdown Timer).**

#### 

#### **Smart Search: Thanh tìm kiếm AI thiết kế dạng nổi (floating).**

# 

### **📱 Trang Chi Tiết (Product Detail):**

# 

#### **Image Gallery: Khung hiển thị ảnh sản phẩm gọn gàng, hỗ trợ zoom.**

#### 

#### **Variant Selection: Nút chọn Màu sắc/Phiên bản có chỉ báo "active".**

#### 

#### **Sticky Actions: Nút "Mua ngay" và "Thêm giỏ" thiết kế nổi bật.**

# 

### **🔔 Hệ thống Thông báo Thông minh (SweetAlert2):**

# 

#### **Thay thế Bootstrap Toasts bằng Pop-up SweetAlert2 mượt mà góc màn hình.**

# 

## **4. 📦 Quản Lý Tồn Kho Thực Tế (Inventory)**

# 

#### **Tồn kho tự động: Trừ kho ngay khi đặt hàng, hoàn kho khi hủy đơn (nếu đơn chưa xử lý).**

#### 

#### **Cảnh báo: Chặn mua nếu số lượng chọn lớn hơn tồn kho thực tế.**

# 

## **5. 🤖 Trí Tuệ Nhân Tạo (Gemini AI)**

# 

#### **Tìm Kiếm Thông Minh: Hiểu ngôn ngữ tự nhiên (VD: "iPhone giá rẻ dưới 10 triệu").**

#### 

#### **So Sánh Sản Phẩm: Kẻ bảng so sánh thông số chi tiết (HTML Table).**

#### 

#### **Chatbot: Trả lời tự động các câu hỏi thường gặp và tư vấn sản phẩm.**

#### 

#### **Chatbot Memory (MỚI): Ghi nhớ lịch sử hội thoại ngắn hạn (Contextual Awareness), giúp AI hiểu các đại từ như "nó", "cái đó" trong câu hỏi nối tiếp.**

# 

## **6. 🧪 Tái Cấu Trúc Hệ Thống Kiểm Thử (Testing Refactor)**

# 

#### **Dự án tích hợp hệ thống kiểm thử tự động, sử dụng DB ảo trên RAM (sqlite:///:memory:):**

#### 

#### **Unit Testing: Login, Cart, Phân quyền Admin.**

#### 

#### **Integration Testing: Toàn vẹn dữ liệu.**

#### 

#### **System Testing (E2E): Vòng đời đơn hàng (Mua -> Trừ kho -> Hủy -> Hoàn kho).**

#### 

#### **Hệ thống kiểm thử đã được tổ chức lại để chuyên nghiệp và dễ bảo trì hơn:**

# 

#### **✅ run\_tests.py: Script chạy toàn bộ test case chỉ với 1 lệnh (python run\_tests.py).**

#### 

#### **✅ Phân chia Module Test Rõ Ràng:**

#### 

#### **- test\_core.py: Kiểm tra chức năng cốt lõi (Đăng ký, Đăng nhập, Giỏ hàng, Thanh toán, Thu cũ). Thay thế cho các file cũ rời rạc.**

#### 

#### **- test\_ai.py: Kiểm tra chuyên sâu AI (Mocking API Gemini, Logic Fallback khi mất mạng, RAG Context).**

#### 

#### **- test\_security.py: Kiểm tra lỗ hổng bảo mật (IDOR, Tấn công Upload file).**

#### 

#### **- test\_integration\_system.py: Kiểm tra tích hợp hệ thống (End-to-End Flow).**

#### 

#### **✅ Dọn dẹp Code:**

#### 

#### **- Xóa bỏ các file test dư thừa trùng lặp (tests.py, test\_app.py, test\_features.py).**

#### 

#### **- Chuyển logic local\_analyze\_intent sang utils.py để tái sử dụng và kiểm thử độc lập.**

# 

## **7. 🌐 Sẵn Sàng Triển Khai (Production Ready)**

# 

#### **wsgi.py: Entry Point độc lập cho Production.**

#### 

#### **Procfile: Cấu hình cho Gunicorn (Linux/Heroku/Render).**

#### 

#### **Waitress: Hỗ trợ chạy server trên môi trường Windows.**

# 

## **8. 🛡️ Bảo Mật Nâng Cao**

# 

#### **✅ Ngăn Chặn Race Condition: Áp dụng khóa dòng (with\_for\_update()) khi thanh toán để tránh bán quá số lượng tồn kho.**

#### 

#### **✅ Bảo Mật CSRF: Tích hợp Flask-WTF bảo vệ toàn bộ Form.**

#### 

#### **✅ Chống DDoS Upload: Giới hạn MAX\_CONTENT\_LENGTH.**

#### 

#### **✅ Security Audit: Script test\_security.py quét lỗ hổng IDOR.**

## 

## **9. 📊 Dashboard Quản Trị (Admin Dashboard)**

# 

#### **📈 Real-time Analytics: Thống kê doanh thu từ đơn hàng "Completed".**

#### 

#### **📉 Biểu Đồ (Chart.js):**

#### 

#### **Biểu đồ đường: Doanh thu 7 ngày gần nhất.**

#### 

#### **Biểu đồ tròn: Tỷ lệ trạng thái đơn hàng.**

#### 

#### **🏆 Top Sản Phẩm: Xếp hạng 5 sản phẩm bán chạy nhất.**

# 

## **10. 🧠 Tối Ưu Hóa AI \& Persona**

# 

#### **AI Persona: Thiết lập tính cách nhân viên bán hàng vui vẻ, dùng emoji Tết (🧧, 🌸).**

#### 

#### **RAG Optimization: Cải thiện ngữ cảnh dữ liệu giúp AI nhận biết tình trạng "Hết hàng".**

#### 

#### **Refactor Code: Tách logic AI sang utils.py.**

# 

## **11. 💳 Thanh Toán Online Tự Động (VietQR)**

# 

#### **✅ Cổng Thanh Toán VietQR Động: Tự động tạo mã QR chính xác theo số tiền đơn hàng.**

#### 

#### **✅ Real-time Polling: Tự động kiểm tra trạng thái mỗi 3 giây (AJAX).**

#### 

#### **✅ Countdown Timer: Giao dịch hết hạn sau 3 phút để bảo mật tồn kho.**

#### 

#### **✅ Chế Độ Giả Lập (Local): Nút "Gửi tín hiệu ĐÃ NHẬN TIỀN" để test luồng thanh toán mà không cần chuyển khoản thật.**

# 

# **📂 Cấu Trúc Dự Án (Modular MVC)**

# 

## **MobileStore/**

#### **│**

#### **├── run.py                  # (ENTRY POINT) File chạy chính**

#### **├── run\_tests.py            # (TEST RUNNER) Script chạy toàn bộ test**

#### **├── wsgi.py                 # (PROD ENTRY) File chạy cho máy chủ thực tế**

#### **├── Procfile                # Cấu hình Web Server (Gunicorn)**

#### **├── migrations/             # (NEW) Thư mục chứa file migration DB**

#### **├── test\_core.py            # Test chức năng cơ bản (Core)**

#### **├── test\_ai.py              # Test tính năng AI (Mocking)**

#### **├── test\_security.py        # Test bảo mật**

#### **├── test\_integration\_system.py # Test tích hợp hệ thống**

#### **├── .env                    # Cấu hình bảo mật**

#### **├── requirements.txt        # Thư viện**

#### **│**

#### **└── app/                    # (PACKAGE) Source Code**

#### **├── \_\_init\_\_.py         # App Factory**

#### **├── extensions.py       # DB, Login, OAuth, Migrate, CSRF**

#### **├── models.py           # Database Models**

#### **├── utils.py            # AI Logic \& Helpers**

#### **│**

#### **├── templates/          # (VIEW) Giao diện HTML**

#### **└── routes/             # (CONTROLLER)**

#### **├── main.py         # Xử lý chính**

#### **├── auth.py         # Xác thực**

#### **└── admin.py        # Quản trị**

#### 

# 

# **🛠 Cài Đặt \& Chạy**

# 

## **Bước 1: Cài đặt thư viện**

# 

#### **pip install -r requirements.txt**

# 

# 

## **Bước 2: Cấu hình .env**

# 

#### **Tạo file .env và điền API Key (Gemini, Google OAuth, Secret Key).**

# 

## **Bước 3: Khởi tạo Database (QUAN TRỌNG)**

# 

#### **Do đã tích hợp Flask-Migrate, bạn chạy các lệnh sau để khởi tạo DB:**

#### 

#### **# 1. Khởi tạo môi trường migration (chỉ chạy lần đầu)**

#### **flask db init**

#### 

#### **# 2. Tạo file migration từ Models**

#### **flask db migrate -m "Initial migration"**

#### 

#### **# 3. Áp dụng vào Database**

#### **flask db upgrade**

# 

# 

## **Bước 4: Chạy Website (Local)**

# 

#### **python run.py**

# 

# 

### **👉 Truy cập: http://127.0.0.1:5000**

# 

## **Bước 5: Chạy Production (Windows)**

# 

#### **waitress-serve --port=5000 wsgi:app**

# 

# 

# **🔑 Tài Khoản Demo**

# 

# **Vai trò**

# 

# **Username**

# 

# **Password**

# 

# **Admin**

# 

# **admin**

# 

# **123456**

# 

# **Khách**

# 

# **khach**

# 

# **123456**

# 

# **Chúc bạn có trải nghiệm tuyệt vời với MobileStore phiên bản Tết 2026! 🚀🌸**

