import unittest
import io
import json
from app import create_app, db
from app.models import User, Product, Order, TradeInRequest
from werkzeug.security import generate_password_hash


class CoreFunctionalityTestCase(unittest.TestCase):
    """
    Test các chức năng cốt lõi của Website:
    1. Xác thực (Login/Register/Phân quyền)
    2. Mua sắm (Giỏ hàng/Thanh toán/Tồn kho)
    3. Thu cũ đổi mới (Trade-In)
    """

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.create_sample_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_sample_data(self):
        admin = User(username='admin', email='admin@test.com', password=generate_password_hash('123'), role='admin',
                     full_name='Admin')
        user = User(username='user', email='user@test.com', password=generate_password_hash('123'), role='user',
                    full_name='User')
        p1 = Product(name='iPhone 15', brand='Apple', price=20000000, category='phone', stock_quantity=10,
                     is_active=True)
        db.session.add_all([admin, user, p1])
        db.session.commit()

    def login(self, username, password):
        return self.client.post('/login', data=dict(username=username, password=password), follow_redirects=True)

    # --- 1. AUTHENTICATION ---
    def test_auth_flow(self):
        # Register
        self.client.post('/register', data=dict(username='new', email='n@t.com', password='123'), follow_redirects=True)
        # Login
        res = self.login('new', '123')
        self.assertIn(b'new', res.data)
        # Access Admin (Forbidden)
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 403)

    # --- 2. SHOPPING CART & CHECKOUT ---
    def test_shopping_flow(self):
        self.login('user', '123')
        p = Product.query.first()

        # Add to cart
        self.client.post(f'/cart/add/{p.id}', follow_redirects=True)

        # Checkout
        res = self.client.post('/checkout', data=dict(address='Home', phone='090', payment='cod'),
                               follow_redirects=True)
        self.assertIn("thành công".encode('utf-8'), res.data)

        # Verify Inventory
        p_after = db.session.get(Product, p.id)
        self.assertEqual(p_after.stock_quantity, 9)

    # --- 3. TRADE-IN (THU CŨ) ---
    def test_tradein_submission(self):
        self.login('user', '123')
        data = {
            'device_name': 'iPhone 11 Cũ',
            'condition': 'Trầy xước',
            'image': (io.BytesIO(b"fake image"), 'test.jpg')
        }
        res = self.client.post('/trade-in', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertIn("yêu cầu định giá".encode('utf-8'), res.data)

        req = TradeInRequest.query.first()
        self.assertIsNotNone(req)
        self.assertEqual(req.device_name, 'iPhone 11 Cũ')


if __name__ == '__main__':
    unittest.main()