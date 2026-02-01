import os
import random
import string
from flask import Flask, render_template, redirect, url_for, flash, request, abort, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from extensions import db, login_manager
from models import User, Product, Order, OrderDetail
# Thư viện cho Google Login (Cần cài: pip install authlib requests)
from authlib.integrations.flask_client import OAuth
from utils import get_gemini_suggestions, analyze_search_intents, get_comparison_result


# --- HÀM LOAD .ENV ---
def load_env_file():
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


load_env_file()
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mobilestore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- CẤU HÌNH OAUTH (GOOGLE) ---
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.template_filter('vnd')
def vnd_filter(value):
    if value is None: return "0 đ"
    return "{:,.0f} đ".format(value).replace(",", ".")

# Thêm bộ lọc markdown để hiển thị bảng so sánh đẹp.
@app.template_filter('markdown')
def markdown_filter(text):
    """Chuyển đổi Markdown cơ bản sang HTML để hiển thị bảng so sánh AI"""
    if not text: return ""
    text = html.escape(text)
    # Xử lý xuống dòng
    text = text.replace('\n', '<br>')
    # Xử lý in đậm **text** -> <strong>text</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Xử lý ký tự bảng để hiển thị tốt hơn (nếu AI trả về bảng markdown)
    text = text.replace('|', '&#124;')
    return text

# --- DỮ LIỆU CHATBOT ---
CHATBOT_DATA = {
    "xin chào": "Chào bạn! MobileStore có thể giúp gì cho bạn?",
    "hi": "Chào bạn! Bạn cần tư vấn điện thoại nào?",
    "cửa hàng ở đâu": "Địa chỉ của chúng tôi tại: 123 Đường ABC, Quận 1, TP.HCM.",
    "địa chỉ": "Bạn có thể ghé thăm shop tại 123 Đường ABC, Quận 1, TP.HCM nhé!",
    "có ship không": "Chúng tôi hỗ trợ giao hàng toàn quốc (COD).",
    "giao hàng": "Thời gian giao hàng từ 2-4 ngày tùy khu vực.",
    "thanh toán": "Bạn có thể thanh toán khi nhận hàng (COD) hoặc chuyển khoản.",
    "bảo hành": "Tất cả máy bán ra đều được bảo hành chính hãng 12 tháng.",
    "iphone 15 giá bao nhiêu": "iPhone 15 hiện đang có giá cực tốt, mời bạn xem chi tiết tại trang chủ.",
    "samsung s24 ultra": "Siêu phẩm Galaxy S24 Ultra đang sẵn hàng, camera cực đỉnh!",
    "xiaomi": "Xiaomi bên mình có nhiều dòng ngon bổ rẻ như Xiaomi 14.",
    "tư vấn điện thoại": "Bạn thích chụp ảnh, chơi game hay pin trâu? Hãy cho mình biết nhu cầu nhé.",
    "pin trâu": "Nếu thích pin trâu, bạn có thể tham khảo iPhone 15 Pro Max hoặc S24 Ultra.",
    "chụp ảnh đẹp": "Để chụp ảnh đẹp, Pixel 8 Pro hoặc S24 Ultra là lựa chọn số 1.",
    "chơi game": "Chơi game thì iPhone hoặc các dòng Gaming Phone là mượt nhất.",
    "trả góp": "Hiện tại shop chưa hỗ trợ trả góp, xin lỗi bạn nha.",
    "đổi trả": "Hỗ trợ 1 đổi 1 trong 30 ngày nếu có lỗi nhà sản xuất.",
    "khuyến mãi": "Đang có chương trình giảm giá ốp lưng khi mua kèm máy đấy!",
    "liên hệ": "Hotline: 1900 1234 - Email: support@mobilestore.com",
    "giờ làm việc": "Shop mở cửa từ 8:00 - 21:00 tất cả các ngày trong tuần.",
    "phụ kiện": "Bên mình có đầy đủ cáp, sạc, tai nghe, ốp lưng chính hãng.",
    "ốp lưng": "Rất nhiều mẫu ốp lưng thời trang đang chờ bạn.",
    "tai nghe": "Tai nghe bluetooth, có dây đủ cả.",
    "sạc dự phòng": "Sạc dự phòng 10.000mAh, 20.000mAh giá chỉ từ 300k.",
    "iphone cũ": "Hiện shop chỉ bán máy mới 100% nguyên seal.",
    "samsung cũ": "Shop cam kết chỉ bán hàng mới chính hãng.",
    "quên mật khẩu": "Bạn vui lòng liên hệ admin để được reset mật khẩu nhé.",
    "đăng ký": "Bạn nhấn vào nút Đăng ký ở góc trên bên phải màn hình nhé.",
    "đăng nhập": "Nút Đăng nhập nằm ngay cạnh nút Đăng ký đó ạ.",
    "giỏ hàng": "Bạn có thể xem lại các sản phẩm đã chọn trong mục Giỏ hàng.",
    "xóa giỏ hàng": "Vào giỏ hàng và nhấn nút Xóa để loại bỏ sản phẩm không ưng ý.",
    "đặt hàng": "Sau khi chọn xong, nhấn Thanh toán để hoàn tất đơn hàng nhé.",
    "hủy đơn": "Để hủy đơn, vui lòng gọi hotline ngay lập tức.",
    "admin": "Admin rất đẹp trai và thân thiện.",
    "bot tên gì": "Mình là trợ lý ảo AI của MobileStore.",
    "ngu": "Bạn đừng mắng mình, mình chỉ là bot thôi mà :(",
    "thông minh": "Cảm ơn bạn đã khen, mình sẽ cố gắng hơn!",
    "giá rẻ": "Shop luôn cam kết giá tốt nhất thị trường.",
    "uy tín": "Uy tín làm nên thương hiệu MobileStore.",
    "cảm ơn": "Không có chi! Cần gì cứ hỏi mình nhé."
}


# --- ROUTES CHÍNH ---

@app.route('/')
def home():
    search_query = request.args.get('q', '')
    brand_filter = request.args.get('brand', '')
    sort_by = request.args.get('sort', '')
    price_min = request.args.get('price_min', type=int)
    price_max = request.args.get('price_max', type=int)

    # Biến thông báo nếu AI can thiệp lọc (Smart Search)
    ai_message = ""

    query = Product.query

    # --- SMART SEARCH LOGIC ---
    # Nếu có từ khóa dài (>2 từ) và không chọn hãng thủ công -> Dùng AI phân tích
    if search_query and len(search_query.split()) > 2 and not brand_filter:
        ai_data = analyze_search_intents(search_query)

        if ai_data:
            if ai_data.get('brand'):
                query = query.filter(Product.brand.contains(ai_data['brand']))
                ai_message += f"Hãng: {ai_data['brand']} "

            if ai_data.get('min_price'):
                query = query.filter(Product.price >= ai_data['min_price'])
                ai_message += f"| Trên: {'{:,.0f}'.format(ai_data['min_price'])}đ "

            if ai_data.get('max_price'):
                query = query.filter(Product.price <= ai_data['max_price'])
                ai_message += f"| Dưới: {'{:,.0f}'.format(ai_data['max_price'])}đ "

            if ai_data.get('sort'):
                sort_by = ai_data['sort']  # Ghi đè sắp xếp theo ý định user

            if ai_message:
                ai_message = f"🔍 AI đã tự động lọc: {ai_message}"
        else:
            # Fallback: Tìm kiếm thường nếu AI không hiểu
            query = query.filter(Product.name.contains(search_query))
    elif search_query:
        # Tìm kiếm thường (từ khóa ngắn)
        query = query.filter(Product.name.contains(search_query))

    # Lọc thường (nếu user chọn dropdown)
    if brand_filter:
        query = query.filter(Product.brand == brand_filter)

    # Sắp xếp
    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.id.desc())  # Mặc định mới nhất

    products = query.all()
    brands = db.session.query(Product.brand).distinct().all()
    brands = [b[0] for b in brands]

    return render_template('home.html', products=products, brands=brands, search_query=search_query,
                           ai_message=ai_message)


# --- [NEW] ROUTE SO SÁNH SẢN PHẨM ---
@app.route('/compare', methods=['GET', 'POST'])
def compare_page():
    all_products = Product.query.all()
    result = None
    p1 = None
    p2 = None

    if request.method == 'POST':
        p1_id = request.form.get('product1')
        p2_id = request.form.get('product2')

        if p1_id and p2_id and p1_id != p2_id:
            p1 = Product.query.get(p1_id)
            p2 = Product.query.get(p2_id)

            # Gọi AI so sánh
            result = get_comparison_result(
                p1.name, p1.price, p1.description,
                p2.name, p2.price, p2.description
            )
        else:
            flash("Vui lòng chọn 2 sản phẩm khác nhau!", "warning")

    return render_template('compare.html', products=all_products, result=result, p1=p1, p2=p2)

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    # Gợi ý phụ kiện AI
    ai_suggestion = get_gemini_suggestions(product.name)
    return render_template('detail.html', product=product, ai_suggestion=ai_suggestion)


# --- ROUTES GOOGLE LOGIN ---

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/authorize/google')
def authorize_google():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        # Lấy thông tin từ Google
        email = user_info['email']
        name = user_info['name']

        # Xử lý đăng nhập/đăng ký
        return handle_social_login(email, name, 'Google')
    except Exception as e:
        flash(f'Lỗi đăng nhập Google: {str(e)}', 'danger')
        return redirect(url_for('login'))


def handle_social_login(email, full_name, provider):
    user = User.query.filter_by(email=email).first()
    if user:
        login_user(user)
        flash(f'Đăng nhập thành công qua {provider}!', 'success')
    else:
        # Tạo user mới, password ngẫu nhiên
        random_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        base_username = email.split('@')[0]
        new_username = f"{base_username}_{random.randint(1000, 9999)}"

        new_user = User(
            username=new_username,
            email=email,
            password=generate_password_hash(random_pass),
            full_name=full_name,
            role='user'
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash(f'Chào mừng thành viên mới! Đăng nhập qua {provider} thành công.', 'success')

    return redirect(url_for('home'))


# --- GIỎ HÀNG & THANH TOÁN ---

@app.route('/cart/add/<int:id>', methods=['POST'])
def add_to_cart(id):
    product = Product.query.get_or_404(id)
    if 'cart' not in session: session['cart'] = {}

    cart = session['cart']
    str_id = str(id)

    if str_id in cart:
        cart[str_id]['quantity'] += 1
    else:
        price = product.sale_price if product.is_sale else product.price
        cart[str_id] = {
            'name': product.name,
            'price': price,
            'image': product.image_url,
            'quantity': 1
        }
    session.modified = True
    flash(f'Đã thêm {product.name} vào giỏ!', 'success')
    return redirect(request.referrer)


@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('cart.html', cart=cart, total_amount=total_amount)


@app.route('/cart/update/<int:id>/<action>')
def update_cart(id, action):
    cart = session.get('cart', {})
    str_id = str(id)

    if str_id in cart:
        if action == 'increase':
            cart[str_id]['quantity'] += 1
        elif action == 'decrease':
            cart[str_id]['quantity'] -= 1
            if cart[str_id]['quantity'] <= 0:
                del cart[str_id]
        elif action == 'delete':
            del cart[str_id]

    session['cart'] = cart
    session.modified = True
    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Giỏ hàng trống!', 'warning')
        return redirect(url_for('home'))

    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())

    if request.method == 'POST':
        address = request.form.get('address')
        phone = request.form.get('phone')

        new_order = Order(
            user_id=current_user.id,
            total_price=total_amount,
            address=address,
            phone=phone,
            status='Completed'
        )
        db.session.add(new_order)
        db.session.flush()

        for p_id, item in cart.items():
            detail = OrderDetail(
                order_id=new_order.id,
                product_id=int(p_id),
                product_name=item['name'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(detail)

        db.session.commit()
        session.pop('cart', None)
        flash('Thanh toán thành công!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('checkout.html', cart=cart, total=total_amount)


# --- API CHATBOT ---
@app.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    data = request.json
    user_msg = data.get('message', '').lower().strip()
    response = "Xin lỗi, mình chưa hiểu ý bạn."
    for key, value in CHATBOT_DATA.items():
        if key in user_msg:
            response = value
            break
    return jsonify({'response': response})


# --- AUTH ROUTES (CƠ BẢN) ---

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
            flash('Sai thông tin đăng nhập.', 'danger')
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
        flash('Đăng ký thành công! Hãy đăng nhập.', 'success')
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
    my_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_created.desc()).all()
    return render_template('dashboard.html', orders=my_orders)


@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    current_user.full_name = full_name
    current_user.email = email
    db.session.commit()
    flash('Cập nhật thành công', 'success')
    return redirect(url_for('dashboard'))


# --- ADMIN ROUTES ---

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': abort(403)
    products = Product.query.all()
    users = User.query.all()
    orders = Order.query.all()
    return render_template('admin_dashboard.html', products=products, users=users, orders=orders)


@app.route('/admin/product/add', methods=['POST'])
@login_required
def add_product():
    if current_user.role != 'admin': abort(403)
    name = request.form.get('name')
    brand = request.form.get('brand')
    price = request.form.get('price')
    description = request.form.get('description')
    image_url = request.form.get('image_url')
    category = request.form.get('category')

    new_product = Product(name=name, brand=brand, price=price,
                          description=description, image_url=image_url, category=category)
    db.session.add(new_product)
    db.session.commit()
    flash('Thêm sản phẩm thành công!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/product/delete/<int:id>')
@login_required
def delete_product(id):
    if current_user.role != 'admin': abort(403)
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Đã xóa sản phẩm.', 'success')
    return redirect(url_for('admin_dashboard'))


# --- KHỞI TẠO DỮ LIỆU ---
def initialize_database():
    with app.app_context():
        db.create_all()

        # 1. Admin & Khách
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@store.com', password=generate_password_hash('123456'),
                         role='admin', full_name='Admin Shop')
            guest = User(username='khach', email='khach@store.com', password=generate_password_hash('123456'),
                         role='user', full_name='Khách hàng')
            db.session.add_all([admin, guest])

        # 2. Danh sách sản phẩm
        products_data = [
            # --- CÁC SẢN PHẨM CŨ ---
            {"name": "iPhone 15 Pro Max", "brand": "Apple", "price": 34990000, "category": "phone", "is_sale": False,
             "desc": "Titan tự nhiên, Chip A17 Pro, Camera 5x.",
             "img": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=800"},
            {"name": "Samsung Galaxy S24 Ultra", "brand": "Samsung", "price": 31990000, "category": "phone",
             "is_sale": True, "sale_price": 29990000,
             "desc": "Quyền năng AI, Camera 200MP, S-Pen.",
             "img": "https://images.unsplash.com/photo-1706801933957-e89c6d482253?w=800"},
            {"name": "Xiaomi 14", "brand": "Xiaomi", "price": 22990000, "category": "phone", "is_sale": False,
             "desc": "Ống kính Leica, Snapdragon 8 Gen 3.",
             "img": "https://images.unsplash.com/photo-1663641773426-30239b03cb8d?w=800"},
            {"name": "Google Pixel 8 Pro", "brand": "Google", "price": 24000000, "category": "phone", "is_sale": False,
             "desc": "Camera AI đỉnh cao, Android gốc.",
             "img": "https://images.unsplash.com/photo-1696357062402-990861194247?w=800"},

            # --- 15 ĐIỆN THOẠI MỚI ---
            {"name": "iPhone 13 128GB", "brand": "Apple", "price": 13990000, "category": "phone", "is_sale": True,
             "sale_price": 12590000,
             "desc": "Thiết kế vuông vức, Camera kép sắc nét.",
             "img": "https://images.unsplash.com/photo-1632661674596-df8be070a5c5?w=800"},
            {"name": "Samsung Galaxy A54 5G", "brand": "Samsung", "price": 8490000, "category": "phone",
             "is_sale": False,
             "desc": "Chống nước IP67, Camera OIS ổn định.",
             "img": "https://images.unsplash.com/photo-1678911820864-e2c567c655d7?w=800"},
            {"name": "Xiaomi Redmi Note 13 Pro", "brand": "Xiaomi", "price": 7290000, "category": "phone",
             "is_sale": True, "sale_price": 6890000,
             "desc": "Camera 200MP, Sạc siêu nhanh 67W.",
             "img": "https://images.unsplash.com/photo-1598327105666-5b89351aff23?w=800"},
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
            p = Product.query.filter_by(name=p_data["name"]).first()
            if not p:
                new_p = Product(
                    name=p_data["name"], brand=p_data["brand"], price=p_data["price"],
                    description=p_data["desc"], image_url=p_data["img"],
                    category=p_data["category"], is_sale=p_data["is_sale"],
                    sale_price=p_data.get("sale_price")
                )
                db.session.add(new_p)

        db.session.commit()
        print("Đã cập nhật dữ liệu MobileStore thành công!")


if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, port=5000)