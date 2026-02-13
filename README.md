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

### **✅ Fix Lỗi API Chatbot (CSRF Error): (MỚI)**

# 

#### **Vấn đề: API Chatbot gặp lỗi 400 Bad Request do bị chặn bởi cơ chế bảo vệ CSRF khi gọi từ AJAX.**

#### 

#### **Giải pháp: Sử dụng decorator @csrf.exempt cho endpoint /api/chatbot để cho phép giao tiếp API mượt mà mà vẫn giữ bảo mật cho các form khác.**

# 

### **✅ Fix Lỗi AI Smart Search (Bộ lọc thông minh): (MỚI)**

# 

#### **Vấn đề: Trước đây tìm kiếm "ốp lưng", "sạc" vẫn hiển thị cả điện thoại do AI chỉ lọc theo Hãng.**

#### 

#### **Giải pháp:**

#### 

#### **1. Cập nhật Prompt Engineering: Bắt buộc AI phân loại rõ ràng category: 'phone' hoặc category: 'accessory' dựa trên từ khóa.**

#### 

#### **2. Trích xuất Keyword chuyên sâu: AI tự động lấy từ khóa chính (VD: "ốp", "tai nghe") để lọc chính xác tên sản phẩm.**

#### 

#### **3. Cache Versioning: Đổi key cache (v3) để xóa bỏ các kết quả phân tích cũ sai lệch, buộc hệ thống chạy lại logic mới.**

# 

### **✅ Fix Lỗi Giá Giỏ Hàng (Pricing Logic Security):**

# 

#### **Vấn đề: Trước đây, giá sản phẩm được lưu trong session giỏ hàng. Nếu Admin tăng giá sản phẩm trong lúc khách đang chọn mua, khách vẫn thanh toán với giá cũ.**

#### 

#### **Giải pháp: Tại bước thanh toán (checkout), hệ thống hiện truy vấn lại giá thực tế từ Database để tính tổng tiền, đảm bảo tính chính xác và bảo mật doanh thu.**

# 

## **✅ Fix Lỗi Toàn Vẹn Dữ Liệu (Cascade Delete):**

# 

#### **Vấn đề: Khi xóa một sản phẩm, các dữ liệu liên quan (như bình luận) còn sót lại gây lỗi Foreign Key hoặc rác dữ liệu.**

#### 

#### **Giải pháp: Thêm cấu hình cascade="all, delete-orphan" vào Model. Khi xóa sản phẩm, toàn bộ bình luận liên quan sẽ tự động được dọn dẹp.**

# 

## **✅ Tối ưu Cấu trúc Database (SQLAlchemy 2.0): (MỚI)**



# 

#### **Cập nhật: Thay thế toàn bộ cú pháp truy vấn cũ (Model.query.get) bằng chuẩn mới của SQLAlchemy 2.0 (db.session.get()) giúp tối ưu hiệu suất và loại bỏ hoàn toàn các cảnh báo (LegacyAPIWarning).**

# 

# **2. ✨ Tính Năng Mới: Bình Luận \& Đánh Giá (Reviews)**

# 

## **⭐ Hệ thống đánh giá 5 sao:**

# 

#### **Cho phép người dùng đăng nhập gửi đánh giá chất lượng sản phẩm từ 1 đến 5 sao.**

#### 

#### **Giao diện nhập liệu trực quan với các ngôi sao tương tác.**

#### 

#### **💬 Bình luận thời gian thực:**

#### 

#### **Hiển thị danh sách bình luận mới nhất ngay dưới trang chi tiết sản phẩm.**

#### 

#### **Hiển thị thông tin người dùng (Avatar, Tên) và thời gian gửi.**

# 

# **3. 🎨 Nâng Cấp Giao Diện (UI/UX Optimization)**

# 

## **🏠 Trang Chủ (Homepage) - Giao diện Tết:**

# 

#### **Banner Tết Bính Ngọ: Banner tĩnh khổ lớn với hiệu ứng zoom nhẹ (hover) sang trọng.**

#### 

#### **Flash Sale: Khu vực khuyến mãi với đồng hồ đếm ngược (Countdown Timer) sống động.**

#### 

#### **Smart Search: Thanh tìm kiếm AI thiết kế dạng nổi (floating), đẹp mắt và dễ sử dụng.**

#### 

#### **Tiện ích: Các icon cam kết (Giao hỏa tốc, Bảo hành vàng...) được thiết kế lại hiện đại.**

# 

## **📱 Trang Chi Tiết (Product Detail):**

# 

#### **Image Gallery: Khung hiển thị ảnh sản phẩm gọn gàng, hỗ trợ zoom khi di chuột.**

#### 

#### **Variant Selection: Nút chọn Màu sắc/Phiên bản có chỉ báo "active" (dấu tick) rõ ràng.**

#### 

#### **Sticky Actions: Nút "Mua ngay" và "Thêm giỏ" được thiết kế nổi bật, đổ bóng 3D.**

# 

## **🔔 Hệ thống Thông báo Thông minh (SweetAlert2): (MỚI)**

#### 

#### **Thay thế hoàn toàn Bootstrap Toasts mặc định.**

#### 

#### **Các thông báo (Thêm giỏ hàng thành công, Lỗi đăng nhập, Cảnh báo kho hàng) giờ đây hiển thị dưới dạng Pop-up góc màn hình cực kỳ mượt mà, có thanh thời gian tự động ẩn.**

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

#### **So Sánh Sản Phẩm: Kẻ bảng so sánh thông số chi tiết.**

#### 

#### **Chatbot: Trả lời tự động các câu hỏi thường gặp.**

# 

## **6. 🧪 Kiểm Thử Tự Động (Automated Testing) (MỚI)**

# 



#### **Dự án đã được tích hợp hệ thống kiểm thử tự động, sử dụng DB ảo trên RAM (sqlite:///:memory:) đảm bảo không ảnh hưởng dữ liệu thật:**

#### 

#### **Unit Testing: Kiểm tra luồng Đăng nhập, Giỏ hàng, Phân quyền bảo mật Admin.**

#### 

#### **Integration Testing: Đảm bảo toàn vẹn dữ liệu (xóa sản phẩm tự động xóa bình luận).**

#### 

#### **System Testing (E2E): Giả lập vòng đời đơn hàng hoàn chỉnh (Khách mua hàng -> Trừ kho -> Admin hủy đơn -> Hoàn lại kho an toàn).**

# 



## **7. 🌐 Sẵn Sàng Triển Khai (Production Ready) (MỚI)**

# 



#### **Dự án đã được cấu hình sẵn sàng để đẩy lên các máy chủ thực tế (VPS, Render, Heroku...):**

#### 

#### **Tích hợp wsgi.py làm Entry Point độc lập.**

#### 

#### **Cấu hình sẵn Procfile cho Gunicorn (môi trường Linux).**

#### 

#### **Hỗ trợ chạy máy chủ ảo hóa bằng Waitress trên môi trường Windows.**

# 

# **📂 Cấu Trúc Dự Án (Modular MVC)**

# 

### **MobileStore/**

### **│**

### **├── run.py                  # (ENTRY POINT) File chạy chính**

#### **├── wsgi.py                 # (PROD ENTRY) File chạy cho máy chủ thực tế**

#### **├── Procfile                # Cấu hình Web Server (Gunicorn)**

#### **├── test\_\*.py               # Các kịch bản kiểm thử tự động**

#### **├──test\_security.py         # Kiểm thử bảo mật chuyên biệt**

### **├── .env                    # Cấu hình bảo mật**

### **├── requirements.txt        # Thư viện**

### **│**

### **└── app/                    # (PACKAGE) Source Code**

### **├── \_\_init\_\_.py         # App Factory**

### **├── extensions.py       # DB, Login, OAuth**

### **├── models.py           # Database (User, Product, Order, Comment...)**

### **├── utils.py            # AI Logic**

### **│**

### **├── templates/          # (VIEW) Giao diện HTML**

### **│   ├── base.html       # Layout chung**

### **│   ├── home.html       # Trang chủ (New UI)**

### **│   ├── detail.html     # Chi tiết (Reviews added)**

### **│   └── ...**

### **│**

### **└── routes/             # (CONTROLLER)**

### **├── main.py         # Xử lý chính (Home, Cart, Comment)**

### **├── auth.py         # Xác thực**

### **└── admin.py        # Quản trị**

# 

# 

# **🛠 Cài Đặt \& Chạy**

# 

## **Bước 1: Cài đặt**

# 

#### **pip install -r requirements.txt**

# 

# 

## **Bước 2: Cấu hình .env**

# 

#### **Tạo file .env và điền API Key (Gemini, Google OAuth, Secret Key).**

# 

## **Bước 3: Khởi tạo Database (BẮT BUỘC)**

# 

#### **Do có thêm bảng Comment và các quan hệ mới, hãy:**

#### 

#### **Xóa file mobilestore.db cũ.**

#### 

#### **Chạy lại server để hệ thống tự tạo DB mới.**

# 

## **Bước 4: Chạy Website (Môi trường Phát triển)**

# 

#### **python run.py**

#### **👉 Truy cập: http://127.0.0.1:5000**

# 

## **Bước 5: Chạy Website (Môi trường Thực tế - Windows)**

## 

#### **pip install waitress**

#### **waitress-serve --port=5000 wsgi:app**

# 



# **🔑 Tài Khoản Demo**

# 

#### **Vai trò**

#### 

#### **Username**

#### 

#### **Password**

#### 

#### **Admin**

#### 

#### **admin**

#### 

#### **123456**

#### 

#### **Khách**

#### 

#### **khach**

#### 

#### **123456**

# 

# **8. 🛡️ Cập Nhật Bảo Mật Nâng Cao \& Tối Ưu Hóa (Vừa Cập Nhật)**

# 

#### **Dự án vừa trải qua đợt đánh giá bảo mật (Security Audit) và đã khắc phục triệt để các rủi ro:**

# 

## **✅ Ngăn Chặn Race Condition (Tranh chấp tài nguyên):**

#### 

* #### **Áp dụng kỹ thuật khóa dòng bi quan (Pessimistic Locking - with\_for\_update()) vào logic thanh toán (checkout). Khắc phục hoàn toàn lỗi âm kho khi có nhiều khách hàng cùng bấm thanh toán một sản phẩm tại cùng một thời điểm.**

# 

## **✅ Củng Cố Bảo Mật CSRF (Cross-Site Request Forgery):**

#### 

* #### **Tích hợp thư viện Flask-WTF giúp tự động sinh và kiểm chứng CSRF Token cho toàn bộ các Form trên hệ thống (Login, Register, Checkout, Admin), ngăn chặn hacker đánh cắp phiên và giả mạo thao tác.**

# 

## **✅ Phòng Chống Tấn Công DDoS Upload:**

* #### **Khẳng định tính an toàn trước các thủ đoạn DDoS thông qua việc cố tình tải lên file rác cực lớn nhờ cấu hình MAX\_CONTENT\_LENGTH chặt chẽ.**

# 

## **✅ Fix Cảnh Báo Deprecation Python:**

#### 

* #### **Cập nhật code import đối tượng thời gian theo chuẩn mới nhất của Python (from datetime import datetime, timezone), làm sạch hoàn toàn terminal khỏi các dòng cảnh báo cũ.**

# 

## **✅ Tích Hợp Kịch Bản Penetration Testing:**

#### 

* #### **Bổ sung thêm script kiểm thử bảo mật chuyên biệt test\_security.py giúp tự động quét và ngăn chặn lỗ hổng IDOR (Insecure Direct Object Reference).**

# 

# **9. 📊 Dashboard Quản Trị \& Analytics (Admin Dashboard) (MỚI NHẤT)**

# 

#### **Hệ thống quản trị viên đã được nâng cấp toàn diện với khả năng phân tích dữ liệu trực quan, giúp chủ cửa hàng nắm bắt tình hình kinh doanh tức thì:**

# 

## **📈 Thống Kê Doanh Thu Thực Tế (Real-time Analytics):**

# 

#### **Tổng hợp doanh thu chính xác từ các đơn hàng có trạng thái "Completed".**

#### 

#### **Hiển thị các chỉ số quan trọng (Key Metrics) ngay đầu trang: Tổng doanh thu, Tổng đơn hàng, Số lượng thành viên, Tổng sản phẩm tồn kho.**

# 

## **📉 Biểu Đồ Trực Quan (Chart.js Integration):**

# 

#### **Tích hợp thư viện Chart.js nhẹ và mượt mà để vẽ biểu đồ động:**

#### 

#### **Biểu đồ đường (Line Chart): Theo dõi biến động doanh thu trong 7 ngày gần nhất.**

#### 

#### **Biểu đồ tròn (Doughnut Chart): Phân tích tỷ lệ trạng thái đơn hàng (Chờ xử lý, Đang giao, Hoàn thành, Hủy).**

# 

## **🏆 Top Sản Phẩm Bán Chạy (Best Sellers):**

# 

#### **Tự động thống kê và xếp hạng 5 sản phẩm có số lượng bán ra cao nhất hệ thống.**

#### 

#### **Giúp Admin dễ dàng nhận biết xu hướng mua sắm để nhập hàng phù hợp.**

# 

# **10. 🧠 Tối Ưu Hóa AI \& Kiểm Thử Nâng Cao (Mới Nhất)**

# 

## **✅ Nâng Cấp Trí Tuệ Nhân Tạo (AI Persona \& RAG):**

# 

#### **Tối ưu hóa utils.py để "thổi hồn" cho Chatbot:**

#### 

#### **System Persona (Nhân cách hệ thống): Thiết lập tính cách cho AI là một nhân viên bán hàng thân thiện, vui vẻ, mang đậm không khí Tết Bính Ngọ (sử dụng emoji 🧧, 🌸).**

#### 

#### **Prompt Engineering: Cải thiện câu lệnh (prompt) để AI trả lời ngắn gọn, biết in đậm giá tiền và luôn gợi ý khách mua thêm (Upsell).**

#### 

#### **RAG Optimization: Cấu trúc lại dữ liệu sản phẩm nạp vào ngữ cảnh (Context) giúp AI hiểu rõ tình trạng "Sẵn hàng" hay "Hết hàng" để tư vấn chính xác hơn.**

# 

## **✅ Refactor Code (Tái cấu trúc):**

# 

#### **Cleaner Architecture: Chuyển toàn bộ logic xử lý AI từ main.py sang utils.py (generate\_chatbot\_response), giúp code gọn gàng và dễ bảo trì hơn.**

# 

## **✅ Bổ Sung Unit Test Chuyên Sâu (test\_new\_features.py):**

# 

### **1. Kiểm thử tính năng Thu Cũ Đổi Mới (Trade-In):**

# 

#### **Kiểm tra bắt buộc đăng nhập.**

#### 

#### **Kiểm tra luồng gửi yêu cầu thành công.**

#### 

#### **Security Test: Ngăn chặn upload file không hợp lệ (ví dụ: file .txt giả danh ảnh).**

#### 

### **2. Kiểm thử Chatbot (Mocking Technique):**

# 

#### **Mocking API: Sử dụng kỹ thuật unittest.mock để giả lập phản hồi từ Google Gemini. Điều này giúp chạy test siêu tốc, không cần mạng và không tốn quota API Key.**

#### 

#### **Kiểm tra logic phản hồi theo từ khóa (Rule-based) và phản hồi từ AI.**

# 

# **Chúc bạn có trải nghiệm tuyệt vời với MobileStore phiên bản Tết 2026! 🚀🌸**

