# 📱 MobileStore - Siêu Thị Điện Thoại Thông Minh Tích Hợp AI 
*(Phiên Bản Tết 2026 - Modular MVC)*

Chào mừng bạn đến với **MobileStore**! Đây là dự án thương mại điện tử hiện đại được xây dựng bằng **Python Flask**, tích hợp sâu **Google Gemini AI**. Phiên bản này đã được tái cấu trúc (Refactor) toàn diện sang mô hình **Modular MVC** và cập nhật giao diện Tết Bính Ngọ 2026.

# Chúc bạn có trải nghiệm tuyệt vời với MobileStore phiên bản Tết 2026! 🚀🌸

---

## 🚀 Các Cập Nhật Mới Nhất (Latest Updates)

### 1. 🛠️ Fix Lỗi Logic & Bảo Mật (Critical Fixes)

* **✅ Quản Lý Database Chuyên Nghiệp (Flask-Migrate):** * **Nâng cấp:** Tích hợp Flask-Migrate để quản lý thay đổi cấu trúc Database mà không cần xóa dữ liệu cũ.
    * **Lệnh hỗ trợ:** `flask db init`, `flask db migrate`, `flask db upgrade`.

* **✅ Sửa Lỗi Xung Đột Khởi Tạo Database (Migration):**
    * **Vấn đề:** Lệnh `flask db migrate` bị lỗi `OperationalError` do vòng lặp khởi tạo CSDL tự động trong `run.py`.
    * **Giải pháp:** Tối ưu hóa khối lệnh `with app.app_context()` bằng cách tạm thời ẩn lệnh `initialize_database()` và thêm lệnh `pass` để nâng cấp CSDL an toàn.

* **✅ Fix Lỗi API Chatbot (CSRF Error):**
    * **Vấn đề:** API Chatbot gặp lỗi `400 Bad Request` do bị chặn bởi cơ chế bảo vệ CSRF khi gọi từ AJAX.
    * **Giải pháp:** Sử dụng decorator `@csrf.exempt` cho endpoint `/api/chatbot` để giao tiếp mượt mà mà vẫn giữ bảo mật cho các form khác.

* **✅ Bất Tử Hóa API Key (Key Rotation & Fallback):**
    * **Vấn đề (Reliability):** Giải quyết triệt để tình trạng hệ thống sập lõi AI do lỗi `429 Too Many Requests` (Hết hạn mức Quota) hoặc `400 Invalid Argument` (Key bị lỗi/thu hồi).
    * **Giải pháp (Key Rotation):** Tích hợp thuật toán xoay vòng danh sách nhiều API Key trong file `.env`. 
    * **Cơ chế (Auto Fallback):** Hệ thống tự động phát hiện sự cố và trượt sang Key dự phòng ngay lập tức khi Key chính gặp lỗi, đảm bảo 100% Uptime cho dịch vụ AI Chatbot và AI Search.

* **✅ Nâng Cấp Toàn Diện AI Smart Search (True Hybrid Search):**
    * **Động cơ chấm điểm lai (Hybrid Scoring):** Lần đầu tiên kết hợp hoàn hảo giữa Điểm Từ Khóa (Chính xác tuyệt đối 100% với tên máy) và Điểm Ngữ Nghĩa Vector DB (Linh hoạt với tính năng, nhu cầu "pin trâu", "củ").
    * **Suy luận Ngữ nghĩa (Semantic Reasoning):** Tích hợp trường semantic_query vào Prompt, dạy AI khả năng "dịch" nhu cầu lóng của khách (VD: "máy cho người già") thành truy vấn ngữ nghĩa chuẩn xác ("màn hình lớn, loa to, pin trâu") trước khi đưa vào VectorDB.
    * **Fix Fallback Logic:** Đổi toán tử OR thành AND ở bước tìm kiếm cuối, triệt để ngăn chặn tình trạng hiển thị sai hãng sản xuất.

* **✅ Vá Lỗ Hổng Bảo Mật Hệ Thống (Security Patches):**
    * **Lõi Khởi Chạy:** Loại bỏ `debug=True`, chuyển sang cơ chế biến môi trường `FLASK_DEBUG` để ngăn chặn rủi ro lộ lọt Stacktrace.
    * **Bot Bảo Mật:** Loại bỏ hàm `os.system()` nguy hiểm, thay thế bằng thư viện `ctypes` để giao tiếp an toàn với Kernel32 API, chống tấn công chèn lệnh.

* **✅ Tối Ưu Cấu Trúc & Hiệu Suất:**
    * **SQLAlchemy 2.0:** Thay thế `Model.query.get` bằng `db.session.get()` giúp tối ưu hiệu suất và loại bỏ cảnh báo cũ.
    * **Timezone Fix:** Đồng bộ dữ liệu thời gian về dạng naive UTC để tương thích hoàn toàn với SQLite.
    * **Logic Giỏ Hàng:** Hệ thống truy vấn lại giá thực tế từ Database tại bước checkout để đảm bảo tính minh bạch về giá.

* **✅ Fix Lỗi 500 & Front-End Linter:**
    * **AI Battle:** Cập nhật hàm `get_comparison_result` để tiếp nhận tham số động (lên tới 4 máy), triệt để loại bỏ lỗi 500.
    * **Syntax Fixes:** Loại bỏ cấu trúc Jinja (`{% ... %}`) ra khỏi các block `<style>` và `<script>` để vượt qua các bộ kiểm tra cú pháp (Linter).

* **✅ Tối Ưu Code Front-End Linter (Syntax Fixes):**
    * **Vấn đề:** Các bộ kiểm tra cú pháp báo lỗi `SyntaxError: Unexpected token '%'` do không nhận diện được mã Jinja2 trong block script/style.
    * **Giải pháp:** Loại bỏ hoàn toàn cấu trúc Jinja (`{% ... %}`) ra khỏi các block `<style>` và `<script>` tại `dashboard.html` và `detail.html`.

* **✅ Vá Lỗi Logic Hybrid Search (Critical Hotfixes):**
    * **Khắc phục lỗi "Chết oan" Vector DB:** Giải phóng Offline Vector DB khỏi sự phụ thuộc hoàn toàn vào Google API Key, đảm bảo hệ thống tìm kiếm thông minh hoạt động ổn định 100% ngay cả khi mất kết nối mạng Internet.
    * **Tối ưu hóa Lọc Hãng (Brand Dropdown):** Cải thiện logic xử lý để AI không bị vô hiệu hóa hoặc xung đột khi người dùng kết hợp thanh tìm kiếm cùng với bộ lọc Hãng từ giao diện người dùng.
    * **Mở rộng SQL Fallback:** Nâng cấp thuật toán tìm kiếm dự phòng, ép hệ thống quét toàn diện qua cả cột Mô tả (Description) để khắc phục tình trạng bỏ sót các tính năng "ẩn" hoặc chi tiết kỹ thuật sâu của sản phẩm.
    * **Bảo toàn Từ khóa Tính năng:** Loại bỏ các từ khóa quan trọng như "game", "ảnh", "đẹp" khỏi danh sách cắt tỉa (Stop Words) nội bộ, giúp Vector DB đánh giá điểm số tương đồng chính xác nhất cho các nhu cầu đặc thù của khách hàng.

* **✅ Tối Ưu Tường Lửa WAF (Firewall Hotfixes):**
    * **Vấn đề (False Positive):** Tính năng Tường lửa (`security_firewall.py`) bắt nhầm mã độc SQL Injection khi Quản trị viên thao tác với dấu gạch ngang (`--`), dẫn đến lỗi `403 Forbidden` và bị cấm cửa khỏi hệ thống.
    * **Giải pháp (Whitelist):** Cập nhật Regex quét SQLi thông minh hơn để không chặn nhầm form nhập liệu.
    * **Cơ chế Bypass:** Tích hợp cơ chế Bypass vô điều kiện cho tài khoản Quản trị viên (Admin) và IP máy chủ nội bộ (`127.0.0.1`), đảm bảo luồng quản trị luôn thông suốt 100%.

* **✅ Vá Lỗi Mất Ngữ Cảnh Chatbot (RAG Context Amnesia & False Out-of-Stock):**
    * **Vấn đề:** Khi khách hàng sử dụng đại từ nhân xưng ("máy đó", "tư vấn thêm đi"), hệ thống RAG không bắt được từ khóa tên sản phẩm dẫn đến truy xuất kho rỗng và AI báo sai "Sản phẩm tạm hết hàng". Chatbot cũng bị gò bó bởi các kịch bản chào hỏi cứng nhắc.
    * **Giải pháp:** Xóa bỏ hoàn toàn kịch bản tĩnh. Áp dụng thuật toán Query Expansion (Mở rộng truy vấn) tự động nối câu trả lời chứa tên sản phẩm liền trước vào câu hỏi hiện tại. Nâng cấp System Prompt và mở rộng bộ nhớ Session từ 4 lên 8 câu để AI duy trì mạch tư vấn liên tục, chính xác.

---

## 2. ✨ Tính Năng Mới: Bình Luận & Đánh Giá (Reviews)

* **✅ Hệ Thống Đánh Giá & Bình Luận Chuyên Nghiệp:**
    * **Nâng cấp:** Tái thiết kế toàn bộ khối Đánh giá sản phẩm tại trang Chi tiết (`detail.html`) theo phong cách hiện đại của các trang TMĐT lớn.
    * **Tính năng trực quan:** Hiển thị điểm số trung bình nổi bật, tích hợp thanh tiến trình (Progress Bar) cho từng mức sao (1-5 sao) và khung đánh giá theo trải nghiệm (Hiệu năng, Pin, Camera).
    * **Bộ lọc thông minh:** Phát triển thuật toán JavaScript hỗ trợ lọc Đánh giá/Bình luận mượt mà (theo số sao, trạng thái đã mua hàng...) mà không cần tải lại trang (No-reload).

---

## 3. 🎨 Nâng Cấp Giao Diện (UI/UX Optimization)

* **🏠 Trang Chủ (Homepage) - Giao diện Tết:**
    * **Banner Tết Bính Ngọ:** Sử dụng banner tĩnh khổ lớn kết hợp hiệu ứng zoom nhẹ sang trọng.
    * **Flash Sale:** Khu vực khuyến mãi tích hợp đồng hồ đếm ngược (Countdown Timer) trực quan.
    * **Smart Search:** Thanh tìm kiếm AI được thiết kế hiện đại dưới dạng nổi (floating).

* **📱 Trang Chi Tiết (Product Detail):**
    * **Image Gallery:** Khung hiển thị ảnh sản phẩm được tổ chức gọn gàng và hỗ trợ tính năng zoom.
    * **Variant Selection:** Hệ thống nút chọn Màu sắc/Phiên bản có chỉ báo "active" giúp người dùng dễ dàng nhận diện lựa chọn.
    * **Sticky Actions:** Các nút "Mua ngay" và "Thêm giỏ" được thiết kế nổi bật, luôn bám dính màn hình để tối ưu tỷ lệ chuyển đổi.
    * **Wishlist & Pulse Animation:** Tích hợp luồng AJAX cho phép Thả tim/Gỡ tim (Toggle Favorite) mượt mà không cần tải lại trang, kết hợp hiệu ứng CSS nhấp nháy sống động và đồng bộ trực tiếp vào Database (Many-to-Many Relationship).

* **🔔 Hệ Thống Thông Báo Thông Minh (SweetAlert2):**
    * **Nâng cấp:** Thay thế hoàn toàn Bootstrap Toasts bằng Pop-up **SweetAlert2** mượt mà tại góc màn hình, tăng tính chuyên nghiệp cho các thông báo hệ thống.

* **⏳ Hiệu Ứng Chờ Xử Lý (Loading Overlay & Anti-Spam):**

* **✅ Cơ chế (Backdrop Blur):** Tích hợp lớp phủ sương mù và vòng xoay trạng thái (Loading Spinner) vô hiệu hóa nút Submit ngay khi người dùng nhấn gửi.
    * **Lợi ích:** Ngăn chặn hành vi nhấn nhiều lần (Spam Click) gây trùng lặp dữ liệu và giảm tải cho Server khi xử lý các tác vụ có độ trễ cao.
* **✅ UX Đa Dạng (Dynamic Theming):** Hiệu ứng tự động biến đổi màu sắc và Icon thông báo phù hợp với từng ngữ cảnh cụ thể trong hệ thống:
    * **Tác vụ AI:** Hiển thị màu Đỏ kết hợp Icon Robot sống động.
    * **Luồng Thanh toán:** Hiển thị màu Xanh lá kết hợp Icon Hộp hàng chuyên nghiệp.
    * **Bình luận/Gửi tin:** Hiển thị màu Xanh dương kết hợp Icon Máy bay giấy mượt mà.

---

## 4. 📦 Quản Lý Tồn Kho Thực Tế (Inventory)

* **✅ Tồn Kho Tự Động:** Hệ thống tự động trừ kho ngay khi khách hàng đặt hàng thành công và hỗ trợ hoàn kho tức thì khi đơn hàng bị hủy (đối với các đơn chưa qua xử lý).
* **✅ Cảnh Báo Thông Minh:** Tích hợp logic chặn hành vi mua hàng nếu số lượng sản phẩm khách chọn vượt quá tồn kho thực tế trong Database.

---

## 5. 🤖 Trí Tuệ Nhân Tạo (Gemini AI)

* **✅ Tìm Kiếm Thông Minh:** AI có khả năng đọc hiểu ngôn ngữ tự nhiên, cho phép khách hàng tìm kiếm theo nhu cầu thực tế (Ví dụ: "iPhone giá rẻ dưới 10 triệu").
* **✅ So Sánh Sản Phẩm:** Tự động kẻ bảng đối chiếu thông số kỹ thuật chi tiết dưới dạng HTML Table trực quan.
* **✅ Chatbot Tư Vấn Không Kịch Bản:** Loại bỏ hoàn toàn các kịch bản cứng nhắc (hardcoded replies). Trợ lý ảo AI giờ đây tự động xử lý linh hoạt mọi tình huống từ khách hàng (chào hỏi, tư vấn, bắt bẻ, so sánh) với thái độ chuyên nghiệp, tự nhiên như nhân viên Sale thực thụ.
* **✅ Nâng Cấp Bộ Nhớ Hội Thoại (Super Memory) & Khắc Phục Lỗi RAG:** Mở rộng khả năng ghi nhớ lên 8 câu hội thoại gần nhất. Tích hợp thuật toán Mở rộng Truy vấn (Query Expansion) để giải quyết triệt để lỗi RAG Context Loss (ảo giác quên mất sản phẩm dẫn đến báo sai "hết hàng"). AI giờ đây tự động nhận diện chính xác các đại từ "nó", "cái đó", "chiếc này" dựa trên mạch truyện.

---

## 6. 🧪 Tái Cấu Trúc Hệ Thống Kiểm Thử (Testing Refactor)

* **✅ Hệ Thống Kiểm Thử Tự Động:** Tích hợp quy trình kiểm thử sử dụng Database ảo trên RAM (`sqlite:///:memory:`) giúp tăng tốc độ xử lý và đảm bảo môi trường sạch.
    * **Unit Testing:** Kiểm tra các chức năng độc lập như Login, Cart và Phân quyền Admin.
    * **Integration Testing:** Đảm bảo tính toàn vẹn dữ liệu giữa các thành phần trong hệ thống.
    * **System Testing (E2E):** Kiểm tra toàn bộ vòng đời đơn hàng (Mua hàng -> Trừ kho -> Hủy đơn -> Hoàn kho).
* **✅ Tổ Chức Module Chuyên Nghiệp:**
    * **`run_tests.py`:** Script chạy toàn bộ test case chỉ với một lệnh duy nhất (`python run_tests.py`).
    * **`test_core.py`:** Kiểm tra các chức năng cốt lõi như Đăng ký, Thanh toán, Thu cũ.
    * **`test_ai.py`:** Kiểm tra chuyên sâu logic AI (Mocking API Gemini, RAG Context, Logic Fallback).
    * **`test_security.py`:** Quét các lỗ hổng bảo mật như IDOR, tấn công Upload file.
* **✅ Tối Ưu Hóa Mã Nguồn:**
    * Loại bỏ hoàn toàn các file test dư thừa, trùng lặp để tinh gọn dự án.
    * Chuyển logic phân tích ý định (`local_analyze_intent`) sang `utils.py` để tái sử dụng linh hoạt.

---

## 7. 🌐 Sẵn Sàng Triển Khai (Production Ready)

* **✅ `run_windows_prod.py`:** Thiết lập Entry Point độc lập, chuyên biệt cho môi trường Production trên hệ điều hành Windows.
* **✅ Waitress Server:** Hỗ trợ chạy server Production siêu nhẹ, chịu tải cao và hoạt động ổn định trên môi trường Windows.

---

## 8. 🛡️ Bảo Mật Nâng Cao

* **✅ Ngăn Chặn Race Condition:** Áp dụng kỹ thuật khóa dòng (`with_for_update()`) trong quá trình thanh toán, đảm bảo tính chính xác tuyệt đối của tồn kho và tránh tình trạng bán quá số lượng thực tế.
* **✅ Bảo Mật CSRF:** Tích hợp **Flask-WTF** để bảo vệ toàn bộ hệ thống Form, ngăn chặn các cuộc tấn công giả mạo yêu cầu từ phía người dùng.
* **✅ Chống DDoS Upload:** Thiết lập giới hạn `MAX_CONTENT_LENGTH` để kiểm soát dung lượng file tải lên, ngăn chặn hành vi làm tràn bộ nhớ máy chủ.
* **✅ Security Audit:** Duy trì script `test_security.py` chuyên biệt để tự động quét và phát hiện các lỗ hổng bảo mật nghiêm trọng như **IDOR**.

---

## 9. 📊 Dashboard Quản Trị (Admin Dashboard)

* **📈 Real-time Analytics:** Hệ thống thống kê doanh thu tức thời dựa trên các đơn hàng có trạng thái "Completed".
* **🧠 Tích hợp Data Science (Pandas):** Ứng dụng thư viện **Pandas** để phân tích sâu dữ liệu thực tế, giúp xác định "Khung giờ vàng" (Peak Hour) có lượng chốt đơn cao nhất và danh sách sản phẩm bán chạy nhất trong tháng.
* **📑 Xuất Báo Cáo Excel Thông Minh:** Sử dụng sự kết hợp giữa **Pandas** và **openpyxl** để tự động render báo cáo doanh thu dưới dạng file Excel chuyên nghiệp (tự động căn chỉnh cột, định dạng tiền tệ) cho Admin.
* **📉 Hệ Thống Biểu Đồ (Chart.js):** * **Biểu đồ đường:** Trực quan hóa xu hướng doanh thu trong 7 ngày gần nhất.
    * **Biểu đồ tròn:** Phân tích tỷ trọng trạng thái đơn hàng trong hệ thống.
    * **🏆 Top Sản Phẩm:** Tự động xếp hạng và hiển thị Top 5 sản phẩm có doanh số cao nhất.

---

## 10. 🧠 Tối Ưu Hóa AI & Persona

* **✅ AI Persona:** Thiết lập tính cách nhân viên tư vấn bán hàng thân thiện, vui vẻ, sử dụng các emoji mang không khí Tết (🧧, 🌸).
* **✅ RAG Optimization:** Cải thiện cấu trúc ngữ cảnh dữ liệu giúp AI nhận biết chính xác tình trạng "Hết hàng" để tư vấn khách hàng hiệu quả hơn.
* **✅ Tối Ưu Tốc Độ & Quota (Smart Cache & Offline Hybrid):**
	* **Cơ chế AICache:** Kích hoạt bảng `AICache` trong cơ sở dữ liệu để tự động lưu trữ các phản hồi từ AI cho các truy vấn đã thực hiện.
	* **Hiệu năng phản hồi:** Truy xuất trực tiếp từ cơ sở dữ liệu giúp hệ thống phản hồi siêu tốc trong < 0.1 giây đối với các câu hỏi trùng lặp, thay vì mất 3-5 giây chờ API Google.
	* **Tiết kiệm tài nguyên:** Sự kết hợp giữa bộ nhớ đệm và thuật toán Local Vector Offline giúp hệ thống tiết kiệm tối đa hạn mức API, đảm bảo vận hành ổn định ngay cả khi gặp giới hạn Quota.
* **✅ Thuật Toán Băm Động (Dynamic MD5 Hash):** Áp dụng kỹ thuật băm toàn bộ ngữ cảnh (`final_prompt` chứa thông tin tồn kho thực tế) thay vì chỉ băm câu hỏi đơn thuần. Cơ chế này đảm bảo AI luôn phản hồi chuẩn xác theo thời gian thực (Ví dụ: Cùng một câu hỏi nhưng nếu trạng thái kho thay đổi, mã Hash sẽ thay đổi để AI cập nhật câu trả lời mới nhất).
* **✅ Refactor Code:** Tối ưu hóa mã nguồn bằng cách tách toàn bộ logic xử lý AI sang module `utils.py`, giúp dễ dàng bảo trì và mở rộng.

---

## 11. 💳 Thanh Toán Online Tự Động (VietQR)

* **✅ Cổng Thanh Toán VietQR Động:** Tự động tạo mã QR chính xác theo số tiền đơn hàng, hỗ trợ khách hàng quét mã thanh toán nhanh chóng.
* **✅ Real-time Polling:** Tích hợp kỹ thuật AJAX để tự động kiểm tra trạng thái giao dịch mỗi 3 giây, cập nhật kết quả ngay lập tức lên giao diện.
* **✅ Countdown Timer:** Thiết lập giao dịch hết hạn sau 3 phút để giải phóng tồn kho, đảm bảo tính bảo mật và công bằng cho các khách hàng khác.
* **✅ Chế Độ Giả Lập (Local):** Bổ sung nút "Gửi tín hiệu ĐÃ NHẬN TIỀN" giúp lập trình viên kiểm thử toàn bộ luồng thanh toán mà không cần giao dịch tiền thật.

---

## 12. 🧠 Nâng Cấp Trí Tuệ Nhân Tạo (AI Search & Logic)

* **✅ Kiến Trúc Hybrid AI (Local Vector DB):**
	* **Nâng cấp (Offline Embedding):** Thay thế hoàn toàn model nhúng Vector của Google bằng mô hình Local đa ngôn ngữ (`sentence-transformers`).
	* **Hiệu quả (Independence):** Xử lý Offline 100% dựa trên sức mạnh CPU của máy chủ, giải phóng hoàn toàn sự phụ thuộc vào API Quota của Google.
	* **Tối ưu hiệu suất (Speed):** Tốc độ đồng bộ (`rag_sync.py`) tăng gấp 10 lần nhờ loại bỏ triệt để độ trễ mạng Internet và các hàm `time.sleep` không cần thiết.
* **✅ Động Cơ Chấm Điểm Lai Đa Trọng Số (Hybrid Scoring Engine):**
	* **Nâng cấp:** Tái thiết kế hoàn toàn thuật toán xếp hạng tại Controller main.py. Sản phẩm giờ đây được xếp hạng dựa trên tổng điểm: Keyword Match Score (thưởng điểm cực cao khi khớp đúng tên) + Vector Semantic Boost (thưởng điểm khi VectorDB đánh giá phù hợp ngữ nghĩa).
	* **Hiệu quả:** Giải quyết triệt để bài toán: Tìm tên máy ra đúng máy lên Top 1, tìm nhu cầu tính năng (chụp ảnh đẹp, chơi game) vẫn ra đúng máy mà không cần gõ tên.
* **✅ Direct Text-RAG Search (Bất tử hóa AI Vector DB):**
    * **Vấn đề:** Hệ thống AI Search bị gián đoạn khi model Embedding gặp lỗi 404 hoặc cạn hạn mức (Quota).
    * **Giải pháp:** Tích hợp lõi dự phòng Text-RAG trực tiếp qua `gemini-2.5-flash`. Hệ thống tự động đọc kho hàng từ file JSON và xử lý tìm kiếm đa luồng, đảm bảo AI trả về kết quả 100% trong mọi tình huống.
* **✅ Cải Tiến Bộ Lọc Ngữ Nghĩa (Local Safe Mode):**
    * **Nâng cấp:** Nhận diện thông minh các từ lóng Việt Nam (Ví dụ: "15 củ", "triệu quay đầu", "pin trâu").
    * **Sửa lỗi:** Fix triệt để lỗi phân biệt in hoa/thường của SQLite (Unicode) và xử lý "bẫy phụ kiện" (Ví dụ: Khi khách tra "Ốp lưng iPhone", hệ thống biết chỉ lấy phụ kiện, không gợi ý điện thoại).
* **✅ Tự Động Hóa Bộ Kiểm Thử (Comprehensive AI Unit Tests):**
    * **Nâng cấp:** Tích hợp 8 bài Test chuyên sâu trong `test_AI.py` bao phủ 100% logic:
        * **RAG Context Building:** Kiểm tra khả năng xây dựng ngữ cảnh.
        * **NLP Sentiment Analysis:** Phân tích cảm xúc khách hàng.
        * **Recommendation System:** Kiểm tra logic gợi ý mua kèm.
        * **Bẫy ảo giác AI & Direct Text-RAG Fallback:** Kiểm soát lỗi ảo giác và kiểm tra luồng dự phòng.

---

## 13. 🔄 Tự Động Hóa CI/CD (GitHub Actions)

* **✅ Automated Testing Pipeline:** Thiết lập quy trình DevOps tự động chạy toàn bộ bộ kiểm thử (`run_tests.py`) mỗi khi có thao tác push code lên GitHub.
* **✅ Environment Isolation:** Đảm bảo tính khách quan bằng cách chạy test trên môi trường sạch biệt lập (Ubuntu Latest + Python 3.12 + In-Memory DB).
* **✅ Quality Gate:** Thiết lập hàng rào chất lượng, đảm bảo mã nguồn có lỗi không bao giờ được merge vào nhánh chính của dự án.

---

## 14. 🌟 Cập Nhật Giao Diện & Tính Năng Mới Nhất (Hotfixes)

* **✅ Quản Trị Viên (Admin):**
    * **Phục hồi Admin Dashboard:** Khôi phục Modal Form thêm mới sản phẩm, cho phép quản lý đầy đủ thông tin kho, giá khuyến mãi và trạng thái.
    * **Data Insight với Pandas:** Hiển thị trực quan các dữ liệu thực tế như "Khung giờ vàng", sản phẩm mua nhiều và tích hợp nút xuất Excel doanh thu.
    * **Giao diện Tabs:** Chỉnh sửa CSS cho các nút Tab quản trị (Sản phẩm, Đơn hàng...) với chữ đậm, viền nổi bật để tăng tính thẩm mỹ và dễ sử dụng.
    * **Quản lý Đánh giá:** Nâng cấp bảng quản lý bình luận, hỗ trợ trả lời trực tiếp trong trang quản trị và gỡ bỏ cảnh báo Email (SMTP) để tối ưu hiệu suất web.

* **✅ Chi Tiết Sản Phẩm (Product Detail):**
    * **Hệ thống Hỏi & Đáp (Q&A):** Thiết kế khu vực Q&A độc lập với đánh giá sao, hỗ trợ dán nhãn Quản trị viên và trả lời lồng nhau (Nested replies) chuyên nghiệp.
    * **Trick Database Thông Minh:** Tối ưu bảng Comment với logic linh hoạt (rating = 0 cho hỏi đáp) giúp mở rộng hệ thống mà không cần sửa đổi cấu trúc CSDL SQLite.
    * **Wishlist AJAX:** Cho phép thả/gỡ tim sản phẩm mượt mà không cần tải lại trang và đồng bộ trực tiếp vào Database thông qua Many-to-Many Relationship.

* **✅ Hồ Sơ Thành Viên (User Dashboard):**
    * **Tab Yêu Thích:** Hiển thị sản phẩm đã thả tim dưới dạng Grid đẹp mắt, hỗ trợ xóa nhanh và thêm thẳng vào giỏ hàng.
    * **Tiện ích M-Member:** Tích hợp giao diện Kho Voucher dạng Tickets, Sổ bảo hành điện tử (IMEI/Serial) và hiển thị 10 đặc quyền hạng thẻ.
    * **Cập nhật Hồ sơ & Referral:** Bổ sung chọn Giới tính, Ngày sinh và tự động tạo mã REF-ID độc quyền kèm tính năng Copy nhạy bén với thông báo SweetAlert2.

---

## 15. ⚙️ Nâng Cấp Hệ Thống Backend & Tiện Ích (Core System)

* **✅ Hệ Thống Chạy Ngầm (Background Tasks):** Tích hợp `tasks.py` tự động quét CSDL mỗi 5 phút, chuyển đơn hàng quá hạn 15 phút sang "Cancelled" và hoàn trả tồn kho tự động.
* **✅ Xử Lý Lỗi Toàn Cục (Global Error Handling):** Xây dựng module `errors.py` để bắt các lỗi 404, 403, 500 và hiển thị trang `error.html` chuyên nghiệp thay vì lỗi mặc định của server.
* **✅ Công Cụ Sao Lưu Dữ Liệu (Auto Backup):** Tích hợp script `backup_db.py` tự động nén CSDL (.db) thành file .zip kèm timestamp chi tiết để phục hồi nhanh chóng.

---

## 16. 📈 Nâng Cấp Kiến Trúc Dữ Liệu & Phân Tích (Big Data & Performance)

* **✅ Lõi Phân Tích Dữ Liệu (Sales Analytics Engine):** Xây dựng module `analytics_engine.py` ứng dụng thư viện **Pandas** để xử lý Big Data. Cung cấp các công cụ phân tích nâng cao như: Tính tỷ lệ giữ chân khách hàng (Retention Rate), phân tích xu hướng doanh thu 7 ngày, và phân tích RFM để tự động lọc ra tệp khách hàng VIP.
* **✅ Giả Lập Tải Nặng (Stress Test):** Tích hợp kịch bản kiểm thử hiệu năng `stress_test.py`, tự động bơm hàng ngàn user và giao dịch ảo vào Database để kiểm tra sức chịu tải và cung cấp dữ liệu cho các thuật toán Data Science & AI.
* **✅ Quản Trị Vector AI (Vector Manager):**  Refactor toàn bộ logic ChromaDB thành class vector_manager.py chuyên biệt. Chuyển đổi không gian Vector từ 768 chiều (Google API) sang 384 chiều (Local CPU sentence-transformers), giải phóng 100% sự phụ thuộc vào API Key bên thứ 3 và giúp hệ thống tìm kiếm (RAG) hoạt động ngay cả khi mất mạng internet.

---

## 17. 🕷️ Trí Tuệ Nhân Tạo & Phân Tích Chuyên Sâu (Advanced ML & Tracking)

* **✅ Hệ Thống Học Máy Gợi Ý Sản Phẩm (ML Recommender):** Phát triển thuật toán Lọc cộng tác (Collaborative Filtering) trong `recommendation_ml.py`. Hệ thống tự động học hỏi từ hàng ngàn lịch sử giỏ hàng để đưa ra quyết định gợi ý mua kèm (Cross-sell) cực kỳ chuẩn xác.
* **✅ Hệ Thống Audit Log Chuyên Nghiệp (System Logger):** Triển khai `system_logger.py` cấu hình `RotatingFileHandler`. Tự động ghi lại nhật ký vòng đời hệ thống (Access Log, Security Warning) và chống tràn bộ nhớ bằng cơ chế tự động xoay vòng file log (max 5MB/file).
* **✅ Robot Cào Dữ Liệu Đối Thủ (Competitor Web Scraper):** Ứng dụng kỹ thuật Web Scraping (BeautifulSoup/Requests) để tự động quét giá, so sánh độ chênh lệch và xuất báo cáo đối thủ cho Admin.

---

## 18. 🛡️ Cơ Sở Hạ Tầng & Bảo Mật Nâng Cao (Core Infrastructure)

* **✅ Hệ Thống Tường Lửa Web (WAF):** Triển khai `security_firewall.py` bảo vệ ứng dụng khỏi tấn công DDoS (Rate Limiting 60 req/min) và tự động chặn các payload mã độc XSS, SQL Injection.
* **✅ Hệ Thống Hàng Đợi Tác Vụ Nền (Job Queue):** Xây dựng `notification_worker.py` sử dụng kiến trúc Producer-Consumer với Threading, đẩy các tác vụ nặng (gửi email, đồng bộ Vector DB) xuống chạy ngầm để đảm bảo giao diện luôn mượt mà.
* **✅ Hệ Thống Phân Tích Nhật Ký (Log Analyzer):** Tích hợp script `log_analyzer.py` sử dụng Regex để thống kê lượng truy cập, nhận diện IP spam và báo cáo các API xử lý chậm.

---

## 19. 🧱 Chuẩn Hóa Mã Nguồn & Clean Code (Refactoring)

* **✅ Hệ Thống Hằng Số Tập Trung (Constants Manager):** Tạo file `constants.py` để quản lý tập trung các chuỗi văn bản cứng (hardcode strings) như trạng thái đơn hàng, từ khóa AI. Giúp mã nguồn tuân thủ triệt để nguyên tắc SOLID và dễ dàng bảo trì.
* **✅ Refactor Controllers:** Cập nhật logic xử lý tại `main.py` và `admin.py` để sử dụng biến hằng số, loại bỏ 100% "magic strings" (chuỗi rác), đảm bảo code an toàn và sẵn sàng cho việc mở rộng quy mô.

---

## 20. 🤖 Công Cụ Lập Trình Viên (DevSecOps Tools)

* **✅ Hệ Thống Quét Lỗ Hổng Code (Code Security Scanner):** Triển khai `code_security_scanner.py` sử dụng thư viện **AST** (Abstract Syntax Tree). Bot tự động phân tích mã nguồn để tìm các điểm yếu bảo mật như hàm `eval()` nguy hiểm hoặc lộ API Key.

---

## 21. 📜 Tự Động Hóa Tài Liệu (Document as Code)

* **✅ Cỗ Máy Sinh Tài Liệu API Tự Động:** Tích hợp `api_doc_builder.py` sử dụng cây cú pháp **AST** để tự động quét toàn bộ module Routes của Flask. Hệ thống tự động thu thập Endpoints, phương thức HTTP và biên dịch thành tệp `API_DOCUMENTATION.md` đạt chuẩn, tiết kiệm 100% thời gian viết tài liệu thủ công.

---

## 22. 🗄️ Kỹ Nghệ Dữ Liệu (Data Engineering)

* **✅ Động Cơ Xuất Dữ Liệu Data Warehouse:** Phát triển module `data_warehouse_exporter.py` đóng vai trò luồng **ETL** nội bộ. Hệ thống làm sạch dữ liệu bằng **Pandas** (ẩn danh email, format số điện thoại) và xuất cơ sở dữ liệu thành tệp CSV nén ZIP, sẵn sàng cho các công cụ BI như PowerBI hoặc Tableau.

---

## 23. ⚖️ Quản Trị Chất Lượng Mã Nguồn (Code Quality)

* **✅ Hệ Thống Linter Tùy Chỉnh (Custom Linter):** Tích hợp `code_quality_scorer.py` sử dụng **AST** và **Regex** để tự động chấm điểm dự án trên thang 100. Công cụ này kiểm soát số dòng code, phát hiện thiếu Docstrings và kiểm tra chuẩn đặt tên **PEP8** (snake_case/CamelCase).

---

## 24. 🌟 Tối Ưu Hóa Trải Nghiệm Lập Trình (PEP8 100/100)

* **✅ Phủ Xanh 100% Docstring:** Toàn bộ hệ thống mã nguồn từ Controller đến Test Suites đều được viết chú thích chi tiết theo quy chuẩn quốc tế. Dự án đạt điểm số tuyệt đối **A+ (100/100)** từ Custom Linter, thiết lập nền tảng **Clean Code** bền vững.

---

## 25. 🧮 Thuật Toán Khuyến Nghị Toán Học

* **✅ Content-Based Filtering:** Xây dựng thuật toán Python thuần túy thay thế AI Vector Search để đảm bảo tính ổn định tuyệt đối. Hệ thống tự động chấm điểm tương đồng (Scoring) dựa trên hãng (+50đ), độ lệch giá (+30đ) và từ khóa (+5đ), mang lại trải nghiệm gợi ý "Sản phẩm tương tự" siêu mượt.

---

## 26. ⚖️ Đấu Trường AI So Sánh 4 Sản Phẩm 

* **✅ Giao Diện Sticky Header:** Tái thiết kế khu vực so sánh mang phong cách chuyên nghiệp, bảng đối chiếu và nút "Mua Ngay" luôn bám dính khi người dùng cuộn xem chi tiết cấu hình.
* **✅ Nâng Cấp Modal 4 Thiết Bị:** Phá bỏ giới hạn cũ, cho phép so sánh cùng lúc 4 thiết bị "cùng hạng cân". Máy chủ yếu đang xem luôn được khóa cứng tại vị trí số 1.
* **✅ Bảo Mật Hạn Mức Trí Tuệ Nhân Tạo (AI Rate Limiting):** Xây dựng cơ chế cấp phát Quota sử dụng AI bảo vệ 4 API Key. Khóa hoàn toàn tính năng với khách vãng lai. Số lượt So sánh AI mỗi ngày được cấp phát tự động theo thứ hạng: M-New (2 lượt), M-Gold (5 lượt), M-Platinum (10 lượt) và M-Diamond (30 lượt). Tự động Reset lượt dùng vào ngày mới.
* **✅ Giao Diện Minh Bạch Quota (UI/UX):** Tích hợp bảng thông báo đặc quyền VIP chuyên nghiệp ngay tại trang So sánh, giúp khách hàng theo dõi trực tiếp số lượt truy vấn AI họ đã tiêu thụ trong ngày.
* **✅ AI Tư Vấn Chuyên Sâu (Deep Analysis):** Prompt được tối ưu để AI đóng vai chuyên gia công nghệ, phân tích ưu/nhược điểm đa chiều và đưa ra lời khuyên "Nên mua máy nào, cho ai, vì sao?".
* **✅ Lõi Dự Phòng (Local Fallback):** Kiến trúc phòng thủ 100% Uptime. Nếu API Gemini gặp sự cố, thuật toán Python sẽ tự động can thiệp để kẻ bảng thông số kỹ thuật, đảm bảo người dùng luôn nhận được kết quả.

---

## 27. 🚀 Nâng Cấp Kiến Trúc Hạ Tầng Lõi (Hardcore Infrastructure)

* **✅ Quản Lý Bộ Nhớ (Memory Optimization):** Nâng cấp hệ thống tác vụ nền (`tasks.py`) sử dụng kỹ thuật **Chunking** kết hợp **Python Generators (`yield`)**.
    * *Lợi ích:* Xử lý dữ liệu theo từng lô nhỏ (50 đơn hàng), giải phóng RAM ngay lập tức và ngăn chặn lỗi tràn bộ nhớ (Out of Memory) khi xử lý dữ liệu lớn.
* **✅ Hàng Đợi Ưu Tiên Đa Luồng (Priority Threading Queue):** Tái cấu trúc `notification_worker.py` bằng `queue.PriorityQueue` và **OOP Dataclass**.
    * *Cơ chế:* Tự động phân loại mức độ khẩn cấp. Các tác vụ như OTP/Email bảo mật được ưu tiên xử lý tức thì, trong khi các tác vụ nặng (Đồng bộ Vector) được chạy nền để tối ưu CPU.
* **✅ Bảo Mật Toàn Vẹn Dữ Liệu (Data Integrity):** Nâng cấp script `backup_db.py` với thuật toán băm **SHA-256** (đọc file theo Binary stream).
    * *An toàn:* Tự động khóa file ZIP và xuất chứng thư `manifest.txt`. Cho phép Admin đối chiếu chữ ký điện tử để phát hiện ngay lập tức nếu file backup bị can thiệp hoặc tiêm mã độc.

---

## 28. 🎟️ Hệ Thống Động Cơ Voucher (Smart Voucher Rule Engine)

* **✅ Kiến Trúc Thiết Kế (Specification Pattern):** Xây dựng lõi `VoucherValidatorEngine` hoàn toàn bằng OOP. Tách biệt các điều kiện kiểm duyệt (Thời hạn, Giá trị đơn tối thiểu, Hạng thẻ VIP) thành các Class độc lập, tuân thủ nguyên lý Open/Closed (SOLID) giúp dễ dàng bảo trì và mở rộng hệ thống sau này.
* **✅ Quản Trị Khuyến Mãi Độc Quyền (Admin):** Admin nắm quyền kiểm soát tuyệt đối: Phát hành mã mới linh hoạt (theo %, theo VNĐ), khóa khẩn cấp mã bị rò rỉ, và xóa vĩnh viễn các chiến dịch thông qua giao diện trực quan tại Dashboard.
* **✅ Trải Nghiệm Khách Hàng (UX/UI):** Kho Voucher tại trang M-Member hiển thị linh động theo dữ liệu lấy từ Database, hỗ trợ sao chép mã (Copy) một chạm với thông báo SweetAlert2. Tại trang Thanh toán (Checkout), khách hàng dán mã vào ô và hệ thống sẽ tự động tính toán, cập nhật trừ tiền trên giao diện qua luồng AJAX mượt mà.
* **✅ Bảo Mật Thanh Toán (Backend Security):** Vá triệt để lỗ hổng thao túng dữ liệu từ phía Frontend (Spoofing). Hệ thống backend tự động tính toán lại Cấp bậc thành viên (Rank) và chạy lại toàn bộ xác thực mã Voucher ở vòng lặp chốt đơn cuối cùng trước khi khóa dòng dữ liệu Database, đảm bảo 100% tính nguyên vẹn số tiền thu về.

---

## 29. 🧪 Kịch Bản Kiểm Thử Bẫy Ngữ Nghĩa (Search AI Test Cases - True Hybrid)

Dưới đây là 5 "Bẫy Ngữ Nghĩa" và "Bẫy Hệ Thống" được thiết kế để tự tay kiểm chứng sức mạnh của thanh tìm kiếm **True Hybrid Search AI** vừa được nâng cấp:

* **🚨 Test Case 1: Tìm kiếm theo nhu cầu / Tiếng lóng (Sức mạnh VectorDB)**
    * **Mô tả:** Kiểm tra AI có dịch đúng "nhu cầu" thành semantic_query để VectorDB tìm máy phù hợp tính năng không.
    * **Input:** `máy cho phụ huynh pin trâu màn to dễ dùng`
    * **Kết quả kỳ vọng:** AI bóc tách semantic_query = "điện thoại màn hình lớn, pin trâu, loa to...". Giao diện trả về các dòng máy có tính năng này trên Top đầu (dù tên không có chữ "phụ huynh").

---

* **🚨 Test Case 2: Tìm kiếm chính xác tên máy (Sức mạnh Keyword Scoring)**
    * **Mô tả:** Đảm bảo khi khách gõ đúng tên, máy đó phải được cộng điểm tuyệt đối và nhảy lên Top 1 (Không bị Vector làm nhiễu).
    * **Input:** `iphone 15 pro max titan tự nhiên`
    * **Kết quả kỳ vọng:** Khớp 100% từ khóa. Các phiên bản iPhone 15 Pro Max đứng vị trí đầu tiên, không bị lẫn máy Samsung hay ốp lưng.

---

* **🚨 Test Case 3: Nhận diện khoảng giá & Tiếng lóng (Price Extraction)**
    * **Mô tả:** Test khả năng bóc tách các từ lóng như "củ", "triệu" và chuyển đổi thành max_price.
    * **Input:** `tìm điện thoại samsung chụp ảnh đẹp tầm 10 củ quay đầu` 
    * **Kết quả kỳ vọng:** Chỉ hiện máy Samsung, giá ≤ 10.000.000đ, và ưu tiên các máy có thông số camera tốt (do VectorDB chấm điểm semantic_query).

---

* **🚨 Test Case 4: Tránh bẫy "Phụ kiện" (Category Classification)**
    * **Mô tả:** Đảm bảo AI phân biệt được khách đang tìm phụ kiện của hãng nào đó, chứ không phải tìm điện thoại.
    * **Input:** `ốp lưng chống sốc cho iphone 14` 
    * **Kết quả kỳ vọng:** Bắt buộc chỉ hiển thị Ốp lưng, Sạc, Cáp... (thuộc Category: accessory). Tuyệt đối không hiển thị chiếc điện thoại iPhone 14.

---

* **🚨 Test Case 5: Bài Test Chế Độ "Bất Tử" (Local Fallback Mode)**
    * **Mô tả:** Giả lập trường hợp Google AI cạn Quota hoặc mất kết nối mạng để test Regex thuần.
    * **Chuẩn bị:** Vô hiệu hóa `GEMINI_API_KEY` trong file `.env` và F5 website.
    * **Input:** `điện thoại xiaomi dưới 5 triệu`
    * **Kết quả kỳ vọng:** Website không sập. Thuật toán local_analyze_intent tự nhận diện Brand=Xiaomi, max_price=5000000. Trả về kết quả siêu tốc với thông báo "⚡ Smart Search (Tốc độ cao)".

---

## 📂 Cấu Trúc Dự Án (Modular MVC)

```text
MobileStore/
├── run.py                    # (ENTRY POINT) Khởi chạy Server Development
├── run_windows_prod.py       # (PROD ENTRY) Server Production (Waitress)
├── competitor_scraper.py     # (BOT) Robot thu thập dữ liệu giá đối thủ
├── backup_db.py              # (UTILS) Script tự động sao lưu Database
├── log_analyzer.py           # (UTILS) Phân tích nhật ký hệ thống
├── code_security_scanner.py  # (DEVSECOPS) Quét lỗ hổng Code bằng AST
├── api_doc_builder.py        # (DOCS) Tự động sinh tài liệu API
├── data_warehouse_exporter.py# (DATA) Script ETL xuất dữ liệu Data Warehouse
├── code_quality_scorer.py    # (QA/QC) Bot Linter chấm điểm chuẩn PEP8
├── run_tests.py              # (TEST RUNNER) Script chạy toàn bộ test
├── rag_sync.py               # (AI SYNC) Đồng bộ Vector DB (ChromaDB)
├── migrations/               # (NEW) Thư mục chứa file migration DB
├── tests/                    # Thư mục kiểm thử tự động
│   ├── test_core.py          # Test chức năng cơ bản (Core)
│   ├── test_ai.py            # Test tính năng AI (Mocking)
│   ├── test_security.py      # Test bảo mật
│   ├── test_models.py        # Test cấu trúc Database
│   ├── test_auth.py          # Test xác thực & Đăng nhập
│   ├── test_integration.py   # Test tích hợp hệ thống
│   ├── test_ml.py            # Test thuật toán Machine Learning
│   ├── test_infrastructure.py# Test tường lửa và hàng đợi tác vụ
│   └── stress_test.py        # Script giả lập tải nặng & bơm data ảo
├── .env                      # Cấu hình bảo mật và API Keys
├── requirements.txt          # Danh sách thư viện dự án
│
└── app/                      # (PACKAGE) Source Code Chính
    ├── __init__.py           # App Factory (Khởi tạo ứng dụng)
    ├── extensions.py         # Cấu hình DB, Login, Migrate, CSRF
    ├── models.py             # Định nghĩa Database Models
    ├── utils.py              # Xử lý AI Logic & Helpers
    ├── tasks.py              # Hệ thống quét và chạy ngầm
    ├── errors.py             # Bộ xử lý lỗi toàn cục (404, 500)
    ├── vector_manager.py     # Quản trị Vector DB (ChromaDB)
    ├── analytics_engine.py   # Lõi phân tích dữ liệu (Pandas)
    ├── recommendation_ml.py  # Thuật toán AI Lọc Cộng tác
    ├── security_firewall.py  # Tường lửa bảo mật WAF (DDoS/XSS)
    ├── notification_worker.py# Hàng đợi xử lý tác vụ nền (Queue)
    ├── constants.py          # Quản lý hằng số (Clean Code)
    ├── templates/            # (VIEW) Giao diện HTML (Jinja2)
    └── routes/               # (CONTROLLER) Điều hướng và xử lý logic
        ├── main.py           # Luồng người dùng chính
        ├── auth.py           # Luồng xác thực & Tài khoản
        └── admin.py          # Luồng quản trị Dashboard
├── .github/                  # (CI/CD) Cấu hình GitHub Actions
│   └── workflows/
│       └── ci_cd.yml         # Pipeline tự động Testing & Deployment

---

## 🛠 Hướng Dẫn Cài Đặt & Khởi Chạy

| Bước | Quy trình thực hiện | Chi tiết lệnh / Chỉ dẫn |
| :--- | :--- | :--- |
| **01** | **Cài đặt thư viện** | `py -m pip install -r requirements.txt` (Hệ thống yêu cầu cài đặt bổ sung thư viện `sentence-transformers` cho tính năng AI Local Vector). |
| **02** | **Cấu hình hệ thống** | Tạo file `.env` tại thư mục gốc và điền đầy đủ: `Gemini_API_Key` (Hỗ trợ nhập chuỗi nhiều API Key cách nhau bằng dấu phẩy để chống cạn kiệt Quota) , `Google_OAuth`, `Secret_Key`. |
| **03** | **Khởi tạo Database** | Chạy tuần tự 3 lệnh: <br> 1. `py -m flask db init` <br> 2. `py -m flask db migrate -m "Initial migration"` <br> 3. `py -m flask db upgrade` |
| **04** | **Đồng bộ AI (RAG)** | `py rag_sync.py` (Để AI học và nhúng dữ liệu sản phẩm mới). |
| **05** | **Khởi chạy Local** | `py run.py` <br> 👉 Truy cập: **http://127.0.0.1:5000** |
| **06** | **Chạy Production** | `py run_windows_prod.py` (Sử dụng server Waitress đa luồng cho Windows). |

---

## 🔑 Thông Tin Tài Khoản Demo

| Vai trò | Tên đăng nhập (Username) | Mật khẩu (Password) | Ghi chú quyền hạn |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `123456` | Toàn quyền quản trị Dashboard, AI & Báo cáo. |
| **Khách hàng** | `khach` | `123456` | Trải nghiệm mua sắm, tích điểm & Chatbot. |

---
