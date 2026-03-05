from flask_login import UserMixin
from .extensions import db
from datetime import datetime, timezone

# =========================================================================
# ---> [NEW: Bảng trung gian (Association Table) cho tính năng Yêu Thích] <---
# =========================================================================
user_favorites = db.Table('user_favorites',
                          db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                          db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
                          )


# =========================================================================

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
    comments = db.relationship('Comment', backref='user', lazy=True)

    # Quan hệ Sản phẩm Yêu thích (Wishlist)
    favorites = db.relationship('Product', secondary=user_favorites, lazy='dynamic',
                                backref=db.backref('favorited_by', lazy='dynamic'))

    avatar_url = db.Column(db.String(500), default='https://cdn-icons-png.flaticon.com/512/3135/3135715.png')

    # ---> [NEW: BIẾN THEO DÕI GIỚI HẠN SỬ DỤNG AI THEO NGÀY] <---
    daily_compare_count = db.Column(db.Integer, default=0)
    last_compare_date = db.Column(db.Date, nullable=True)


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

    comments = db.relationship('Comment', backref='product', lazy=True, cascade="all, delete-orphan")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1 đến 5 sao
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # =========================================================================
    # ---> [NEW: Thêm khóa ngoại tự trỏ để hỗ trợ tính năng Trả lời (Reply)] <---
    # =========================================================================
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    replies = db.relationship(
        'Comment',
        backref=db.backref('parent', remote_side=[id]),
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Comment.created_at.asc()"
    )
    # =========================================================================


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), default='COD')  # COD hoặc Banking

    # ---> [SỬA CHỖ NÀY: Thêm cascade="all, delete-orphan" để vượt qua bài test và chống lỗi DB] <---
    details = db.relationship('OrderDetail', backref='order', lazy=True, cascade="all, delete-orphan")


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class TradeInRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_name = db.Column(db.String(150), nullable=False)
    condition = db.Column(db.Text, nullable=False)
    image_proof = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    valuation_price = db.Column(db.Integer, default=0)
    admin_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# =========================================================================
# ---> [NEW: BẢNG DỮ LIỆU ĐỘNG CƠ VOUCHER (VOUCHER RULE ENGINE)] <---
# =========================================================================
class Voucher(db.Model):
    """
    Mô hình dữ liệu lưu trữ các Chiến dịch Khuyến mãi (Vouchers).
    Được quản lý hoàn toàn bởi Admin.
    """
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(20), default='percent')  # 'percent' hoặc 'fixed'
    discount_value = db.Column(db.Integer, nullable=False)
    max_discount = db.Column(db.Integer, nullable=True)  # Mức giảm tối đa (nếu dùng %)
    min_order_value = db.Column(db.Integer, default=0)  # Đơn hàng tối thiểu
    valid_from = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    valid_to = db.Column(db.DateTime, nullable=False)
    required_rank = db.Column(db.Integer, default=1)  # 1: M-New, 2: M-Gold, 3: M-Plat, 4: M-Diamond
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(255), nullable=True)

    # UI Customization (Giữ lại giao diện đẹp)
    icon = db.Column(db.String(50), default='fas fa-ticket-alt')
    color_theme = db.Column(db.String(50), default='danger')  # 'danger', 'primary', 'warning'