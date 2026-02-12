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

# **📂 Cấu Trúc Dự Án (Modular MVC)**

# 

### **MobileStore/**

### **│**

### **├── run.py                  # (ENTRY POINT) File chạy chính**

### **├── .env                    # Cấu hình bảo mật**

### **├── requirements.txt        # Thư viện**

### **│**

### **└── app/                    # (PACKAGE) Source Code**

###     **├── \_\_init\_\_.py         # App Factory**

###     **├── extensions.py       # DB, Login, OAuth**

###     **├── models.py           # Database (User, Product, Order, Comment...)**

###     **├── utils.py            # AI Logic**

###     **│**

###     **├── templates/          # (VIEW) Giao diện HTML**

###     **│   ├── base.html       # Layout chung**

###     **│   ├── home.html       # Trang chủ (New UI)**

###     **│   ├── detail.html     # Chi tiết (Reviews added)**

###     **│   └── ...**

###     **│**

###     **└── routes/             # (CONTROLLER)**

###         **├── main.py         # Xử lý chính (Home, Cart, Comment)**

###         **├── auth.py         # Xác thực**

###         **└── admin.py        # Quản trị**

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

## **Bước 4: Chạy Website**

# 

#### **python run.py**

# 

# 

# **👉 Truy cập: http://127.0.0.1:5000**

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

# **Chúc bạn có trải nghiệm tuyệt vời với MobileStore phiên bản Tết 2026! 🚀🌸**

