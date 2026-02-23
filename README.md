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

### **✅ Sửa Lỗi Xung Đột Khởi Tạo Database (Migration):**

## 

#### **Vấn đề: Lệnh flask db migrate bị lỗi OperationalError do vòng lặp khởi tạo CSDL tự động trong run.py/wsgi.py.**

#### 

#### **Giải pháp: Xử lý và tối ưu hóa khối lệnh with app.app\_context(): bằng cách tạm thời ẩn lệnh initialize\_database() trong run.py/wsgi.py và thêm lệnh pass ( bỏ qua ) tránh việc lỗi thụt lề , cho phép chạy lệnh nâng cấp CSDL an toàn mà không làm mất dữ liệu hiện tại.**

# 

### **✅ Fix Lỗi API Chatbot (CSRF Error):**

# 

#### **Vấn đề: API Chatbot gặp lỗi 400 Bad Request do bị chặn bởi cơ chế bảo vệ CSRF khi gọi từ AJAX.**

#### 

#### **Giải pháp: Sử dụng decorator @csrf.exempt cho endpoint /api/chatbot để cho phép giao tiếp API mượt mà mà vẫn giữ bảo mật cho các form khác.**

# 

### **✅ Fix Lỗi \& Nâng Cấp Toàn Diện AI Smart Search (Hybrid Search):**

# 

#### **Vấn đề: Trước đây tìm kiếm đôi khi hiển thị kết quả rác (nhầm hãng) do logic Fallback mở rộng dùng phép toán OR, đồng thời AI chưa hiểu được các từ lóng ngữ nghĩa cao (như "pin trâu", "củ").**

#### 

#### **Giải pháp:**

#### 

#### **Hybrid Search (Tìm kiếm lai): Kết hợp hoàn hảo giữa SQL (lọc chính xác giá, hãng) và Vector DB (đọc hiểu ngữ nghĩa từ lóng, tính năng đặc thù).**

#### 

#### **Advanced Prompt Engineering (Few-Shot): Dạy AI cách quy đổi tiền tệ ("củ", "triệu" -> số 0), tự động sửa lỗi chính tả và phân loại cực chuẩn phụ kiện/điện thoại.**

#### 

#### **Fix Fallback Logic: Đổi toán tử OR thành AND ở bước tìm kiếm cuối cùng, triệt để ngăn chặn tình trạng "tìm Samsung hiển thị sạc Xiaomi".**

#### 

#### **Cache Versioning: Đổi key cache để làm sạch toàn bộ các kết quả phân tích cũ sai lệch.**

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

### **✅ Nâng Cấp Hệ Thống AI So Sánh (AI Battle):**

## 

#### **Vấn đề: AI đôi khi chỉ trả về phần tóm tắt ngắn, ngoài ra hệ thống lưu Cache cũ (câu trả lời ngắn) làm ảnh hưởng trải nghiệm.**

#### 

#### **Giải pháp: Tối ưu hóa hệ thống System Instruction \& Prompt, ép buộc AI sinh ra mã HTML chi tiết và đưa ra lời khuyên (Pros/Cons). Đổi cơ chế băm cache\_key để hệ thống luôn nạp kết quả phân tích chuyên sâu mới nhất.**

# 

## **2. ✨ Tính Năng Mới: Bình Luận \& Đánh Giá (Reviews)**

# 

### **✅ Hệ Thống Đánh Giá \& Bình Luận Chuyên Nghiệp:**

### 

#### **Nâng cấp: Tái thiết kế toàn bộ khối Đánh giá sản phẩm ở trang Chi tiết (detail.html) mang phong cách hiện đại của các trang TMĐT lớn.**

#### 

#### **Tính năng trực quan: Hiển thị Điểm số trung bình nổi bật, Tích hợp thanh tiến trình (Progress Bar) cho từng mức sao (1 đến 5 sao), và khung Đánh giá theo trải nghiệm (Hiệu năng, Pin, Camera).**

#### 

#### **Bộ lọc thông minh: Viết thêm thuật toán JavaScript hỗ trợ lọc Đánh giá/Bình luận mượt mà (Lọc theo số sao, Đã mua hàng...) không cần phải tải lại trang (No-reload).**

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

#### 

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

#### **run\_windows\_prod.py: Entry Point độc lập cho Production chạy môi trường Windows.**

#### 

#### **Waitress: Hỗ trợ chạy server trên môi trường Windows siêu nhẹ và chịu tải cao.**

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

#### **🧠 Tích hợp Data Science (Pandas): Áp dụng thư viện Pandas để phân tích dữ liệu thực tế, tìm ra "Khung giờ vàng" (Peak Hour) chốt đơn nhiều nhất và Sản phẩm bán chạy nhất tháng.**

#### 

#### **📑 Xuất Báo Cáo Excel Thông Minh: Sử dụng Pandas kết hợp openpyxl để render tự động file Excel báo cáo doanh thu, tự động căn chỉnh độ rộng cột và định dạng tiền tệ chuyên nghiệp cho Admin tải về.**

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

## **12. 🧠 Nâng Cấp AI: True RAG \& Vector Search (Hybrid)**

## 

#### **Chuyển đổi từ "Keyword Search" sang hệ thống "Hybrid Search" (Lai giữa Semantic và SQL):**

#### 

#### **✅ Tích hợp trực tiếp vào Thanh Tìm Kiếm: Thanh tìm kiếm chính giờ đây hiểu được cả thông số kỹ thuật lẫn nhu cầu sử dụng bằng từ lóng (Ví dụ: "máy chuyên chơi game", "pin trâu").**

#### 

#### **✅ Vector Database (ChromaDB): Lưu trữ dữ liệu sản phẩm dưới dạng Vector Embeddings thay vì text thuần.**

#### 

#### **✅ Gemini Embedding API: Chuyển đổi mô tả sản phẩm thành vector số học (768 chiều).**

#### 

#### **✅ Tìm Kiếm Ngữ Nghĩa: AI có thể tìm thấy sản phẩm phù hợp ngay cả khi không khớp từ khóa.**

#### 

#### **✅ Script Đồng Bộ (rag\_sync.py): Công cụ tự động quét Database và cập nhật lại Vector Index.**

# 

## **13. 🔄 Tự Động Hóa CI/CD (GitHub Actions)**

# 

#### **Thiết lập quy trình DevOps chuyên nghiệp:**

#### 

#### **✅ Automated Testing Pipeline: Mỗi khi push code lên GitHub, hệ thống tự động chạy toàn bộ bộ kiểm thử (run\_tests.py).**

#### 

#### **✅ Environment Isolation: Test chạy trên môi trường sạch (Ubuntu Latest + Python 3.12 + In-Memory DB).**

#### 

#### **✅ Quality Gate: Đảm bảo code lỗi không bao giờ được merge vào nhánh chính.**

# 

## **14. 🌟 Cập Nhật Giao Diện \& Tính Năng Mới Nhất (Hotfixes)**

## 

### **✅ Quản Trị Viên (Admin):**

## 

#### **- Cập nhật lỗi Admin Dashboard: Khôi phục lại Modal Form thêm mới sản phẩm (admin\_dashboard.html), cho phép nhập đầy đủ thông tin (Kho, Giá khuyến mãi, Trạng thái) và lưu vào Database.**

#### 

#### **- Nâng cấp Admin Dashboard với Pandas: Hiển thị thêm các insight dữ liệu thực tế (Khung giờ vàng, Sản phẩm mua nhiều) thay vì chỉ báo cáo thô, tích hợp nút Xuất file Excel doanh thu chuyên nghiệp.**

#### 

#### **- Giao diện Tabs Admin (MỚI): Chỉnh sửa CSS giúp các nút Tab (Sản phẩm, Đơn hàng, Thu cũ...) hiển thị chữ đen đậm, viền nổi bật không bị chìm vào nền trắng.**

#### 

#### **- Quản lý Đánh giá \& Trả lời (MỚI): Bảng quản lý bình luận được nâng cấp, phân loại rõ ràng (Tích cực/Tiêu cực/Câu hỏi). Bổ sung tính năng "Trả lời" trực tiếp ngay trong trang quản trị, gỡ bỏ hoàn toàn gửi cảnh báo qua Email (SMTP) để tránh làm nặng web.**

## 

### **✅ Chi Tiết Sản Phẩm (Product Detail):**

#### 

#### **- Hệ thống Hỏi \& Đáp (Q\&A) chuẩn CellphoneS (MỚI): Thiết kế một khu vực Hỏi \& Đáp hoàn toàn độc lập với phần đánh giá sao. Khách hàng có thể đặt câu hỏi và nhận phản hồi trực tiếp từ Admin (có dán nhãn Quản Trị Viên nổi bật). Hỗ trợ trả lời lồng nhau (Nested replies) cực kỳ chuyên nghiệp.**

#### 

#### **- Trick Database Thông minh (MỚI): Tái sử dụng bảng Comment với cấu trúc logic linh hoạt (rating = 0 cho Hỏi đáp, rating > 0 cho Đánh giá), giúp mở rộng hệ thống lớn mà không cần đụng chạm, sửa đổi cấu trúc Database (tránh được lỗi Constraint đặc thù của SQLite).**

## 

### **✅ Hồ Sơ Thành Viên (User Dashboard):**

## 

#### **- Tab Kho Voucher: Thiết kế giao diện thẻ ưu đãi (Tickets) đẹp mắt, chia bố cục rõ ràng giữa mức giảm và điều kiện áp dụng.**

#### 

#### **- Sổ Bảo Hành Điện Tử: Bổ sung bảng hiển thị danh sách các thiết bị đã mua, số IMEI/Serial ảo và thời gian hiệu lực bảo hành.**

#### 

#### **- 10 Đặc Quyền Hạng Thẻ: Thiết kế dạng lưới (Grid) trực quan hiển thị 10 quyền lợi M-Member (VD: Miễn phí giao hỏa tốc, Lỗi 1 đổi 1, Quà sinh nhật,...).**

#### 

#### **- Cập nhật Form Hồ Sơ: Bổ sung thêm các trường quan trọng gồm Giới tính (Select box) và Ngày tháng năm sinh (Date picker).**

#### 

#### **- Giới Thiệu Nhận Quà (Referral): Tự động tạo mã chia sẻ REF-ID độc quyền cho từng user kèm link chia sẻ. Tích hợp tính năng Copy nhạy bén với thông báo SweetAlert2.**

# 

## **15. ⚙️ Nâng Cấp Hệ Thống Backend \& Tiện Ích (Core System)**

## 

#### **- Hệ Thống Chạy Ngầm (Background Tasks): Tích hợp luồng chạy ngầm (tasks.py) tự động quét cơ sở dữ liệu mỗi 5 phút. Tự động chuyển các đơn hàng ở trạng thái "Pending" (Chờ thanh toán) quá hạn 15 phút sang "Cancelled" và hoàn trả lại số lượng sản phẩm vào kho, ngăn chặn tình trạng giam hàng ảo.**

#### 

#### **- Xử Lý Lỗi Toàn Cục (Global Error Handling): Xây dựng module errors.py bắt và xử lý các lỗi hệ thống phổ biến (404 Not Found, 403 Forbidden, 500 Internal Server Error). Thay vì hiển thị trang lỗi mặc định của máy chủ, hệ thống sẽ trả về trang giao diện error.html thân thiện, chuyên nghiệp giúp giữ chân khách hàng.**

#### 

#### **- Công Cụ Sao Lưu Dữ Liệu (Auto Backup): Tích hợp script backup\_db.py cho phép Admin sao lưu an toàn toàn bộ cơ sở dữ liệu (.db). Hệ thống tự động tìm file, copy, và nén thành file .zip gọn nhẹ kèm theo mốc thời gian (timestamp) chi tiết để dễ dàng phục hồi khi cần thiết.**

# 

## **16. 📈 Nâng Cấp Kiến Trúc Dữ Liệu \& Phân Tích (Big Data \& Performance)**

## 

#### **- Lõi Phân Tích Dữ Liệu (Sales Analytics Engine): Xây dựng module analytics\_engine.py ứng dụng thư viện Pandas để xử lý Big Data. Cung cấp các công cụ phân tích nâng cao như: Tính tỷ lệ giữ chân khách hàng (Retention Rate), Phân tích xu hướng doanh thu 7 ngày, và Phân tích RFM (Recency, Frequency, Monetary) để tự động lọc ra tệp Khách hàng VIP.**

#### 

#### **- Giả Lập Tải Nặng (Stress Test): Tích hợp kịch bản kiểm thử hiệu năng stress\_test.py. Tự động bơm hàng ngàn user, đơn hàng và lịch sử giao dịch ảo vào Database để kiểm tra sức chịu tải của hệ thống, đồng thời cung cấp nguồn khối lượng lớn dữ liệu để test các thuật toán Data Science \& AI.**

#### 

#### **- Quản Trị Vector AI (Vector Manager): Refactor toàn bộ logic ChromaDB thành class vector\_manager.py chuyên biệt. Hệ thống mã hóa ngôn ngữ tự nhiên thành Vector đa chiều (768 chiều) với model Google Embedding chuẩn xác, sẵn sàng mở rộng quy mô dữ liệu RAG.**

# 

## **17. 🕷️ Trí Tuệ Nhân Tạo \& Phân Tích Chuyên Sâu (Advanced ML \& Tracking)**

# 

#### **- Hệ Thống Học Máy Gợi Ý Sản Phẩm (ML Recommender): Xây dựng thuật toán Lọc Cộng Tác (Collaborative Filtering) trong file recommendation\_ml.py sử dụng Đại số tuyến tính của Numpy và Pandas. Hệ thống có khả năng tự động học hỏi từ hàng ngàn lịch sử giỏ hàng của người dùng để sinh ra Ma trận Độ Tương Đồng (Item-Item Similarity Matrix), từ đó đưa ra quyết định gợi ý mua kèm (Cross-sell) cực kỳ chuẩn xác.**

#### 

#### **- Hệ Thống Audit Log Chuyên Nghiệp (System Logger): Triển khai file system\_logger.py cấu hình RotatingFileHandler của Python. Tự động ghi lại nhật ký toàn bộ vòng đời của hệ thống (Access Log, Security Warning, Response Time). Chống tràn bộ nhớ bằng cơ chế tự động xoay vòng file log (max 5MB/file), hỗ trợ cực tốt cho quy trình DevOps \& Traceability.**

#### 

#### **- Robot Cào Dữ Liệu Đối Thủ (Competitor Web Scraper): Ứng dụng kỹ thuật Web Scraping với BeautifulSoup/Requests trong file competitor\_scraper.py. Tạo lập các kịch bản bot giả lập trình duyệt (Bypass Anti-bot) để tự động quét giá trị trường, so sánh độ chênh lệch giá của sản phẩm nội bộ so với đối thủ và xuất báo cáo tự động cho Admin.**

# 

## **18. 🛡️ Cơ Sở Hạ Tầng \& Bảo Mật Nâng Cao (Core Infrastructure)**

#### 

#### **- Hệ Thống Tường Lửa Web (WAF): Triển khai file security\_firewall.py bảo vệ ứng dụng khỏi các cuộc tấn công DDoS (Rate Limiting 60 req/min) và tự động quét/chặn các payload chứa mã độc XSS, SQL Injection từ người dùng.**

#### 

#### **- Hệ Thống Hàng Đợi Tác Vụ Nền (Job Queue): Xây dựng notification\_worker.py sử dụng kiến trúc Producer-Consumer với Threading. Tự động đẩy các tác vụ nặng (như gửi email sinh nhật, đồng bộ Vector DB) xuống chạy ngầm, đảm bảo giao diện người dùng luôn mượt mà và không bị gián đoạn.**

#### 

#### **- Hệ Thống Phân Tích Nhật Ký (Log Analyzer): Tích hợp script log\_analyzer.py sử dụng Regex và Counter để đọc file access.log. Tự động thống kê lượng truy cập, nhận diện các IP có dấu hiệu spam và báo cáo các API xử lý chậm để tối ưu.**

# 

## **19. 🧱 Chuẩn Hóa Mã Nguồn \& Clean Code (Refactoring)**

## 

#### **- Hệ Thống Hằng Số Tập Trung (Constants Manager): Tạo file constants.py để tách toàn bộ các chuỗi văn bản cứng (hardcode strings) như: Trạng thái đơn hàng, Từ khóa AI, Cấu hình Chatbot, và Thông báo lỗi ra khỏi logic chính. Giúp mã nguồn tuân thủ triệt để nguyên tắc SOLID, dễ dàng bảo trì và đồng bộ đa ngôn ngữ sau này.**

#### 

#### **- Refactor Controllers (main.py \& admin.py): Cập nhật toàn bộ logic xử lý chính để import và sử dụng các biến hằng số từ constants.py. Loại bỏ 100% "magic strings" (chuỗi rác) trong mã nguồn, giúp code an toàn hơn, tránh sai sót do gõ nhầm text và chuẩn bị sẵn sàng cho các đợt scale-up hệ thống lớn.**

# 

# **📂 Cấu Trúc Dự Án (Modular MVC)**

# 

## **MobileStore/**

#### **│**

#### **├── run.py                  # (ENTRY POINT) File chạy chính**

#### **├── competitor\_scraper.py   # (BOT) Robot thu thập dữ liệu giá đối thủ**

#### **├── backup\_db.py            # (UTILS) Script tự động sao lưu Database**

#### **├── log\_analyzer.py         # (UTILS) Phân tích nhật ký hệ thống**

#### **├── run\_tests.py            # (TEST RUNNER) Script chạy toàn bộ test**

#### **├── rag\_sync.py             # (AI SYNC) Script đồng bộ Vector DB (ChromaDB)**

#### **├── run\_windows\_prod.py   # Khởi chạy Server Production cho Windows** 

#### **├── migrations/             # (NEW) Thư mục chứa file migration DB**

#### **├── test\_core.py            # Test chức năng cơ bản (Core)**

#### **├── test\_ai.py              # Test tính năng AI (Mocking)**

#### **├── test\_security.py        # Test bảo mật**

#### **├── test\_models.py        # Test cấu trúc Database**

#### **├── test\_auth.py        # Test xác thực \& Đăng nhập**

#### **├── test\_integration\_system.py # Test tích hợp hệ thống**

#### **├── test\_ml.py              # (TEST) thuật toán Machine Learning**

#### **├── stress\_test.py          # (TEST) Script giả lập tải nặng \& bơm data ảo**

#### **├── test\_infrastructure.py  # Test hệ thống Firewall , Hàng đợi tác vụ**

#### **├── .env                    # Cấu hình bảo mật**

#### **├── requirements.txt        # Thư viện**

#### **│**

#### **└── app/                    # (PACKAGE) Source Code**

#### **├── \_\_init\_\_.py         # App Factory**

#### **├── extensions.py       # DB, Login, OAuth, Migrate, CSRF**

#### **├── models.py           # Database Models**

#### **├── utils.py            # AI Logic \& Helpers**

#### **├── tasks.py            # Hệ thống quét và chạy ngầm**

#### **├── errors.py           # Bộ xử lý lỗi toàn cục**

#### **├── vector\_manager.py   # Quản trị Vector DB (ChromaDB)**

#### **├── analytics\_engine.py # Lõi phân tích dữ liệu bán hàng (Pandas)**

#### **├── recommendation\_ml.py# Thuật toán AI Lọc Cộng tác (Machine Learning)**

#### **├── security\_firewall.py  # Tường lửa bảo mật WAF (Chống DDoS/XSS)**

#### **├── notification\_worker.py # Hàng đợi xử lý tác vụ nền (Queue)**

#### **├── constants.py        # Quản lý hằng số hệ thống (Clean Code)**

#### **│**

#### **├── templates/          # (VIEW) Giao diện HTML**

#### **└── routes/             # (CONTROLLER)**

#### **├── main.py         # Xử lý chính**

#### **├── auth.py         # Xác thực**

#### **└── admin.py        # Quản trị**

#### **├── .github/                # (CI/CD) Cấu hình GitHub Actions**

#### **│   └── workflows/**

#### **│       └── ci\_cd.yml**

# 

# **🛠 Cài Đặt \& Chạy**

# 

## **Bước 1: Cài đặt thư viện**

# 

#### **py -m pip install -r requirements.txt**

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

#### **py -m flask db init**

#### 

#### **# 2. Tạo file migration từ Models**

#### **py -m flask db migrate -m "Initial migration"**

#### 

#### **# 3. Áp dụng vào Database**

#### **py -m flask db upgrade**

# 

## **Bước 4: Đồng bộ Vector Database (Cho AI)**

# 

#### **Chạy lệnh này để AI "học" dữ liệu sản phẩm lần đầu:**

#### 

#### **py rag\_sync.py**

# 

## **Bước 5: Chạy Website (Local)**

## 

#### **py run.py**

## 

### **👉 Truy cập: http://127.0.0.1:5000**

## 

## **Bước 6: Chạy Production (Chế độ Doanh nghiệp trên Windows)**

## 

#### **Hệ điều hành Windows không hỗ trợ Gunicorn, vì vậy dự án đã thiết lập hệ thống máy chủ Waitress WSGI có khả năng chịu tải cao, hỗ trợ đa luồng (multi-threading).**

#### 

#### **Chỉ cần chạy lệnh sau để bật Server chuẩn Production:**

#### 

#### **py run\_windows\_prod.py**

# 

# **🔑 Tài Khoản Demo**

# 

## **Vai trò**

## 

## **Username**

## 

## **Password**

## 

## **Admin**

# 

#### **admin**

#### 

#### **123456**

# 

## **Khách**

# 

#### **khach**

#### 

#### **123456**

# 

# **Chúc bạn có trải nghiệm tuyệt vời với MobileStore phiên bản Tết 2026! 🚀🌸**

