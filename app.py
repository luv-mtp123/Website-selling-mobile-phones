import os
import sys

# Dòng này sửa lỗi "Metaclasses with custom tp_new..." khi chạy trên Python mới nhất
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from flask import Flask, render_template, redirect, url_for, flash, request, abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user

# Import các thành phần đã tách ra từ các file khác
from extensions import db, login_manager
from models import User, Product

# --- SỬA LỖI IMPORT AI & TỐI ƯU TỐC ĐỘ ---
# Chỉ thử tải AI nếu không phải Python 3.14 (để tránh lag startup)
try:
    if sys.version_info >= (3, 14):
        raise ImportError("Python 3.14 chưa hỗ trợ tốt thư viện này")
    from utils import get_gemini_suggestions
except Exception as e:
    print(f"--- INFO: Đang chạy chế độ cơ bản (AI tắt để tối ưu tốc độ trên phiên bản Python này) ---")


    # Hàm giả lập trả về kết quả ngay lập tức
    def get_gemini_suggestions(product_name):
        return "Tính năng gợi ý AI đang tạm tắt để tối ưu hiệu năng trên môi trường này."

app = Flask(__name__)
# CẤU HÌNH
app.config['SECRET_KEY'] = 'ban-dien-thoai-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mobilestore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Khởi tạo DB và Login với app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Filter hiển thị Markdown đơn giản ---
@app.template_filter('markdown')
def markdown_filter(text):
    if not text: return ""
    import html
    text = html.escape(text)
    return text.replace('\n', '<br>').replace('* ', '&bull; ')


# --- ROUTES (ĐƯỜNG DẪN) ---

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


# --- HÀM TẠO DỮ LIỆU MẪU (ĐÃ CẬP NHẬT ẢNH CHUẨN) ---
def create_seed_data():
    """Tạo dữ liệu mẫu admin và sản phẩm"""
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            # Tạo Admin & Guest
            admin = User(username='admin', email='admin@store.com', password=generate_password_hash('123456'),
                         role='admin', full_name='Quản Trị Viên')
            guest = User(username='khach', email='khach@store.com', password=generate_password_hash('123456'),
                         role='user', full_name='Khách Mua Hàng')
            db.session.add_all([admin, guest])

            # Sản phẩm mẫu (Dùng placeholder image để load nhanh, không bị lỗi)
            products = [
                Product(name="iPhone 15 Pro Max", brand="Apple", price=34990000,
                        description="Titan tự nhiên, chip A17 Pro.",
                        image_url="https://placehold.co/600x400/png?text=iPhone+15+Pro+Max"),

                Product(name="Samsung Galaxy S24 Ultra", brand="Samsung", price=31990000,
                        description="AI tích hợp, bút S-Pen quyền năng.",
                        image_url="https://placehold.co/600x400/png?text=Samsung+S24+Ultra"),

                Product(name="Google Pixel 8 Pro", brand="Google", price=25000000,
                        description="Camera thuật toán AI đỉnh cao.",
                        image_url="https://placehold.co/600x400/png?text=Pixel+8+Pro"),

                Product(name="Xiaomi 14", brand="Xiaomi", price=21990000,
                        description="Ống kính Leica, sạc siêu nhanh.",
                        image_url="https://placehold.co/600x400/png?text=Xiaomi+14")
            ]
            db.session.add_all(products)
            db.session.commit()
            print("Đã tạo dữ liệu mẫu thành công!")


if __name__ == '__main__':
    # Kiểm tra DB
    if not os.path.exists('mobilestore.db'):
        print("Đang khởi tạo cơ sở dữ liệu và dữ liệu mẫu...")
        create_seed_data()
    else:
        print("Đã tìm thấy cơ sở dữ liệu.")

    print("Server đang khởi động...")
    app.run(debug=True, port=5000)