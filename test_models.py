import unittest
from app import create_app, db
from app.models import User, Product, Comment, Order, OrderDetail


class ModelsTestCase(unittest.TestCase):
    """
    Bộ Test Suite chuyên kiểm tra cấu trúc Database (Models)
    Đảm bảo các mối quan hệ (Relationships) và Ràng buộc (Constraints) hoạt động đúng.
    """

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation(self):
        """Kiểm tra tạo User mặc định"""
        u = User(username='test_user', email='test@mail.com', password='hashed_password')
        db.session.add(u)
        db.session.commit()

        # User mới mặc định phải có role là 'user'
        self.assertEqual(u.role, 'user')
        self.assertIsNotNone(u.id)

    def test_product_defaults(self):
        """Kiểm tra giá trị mặc định của bảng Product"""
        p = Product(name='iPhone 15', brand='Apple', price=20000)
        db.session.add(p)
        db.session.commit()

        # Kiểm tra các giá trị default
        self.assertEqual(p.category, 'phone')
        self.assertEqual(p.is_sale, False)
        self.assertEqual(p.stock_quantity, 10)
        self.assertTrue(p.is_active)

    def test_comment_reply_relationship(self):
        """Kiểm tra tính năng Trả lời Bình luận (Self-referential relationship)"""
        u = User(username='commenter', email='c@mail.com', password='123')
        p = Product(name='Test Phone', brand='Test', price=100)
        db.session.add_all([u, p])
        db.session.commit()

        # Tạo bình luận gốc (Câu hỏi)
        parent_comment = Comment(user_id=u.id, product_id=p.id, content='Máy này pin bao lâu?', rating=0)
        db.session.add(parent_comment)
        db.session.commit()

        # Tạo câu trả lời (Reply)
        child_comment = Comment(user_id=u.id, product_id=p.id, content='Pin tầm 8 tiếng nhé.',
                                parent_id=parent_comment.id)
        db.session.add(child_comment)
        db.session.commit()

        # Truy vấn lại và kiểm tra mối quan hệ lồng nhau
        fetched_parent = db.session.get(Comment, parent_comment.id)

        self.assertEqual(len(fetched_parent.replies), 1)
        self.assertEqual(fetched_parent.replies[0].content, 'Pin tầm 8 tiếng nhé.')
        self.assertEqual(fetched_parent.replies[0].parent.content, 'Máy này pin bao lâu?')

    def test_order_cascade_delete(self):
        """Kiểm tra nếu xóa Order thì OrderDetail có bị xóa theo không"""
        u = User(username='buyer', email='b@mail.com', password='123')
        db.session.add(u)
        db.session.commit()

        o = Order(user_id=u.id, total_price=500, address='HCM', phone='123')
        db.session.add(o)
        db.session.commit()

        od = OrderDetail(order_id=o.id, product_id=1, product_name='Item', quantity=1, price=500)
        db.session.add(od)
        db.session.commit()

        # Xóa Order gốc
        db.session.delete(o)
        db.session.commit()

        # Kiểm tra OrderDetail có bị mồ côi không
        remaining_details = OrderDetail.query.all()
        self.assertEqual(len(remaining_details), 0)


if __name__ == '__main__':
    unittest.main()