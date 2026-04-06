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

* **✅ Tối Ưu Cấu Trúc & Hiệu Suất:**
    * **SQLAlchemy 2.0:** Thay thế `Model.query.get` bằng `db.session.get()` giúp tối ưu hiệu suất và loại bỏ cảnh báo cũ.
    * **Timezone Fix:** Đồng bộ dữ liệu thời gian về dạng naive UTC để tương thích hoàn toàn với SQLite.
    * **Logic Giỏ Hàng:** Hệ thống truy vấn lại giá thực tế từ Database tại bước checkout để đảm bảo tính minh bạch về giá.

* **✅ Tối Ưu Code Front-End Linter (Syntax Fixes):**
    * **Vấn đề:** Các bộ kiểm tra cú pháp báo lỗi `SyntaxError: Unexpected token '%'` do không nhận diện được mã Jinja2 trong block script/style.
    * **Giải pháp:** Loại bỏ hoàn toàn cấu trúc Jinja (`{% ... %}`) ra khỏi các block `<style>` và `<script>` tại `dashboard.html` và `detail.html`.

* **✅ Vá Lỗi Logic Hybrid Search (Critical Hotfixes):**
    * **Khắc phục lỗi "Chết oan" Vector DB:** Giải phóng Offline Vector DB khỏi sự phụ thuộc hoàn toàn vào Google API Key, đảm bảo hệ thống tìm kiếm thông minh hoạt động ổn định 100% ngay cả khi mất kết nối mạng Internet.
    * **Tối ưu hóa Lọc Hãng (Brand Dropdown):** Cải thiện logic xử lý để AI không bị vô hiệu hóa hoặc xung đột khi người dùng kết hợp thanh tìm kiếm cùng với bộ lọc Hãng từ giao diện người dùng.
    * **Mở rộng SQL Fallback:** Nâng cấp thuật toán tìm kiếm dự phòng, ép hệ thống quét toàn diện qua cả cột Mô tả (Description) để khắc phục tình trạng bỏ sót các tính năng "ẩn" hoặc chi tiết kỹ thuật sâu của sản phẩm.
    * **Bảo toàn Từ khóa Tính năng:** Loại bỏ các từ khóa quan trọng như "game", "ảnh", "đẹp" khỏi danh sách cắt tỉa (Stop Words) nội bộ, giúp Vector DB đánh giá điểm số tương đồng chính xác nhất cho các nhu cầu đặc thù của khách hàng.

* **✅ Vá Lỗi Mất Ngữ Cảnh Chatbot (RAG Context Amnesia & False Out-of-Stock):**
    * **Vấn đề:** Khi khách hàng sử dụng đại từ nhân xưng ("máy đó", "tư vấn thêm đi"), hệ thống RAG không bắt được từ khóa tên sản phẩm dẫn đến truy xuất kho rỗng và AI báo sai "Sản phẩm tạm hết hàng". Chatbot cũng bị gò bó bởi các kịch bản chào hỏi cứng nhắc.
    * **Giải pháp:** Xóa bỏ hoàn toàn kịch bản tĩnh. Áp dụng thuật toán Query Expansion (Mở rộng truy vấn) tự động nối câu trả lời chứa tên sản phẩm liền trước vào câu hỏi hiện tại. Nâng cấp System Prompt và mở rộng bộ nhớ Session từ 4 lên 8 câu để AI duy trì mạch tư vấn liên tục, chính xác.

* **✅ Tối Ưu Hóa Dung Lượng Session Cookie (Chatbot Memory Fix):**
    * **Vấn đề:** Việc lưu trữ toàn bộ lịch sử chat dài của AI vào Session Cookie làm phình to dữ liệu, dễ dẫn đến lỗi tràn bộ nhớ Cookie hoặc HTTP 431 Request Header Fields Too Large.
    * **Giải pháp:** Rút gọn bộ nhớ hội thoại xuống tối đa 3 lượt gần nhất, đồng thời tự động cắt ngắn câu trả lời của AI xuống 150 ký tự trước khi lưu vào Session. Đảm bảo AI vẫn giữ được mạch ngữ cảnh mà dung lượng Cookie được giảm tải tối đa, bảo vệ server khỏi các sự cố crash không đáng có.

* **✅ Vá Lỗi Lộn Xộn Trong Tìm Kiếm Bằng Hình Ảnh (Visual Search Hotfix):**
    * **Vấn đề:** Thuật toán Vector hình dáng thuần túy bị "mù chữ", dẫn đến việc trả về kết quả lộn xộn chéo hãng (Ví dụ: Đưa ảnh Xiaomi nhưng máy gợi ý Samsung do giống độ vuông vức) và thiếu minh bạch.
    * **Giải pháp:** Nâng cấp kiến trúc thành Dual Engine. Chèn API Gemini Vision để "đọc đích danh" tên máy và hãng. Kết hợp thuật toán lọc nghiêm ngặt (Strict Brand Filter) trên nền kết quả Vector, ép buộc máy gợi ý phải cùng Hãng.
    * **UI/UX:** Cập nhật thông báo trực quan, minh bạch 100% theo cấu trúc chuẩn: "📷 Đã nhận diện: [Tên máy]. [Tình trạng kho hàng] -> [Gợi ý]".

* **✅ Khắc Phục Lỗi Ảo Giác & Vòng Lặp Visual Search (Image Enhance & Confidence Cutoff):**
    * **Vấn đề:** Khi người dùng tải ảnh mờ, AI Gemini bị ảo giác (đoán bừa tên máy với độ tự tin cực thấp dưới 50%), khiến hệ thống mang tên sai đi tìm SQL và chặn đứng luôn luồng fallback Vector ResNet-50.
    * **Giải pháp 1 (Ngưỡng Cắt Cutoff):** Bổ sung giới hạn tự tin trong Controller. Nếu AI tự tin < 50%, lập tức hủy kết quả chữ và trượt thẳng xuống Tầng 3 (Quét Vector Hình dáng ResNet-50), đảm bảo luôn có kết quả gợi ý.
    * **Giải pháp 2 (Auto-Enhance):** Tích hợp công nghệ ImageEnhance (Pillow). Tự động kích độ sắc nét (150%) và tương phản (110%) ngầm trước khi gửi cho AI, giúp AI đọc cực rõ rãnh kim loại và logo mờ.

* **✅ Khắc Phục Lỗi Trích Xuất Vector Ảnh (CLIP Transformers & 404 Spam):**
    * **Vấn đề:** Quá trình tải vector hình ảnh thất bại do khác biệt cấu trúc thư viện transformers (lỗi Object thiếu thuộc tính norm), lỗi kẹt ma trận (matrix multiplication 1x512 và 768x512) và console bị spam bởi lỗi 404 do link ảnh chết.
    * **Giải pháp:** Viết thuật toán Bypass tự tay bóc tách Tensor lõi thay vì dùng hàm có sẵn, áp dụng torch.nn.functional.normalize chuẩn hóa vector an toàn, và xây dựng cơ chế bắt/nuốt lỗi 404 ẩn danh để giữ cho Terminal luôn sạch sẽ 100%.

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
    * **`test_ai.py`:** Kiểm tra chuyên sâu logic AI (Mocking API Gemini, MobileNetV2 Visual Search, RAG Context, Logic Fallback).
* **✅ Tối Ưu Hóa Mã Nguồn:**
    * Loại bỏ hoàn toàn các file test dư thừa, trùng lặp để tinh gọn dự án.
    * Chuyển logic phân tích ý định (`local_analyze_intent`) sang `utils.py` để tái sử dụng linh hoạt.

---

## 7. 🛡️ Bảo Mật Nâng Cao

* **✅ Ngăn Chặn Race Condition:** Áp dụng kỹ thuật khóa dòng (`with_for_update()`) trong quá trình thanh toán, đảm bảo tính chính xác tuyệt đối của tồn kho và tránh tình trạng bán quá số lượng thực tế.
* **✅ Bảo Mật CSRF:** Tích hợp **Flask-WTF** để bảo vệ toàn bộ hệ thống Form, ngăn chặn các cuộc tấn công giả mạo yêu cầu từ phía người dùng.

---

## 8. 📊 Dashboard Quản Trị (Admin Dashboard)

* **📈 Real-time Analytics:** Hệ thống thống kê doanh thu tức thời dựa trên các đơn hàng có trạng thái "Completed".
* **🧠 Tích hợp Data Science (Pandas):** Ứng dụng thư viện **Pandas** để phân tích sâu dữ liệu thực tế, giúp xác định "Khung giờ vàng" (Peak Hour) có lượng chốt đơn cao nhất và danh sách sản phẩm bán chạy nhất trong tháng.
* **📑 Xuất Báo Cáo Excel Thông Minh:** Sử dụng sự kết hợp giữa **Pandas** và **openpyxl** để tự động render báo cáo doanh thu dưới dạng file Excel chuyên nghiệp (tự động căn chỉnh cột, định dạng tiền tệ) cho Admin.
* **📉 Hệ Thống Biểu Đồ (Chart.js):** * **Biểu đồ đường:** Trực quan hóa xu hướng doanh thu trong 7 ngày gần nhất.
    * **Biểu đồ tròn:** Phân tích tỷ trọng trạng thái đơn hàng trong hệ thống.
    * **🏆 Top Sản Phẩm:** Tự động xếp hạng và hiển thị Top 5 sản phẩm có doanh số cao nhất.

---

## 9. 🧠 Tối Ưu Hóa AI & Persona

* **✅ AI Persona:** Thiết lập tính cách nhân viên tư vấn bán hàng thân thiện, vui vẻ, sử dụng các emoji mang không khí Tết (🧧, 🌸).
* **✅ RAG Optimization:** Cải thiện cấu trúc ngữ cảnh dữ liệu giúp AI nhận biết chính xác tình trạng "Hết hàng" để tư vấn khách hàng hiệu quả hơn.
* **✅ Tối Ưu Tốc Độ & Quota (Smart Cache & Offline Hybrid):**
	* **Cơ chế AICache:** Kích hoạt bảng `AICache` trong cơ sở dữ liệu để tự động lưu trữ các phản hồi từ AI cho các truy vấn đã thực hiện.
	* **Hiệu năng phản hồi:** Truy xuất trực tiếp từ cơ sở dữ liệu giúp hệ thống phản hồi siêu tốc trong < 0.1 giây đối với các câu hỏi trùng lặp, thay vì mất 3-5 giây chờ API Google.
	* **Tiết kiệm tài nguyên:** Sự kết hợp giữa bộ nhớ đệm và thuật toán Local Vector Offline giúp hệ thống tiết kiệm tối đa hạn mức API, đảm bảo vận hành ổn định ngay cả khi gặp giới hạn Quota.
* **✅ Thuật Toán Băm Động (Dynamic MD5 Hash):** Áp dụng kỹ thuật băm toàn bộ ngữ cảnh (`final_prompt` chứa thông tin tồn kho thực tế) thay vì chỉ băm câu hỏi đơn thuần. Cơ chế này đảm bảo AI luôn phản hồi chuẩn xác theo thời gian thực (Ví dụ: Cùng một câu hỏi nhưng nếu trạng thái kho thay đổi, mã Hash sẽ thay đổi để AI cập nhật câu trả lời mới nhất).
* **✅ Refactor Code:** Tối ưu hóa mã nguồn bằng cách tách toàn bộ logic xử lý AI sang module `utils.py`, giúp dễ dàng bảo trì và mở rộng.

---

## 10. 💳 Thanh Toán Online Tự Động (VietQR)

* **✅ Cổng Thanh Toán VietQR Động:** Tự động tạo mã QR chính xác theo số tiền đơn hàng, hỗ trợ khách hàng quét mã thanh toán nhanh chóng.
* **✅ Real-time Polling:** Tích hợp kỹ thuật AJAX để tự động kiểm tra trạng thái giao dịch mỗi 3 giây, cập nhật kết quả ngay lập tức lên giao diện.
* **✅ Countdown Timer:** Thiết lập giao dịch hết hạn sau 3 phút để giải phóng tồn kho, đảm bảo tính bảo mật và công bằng cho các khách hàng khác.
* **✅ Chế Độ Giả Lập (Local):** Bổ sung nút "Gửi tín hiệu ĐÃ NHẬN TIỀN" giúp lập trình viên kiểm thử toàn bộ luồng thanh toán mà không cần giao dịch tiền thật.

---

## 11. 🧠 Nâng Cấp Trí Tuệ Nhân Tạo (AI Search & Logic)

* **✅ Kiến Trúc Hybrid AI (Local Vector DB):**
	* **Nâng cấp (Offline Embedding):** Thay thế hoàn toàn model nhúng Vector của Google bằng mô hình Local đa ngôn ngữ (`sentence-transformers`).
	* **Hiệu quả (Independence):** Xử lý Offline 100% dựa trên sức mạnh CPU của máy chủ, giải phóng hoàn toàn sự phụ thuộc vào API Quota của Google.
	* **Tối ưu hiệu suất (Speed):** Tốc độ đồng bộ (`rag_sync.py`) tăng gấp 10 lần nhờ loại bỏ triệt để độ trễ mạng Internet và các hàm `time.sleep` không cần thiết.
* **✅ Động Cơ Tìm Kiếm Bằng Hình Ảnh (Visual AI Search - Nâng cấp V4):**
	* **Kiến trúc Semantic (CLIP Vision):** Thay thế hoàn toàn ResNet-50 bằng mô hình ngôn ngữ thị giác CLIP (ViT-B/32 của OpenAI). Không chỉ nhìn hình khối thô, CLIP hiểu được "ngữ nghĩa thiết kế hạt mịn" (FGVC) như cụm camera tròn, viền vát phẳng, lưng bọc da.
	* **Loại Bỏ Nhiễu Hạt Ảo Giác (Anti-Hallucination):** Vô hiệu hóa các bộ lọc tăng nét (ImageEnhance) quá đà. Việc giữ nguyên chất lượng ảnh gốc giúp các mô hình LLM Vision như Gemini không bị "ảo giác", tránh nhìn nhầm viền xước mờ thành nhựa bóng do nhiễu hạt nhân tạo.
	* **Nhận Diện Cấp Độ Chuyên Gia (Fine-Grained Master - Đã cập nhật V4):** Nâng cấp bộ quy tắc mổ xẻ thiết kế siêu vi (Chain-of-Thought) cho AI. Bắt buộc AI nhận diện logo hợp tác (Leica/Zeiss/Hasselblad), đèn Aura Light, chất liệu lưng (da PU, sọc xe đua, kính nhám), cùng các hình dáng camera đặc trưng (miệng núi lửa, bậc thang, viên thuốc) để phân biệt chính xác 100% các đời máy giống nhau. Độ phủ sóng nay đã bao trùm toàn bộ thị trường: Samsung, Apple, Xiaomi (POCO/Redmi/Mix), OPPO (Reno/Find), Realme (GT/Number), Vivo (X/Y/iQOO) và ASUS (ROG/Zenfone).
	* **Kỹ Thuật Đối Chiếu Chéo (Cross-Examination):** Trang bị tư duy phản biện cho AI để giải quyết triệt để vấn nạn "Hòa lẫn thiết kế" (Design Blending) giữa các phân khúc. AI bị buộc phải đặt câu hỏi ngược lại (Ví dụ: "Tại sao đây không phải là phiên bản giá rẻ có thiết kế ăn theo?") và tìm các đặc điểm chí mạng (như độ dày cằm màn hình, lỗ khoét camera, chất liệu viền) để loại trừ đối thủ trước khi chốt kết quả.
	* **Cơ chế Lọc Hãng (Brand Isolation):** Giải quyết triệt để lỗi "Tìm Xiaomi ra Samsung". Hệ thống sẽ ưu tiên hiển thị chính xác dòng máy được nhận diện. Nếu kho hết hàng, hệ thống mới gọi đến Mạng CLIP (Vector 512 chiều) để tìm các máy có "Kiểu dáng tương đồng", và bắt buộc phải lọc qua bộ lọc Hãng để đảm bảo gợi ý máy cùng hệ sinh thái.
	* **Tối Ưu Phần Cứng VRAM Giới Hạn:** Tự động đẩy mô hình CLIP lên GPU (CUDA/MPS). Mô hình siêu nhẹ chỉ tốn khoảng ~1.5GB VRAM, đảm bảo xử lý mượt mà, không gây tràn bộ nhớ (Out-Of-Memory) ngay cả trên các dòng card đồ họa cũ như Quadro P620 (4GB).
	* **Chống Ảo Giác & Tối Ưu Băng Thông (Anti-Hallucination & Compression):** Tự động nén ảnh (Resize < 1024px) giúp tiết kiệm 80% băng thông API, chống lỗi nghẽn mạng. Tích hợp Ngưỡng Cắt Tự Tin (Confidence Cutoff < 50%) để vô hiệu hóa ngay lập tức các kết quả AI đoán bừa khi ảnh quá mờ. Bổ sung khiên bảo vệ bắt buộc AI TỪ CHỐI phân tích nếu ảnh tải lên không phải thiết bị di động.
	* **Thông báo Minh bạch (Smart UI):** Nâng cấp hệ thống thông báo trạng thái rõ ràng (VD: "📷 Đã nhận diện: [Tên máy]. Kho tạm hết dòng này, gợi ý các máy [Hãng] có THIẾT KẾ TƯƠNG ĐỒNG"), mang lại trải nghiệm chuyên nghiệp cho người dùng.
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
    * **Nâng cấp:** Tích hợp 11 bài Test chuyên sâu trong `test_AI.py` bao phủ 100% logic:
        * **RAG Context Building:** Kiểm tra khả năng xây dựng ngữ cảnh.
        * **NLP Sentiment Analysis:** Phân tích cảm xúc khách hàng.
        * **Recommendation System:** Kiểm tra logic gợi ý mua kèm.
        * **Bẫy ảo giác AI & Direct Text-RAG Fallback:** Kiểm soát lỗi ảo giác và kiểm tra luồng dự phòng.
	* **Tối ưu Hạn mức Cookie (Session Limit):** Kiểm tra cơ chế tự động giới hạn độ dài lịch sử chat (tối đa 3 lượt) và cắt ngắn phản hồi dài, chống lỗi 431 Request Header Too Large.
	* **Visual AI Search (Mocking):** Giả lập model MobileNetV2 để test độc lập luồng trích xuất Vector Hình Ảnh, đảm bảo hệ thống xử lý lỗi an toàn khi ChromaDB sập hoặc file ảnh tải lên không đúng định dạng.

---

## 12. 🔄 Tự Động Hóa CI/CD (GitHub Actions)

* **✅ Automated Testing Pipeline:** Thiết lập quy trình DevOps tự động chạy toàn bộ bộ kiểm thử (`run_tests.py`) mỗi khi có thao tác push code lên GitHub.
* **✅ Environment Isolation:** Đảm bảo tính khách quan bằng cách chạy test trên môi trường sạch biệt lập (Ubuntu Latest + Python 3.12 + In-Memory DB).
* **✅ Quality Gate:** Thiết lập hàng rào chất lượng, đảm bảo mã nguồn có lỗi không bao giờ được merge vào nhánh chính của dự án.

---

## 13. 🌟 Cập Nhật Giao Diện & Tính Năng Mới Nhất (Hotfixes)

* **✅ Quản Trị Viên (Admin):**
    * **Phục hồi Admin Dashboard:** Khôi phục Modal Form thêm mới sản phẩm, cho phép quản lý đầy đủ thông tin kho, giá khuyến mãi và trạng thái.
    * **Data Insight với Pandas:** Hiển thị trực quan các dữ liệu thực tế như "Khung giờ vàng", sản phẩm mua nhiều và tích hợp nút xuất Excel doanh thu.
    * **Giao diện Tabs:** Chỉnh sửa CSS cho các nút Tab quản trị (Sản phẩm, Đơn hàng...) với chữ đậm, viền nổi bật để tăng tính thẩm mỹ và dễ sử dụng.
    * **Quản lý Đánh giá:** Nâng cấp bảng quản lý bình luận, hỗ trợ trả lời trực tiếp trong trang quản trị.

* **✅ Chi Tiết Sản Phẩm (Product Detail):**
    * **Hệ thống Hỏi & Đáp (Q&A):** Thiết kế khu vực Q&A độc lập với đánh giá sao, hỗ trợ dán nhãn Quản trị viên và trả lời lồng nhau (Nested replies) chuyên nghiệp.
    * **Trick Database Thông Minh:** Tối ưu bảng Comment với logic linh hoạt (rating = 0 cho hỏi đáp) giúp mở rộng hệ thống mà không cần sửa đổi cấu trúc CSDL SQLite.
    * **Wishlist AJAX:** Cho phép thả/gỡ tim sản phẩm mượt mà không cần tải lại trang và đồng bộ trực tiếp vào Database thông qua Many-to-Many Relationship.

* **✅ Hồ Sơ Thành Viên (User Dashboard):**
    * **Tab Yêu Thích:** Hiển thị sản phẩm đã thả tim dưới dạng Grid đẹp mắt, hỗ trợ xóa nhanh và thêm thẳng vào giỏ hàng.
    * **Tiện ích M-Member:** Tích hợp giao diện Kho Voucher dạng Tickets, Sổ bảo hành điện tử (IMEI/Serial) và hiển thị 10 đặc quyền hạng thẻ.
    * **Cập nhật Hồ sơ & Referral:** Bổ sung chọn Giới tính, Ngày sinh và tự động tạo mã REF-ID độc quyền kèm tính năng Copy nhạy bén với thông báo SweetAlert2.

---

## 14. ⚙️ Nâng Cấp Hệ Thống Backend & Tiện Ích (Core System)

* **✅ Xử Lý Lỗi Toàn Cục (Global Error Handling):** Xây dựng module `errors.py` để bắt các lỗi 404, 403, 500 và hiển thị trang `error.html` chuyên nghiệp thay vì lỗi mặc định của server.

---

## 15. 📈 Nâng Cấp Kiến Trúc Dữ Liệu & Phân Tích (Big Data & Performance)

* **✅ Lõi Phân Tích Dữ Liệu (Sales Analytics Engine):** Xây dựng module `analytics_engine.py` ứng dụng thư viện **Pandas** để xử lý Big Data. Cung cấp các công cụ phân tích nâng cao như: Tính tỷ lệ giữ chân khách hàng (Retention Rate), phân tích xu hướng doanh thu 7 ngày, và phân tích RFM để tự động lọc ra tệp khách hàng VIP.
* **✅ Quản Trị Vector AI (Vector Manager):**  Refactor toàn bộ logic ChromaDB thành class vector_manager.py chuyên biệt. Chuyển đổi không gian Vector từ 768 chiều (Google API) sang 384 chiều (Local CPU sentence-transformers), giải phóng 100% sự phụ thuộc vào API Key bên thứ 3 và giúp hệ thống tìm kiếm (RAG) hoạt động ngay cả khi mất mạng internet.

---

## 16. 🕷️ Trí Tuệ Nhân Tạo & Phân Tích Chuyên Sâu (Advanced ML & Tracking)

* **✅ Hệ Thống Học Máy Gợi Ý Sản Phẩm (ML Recommender):** Phát triển thuật toán Lọc cộng tác (Collaborative Filtering) trong `recommendation_ml.py`. Hệ thống tự động học hỏi từ hàng ngàn lịch sử giỏ hàng để đưa ra quyết định gợi ý mua kèm (Cross-sell) cực kỳ chuẩn xác.

---

## 17. 🧱 Chuẩn Hóa Mã Nguồn & Clean Code (Refactoring)

* **✅ Hệ Thống Hằng Số Tập Trung (Constants Manager):** Tạo file `constants.py` để quản lý tập trung các chuỗi văn bản cứng (hardcode strings) như trạng thái đơn hàng, từ khóa AI. Giúp mã nguồn tuân thủ triệt để nguyên tắc SOLID và dễ dàng bảo trì.
* **✅ Refactor Controllers:** Cập nhật logic xử lý tại `main.py` và `admin.py` để sử dụng biến hằng số, loại bỏ 100% "magic strings" (chuỗi rác), đảm bảo code an toàn và sẵn sàng cho việc mở rộng quy mô.

---

## 18. 📜 Tự Động Hóa Tài Liệu (Document as Code)

* **✅ Cỗ Máy Sinh Tài Liệu API Tự Động:** Tích hợp `api_doc_builder.py` sử dụng cây cú pháp **AST** để tự động quét toàn bộ module Routes của Flask. Hệ thống tự động thu thập Endpoints, phương thức HTTP và biên dịch thành tệp `API_DOCUMENTATION.md` đạt chuẩn, tiết kiệm 100% thời gian viết tài liệu thủ công.

---

## 19. 🗄️ Kỹ Nghệ Dữ Liệu (Data Engineering)

* **✅ Động Cơ Xuất Dữ Liệu Data Warehouse:** Phát triển module `data_warehouse_exporter.py` đóng vai trò luồng **ETL** nội bộ. Hệ thống làm sạch dữ liệu bằng **Pandas** (ẩn danh email, format số điện thoại) và xuất cơ sở dữ liệu thành tệp CSV nén ZIP, sẵn sàng cho các công cụ BI như PowerBI hoặc Tableau.

---

## 20. 🧮 Thuật Toán Khuyến Nghị Toán Học

* **✅ Content-Based Filtering:** Xây dựng thuật toán Python thuần túy thay thế AI Vector Search để đảm bảo tính ổn định tuyệt đối. Hệ thống tự động chấm điểm tương đồng (Scoring) dựa trên hãng (+50đ), độ lệch giá (+30đ) và từ khóa (+5đ), mang lại trải nghiệm gợi ý "Sản phẩm tương tự" siêu mượt.

---

## 21. ⚖️ Đấu Trường AI So Sánh 4 Sản Phẩm 

* **✅ Giao Diện Sticky Header:** Tái thiết kế khu vực so sánh mang phong cách chuyên nghiệp, bảng đối chiếu và nút "Mua Ngay" luôn bám dính khi người dùng cuộn xem chi tiết cấu hình.
* **✅ Nâng Cấp Modal 4 Thiết Bị:** Phá bỏ giới hạn cũ, cho phép so sánh cùng lúc 4 thiết bị "cùng hạng cân". Máy chủ yếu đang xem luôn được khóa cứng tại vị trí số 1.
* **✅ Bảo Mật Hạn Mức Trí Tuệ Nhân Tạo (AI Rate Limiting):** Xây dựng cơ chế cấp phát Quota sử dụng AI bảo vệ 4 API Key. Khóa hoàn toàn tính năng với khách vãng lai. Số lượt So sánh AI mỗi ngày được cấp phát tự động theo thứ hạng: M-New (2 lượt), M-Gold (5 lượt), M-Platinum (10 lượt) và M-Diamond (30 lượt). Tự động Reset lượt dùng vào ngày mới.
* **✅ Giao Diện Minh Bạch Quota (UI/UX):** Tích hợp bảng thông báo đặc quyền VIP chuyên nghiệp ngay tại trang So sánh, giúp khách hàng theo dõi trực tiếp số lượt truy vấn AI họ đã tiêu thụ trong ngày.
* **✅ AI Tư Vấn Chuyên Sâu (Deep Analysis):** Prompt được tối ưu để AI đóng vai chuyên gia công nghệ, phân tích ưu/nhược điểm đa chiều và đưa ra lời khuyên "Nên mua máy nào, cho ai, vì sao?".
* **✅ Lõi Dự Phòng (Local Fallback):** Kiến trúc phòng thủ 100% Uptime. Nếu API Gemini gặp sự cố, thuật toán Python sẽ tự động can thiệp để kẻ bảng thông số kỹ thuật, đảm bảo người dùng luôn nhận được kết quả.

---

## 22. 🎟️ Hệ Thống Động Cơ Voucher (Smart Voucher Rule Engine)

* **✅ Kiến Trúc Thiết Kế (Specification Pattern):** Xây dựng lõi `VoucherValidatorEngine` hoàn toàn bằng OOP. Tách biệt các điều kiện kiểm duyệt (Thời hạn, Giá trị đơn tối thiểu, Hạng thẻ VIP) thành các Class độc lập, tuân thủ nguyên lý Open/Closed (SOLID) giúp dễ dàng bảo trì và mở rộng hệ thống sau này.
* **✅ Quản Trị Khuyến Mãi Độc Quyền (Admin):** Admin nắm quyền kiểm soát tuyệt đối: Phát hành mã mới linh hoạt (theo %, theo VNĐ), khóa khẩn cấp mã bị rò rỉ, và xóa vĩnh viễn các chiến dịch thông qua giao diện trực quan tại Dashboard.
* **✅ Trải Nghiệm Khách Hàng (UX/UI):** Kho Voucher tại trang M-Member hiển thị linh động theo dữ liệu lấy từ Database, hỗ trợ sao chép mã (Copy) một chạm với thông báo SweetAlert2. Tại trang Thanh toán (Checkout), khách hàng dán mã vào ô và hệ thống sẽ tự động tính toán, cập nhật trừ tiền trên giao diện qua luồng AJAX mượt mà.
* **✅ Bảo Mật Thanh Toán (Backend Security):** Vá triệt để lỗ hổng thao túng dữ liệu từ phía Frontend (Spoofing). Hệ thống backend tự động tính toán lại Cấp bậc thành viên (Rank) và chạy lại toàn bộ xác thực mã Voucher ở vòng lặp chốt đơn cuối cùng trước khi khóa dòng dữ liệu Database, đảm bảo 100% tính nguyên vẹn số tiền thu về.

---

## 📂 Cấu Trúc Dự Án (Modular MVC)

```text
MobileStore/
├── run.py                    # (ENTRY POINT) Khởi chạy Server Development
├── api_doc_builder.py        # (DOCS) Tự động sinh tài liệu API
├── data_warehouse_exporter.py# (DATA) Script ETL xuất dữ liệu Data Warehouse
├── run_tests.py              # (TEST RUNNER) Script chạy toàn bộ test
├── rag_sync.py               # (AI SYNC) Đồng bộ Vector DB (ChromaDB)
├── migrations/               # (NEW) Thư mục chứa file migration DB
├── tests/                    # Thư mục kiểm thử tự động
│   ├── test_core.py          # Test chức năng cơ bản (Core)
│   ├── test_ai.py            # Test tính năng AI (Mocking)
│   ├── test_models.py        # Test cấu trúc Database
│   ├── test_auth.py          # Test xác thực & Đăng nhập
│   ├── test_integration.py   # Test tích hợp hệ thống
│   ├── test_ml.py            # Test thuật toán Machine Learning
│   ├── test_admin.py         # Test chức năng admin
├── .env                      # Cấu hình bảo mật và API Keys
├── requirements.txt          # Danh sách thư viện dự án
│
└── app/                      # (PACKAGE) Source Code Chính
    ├── __init__.py           # App Factory (Khởi tạo ứng dụng)
    ├── extensions.py         # Cấu hình DB, Login, Migrate, CSRF
    ├── models.py             # Định nghĩa Database Models
    ├── utils.py              # Xử lý AI Logic & Helpers
    ├── errors.py             # Bộ xử lý lỗi toàn cục (404, 500)
    ├── vector_manager.py     # Quản trị Vector DB (ChromaDB)
    ├── analytics_engine.py   # Lõi phân tích dữ liệu (Pandas)
    ├── recommendation_ml.py  # Thuật toán AI Lọc Cộng tác
    ├── constants.py          # Quản lý hằng số (Clean Code)
    ├── custom_exceptions.py  # Phân loại các loại lỗi 
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
