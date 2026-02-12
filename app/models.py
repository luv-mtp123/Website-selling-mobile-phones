from flask_login import UserMixin
from .extensions import db
from datetime import datetime


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='user')
    full_name = db.Column(db.String(150), nullable=True)

    # Quan hệ
    orders = db.relationship('Order', backref='user', lazy=True)
    trade_ins = db.relationship('TradeInRequest', backref='user', lazy=True)
    # [NEW] Quan hệ với Comment
    comments = db.relationship('Comment', backref='user', lazy=True)

    avatar_url = db.Column(db.String(500), default='https://cdn-icons-png.flaticon.com/512/3135/3135715.png')


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(50), default='phone')
    is_sale = db.Column(db.Boolean, default=False)
    sale_price = db.Column(db.Integer, nullable=True)

    colors = db.Column(db.Text, nullable=True)
    versions = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    stock_quantity = db.Column(db.Integer, default=10)

    # [NEW] Quan hệ với Comment (Xóa sản phẩm -> Xóa luôn comment)
    comments = db.relationship('Comment', backref='product', lazy=True, cascade="all, delete-orphan")


# [NEW] Bảng Bình Luận & Đánh Giá
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1 đến 5 sao
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    details = db.relationship('OrderDetail', backref='order', lazy=True)


class OrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Pending')


class AICache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt_hash = db.Column(db.String(500), unique=True, nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TradeInRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_name = db.Column(db.String(150), nullable=False)
    condition = db.Column(db.Text, nullable=False)
    image_proof = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    valuation_price = db.Column(db.Integer, default=0)
    admin_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)