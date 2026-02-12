import unittest
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.models import User, Product, Order


class MobileStoreTestCase(unittest.TestCase):

    def setUp(self):
        """Khởi tạo môi trường ảo (Test Client) trước mỗi bài test"""
        # Khởi tạo App
        self.app = create_app()
        self.app.config['TESTING'] = True

        # SỬ DỤNG DATABASE ẢO TRÊN RAM ĐỂ TEST (Không ảnh hưởng DB thật mobilestore.db)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False  # Tắt CSRF để dễ giả lập form submit

        # Mở Client giả lập trình duyệt
        self.client = self.app.test_client()

        # Thiết lập Database
        with self.app.app_context():
            db.create_all()

            # Tạo 1 Admin ảo
            admin = User(username='admin_test', email='admin@test.com', password=generate_password_hash('123456'),
                         role='admin')

            # Tạo 1 User ảo
            user = User(username='user_test', email='user@test.com', password=generate_password_hash('123456'),
                        role='user')

            # Tạo 1 Sản phẩm ảo
            product = Product(name='iPhone Test', brand='Apple', price=20000000, stock_quantity=5, is_active=True,
                              category='phone')

            db.session.add_all([admin, user, product])
            db.session.commit()

    def tearDown(self):
        """Xóa Database ảo sau khi Test xong"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # --- BẮT ĐẦU CÁC BÀI TEST TỰ ĐỘNG --- #

    def test_1_home_page_loads(self):
        """Kiểm tra trang chủ có tải thành công không (Mã 200 OK)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'MobileStore', response.data)
        self.assertIn(b'iPhone Test', response.data)

    def test_2_user_registration_and_login(self):
        """Kiểm tra luồng Đăng ký và Đăng nhập của người dùng"""
        # Đăng ký
        res_register = self.client.post('/register', data=dict(
            username='new_user',
            email='new@test.com',
            password='password123'
        ), follow_redirects=True)
        self.assertEqual(res_register.status_code, 200)

        # Đăng nhập
        res_login = self.client.post('/login', data=dict(
            username='new_user',
            password='password123'
        ), follow_redirects=True)
        self.assertIn(b'new_user', res_login.data)  # Tên hiển thị trên thanh điều hướng

    def test_3_add_product_to_cart(self):
        """Kiểm tra logic thêm sản phẩm vào giỏ hàng"""
        with self.client:
            # Thêm sản phẩm ID 1 vào giỏ
            res = self.client.post('/cart/add/1', follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # Kiểm tra Session có lưu giỏ hàng không
            with self.client.session_transaction() as sess:
                self.assertIn('cart', sess)
                self.assertIn('1', sess['cart'])
                self.assertEqual(sess['cart']['1']['quantity'], 1)

            # Vào trang giỏ hàng xem có hiển thị sản phẩm không
            cart_page = self.client.get('/cart')
            self.assertIn(b'iPhone Test', cart_page.data)

    def test_4_admin_route_protection(self):
        """Kiểm tra bảo mật trang Quản trị (Chặn người dùng thường)"""
        # Đăng nhập bằng tài khoản user thường
        self.client.post('/login', data=dict(username='user_test', password='123456'))

        # Cố gắng truy cập Dashboard của Admin
        res = self.client.get('/admin')

        # Sẽ bị văng mã lỗi 403 Forbidden
        self.assertEqual(res.status_code, 403)

    def test_5_checkout_process(self):
        """Kiểm tra luồng tạo đơn hàng và trừ kho tự động"""
        with self.client:
            # 1. Đăng nhập
            self.client.post('/login', data=dict(username='user_test', password='123456'))

            # 2. Thêm vào giỏ hàng (Số lượng 2)
            self.client.post('/cart/add/1')
            self.client.post('/cart/add/1')

            # 3. Checkout
            res = self.client.post('/checkout', data=dict(
                address='123 Duong Test',
                phone='0987654321',
                payment='cod'
            ), follow_redirects=True)

            # Kiểm tra thông báo mua thành công
            self.assertIn("thành công".encode('utf-8'), res.data)

            # 4. Kiểm tra trong DB ảo: Kho giảm đi 2 (Từ 5 xuống 3), Đơn hàng có tồn tại
            with self.app.app_context():
                # Cập nhật cú pháp chuẩn SQLAlchemy 2.0 để tránh LegacyAPIWarning
                product = db.session.get(Product, 1)
                order = Order.query.first()

                self.assertEqual(product.stock_quantity, 3)  # Kho giảm
                self.assertIsNotNone(order)
                self.assertEqual(order.total_price, 40000000)  # 2 * 20.000.000đ


if __name__ == '__main__':
    unittest.main()