import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user


# --- HÀM LOAD .ENV THỦ CÔNG ---
# Giúp chạy app mà không cần cài python-dotenv
def load_env_file():
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


# Gọi hàm load env ngay khi khởi động
load_env_file()

# Fix lỗi Python 3.14 (Vẫn giữ để an toàn hệ thống)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Import các thành phần (Sau khi đã load env)
from extensions import db, login_manager
from models import User, Product
# Import hàm Gemini từ utils
from utils import get_gemini_suggestions

app = Flask(__name__)

# --- CẤU HÌNH ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ban-dien-thoai-secret-key-123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mobilestore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Khởi tạo
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- Filter hiển thị Markdown ---
@app.template_filter('markdown')
def markdown_filter(text):
    if not text: return ""
    import html
    text = html.escape(text)
    # Xử lý xuống dòng và bullet point cơ bản
    text = text.replace('\n', '<br>')
    text = text.replace('* ', '&bull; ').replace('- ', '&bull; ')
    # Xử lý in đậm kiểu **text** của Markdown mà Gemini hay dùng
    import re
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    return text


# --- ROUTES ---

@app.route('/')
def home():
    search_query = request.args.get('q', '')
    brand_filter = request.args.get('brand', '')
    sort_by = request.args.get('sort', '')

    query = Product.query

    if search_query:
        query = query.filter(Product.name.contains(search_query))
    if brand_filter:
        query = query.filter(Product.brand == brand_filter)

    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())

    products = query.all()
    brands = db.session.query(Product.brand).distinct().all()
    brands = [b[0] for b in brands]

    return render_template('home.html', products=products, brands=brands, search_query=search_query)


@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    # Gọi Gemini thay vì ChatGPT
    ai_suggestion = get_gemini_suggestions(product.name)
    return render_template('detail.html', product=product, ai_suggestion=ai_suggestion)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Sai tên đăng nhập hoặc mật khẩu.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=generate_password_hash(password), full_name=username)
        db.session.add(new_user)
        db.session.commit()
        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất.', 'info')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    current_user.full_name = full_name
    current_user.email = email
    db.session.commit()
    flash('Cập nhật hồ sơ thành công!', 'success')
    return redirect(url_for('dashboard'))


# --- ADMIN ROUTES ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        abort(403)
    products = Product.query.all()
    users = User.query.all()
    return render_template('admin_dashboard.html', products=products, users=users)


@app.route('/admin/product/add', methods=['POST'])
@login_required
def add_product():
    if current_user.role != 'admin':
        abort(403)
    name = request.form.get('name')
    brand = request.form.get('brand')
    price = request.form.get('price')
    description = request.form.get('description')
    image_url = request.form.get('image_url')

    new_product = Product(name=name, brand=brand, price=price, description=description, image_url=image_url)
    db.session.add(new_product)
    db.session.commit()
    flash('Thêm sản phẩm thành công!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/product/delete/<int:id>')
@login_required
def delete_product(id):
    if current_user.role != 'admin':
        abort(403)
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Xóa sản phẩm thành công!', 'success')
    return redirect(url_for('admin_dashboard'))


# --- KHỞI TẠO & CẬP NHẬT DỮ LIỆU ---
def initialize_database():
    """
    Tạo bảng và cập nhật dữ liệu mẫu.
    Hàm này được cải tiến để UPDATE ảnh cho sản phẩm nếu chúng đã tồn tại nhưng thiếu ảnh.
    """
    with app.app_context():
        db.create_all()

        # 1. Kiểm tra/Tạo User Admin
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@store.com', password=generate_password_hash('123456'),
                         role='admin', full_name='Quản Trị Viên')
            guest = User(username='khach', email='khach@store.com', password=generate_password_hash('123456'),
                         role='user', full_name='Khách Mua Hàng')
            db.session.add_all([admin, guest])
            db.session.commit()

        # 2. Dữ liệu sản phẩm mẫu (Đã chọn lọc ảnh kỹ càng)
        products_data = [
            {
                "name": "iPhone 15 Pro Max", "brand": "Apple", "price": 34990000,
                "description": "Vỏ Titan tự nhiên, chip A17 Pro mạnh mẽ nhất.",
                "image_url": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=800&q=90"
                # Ảnh iPhone 15 Pro Max màu Titan tự nhiên
            },
            {
                "name": "Samsung Galaxy S24 Ultra", "brand": "Samsung", "price": 31990000,
                "description": "Quyền năng AI, camera 200MP, bút S-Pen.",
                "image_url": "https://images.unsplash.com/photo-1706801933957-e89c6d482253?w=800&q=90"
                # Ảnh S24 Ultra (vuông vức, màu xám)
            },
            {
                "name": "Google Pixel 8 Pro", "brand": "Google", "price": 25000000,
                "description": "Nhiếp ảnh AI đỉnh cao, Android thuần mượt mà.",
                "image_url": "https://images.unsplash.com/photo-1696357062402-990861194247?w=800&q=90"
                # Ảnh Pixel 8 Pro (màu xanh Bay Blue đặc trưng)
            },
            {
                "name": "Xiaomi 14", "brand": "Xiaomi", "price": 21990000,
                "description": "Ống kính Leica huyền thoại, sạc siêu nhanh 90W.",
                "image_url": "https://images.unsplash.com/photo-1663641773426-30239b03cb8d?w=800&q=90"
                # Ảnh minh họa Xiaomi dòng cao cấp (cụm cam to)
            },
            {
                "name": "iPhone 14", "brand": "Apple", "price": 18990000,
                "description": "Thiết kế bền bỉ, màn hình Super Retina XDR.",
                "image_url": "https://images.unsplash.com/photo-1678911820864-e2c567c655d7?w=800&q=90"
                # Ảnh iPhone 14 màu vàng chanh
            },
            {
                "name": "Samsung Galaxy Z Flip5", "brand": "Samsung", "price": 19990000,
                "description": "Gập nhỏ gọn, màn hình phụ Flex Window lớn.",
                "image_url": "https://images.unsplash.com/photo-1697475713228-59f75960098f?w=800&q=90"
                # Ảnh Z Flip 5 màu Mint gập lại
            }
        ]

        # 3. Duyệt và Cập nhật (Upsert)
        for p_data in products_data:
            product = Product.query.filter_by(name=p_data["name"]).first()
            if product:
                # Nếu sản phẩm đã có -> Cập nhật lại ảnh chuẩn
                product.image_url = p_data["image_url"]
                product.description = p_data["description"]
                product.price = p_data["price"]
            else:
                # Nếu chưa có -> Tạo mới
                new_p = Product(
                    name=p_data["name"],
                    brand=p_data["brand"],
                    price=p_data["price"],
                    description=p_data["description"],
                    image_url=p_data["image_url"]
                )
                db.session.add(new_p)

        db.session.commit()
        print("Đã đồng bộ dữ liệu và hình ảnh sản phẩm thành công!")


if __name__ == '__main__':
    # Chạy hàm khởi tạo (Tự động fix ảnh mỗi khi chạy lại app)
    initialize_database()

    app.run(debug=True, port=5000)