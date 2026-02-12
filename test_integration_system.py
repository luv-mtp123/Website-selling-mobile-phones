import unittest
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.models import User, Product, Order, OrderDetail, Comment, TradeInRequest


class AdvancedMobileStoreTestCase(unittest.TestCase):

    def setUp(self):
        """Thiết lập môi trường ảo trước mỗi kịch bản test"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            # BẢO ĐẢM DỌN DẸP SẠCH DB CŨ: Rollback các giao dịch treo và Drop toàn bộ
            db.session.rollback()
            db.drop_all()
            db.create_all()

            # Tạo Dữ liệu giả lập
            admin = User(username='admin', email='admin@test.com', password=generate_password_hash('123456'),
                         role='admin')
            guest = User(username='khachhang', email='khach@test.com', password=generate_password_hash('123456'),
                         role='user')

            product1 = Product(name='iPhone 15', brand='Apple', price=20000000, stock_quantity=10, is_active=True)
            product2 = Product(name='Samsung S24', brand='Samsung', price=25000000, stock_quantity=5, is_active=True)

            db.session.add_all([admin, guest, product1, product2])
            db.session.commit()

    def tearDown(self):
        """Dọn dẹp DB sau mỗi bài test"""
        with self.app.app_context():
            # Rollback trước khi drop để mở khóa (release lock) cho SQLite
            db.session.rollback()
            db.drop_all()
            db.session.remove()

    # ==========================================
    # 1. KIỂM THỬ TÍCH HỢP (INTEGRATION TESTING)
    # ==========================================
    def test_integration_comment_cascade_delete(self):
        """
        Kiểm thử tích hợp: Đảm bảo khi Xóa Sản phẩm (Admin)
        thì toàn bộ Bình luận liên quan bị xóa theo (Cascade Delete)
        """
        with self.client:
            # 1. Khách hàng đăng nhập và bình luận vào Sản phẩm 1
            self.client.post('/login', data=dict(username='khachhang', password='123456'))
            self.client.post('/product/1/comment', data=dict(content='Máy rất tốt', rating=5))

            # Kiểm tra xem bình luận đã lưu vào DB chưa
            with self.app.app_context():
                comments = Comment.query.all()
                self.assertEqual(len(comments), 1)
                self.assertEqual(comments[0].product_id, 1)

            # 2. Đăng xuất khách hàng, Đăng nhập Admin
            self.client.get('/logout')
            self.client.post('/login', data=dict(username='admin', password='123456'))

            # 3. Admin xóa sản phẩm 1
            res = self.client.get('/admin/product/delete/1', follow_redirects=True)
            self.assertIn("Đã xóa sản phẩm".encode('utf-8'), res.data)

            # 4. Kiểm chứng DB (Tích hợp Model & Database)
            with self.app.app_context():
                deleted_product = db.session.get(Product, 1)
                remaining_comments = Comment.query.all()

                # Sản phẩm đã bị xóa
                self.assertIsNone(deleted_product)
                # Tính toàn vẹn dữ liệu: Bình luận cũng phải tự động biến mất
                self.assertEqual(len(remaining_comments), 0)

    # ==========================================
    # 2. KIỂM THỬ HỆ THỐNG (SYSTEM / E2E TESTING)
    # ==========================================
    def test_system_full_order_lifecycle(self):
        """
        Kiểm thử hệ thống (End-to-End):
        Giả lập toàn bộ vòng đời của một Đơn Hàng từ lúc khách mua đến lúc Admin Hủy và Hoàn Kho.
        (Kích hoạt trực tiếp logic db.session.get trong admin.py)
        """
        with self.client:
            # BƯỚC 1: Người dùng mua hàng
            self.client.post('/login', data=dict(username='khachhang', password='123456'))

            # Thêm 2 chiếc iPhone 15 (ID=1, Tồn kho ban đầu=10) vào giỏ
            self.client.post('/cart/add/1')
            self.client.post('/cart/add/1')

            # Thêm 1 chiếc Samsung (ID=2, Tồn kho ban đầu=5)
            self.client.post('/cart/add/2')

            # Thanh toán
            self.client.post('/checkout', data=dict(
                address='123 Đường Hệ Thống',
                phone='0999999999',
                payment='cod'
            ))

            # Đăng xuất khách hàng
            self.client.get('/logout')

            # BƯỚC 2: Kiểm tra trạng thái trung gian
            with self.app.app_context():
                p1 = db.session.get(Product, 1)
                p2 = db.session.get(Product, 2)
                order = Order.query.first()

                # Kho hàng đã bị trừ
                self.assertEqual(p1.stock_quantity, 8)  # 10 - 2
                self.assertEqual(p2.stock_quantity, 4)  # 5 - 1
                self.assertEqual(order.status, 'Pending')
                self.assertEqual(order.total_price, 65000000)  # (2*20M) + 25M

            # BƯỚC 3: Admin xử lý đơn hàng (Hủy đơn để hoàn kho)
            self.client.post('/login', data=dict(username='admin', password='123456'))

            # Gọi thẳng vào Route Admin cập nhật trạng thái đơn (Logic trong admin.py)
            res = self.client.get(f'/admin/order/update/{order.id}/Cancelled', follow_redirects=True)

            # Kiểm tra Flash Message
            self.assertIn("Đã hủy đơn và hoàn trả số lượng về kho".encode('utf-8'), res.data)

            # BƯỚC 4: Kiểm chứng hệ thống cuối cùng
            with self.app.app_context():
                p1_final = db.session.get(Product, 1)
                p2_final = db.session.get(Product, 2)
                order_final = db.session.get(Order, order.id)

                # Đơn hàng phải chuyển thành Cancelled
                self.assertEqual(order_final.status, 'Cancelled')

                # Kho hàng PHẢI ĐƯỢC HOÀN LẠI NHƯ CŨ (Tích hợp logic hoàn kho)
                self.assertEqual(p1_final.stock_quantity, 10)
                self.assertEqual(p2_final.stock_quantity, 5)


if __name__ == '__main__':
    unittest.main()