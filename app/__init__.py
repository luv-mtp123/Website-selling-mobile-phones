import os
import json
from flask import Flask
from werkzeug.security import generate_password_hash
from .extensions import db, login_manager, oauth
from .models import User, Product, AICache


def create_app():
    app = Flask(__name__)

    # 1. Cấu hình App & Load .env
    # (Load thủ công vì file này nằm trong thư mục con app/)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line: continue
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

    # Sử dụng config từ app.py cũ của bạn
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mobilestore.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 2. Khởi tạo Extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Chuyển hướng về route login của blueprint auth
    oauth.init_app(app)

    # Đăng ký Google OAuth (Logic từ app.py cũ)
    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # 3. Đăng ký Filter Tiền tệ (Logic từ app.py cũ - đã fix lỗi ValueError)
    @app.template_filter('vnd')
    def vnd_filter(value):
        if value is None: return "0 đ"
        try:
            # Ép kiểu an toàn về số thực trước khi format
            value = float(value)
        except (ValueError, TypeError):
            return "0 đ"
        return "{:,.0f} đ".format(value).replace(",", ".")

    # 4. Đăng ký Blueprints (Routes)
    # Import bên trong hàm để tránh lỗi vòng lặp (circular import)
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app


# Helper load user cho Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Helper khởi tạo dữ liệu mẫu (Được gọi từ run.py)
# Logic này được lấy từ app.py cũ để đảm bảo dữ liệu nhất quán
def initialize_database():
    # Lưu ý: Hàm này cần được gọi trong app_context từ run.py
    db.create_all()

    # 1. Tạo Admin & Khách
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@store.com', password=generate_password_hash('123456'), role='admin',
                     full_name='Admin Shop')
        guest = User(username='khach', email='khach@store.com', password=generate_password_hash('123456'), role='user',
                     full_name='Khách hàng')
        db.session.add_all([admin, guest])

    # 2. Tạo Sản phẩm mẫu (nếu chưa có)
    if not Product.query.first():
        # Dữ liệu mẫu từ app.py cũ của bạn
        products_data = [
            # --- CÁC SẢN PHẨM CŨ ---
            {"name": "iPhone 15 Pro Max", "brand": "Apple", "price": 34990000, "category": "phone", "is_sale": False,
             "desc": "Titan tự nhiên, Chip A17 Pro, Camera 5x.",
             "img": "https://cdn.mobilecity.vn/mobilecity-vn/images/2023/09/iphone-15-pro-max-titan-trang-cu.jpg.webp"},
            {"name": "Samsung Galaxy S24 Ultra", "brand": "Samsung", "price": 31990000, "category": "phone",
             "is_sale": True, "sale_price": 29990000,
             "desc": "Quyền năng AI, Camera 200MP, S-Pen.",
             "img": "https://m.media-amazon.com/images/I/71WcjsOVOmL._AC_SX679_.jpg"},
            {"name": "Xiaomi 14", "brand": "Xiaomi", "price": 22990000, "category": "phone", "is_sale": False,
             "desc": "Ống kính Leica, Snapdragon 8 Gen 3.",
             "img": "https://m.media-amazon.com/images/I/51hOisZjbeL._AC_SX679_.jpg"},
            {"name": "Google Pixel 8 Pro", "brand": "Google", "price": 24000000, "category": "phone", "is_sale": False,
             "desc": "Camera AI đỉnh cao, Android gốc.",
             "img": "https://m.media-amazon.com/images/I/71h9zq4viSL._AC_SL1500_.jpg"},

            # --- 15 ĐIỆN THOẠI MỚI ---
            {"name": "iPhone 13 128GB", "brand": "Apple", "price": 13990000, "category": "phone", "is_sale": True,
             "sale_price": 12590000,
             "desc": "Thiết kế vuông vức, Camera kép sắc nét.",
             "img": "https://m.media-amazon.com/images/I/51wPUCGf9zL._AC_SL1166_.jpg"},
            {"name": "Samsung Galaxy A54 5G", "brand": "Samsung", "price": 8490000, "category": "phone",
             "is_sale": False,
             "desc": "Chống nước IP67, Camera OIS ổn định.",
             "img": "https://m.media-amazon.com/images/I/61A+wkddftL._AC_SL1500_.jpg"},
            {"name": "Xiaomi Redmi Note 13 Pro", "brand": "Xiaomi", "price": 7290000, "category": "phone",
             "is_sale": True, "sale_price": 6890000,
             "desc": "Camera 200MP, Sạc siêu nhanh 67W.",
             "img": "https://m.media-amazon.com/images/I/51qT8RuY56L._AC_SL1200_.jpg"},
            {"name": "Oppo Reno 10 5G", "brand": "Oppo", "price": 9990000, "category": "phone", "is_sale": False,
             "desc": "Chuyên gia chân dung, Thiết kế 3D cong.",
             "img": "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=800"},
            {"name": "iPhone 15 Plus", "brand": "Apple", "price": 25990000, "category": "phone", "is_sale": False,
             "desc": "Màn hình lớn, Pin trâu nhất dòng iPhone.",
             "img": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=800"},
            {"name": "Samsung Galaxy S23 FE", "brand": "Samsung", "price": 11890000, "category": "phone",
             "is_sale": True, "sale_price": 10500000,
             "desc": "Phiên bản Fan Edition, Cấu hình flagship.",
             "img": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=800"},
            {"name": "Samsung Galaxy Z Fold5", "brand": "Samsung", "price": 36990000, "category": "phone",
             "is_sale": True, "sale_price": 32990000,
             "desc": "Gập mở không kẽ hở, Đa nhiệm PC.",
             "img": "https://images.unsplash.com/photo-1616348436168-de43ad0db179?w=800"},
            {"name": "Xiaomi 13T Pro", "brand": "Xiaomi", "price": 14990000, "category": "phone", "is_sale": False,
             "desc": "Camera Leica, Màn hình 144Hz mượt mà.",
             "img": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800"},
            {"name": "Realme 11 Pro+", "brand": "Realme", "price": 10500000, "category": "phone", "is_sale": False,
             "desc": "Thiết kế da sinh học, Camera 200MP.",
             "img": "https://images.unsplash.com/photo-1605236453806-6ff36851218e?w=800"},
            {"name": "Vivo V29 5G", "brand": "Vivo", "price": 12990000, "category": "phone", "is_sale": True,
             "sale_price": 11990000,
             "desc": "Vòng sáng Aura, Chụp đêm cực đỉnh.",
             "img": "https://images.unsplash.com/photo-1589492477829-5e65395b66cc?w=800"},
            {"name": "iPhone 11 64GB", "brand": "Apple", "price": 9890000, "category": "phone", "is_sale": True,
             "sale_price": 8500000,
             "desc": "Huyền thoại giữ giá, Hiệu năng vẫn tốt.",
             "img": "https://images.unsplash.com/photo-1573148195900-7845dcb9b858?w=800"},
            {"name": "Samsung Galaxy M34", "brand": "Samsung", "price": 5690000, "category": "phone", "is_sale": False,
             "desc": "Pin mãnh thú 6000mAh, Màn hình Super AMOLED.",
             "img": "https://images.unsplash.com/photo-1600087626014-e652e18bbff2?w=800"},
            {"name": "Oppo Find N3 Flip", "brand": "Oppo", "price": 22990000, "category": "phone", "is_sale": False,
             "desc": "Camera Hasselblad, Màn hình phụ tiện lợi.",
             "img": "https://images.unsplash.com/photo-1621330396173-e41b1cafd17f?w=800"},
            {"name": "Asus ROG Phone 7", "brand": "Asus", "price": 26990000, "category": "phone", "is_sale": False,
             "desc": "Quái vật gaming, Tản nhiệt cực tốt.",
             "img": "https://images.unsplash.com/photo-1580910051074-3eb6948d3ea0?w=800"},
            {"name": "Google Pixel 7a", "brand": "Google", "price": 9500000, "category": "phone", "is_sale": True,
             "sale_price": 8900000,
             "desc": "Nhiếp ảnh thuật toán, Nhỏ gọn vừa tay.",
             "img": "https://images.unsplash.com/photo-1598327105666-5b89351aff23?w=800"},

            # --- CÁC PHỤ KIỆN CŨ ---
            {"name": "Sạc Nhanh Anker 20W", "brand": "Phụ kiện chung", "price": 300000, "category": "accessory",
             "is_sale": False,
             "desc": "Sạc nhanh cho iPhone, Samsung nhỏ gọn.",
             "img": "https://images.unsplash.com/photo-1622974332856-7864e493e878?w=800"},
            {"name": "Ốp Lưng MagSafe trong suốt", "brand": "Apple", "price": 990000, "category": "accessory",
             "is_sale": True, "sale_price": 790000,
             "desc": "Chống ố vàng, hít nam châm cực mạnh.",
             "img": "https://images.unsplash.com/photo-1603539279542-e818b6b553e4?w=800"},
            {"name": "Cáp Type-C Dù Siêu Bền", "brand": "Phụ kiện chung", "price": 150000, "category": "accessory",
             "is_sale": False,
             "desc": "Chống đứt gãy, hỗ trợ sạc nhanh 60W.",
             "img": "https://images.unsplash.com/photo-1596708761271-925721731631?w=800"},
            {"name": "Tai nghe Galaxy Buds2 Pro", "brand": "Samsung", "price": 3990000, "category": "accessory",
             "is_sale": True, "sale_price": 2500000,
             "desc": "Chống ồn chủ động, âm thanh Hi-Fi.",
             "img": "https://images.unsplash.com/photo-1662668581005-9b2f6b867c29?w=800"},
            {"name": "Kính Cường Lực KingKong", "brand": "Phụ kiện chung", "price": 120000, "category": "accessory",
             "is_sale": False,
             "desc": "Bảo vệ màn hình tối đa, vuốt mượt.",
             "img": "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=800"},

            # --- 10 PHỤ KIỆN MỚI ---
            {"name": "Cáp Lightning Apple Zin", "brand": "Apple", "price": 490000, "category": "accessory",
             "is_sale": False,
             "desc": "Cáp chính hãng, đồng bộ dữ liệu ổn định.",
             "img": "https://images.unsplash.com/photo-1586527633543-245c3453b6cb?w=800"},
            {"name": "Sạc dự phòng Samsung 10000mAh", "brand": "Samsung", "price": 790000, "category": "accessory",
             "is_sale": True, "sale_price": 550000,
             "desc": "Sạc nhanh 25W, thiết kế kim loại sang trọng.",
             "img": "https://images.unsplash.com/photo-1625723049755-9b0d3674483a?w=800"},
            {"name": "Tai nghe AirPods Pro 2", "brand": "Apple", "price": 5990000, "category": "accessory",
             "is_sale": True, "sale_price": 5290000,
             "desc": "Chống ồn gấp 2 lần, Cổng Type-C mới.",
             "img": "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=800"},
            {"name": "Ốp lưng Silicon iPhone 15", "brand": "Phụ kiện chung", "price": 150000, "category": "accessory",
             "is_sale": False,
             "desc": "Nhiều màu sắc, cảm giác cầm nắm êm ái.",
             "img": "https://images.unsplash.com/photo-1587572236558-a3751c6d42c0?w=800"},
            {"name": "Kính Cường Lực S24 Ultra", "brand": "Phụ kiện chung", "price": 180000, "category": "accessory",
             "is_sale": False,
             "desc": "Full màn hình, hỗ trợ vân tay siêu âm.",
             "img": "https://images.unsplash.com/photo-1585338107529-13f9530575c1?w=800"},
            {"name": "Củ sạc Xiaomi 67W", "brand": "Xiaomi", "price": 450000, "category": "accessory", "is_sale": True,
             "sale_price": 390000,
             "desc": "Sạc siêu tốc cho Xiaomi và Laptop.",
             "img": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=800"},
            {"name": "Dây đeo Apple Watch Alpine", "brand": "Phụ kiện chung", "price": 250000, "category": "accessory",
             "is_sale": False,
             "desc": "Chất liệu vải dù bền bỉ, đậm chất thể thao.",
             "img": "https://images.unsplash.com/photo-1551817958-c1e8892134e6?w=800"},
            {"name": "Loa Bluetooth JBL Go 3", "brand": "Phụ kiện chung", "price": 990000, "category": "accessory",
             "is_sale": True, "sale_price": 850000,
             "desc": "Nhỏ gọn, kháng nước IP67, Âm bass mạnh.",
             "img": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=800"},
            {"name": "Gậy chụp ảnh Bluetooth", "brand": "Phụ kiện chung", "price": 120000, "category": "accessory",
             "is_sale": False,
             "desc": "3 chân chắc chắn, có điều khiển từ xa.",
             "img": "https://images.unsplash.com/photo-1615494488334-972740947ae1?w=800"},
            {"name": "Giá đỡ điện thoại để bàn", "brand": "Phụ kiện chung", "price": 80000, "category": "accessory",
             "is_sale": False,
             "desc": "Kim loại chắc chắn, xoay 360 độ tiện lợi.",
             "img": "https://images.unsplash.com/photo-1586775490184-b79134164193?w=800"},
        ]

        for p_data in products_data:
            # Kiểm tra tránh trùng lặp nếu chạy lại
            existing = Product.query.filter_by(name=p_data["name"]).first()
            if not existing:
                # Tạo sản phẩm cơ bản
                new_p = Product(
                    name=p_data["name"], brand=p_data["brand"], price=p_data["price"],
                    description=p_data["desc"], image_url=p_data["img"],
                    category=p_data["category"], is_sale=p_data["is_sale"],
                    sale_price=p_data.get("sale_price")
                )

                # Thêm variants mẫu cho iPhone và Samsung (Demo)
                if "iPhone 15" in p_data["name"]:
                    new_p.colors = json.dumps([
                        {"name": "Titan Tự Nhiên",
                         "image": "https://cdn.mobilecity.vn/mobilecity-vn/images/2023/09/iphone-15-pro-max-titan-trang-cu.jpg.webp"},
                        {"name": "Titan Xanh",
                         "image": "https://cdn.mobilecity.vn/mobilecity-vn/images/2023/09/iphone-15-pro-max-titan-xanh-cu.jpg.webp"},
                        {"name": "Titan Đen",
                         "image": "https://cdn.mobilecity.vn/mobilecity-vn/images/2023/09/iphone-15-pro-max-titan-den-cu.jpg.webp"}
                    ])
                    new_p.versions = json.dumps([
                        {"name": "256GB", "price": 34990000},
                        {"name": "512GB", "price": 40990000},
                        {"name": "1TB", "price": 46990000}
                    ])
                elif "Samsung" in p_data["name"]:
                    new_p.colors = json.dumps([
                        {"name": "Xám Titan",
                         "image": "https://m.media-amazon.com/images/I/71WcjsOVOmL._AC_SX679_.jpg"},
                        {"name": "Đen Titan", "image": "https://m.media-amazon.com/images/I/71optuHj9WL._AC_SX679_.jpg"}
                    ])
                    new_p.versions = json.dumps([
                        {"name": "12GB/256GB", "price": 29990000},
                        {"name": "12GB/512GB", "price": 33990000}
                    ])

                db.session.add(new_p)

    db.session.commit()
    print("Database & Data initialized successfully!")