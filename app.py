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
from utils import get_gemini_suggestions, analyze_search_intents, get_comparison_result, call_gemini_api


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



# --- CHATBOT LOGIC MỚI ---
def process_chatbot_message(msg):
    msg = msg.lower()

    # 1. Logic Rule-based (Nhanh, không tốn tiền, xử lý câu hỏi thường gặp)
    keywords = {
        "xin chào": "Chào bạn! Chúc bạn một năm mới An Khang Thịnh Vượng! Bạn cần tìm điện thoại gì?",
        "cửa hàng": "MobileStore ở 123 Đường Tết, Quận 1. Mở cửa xuyên Tết nhé!",
        "địa chỉ": "Địa chỉ: 123 Đường Tết, Quận 1, TP.HCM.",
        "giao hàng": "Shop giao hàng hỏa tốc trong 2h nội thành.",
        "bảo hành": "Bảo hành 12 tháng chính hãng, 1 đổi 1 trong 30 ngày.",
        "thanh toán": "Hỗ trợ tiền mặt, chuyển khoản và cà thẻ.",
        "iphone 15": "iPhone 15 đang có giá cực tốt, giảm ngay 2 triệu dịp Tết này.",
        "admin": "Admin đang đi chúc Tết, nhưng bạn cứ để lại lời nhắn nhé!",
        "bot tên gì": "Mình là Trợ lý ảo AI MobileStore v2.0.",
    }

    for key, response in keywords.items():
        if key in msg:
            return response

    # 2. Fallback sang Gemini AI (Nếu không khớp từ khóa nào ở trên)
    # Đây là phần "Tích hợp AI" nhưng vẫn giữ được tốc độ cho câu hỏi dễ
    ai_prompt = (
        f"Khách hàng hỏi: '{msg}'. "
        "Bạn là nhân viên tư vấn bán điện thoại. Hãy trả lời ngắn gọn (dưới 50 từ), thân thiện, có emoji."
        "Nếu khách hỏi sản phẩm cụ thể, hãy mời họ xem chi tiết trên web."
    )
    ai_response = call_gemini_api(ai_prompt)

    if ai_response:
        return ai_response
    else:
        return "Xin lỗi, hiện tại kết nối AI đang bận. Bạn vui lòng hỏi lại sau hoặc gọi hotline nhé."


@app.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    data = request.json
    user_msg = data.get('message', '')
    response = process_chatbot_message(user_msg)
    return jsonify({'response': response})


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
    # Logic Smart Search (Tìm kiếm thông minh)
    if search_query and len(search_query.split()) > 2 and not brand_filter:
        ai_data = analyze_search_intents(search_query)

        if ai_data:
            # Lọc theo Hãng
            if ai_data.get('brand'):
                query = query.filter(Product.brand.contains(ai_data['brand']))
                ai_message += f"Hãng: {ai_data['brand']} "

            # Lọc theo Giá tối thiểu
            if ai_data.get('min_price'):
                query = query.filter(Product.price >= ai_data['min_price'])
                ai_message += f"| > {ai_data['min_price']:,}đ "

            # Lọc theo Giá tối đa
            if ai_data.get('max_price'):
                query = query.filter(Product.price <= ai_data['max_price'])
                ai_message += f"| < {ai_data['max_price']:,}đ "

            # Sắp xếp
            if ai_data.get('sort'):
                sort_by = ai_data['sort']

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

    # Xử lý Sắp xếp
    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.id.desc())  # Mặc định mới nhất

    products = query.all()

    # Lấy danh sách hãng để hiển thị dropdown
    brands = db.session.query(Product.brand).distinct().all()
    brands = [b[0] for b in brands]

    return render_template('home.html', products=products, brands=brands,
                           search_query=search_query, ai_message=ai_message)

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
    # Gợi ý AI (Giữ nguyên)
    ai_suggestion = get_gemini_suggestions(product.name)

    # [FIX] Logic gợi ý sản phẩm
    recommendations = []

    if product.category == 'phone':
        # Nếu đang xem điện thoại -> Gợi ý phụ kiện
        # 1. Lấy phụ kiện cùng hãng (Ví dụ: Tai nghe Samsung cho điện thoại Samsung)
        brand_accessories = Product.query.filter_by(category='accessory', brand=product.brand).limit(2).all()

        # 2. Lấy phụ kiện chung (Ví dụ: Sạc Anker, Kính cường lực, Ốp lưng...)
        general_accessories = Product.query.filter_by(category='accessory', brand='Phụ kiện chung').limit(4).all()

        # Gộp lại: Ưu tiên hàng hãng trước, sau đó điền đầy bằng phụ kiện chung
        recommendations = brand_accessories + general_accessories

        # Nếu vẫn chưa đủ 4 món, lấy thêm phụ kiện bất kỳ
        if len(recommendations) < 4:
            other_accessories = Product.query.filter_by(category='accessory').limit(4).all()
            for acc in other_accessories:
                if acc not in recommendations:
                    recommendations.append(acc)

        # Cắt lấy đúng 4 sản phẩm để hiển thị đẹp
        recommendations = recommendations[:4]

    else:
        # Nếu đang xem phụ kiện -> Gợi ý các sản phẩm cùng hãng khác (có thể là điện thoại)
        recommendations = Product.query.filter(Product.brand == product.brand, Product.id != id).limit(4).all()
        # Fallback: Nếu không có (vd hãng lạ), gợi ý phụ kiện khác
        if not recommendations:
            recommendations = Product.query.filter(Product.category == 'accessory', Product.id != id).limit(4).all()

    return render_template('detail.html', product=product, ai_suggestion=ai_suggestion, recommendations=recommendations)


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
        email = user_info['email']
        # Xử lý logic đăng nhập Google (tự tạo user nếu chưa có)
        user = User.query.filter_by(email=email).first()
        if not user:
            base_name = email.split('@')[0]
            user = User(username=base_name, email=email, password=generate_password_hash('google_login'), full_name=user_info['name'])
            db.session.add(user)
            db.session.commit()
        login_user(user)
        return redirect(url_for('home'))
    except Exception as e:
        flash('Lỗi đăng nhập Google.', 'danger')
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
# @app.route('/api/chatbot', methods=['POST'])
# def chatbot_api():
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




# --- ADMIN ROUTES (ĐÃ NÂNG CẤP) ---
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
    db.session.add(Product(
        name=request.form.get('name'), brand=request.form.get('brand'), price=request.form.get('price'),
        description=request.form.get('description'), image_url=request.form.get('image_url'),
        category=request.form.get('category', 'phone'), is_sale=bool(request.form.get('is_sale')),
        sale_price=request.form.get('sale_price') or 0
    ))
    db.session.commit()
    flash('Thêm thành công!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/product/delete/<int:id>')
@login_required
def delete_product(id):
    if current_user.role != 'admin': abort(403)
    db.session.delete(Product.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


# [NEW] Route Sửa sản phẩm
@app.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if current_user.role != 'admin': abort(403)
    product = Product.query.get_or_404(id)

    if request.method == 'POST':
        product.name = request.form.get('name')
        product.brand = request.form.get('brand')
        product.price = request.form.get('price')
        product.description = request.form.get('description')
        product.image_url = request.form.get('image_url')
        product.is_sale = 'is_sale' in request.form
        product.sale_price = request.form.get('sale_price')

        db.session.commit()
        flash('Cập nhật thành công!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_edit.html', product=product)


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