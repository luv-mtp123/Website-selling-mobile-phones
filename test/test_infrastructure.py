import unittest
import time
from app import create_app
from app.extensions import db
from app.security_firewall import MobileStoreFirewall
from app.notification_worker import BackgroundJobWorker


class InfrastructureTestCase(unittest.TestCase):
    """
    Bộ Test Suite đặc biệt dành riêng cho Hệ thống Hạ tầng (Infrastructure):
    1. Tường lửa bảo mật (WAF - Chống DDoS, XSS, SQLi)
    2. Hàng đợi tác vụ nền (Background Job Queue)
    """

    def setUp(self):
        """
        Khởi tạo hệ thống giả lập với cấu hình Testing.
        Đặc biệt kích hoạt lại Firewall và Background Worker vốn bị tắt tự động ở mode Test.
        """
        # 1. Khởi tạo App ảo dùng cho việc test
        self.app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'  # [FIX] Khai báo dùng DB trên RAM
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # [FIX] Bắt buộc phải tạo các bảng ảo để khi gọi request '/' không bị lỗi thiếu bảng Product
        db.create_all()

        # 2. ÉP KHỞI ĐỘNG FIREWALL
        # (Vì trong __init__.py, khi TESTING=True thì Firewall tự động tắt)
        self.firewall = MobileStoreFirewall()
        self.firewall.init_app(self.app)

        # Chỉnh sửa lại giới hạn Rate Limit cực nhỏ (5 request/phút) để test nhanh
        self.firewall.MAX_REQUESTS_PER_MINUTE = 5
        self.firewall.BLOCK_TIME_SECONDS = 3  # Khóa IP 3 giây rồi thả

        # 3. ÉP KHỞI ĐỘNG WORKER (HÀNG ĐỢI)
        self.worker = BackgroundJobWorker()
        self.worker.start_worker(self.app)

    def tearDown(self):
        """
        Tắt an toàn (Graceful Shutdown) tiến trình Worker chạy ngầm và dọn dẹp Database.
        """
        # Dọn dẹp an toàn: Tắt worker thread, drop bảng và pop context
        self.worker.stop_worker()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ==========================================
    # 1. TEST TƯỜNG LỬA BẢO MẬT (FIREWALL)
    # ==========================================

    def test_firewall_xss_and_sqli_prevention(self):
        """Kiểm tra Tường lửa có chặn các cuộc tấn công SQLi và XSS không"""
        print("\n[Infra Test 1] Testing WAF - Chặn XSS & SQL Injection...")

        # ---> [HOTFIX]: Giả lập một IP bên ngoài vì IP Localhost (127.0.0.1) đã được Whitelist
        env = {'REMOTE_ADDR': '192.168.1.100'}

        with self.client:
            # Tấn công 1: Chèn Script XSS vào URL
            res_xss = self.client.get('/?q=<script>alert("Hacked")</script>', environ_base=env)
            self.assertEqual(res_xss.status_code, 403)
            # Hệ thống đã dùng errors.py nên sẽ trả về trang UI có chữ này
            self.assertIn("Truy cập bị từ chối", res_xss.data.decode('utf-8'))

            # Tấn công 2: Thử xóa Database qua Form (SQL Injection)
            res_sqli = self.client.post('/login', data={'username': 'DROP TABLE users;--'}, environ_base=env)
            self.assertEqual(res_sqli.status_code, 403)
            self.assertIn("Truy cập bị từ chối", res_sqli.data.decode('utf-8'))

            # Request hợp lệ (Phải pass)
            res_normal = self.client.get('/?q=iphone', environ_base=env)
            self.assertNotEqual(res_normal.status_code, 403)

    def test_firewall_ddos_rate_limiting(self):
        """Kiểm tra Tường lửa có khóa IP khi Spam Request (DDoS) không"""
        print("\n[Infra Test 2] Testing WAF - Chặn Spam/DDoS (Rate Limiting)...")

        # ---> [HOTFIX]: Giả lập một IP bên ngoài khác để test Rate Limit
        env = {'REMOTE_ADDR': '192.168.1.101'}

        with self.client:
            # Bắn 5 request liên tục (Vẫn trong giới hạn cho phép)
            for i in range(5):
                res = self.client.get('/', environ_base=env)
                self.assertNotEqual(res.status_code, 429)

            # Request thứ 6: Vượt qua MAX_REQUESTS_PER_MINUTE -> Bị khóa (429)
            res_blocked = self.client.get('/', environ_base=env)
            self.assertEqual(res_blocked.status_code, 429)
            # Thông báo chặn ngay lần đầu vi phạm
            self.assertIn("Phát hiện lưu lượng bất thường", res_blocked.data.decode('utf-8'))

            # Chờ 3.1 giây để IP được mở khóa lại (Vượt qua BLOCK_TIME_SECONDS)
            time.sleep(3.1)
            res_unblocked = self.client.get('/', environ_base=env)
            self.assertNotEqual(res_unblocked.status_code, 429)

    # ==========================================
    # 2. TEST HÀNG ĐỢI TÁC VỤ (JOB QUEUE)
    # ==========================================

    def test_background_worker_queue(self):
        """Kiểm tra Hàng đợi có nhận và xử lý tác vụ dưới nền (Thread) không"""
        print("\n[Infra Test 3] Testing Background Job Worker (Message Queue)...")

        # Tạo một biến mảng (mảng có tính tham chiếu) để hứng kết quả từ Thread khác
        execution_results = []

        # Định nghĩa 1 hàm giả lập (ví dụ gửi email) tốn nhiều thời gian
        def mock_heavy_task(result_list, user_name):
            """Hàm giả lập tác vụ nặng (như gửi email) để test luồng Hàng đợi (Queue)."""
            time.sleep(0.5)  # Giả lập độ trễ mạng khi gửi email
            result_list.append(f"Email đã gửi cho {user_name}")

        # Ném task vào hàng đợi (Sẽ không block code chính)
        self.worker.add_job(mock_heavy_task, execution_results, "Boss VIP")

        # Ngay lúc này (chưa đầy 0.5s), mảng kết quả chắc chắn vẫn đang rỗng
        self.assertEqual(len(execution_results), 0)

        # Chờ 1 giây để Worker (chạy ngầm) kịp lôi Task ra xử lý xong
        time.sleep(1)

        # Kiểm chứng mảng kết quả đã được Thread khác đẩy dữ liệu vào
        self.assertEqual(len(execution_results), 1)
        self.assertEqual(execution_results[0], "Email đã gửi cho Boss VIP")


if __name__ == '__main__':
    unittest.main()