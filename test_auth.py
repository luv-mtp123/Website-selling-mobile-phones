import unittest
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash


class AuthenticationTestCase(unittest.TestCase):
    """
    Bộ Test Suite kiểm tra quy trình Đăng ký, Đăng nhập, Đăng xuất.
    """

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_valid_registration(self):
        """Kiểm tra Đăng ký tài khoản thành công"""
        with self.client:
            res = self.client.post('/register', data={
                'username': 'newuser',
                'email': 'new@mail.com',
                'password': 'password123',
                'confirm_password': 'password123'
            }, follow_redirects=True)

            # Kiểm tra xem user có được lưu vào DB không
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, 'new@mail.com')

    def test_login_success_and_logout(self):
        """Kiểm tra Đăng nhập thành công và Đăng xuất"""
        # Tạo user mẫu
        u = User(username='testlogin', email='test@mail.com', password=generate_password_hash('123456'))
        db.session.add(u)
        db.session.commit()

        with self.client:
            # Login đúng
            res_login = self.client.post('/login', data={
                'username': 'testlogin',
                'password': '123456'
            }, follow_redirects=True)
            self.assertEqual(res_login.status_code, 200)

            # Logout
            res_logout = self.client.get('/logout', follow_redirects=True)
            self.assertEqual(res_logout.status_code, 200)

    def test_login_failure(self):
        """Kiểm tra hệ thống chặn Đăng nhập sai mật khẩu"""
        u = User(username='testfail', email='fail@mail.com', password=generate_password_hash('123456'))
        db.session.add(u)
        db.session.commit()

        with self.client:
            # Login sai mật khẩu
            res = self.client.post('/login', data={
                'username': 'testfail',
                'password': 'wrongpassword'
            }, follow_redirects=True)

            # Giao diện phải chứa thông báo lỗi (Flash message)
            self.assertIn("lỗi".encode('utf-8') or "sai".encode('utf-8'), res.data.lower())


if __name__ == '__main__':
    unittest.main()