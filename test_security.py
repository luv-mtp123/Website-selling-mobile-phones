import unittest
import io
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.models import User, Order, OrderDetail, Product


class SecurityTestCase(unittest.TestCase):

    def setUp(self):
        """Khởi tạo môi trường ảo bỏ qua CSRF để test trực tiếp Logic Backend"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            # Tạo 2 User khác nhau
            user_a = User(username='usera', email='a@test.com', password=generate_password_hash('123'), role='user')
            user_b = User(username='userb', email='b@test.com', password=generate_password_hash('123'), role='user')

            # Tạo 1 Sản phẩm
            prod = Product(name='IP15', brand='Apple', price=1000, stock_quantity=10, is_active=True)
            db.session.add_all([user_a, user_b, prod])
            db.session.commit()

            # Tạo 1 đơn hàng thuộc về User A (ID = 1)
            order_a = Order(id=1, user_id=1, total_price=1000, address='123', phone='09', status='Pending')
            db.session.add(order_a)
            db.session.add(OrderDetail(order_id=1, product_id=1, product_name='IP15', quantity=1, price=1000))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()  # Thêm dòng này để dọn dẹp kết nối database

    def test_1_idor_cancel_order(self):
        """
        [BẢO MẬT] IDOR Test: User B cố tình truyền URL /order/cancel/1 (Đơn của User A)
        Kỳ vọng: Hệ thống phải báo lỗi 404 (Không tìm thấy hoặc không có quyền)
        """
        with self.client:
            # Đăng nhập User B (ID = 2)
            self.client.post('/login', data=dict(username='userb', password='123'))

            # User B cố tình hủy đơn hàng ID=1 của User A
            res = self.client.get('/order/cancel/1')

            # Hệ thống phòng thủ IDOR thành công nếu quăng lỗi 404
            self.assertEqual(res.status_code, 404)

    def test_2_file_upload_size_limit(self):
        """
        [BẢO MẬT] Tấn công DDoS bằng cách đẩy File rác dung lượng siêu lớn (>2MB)
        Kỳ vọng: Cấu hình MAX_CONTENT_LENGTH của hệ thống phải chặn lại và trả về lỗi 413.
        """
        with self.client:
            self.client.post('/login', data=dict(username='usera', password='123'))

            # Giả lập tạo ra 1 file rác nặng 3MB
            large_file_content = b"0" * (3 * 1024 * 1024)
            data = {
                'device_name': 'Hacked Phone',
                'condition': 'Test limit',
                'image': (io.BytesIO(large_file_content), 'hacked.jpg')
            }

            res = self.client.post('/trade-in', data=data, content_type='multipart/form-data', follow_redirects=True)

            # Kiểm tra hệ thống có bắt được lỗi bảo mật và trả về mã 413 (Payload Too Large) không
            self.assertEqual(res.status_code, 413)


if __name__ == '__main__':
    unittest.main()