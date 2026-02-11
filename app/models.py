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
    # [UPDATE] Quan hệ với đơn hàng
    orders = db.relationship('Order', backref='user', lazy=True)
    # Quan hệ với yêu cầu thu cũ đổi mới
    trade_ins = db.relationship('TradeInRequest', backref='user', lazy=True)
    # [NEW] Ảnh đại diện
    avatar_url = db.Column(db.String(500), default='https://cdn-icons-png.flaticon.com/512/3135/3135715.png')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    # [UPDATE] Thêm phân loại (Điện thoại/Phụ kiện) và Trạng thái giảm giá
    category = db.Column(db.String(50), default='phone')  # 'phone' hoặc 'accessory'
    is_sale = db.Column(db.Boolean, default=False)
    sale_price = db.Column(db.Integer, nullable=True) # Giá sau khi giảm

    # [NEW] Lưu trữ thông tin biến thể dưới dạng JSON String
    # Cấu trúc colors: [{"name": "Titan Xanh", "image": "url_anh"}, ...]
    # Cấu trúc versions: [{"name": "256GB", "price": 30000000}, ...]
    colors = db.Column(db.Text, nullable=True)
    versions = db.Column(db.Text, nullable=True)
    # [NEW] Trạng thái sản phẩm (Active: Đang bán, Inactive: Ngừng kinh doanh/Ẩn)
    is_active = db.Column(db.Boolean, default=True)
    # [NEW] Quản lý tồn kho
    stock_quantity = db.Column(db.Integer, default=10)

# [UPDATE] Thêm bảng Đơn hàng
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Pending') # Pending, Completed, Cancelled
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    details = db.relationship('OrderDetail', backref='order', lazy=True)

# [UPDATE] Thêm bảng Chi tiết đơn hàng
class OrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False) # Lưu tên cứng để nếu sp bị xóa vẫn còn lịch sử
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False) # Giá tại thời điểm mua
    # [NOTE] Các trạng thái: 'Pending', 'Confirmed', 'Shipping', 'Completed', 'Cancelled'
    status = db.Column(db.String(50), default='Pending')

# [NEW] Bảng lưu Cache AI để tiết kiệm API
class AICache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt_hash = db.Column(db.String(500), unique=True, nullable=False) # Lưu câu hỏi (hoặc mã băm câu hỏi)
    response_text = db.Column(db.Text, nullable=False) # Lưu câu trả lời của AI
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# [NEW] Bảng Yêu cầu Thu cũ Đổi mới
class TradeInRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_name = db.Column(db.String(150), nullable=False)
    condition = db.Column(db.Text, nullable=False)
    image_proof = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='Pending') # Pending, Approved, Rejected
    valuation_price = db.Column(db.Integer, default=0)
    admin_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)