# **📱 MobileStore - Siêu Thị Điện Thoại Thông Minh Tích Hợp AI (Phiên Bản Tết 2026 - Modular MVC)**

# 

## **Chào mừng bạn đến với MobileStore! Đây là dự án throng mại điện tử hiện đại được xây dựng bằng Python Flask, tích hợp sâu Google Gemini AI.**

## 

## **Phiên bản này đã được Tái cấu trúc (Refactor) toàn diện sang mô hình Modular MVC (Model-View-Controller) sử dụng Flask Blueprints, giúp mã nguồn chuyên nghiệp, dễ bảo trì và mở rộng hơn.**

# 

# **🚀 Các Cập Nhật Mới Nhất (Latest Updates)**

# 

## **1. 📦 Quản Lý Tồn Kho Thực Tế (Inventory Management)**

# 

### **Tồn kho tự động: Hệ thống tự động trừ số lượng sản phẩm trong kho ngay khi khách hàng đặt hàng thành công.**

### 

### **Hoàn kho thông minh: Tự động cộng lại số lượng vào kho khi khách hàng hoặc Admin thực hiện lệnh "Hủy đơn" (chỉ áp dụng cho đơn chưa xử lý).**

### 

### **Cảnh báo hết hàng: Ngăn chặn khách hàng thêm sản phẩm vào giỏ hoặc thanh toán nếu số lượng trong kho không đủ.**

### 

### **Quản trị: Admin có thể theo dõi và chỉnh sửa số lượng tồn kho trực tiếp trong phần chỉnh sửa sản phẩm.**

# 

## **2. 📊 Bộ Lọc Sắp Xếp Động (Dynamic Sorting)**

# 

### **Sắp xếp tại Admin: Tại Dashboard, Admin có thể nhấp vào tiêu đề các cột: ID, Tên sản phẩm, Giá bán, Tồn kho để sắp xếp tăng/giảm dần ngay lập tức mà không cần tải lại trang.**

### 

### **Giao diện trực quan: Hiển thị icon mũi tên (sort-up/sort-down) để nhận biết cột đang được sắp xếp.**

# 

## **3. 👥 Quản Lý Người Dùng \& Hồ Sơ (User \& Profile)**

# 

### **Danh sách thành viên: Admin có thêm tab "Người dùng" để xem toàn bộ danh sách khách hàng, bao gồm ảnh đại diện, email và vai trò (Admin/User).**

### 

### **Tùy biến cá nhân: Người dùng có thể tự thay đổi Họ tên và Ảnh đại diện (Avatar). Hệ thống hỗ trợ upload file ảnh thực tế và lưu trữ an toàn trong thư mục static/uploads.**

### 

## **4. 🔒 Bảo Mật \& Phục Hồi Mật Khẩu (Security)**

# 

### **Quên mật khẩu: Tích hợp quy trình phục hồi mật khẩu qua Email (Simulation). Hệ thống tạo Token an toàn có thời hạn 15 phút.**

### 

### **Đặt lại mật khẩu: Link reset được gửi (hiển thị tại Server Console) cho phép người dùng thiết lập mật khẩu mới khi lỡ quên.**

# 

### **Google OAuth: Đăng nhập nhanh bằng tài khoản Google, tự động khởi tạo tài khoản nếu email chưa tồn tại trên hệ thống.**



# **✨ Cập Nhật Kiến Trúc Phần Mềm (New Architecture)**

# 

### **Dự án đã chuyển từ cấu trúc Monolithic (tất cả trong 1 file app.py) sang cấu trúc Modular MVC:**

# 

## **1. 🏗️ Mô Hình Modular MVC:**

# 

### **Model (M): File app/models.py - Quản lý dữ liệu và cấu trúc Database (User, Product, Order...).**

### 

### **View (V): Thư mục app/templates/ - Giao diện HTML hiển thị cho người dùng.**

### 

### **Controller (C): Thư mục app/routes/ - Xử lý logic nghiệp vụ và điều hướng request.**

### 

### **auth.py: Xử lý Đăng nhập, Đăng ký, Google OAuth.**

### 

### **admin.py: Xử lý Dashboard quản trị, CRUD sản phẩm.**

### 

### **main.py: Xử lý Trang chủ, Giỏ hàng, Chatbot, So sánh AI.**

# 

## **2. 🔌 Application Factory Pattern:**

# 

### **Sử dụng app/\_\_init\_\_.py để khởi tạo ứng dụng, giúp quản lý cấu hình và extensions (DB, Login) tập trung, tránh lỗi vòng lặp (circular imports).**

# 

## **3. 🚀 Entry Point Mới:**

# 

### **File run.py ở thư mục gốc đóng vai trò là điểm khởi chạy duy nhất của ứng dụng.**

# 

# **✨ Các Tính Năng Nghiệp Vụ (Features)**

# 

## **1. 🤖 Trí Tuệ Nhân Tạo (Gemini AI Integration)**

# 

### **Tìm Kiếm Thông Minh (Smart Search): Hiểu ngôn ngữ tự nhiên (VD: "iPhone giá rẻ dưới 10 triệu").**

### 

### **So Sánh Sản Phẩm (AI Comparison): Kẻ bảng so sánh thông số và đưa ra lời khuyên mua sắm.**

### 

### **Gợi Ý Phụ Kiện: Tự động đề xuất phụ kiện phù hợp khi xem điện thoại.**

### 

### **Chatbot Hybrid: Kết hợp trả lời kịch bản và AI, có cơ chế Caching để tiết kiệm quota API.**

# 

## **2. 🎨 Quản Lý Biến Thể Sản Phẩm**

# 

### **Hệ thống Màu sắc \& Phiên bản: Admin có thể thêm tùy chọn màu/dung lượng không giới hạn.**

### 

### **Ảnh \& Giá Động: Khách chọn màu -> Đổi ảnh; Chọn dung lượng -> Đổi giá tiền.**

# 

## **3. ♻️ Nghiệp Vụ Thu Cũ Đổi Mới (Trade-in)**

## 

## **Khách hàng gửi ảnh và mô tả tình trạng máy cũ.**

## 

## **Admin nhận yêu cầu, xem ảnh thực tế và thực hiện Định giá thu mua.**

## 

## **Khách hàng theo dõi kết quả định giá ngay tại trang cá nhân.**



# 

# **📂 Cấu Trúc Thư Mục Mới (Project Structure)**

# 

### **MobileStore/**

### **│**

### **├── run.py                  # (ENTRY POINT) File chạy chính của ứng dụng**

### **├── .env                    # Cấu hình bảo mật (API Key, Secret Key)**

### **├── requirements.txt        # Danh sách thư viện**

### **├── mobilestore.db          # Database SQLite**

### **│**

### **└── app/                    # (PACKAGE) Thư mục chứa Source Code**

### **├── \_\_init\_\_.py         # Khởi tạo App, DB, Login, đăng ký Blueprints**

### **├── extensions.py       # Khởi tạo các công cụ (SQLAlchemy, LoginManager, OAuth)**

### **├── models.py           # Định nghĩa Database (User, Product, Order, AICache)**

### **├── utils.py            # Logic gọi AI và xử lý dữ liệu**

### **│**

### **├── templates/          # (VIEW) Giao diện HTML**

### **│   ├── base.html       # Layout chung**

### **│   ├── home.html       # Trang chủ**

### **│   ├── admin\_\*.html    # Giao diện Admin**

### **│   └── ...             # Các file HTML khác**

### **│**

### **└── routes/             # (CONTROLLER) Các bộ điều khiển**

### **├── main.py         # Xử lý: Home, Cart, Chatbot, So sánh**

### **├── auth.py         # Xử lý: Login, Register, Logout, Google**

### **└── admin.py        # Xử lý: Dashboard, Thêm/Sửa/Xóa sản phẩm**

# 

# 

# **🛠 Cài Đặt \& Chạy Dự Án**

# 

## **Bước 1: Cài đặt thư viện**

# 

### **Mở Terminal tại thư mục dự án và chạy:**

### 

### **pip install -r requirements.txt**

# 

# 

## **Bước 2: Cấu hình Môi trường (.env)**

# 

### **Tạo file .env và điền các thông tin sau:**

### 

### **SECRET\_KEY=chuoi-bi-mat-bao-mat-flask-123**

### **GEMINI\_API\_KEY=Dien\_API\_Key\_Gemini\_Cua\_Ban\_Vao\_Day**

### **GOOGLE\_CLIENT\_ID=Dien\_Client\_ID\_Google**

### **GOOGLE\_CLIENT\_SECRET=Dien\_Client\_Secret\_Google**

# 

# 

## **Bước 3: Khởi tạo Database (Quan Trọng)**

# 

### **Nếu bạn gặp lỗi hiển thị hoặc muốn nạp lại dữ liệu mẫu theo cấu trúc mới:**

### 

### **Xóa file mobilestore.db cũ (nếu có) để hệ thống tự tạo cấu hình bảng mới nhất (có cột stock\_quantity và avatar\_url).**







## **Bước 4: Chạy Website**

# 

### **Lưu ý: Không chạy python app.py nữa mà chạy file run.py.**

### 

### **python run.py**

# 

# 

## **👉 Truy cập: http://127.0.0.1:5000**

## 

## **🔑 Tài Khoản Demo (Seed Data)**

## 

## **Khi khởi chạy lần đầu (sau khi xóa DB cũ), hệ thống tạo sẵn:**

## 

## **Vai trò**

## 

## **Username**

## 

## **Password**

## 

## **Admin**

## 

## **admin**

## 

## **123456**

## 

## **Khách**

## 

## **khach**

## 

## **123456**

# 

# **📝 Ghi Chú Khắc Phục Lỗi (Troubleshooting)**

# 

* ## **Lỗi ModuleNotFoundError: No module named 'extensions':**

## 

## **Do import sai đường dẫn tương đối. Trong gói app, hãy dùng from .extensions import db.**

## 

* ## **Lỗi sqlite3.OperationalError: no such column...:**

## 

## **Do cấu trúc bảng thay đổi. Hãy xóa file .db và chạy lại python run.py.**

## 

* ## **Lỗi SyntaxError: Unexpected token (JSON Parse):**

## 

## **Đã được khắc phục bằng cách xử lý JSON tại Backend (Python) thay vì Frontend.**

# 

# **Chúc bạn thành công với kiến trúc Modular MVC chuyên nghiệp này! 🚀**

