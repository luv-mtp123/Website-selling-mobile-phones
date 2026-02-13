import unittest
import io
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.models import User, TradeInRequest, Product


class FeaturesTestCase(unittest.TestCase):
    """
    Test Suite chuyên biệt cho các tính năng mới:
    1. Thu cũ đổi mới (Trade-In)
    2. Chatbot AI (Mocking)
    """

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            # Tạo User test
            user = User(username='testuser', email='test@mail.com', password=generate_password_hash('123'), role='user')
            # Tạo Product test cho ngữ cảnh Chatbot
            prod = Product(name='iPhone 15 Test', brand='Apple', price=20000000, stock_quantity=5, is_active=True)

            db.session.add_all([user, prod])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # --- TEST 1: TRADE-IN (THU CŨ ĐỔI MỚI) ---

    def test_tradein_requires_login(self):
        """Kiểm tra: Phải đăng nhập mới được vào trang thu cũ"""
        res = self.client.get('/trade-in', follow_redirects=True)
        # Nếu chưa login, sẽ bị chuyển hướng về login (check text trong trang login)
        self.assertIn(b'ng nh', res.data)  # Check chữ 'Đăng nhập' (bytes)

    def test_tradein_submission_success(self):
        """Kiểm tra: Gửi yêu cầu thu cũ thành công"""
        # 1. Login
        self.client.post('/login', data=dict(username='testuser', password='123'))

        # 2. Mock File Upload
        data = {
            'device_name': 'iPhone 11 Cũ',
            'condition': 'Màn hình trầy xước nhẹ, pin 80%',
            'image': (io.BytesIO(b"fake image data"), 'test_img.jpg')
        }

        # 3. Post Form
        res = self.client.post('/trade-in', data=data, content_type='multipart/form-data', follow_redirects=True)

        # 4. Check kết quả
        # [FIX] Chỉ kiểm tra cụm từ cốt lõi "yêu cầu định giá" để tránh lỗi hoa/thường (Gửi vs gửi)
        self.assertIn("yêu cầu định giá".encode('utf-8'), res.data)

        # 5. Check DB
        with self.app.app_context():
            req = TradeInRequest.query.first()
            self.assertIsNotNone(req)
            self.assertEqual(req.device_name, 'iPhone 11 Cũ')
            self.assertEqual(req.status, 'Pending')

    def test_tradein_invalid_file(self):
        """Kiểm tra: Upload file không phải ảnh (VD: .txt) sẽ bị từ chối"""
        self.client.post('/login', data=dict(username='testuser', password='123'))

        data = {
            'device_name': 'iPhone X',
            'condition': 'Hỏng',
            'image': (io.BytesIO(b"text content"), 'virus.txt')  # File đuôi .txt
        }

        res = self.client.post('/trade-in', data=data, content_type='multipart/form-data', follow_redirects=True)

        # Phải báo lỗi định dạng
        self.assertIn("Định dạng file không hỗ trợ".encode('utf-8'), res.data)

    # --- TEST 2: CHATBOT API (MOCKING EXTERNAL API) ---

    @patch('app.utils.requests.post')
    def test_chatbot_api_ai_response(self, mock_post):
        """
        Kiểm tra API Chatbot trả về phản hồi từ AI (Giả lập).
        Sử dụng @patch để chặn call ra Google thật.
        """
        # Cấu hình Mock trả về dữ liệu giả giống Gemini
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{'content': {'parts': [{'text': 'AI trả lời: Chào bạn!'}]}}]
        }
        mock_post.return_value = mock_response

        # Gọi API Chatbot của mình
        payload = {'message': 'Tư vấn cho tôi iPhone 15'}
        res = self.client.post('/api/chatbot', json=payload)

        json_data = res.get_json()

        # Kiểm tra
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json_data['response'], 'AI trả lời: Chào bạn!')

    def test_chatbot_rule_based(self):
        """Kiểm tra Chatbot trả lời theo từ khóa (Không cần gọi AI)"""
        # Gửi từ khóa "địa chỉ"
        payload = {'message': 'Shop địa chỉ ở đâu vậy?'}
        res = self.client.post('/api/chatbot', json=payload)

        json_data = res.get_json()

        # Phải trả về địa chỉ cứng (đã define trong main.py)
        self.assertIn('123 Đường Tết', json_data['response'])

    def test_chatbot_empty_message(self):
        """Kiểm tra gửi tin nhắn rỗng"""
        res = self.client.post('/api/chatbot', json={'message': ''})
        json_data = res.get_json()
        self.assertIn('Mời bạn hỏi', json_data['response'])


if __name__ == '__main__':
    unittest.main()