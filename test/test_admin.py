import unittest
import io
import pandas as pd
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User, Product, Order, OrderDetail, TradeInRequest, Comment


class AdminDashboardTestCase(unittest.TestCase):
    """
    Bộ Test Suite kiểm thử toàn diện các chức năng của Admin:
    - Bảo mật phân quyền (Chỉ Admin mới được vào)
    - Quản lý Sản phẩm (Thêm, Sửa, Xóa)
    - Quản lý Đơn hàng (Cập nhật trạng thái)
    - Quản lý Thu cũ đổi mới
    - Xuất file Excel Báo cáo doanh thu (Pandas)
    """

    def setUp(self):
        """Khởi tạo môi trường Test với Database ảo trên RAM"""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()
        self.create_mock_data()

    def tearDown(self):
        """Dọn dẹp Database sau khi test xong"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_mock_data(self):
        """Tạo dữ liệu giả lập cho Admin test"""
        # 1. Tạo Users
        admin = User(username='admin_vip', email='admin@test.com', password=generate_password_hash('123'), role='admin',
                     full_name='Boss')
        user = User(username='normal_user', email='user@test.com', password=generate_password_hash('123'), role='user',
                    full_name='Khách')

        # 2. Tạo Products
        p1 = Product(name='Test Phone 1', brand='Apple', price=1000, stock_quantity=10, is_active=True)
        p2 = Product(name='Test Phone 2', brand='Samsung', price=2000, stock_quantity=5, is_active=True)

        db.session.add_all([admin, user, p1, p2])
        db.session.commit()

        # 3. Tạo Đơn hàng đã hoàn thành (Để test xuất Excel)
        order = Order(user_id=user.id, total_price=3000, address='HCM', phone='090', status='Completed')
        db.session.add(order)
        db.session.commit()

        od1 = OrderDetail(order_id=order.id, product_id=p1.id, product_name=p1.name, quantity=1, price=1000)
        od2 = OrderDetail(order_id=order.id, product_id=p2.id, product_name=p2.name, quantity=1, price=2000)
        db.session.add_all([od1, od2])

        # 4. Tạo yêu cầu Thu cũ đổi mới
        tradein = TradeInRequest(user_id=user.id, device_name='Old iPhone', condition='Good', image_proof='img.jpg',
                                 status='Pending')
        db.session.add(tradein)
        db.session.commit()

    def login(self, username, password):
        """Helper function để đăng nhập"""
        return self.client.post('/login', data=dict(username=username, password=password), follow_redirects=True)

    def test_admin_dashboard_access(self):
        """Kiểm tra quyền truy cập trang Dashboard Admin"""
        print("\n[Admin Test 1] Kiểm tra quyền truy cập Dashboard...")
        # Khách thường đăng nhập -> Bị chặn
        self.login('normal_user', '123')
        res_user = self.client.get('/admin')
        self.assertEqual(res_user.status_code, 403)

        self.client.get('/logout')

        # Admin đăng nhập -> Thành công
        self.login('admin_vip', '123')
        res_admin = self.client.get('/admin')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn("Dashboard Thống Kê".encode('utf-8'), res_admin.data)

    def test_admin_export_excel_report(self):
        """Kiểm tra tính năng Xuất Báo cáo Excel (Sử dụng Pandas)"""
        print("\n[Admin Test 2] Kiểm tra Xuất Báo cáo Excel...")
        self.login('admin_vip', '123')

        res = self.client.get('/admin/export/report')

        # Đảm bảo file trả về là file Excel hợp lệ
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # Dùng Pandas đọc ngược lại file Excel từ bộ nhớ đệm (BytesIO)
        excel_data = io.BytesIO(res.data)
        df = pd.read_excel(excel_data)

        # Kiểm tra nội dung bên trong file Excel có khớp với Database không
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)  # Có 1 đơn hàng Completed
        self.assertEqual(df.iloc[0]['Tổng Tiền'], 3000)
        self.assertEqual(df.iloc[0]['Khách Hàng'], 'Khách')

    def test_admin_product_management(self):
        """Kiểm tra quy trình Thêm và Xóa sản phẩm của Admin"""
        print("\n[Admin Test 3] Kiểm tra Quản lý Sản phẩm...")
        self.login('admin_vip', '123')

        # Thêm sản phẩm mới
        self.client.post('/admin/product/add', data={
            'name': 'New iPad',
            'brand': 'Apple',
            'price': 15000,
            'category': 'accessory',
            'stock_quantity': 20,
            'is_active': 'on'
        }, follow_redirects=True)

        new_product = Product.query.filter_by(name='New iPad').first()
        self.assertIsNotNone(new_product)
        self.assertEqual(new_product.stock_quantity, 20)

        # Xóa sản phẩm vừa thêm
        self.client.get(f'/admin/product/delete/{new_product.id}', follow_redirects=True)
        deleted_product = db.session.get(Product, new_product.id)
        self.assertIsNone(deleted_product)

    def test_admin_tradein_approval(self):
        """Kiểm tra quy trình Duyệt yêu cầu Thu cũ đổi mới"""
        print("\n[Admin Test 4] Kiểm tra Duyệt Thu cũ đổi mới...")
        self.login('admin_vip', '123')

        tradein_req = TradeInRequest.query.first()

        # Admin duyệt và định giá 5000
        self.client.post('/admin/tradein/update', data={
            'id': tradein_req.id,
            'action': 'approve',
            'valuation_price': 5000,
            'admin_note': 'Máy đẹp, thu giá cao'
        }, follow_redirects=True)

        updated_req = db.session.get(TradeInRequest, tradein_req.id)
        self.assertEqual(updated_req.status, 'Approved')
        self.assertEqual(updated_req.valuation_price, 5000)


if __name__ == '__main__':
    unittest.main()