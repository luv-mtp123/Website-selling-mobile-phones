import os
import time
import json
import hashlib
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Product, Order, OrderDetail, AICache, TradeInRequest
from app.utils import analyze_search_intents, get_comparison_result, call_gemini_api, validate_image_file

main_bp = Blueprint('main', __name__)


# --- AI Cache Helper ---
def cached_ai_call(func, *args):
    """
    Hàm wrapper để cache kết quả gọi AI vào Database.
    Giúp tiết kiệm chi phí API và tăng tốc độ phản hồi cho các câu hỏi trùng lặp.
    """
    try:
        # Tạo key duy nhất dựa trên tham số đầu vào
        key = hashlib.md5(str(args).encode()).hexdigest()
        cached = AICache.query.filter_by(prompt_hash=key).first()

        if cached:
            # Nếu đã có trong cache -> trả về ngay
            return json.loads(cached.response_text) if '{' in cached.response_text else cached.response_text
    except Exception as e:
        print(f"Cache Error: {e}")

    # Nếu chưa có -> Gọi hàm thực thi (API Gemini)
    res = func(*args)

    if res:
        try:
            # Lưu kết quả mới vào cache
            val = json.dumps(res) if isinstance(res, (dict, list)) else str(res)
            # Kiểm tra lại lần cuối để tránh race condition
            if not AICache.query.filter_by(prompt_hash=key).first():
                db.session.add(AICache(prompt_hash=key, response_text=val))
                db.session.commit()
        except Exception as e:
            print(f"Save Cache Error: {e}")

    return res


# --- Routes ---

@main_bp.route('/')
def home():
    q = request.args.get('q', '')
    brand = request.args.get('brand', '')
    sort = request.args.get('sort', '')
    ai_msg = ""

    # Chỉ hiện sản phẩm đang Active (đang kinh doanh)
    query = Product.query.filter_by(is_active=True)

    # Logic tìm kiếm thông minh
    if q and len(q.split()) > 2 and not brand:
        # Nếu query dài > 2 từ, dùng AI để phân tích ý định (tìm hãng, tìm giá...)
        ai_data = cached_ai_call(analyze_search_intents, q)
        if ai_data:
            if ai_data.get('brand'):
                query = query.filter(Product.brand.contains(ai_data['brand']))
                ai_msg += f"Hãng: {ai_data['brand']} "
            if ai_data.get('min_price'):
                query = query.filter(Product.price >= ai_data['min_price'])
            if ai_data.get('max_price'):
                query = query.filter(Product.price <= ai_data['max_price'])
            if ai_data.get('sort'):
                sort = ai_data['sort']
            if ai_msg:
                ai_msg = f"🔍 AI Smart Filter: {ai_msg}"
        else:
            query = query.filter(Product.name.contains(q))
    elif q:
        query = query.filter(Product.name.contains(q))

    if brand:
        query = query.filter(Product.brand == brand)

    # Sắp xếp
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.id.desc())

    products = query.all()
    # Lấy danh sách các hãng để hiển thị bộ lọc
    brands = [b[0] for b in db.session.query(Product.brand).distinct().all()]

    return render_template('home.html', products=products, brands=brands, search_query=q, ai_message=ai_msg)


@main_bp.route('/product/<int:id>')
def product_detail(id):
    p = Product.query.filter_by(id=id, is_active=True).first_or_404()
    try:
        p.colors_list = json.loads(p.colors) if p.colors else []
        p.versions_list = json.loads(p.versions) if p.versions else []
    except:
        p.colors_list, p.versions_list = [], []

    # Gợi ý phụ kiện
    recs = Product.query.filter(Product.category == 'accessory', Product.is_active == True).limit(4).all()
    return render_template('detail.html', product=p, recommendations=recs)


# --- CART & CHECKOUT (LOGIC TỒN KHO) ---

@main_bp.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    total = sum(i['price'] * i['quantity'] for i in cart.values())
    return render_template('cart.html', cart=cart, total_amount=total)


@main_bp.route('/cart/add/<int:id>', methods=['POST'])
def add_to_cart(id):
    p = Product.query.filter_by(id=id, is_active=True).first_or_404()

    # 1. Check Tồn kho cơ bản
    if p.stock_quantity <= 0:
        flash(f'Rất tiếc, {p.name} hiện đã hết hàng.', 'danger')
        return redirect(request.referrer)

    cart = session.get('cart', {})
    sid = str(id)
    current_qty = cart[sid]['quantity'] if sid in cart else 0

    # 2. Check Tồn kho khi cộng thêm số lượng
    if current_qty + 1 > p.stock_quantity:
        flash(f'Kho chỉ còn {p.stock_quantity} sản phẩm. Không thể thêm tiếp.', 'warning')
        return redirect(request.referrer)

    if sid in cart:
        cart[sid]['quantity'] += 1
    else:
        price = p.sale_price if p.is_sale else p.price
        cart[sid] = {'name': p.name, 'price': price, 'image': p.image_url, 'quantity': 1}

    session['cart'] = cart
    flash(f'Đã thêm {p.name} vào giỏ!', 'success')
    return redirect(request.referrer)


@main_bp.route('/cart/update/<int:id>/<action>')
def update_cart(id, action):
    cart = session.get('cart', {})
    sid = str(id)

    if sid in cart:
        if action == 'increase':
            # Check tồn kho lại trước khi tăng
            p = Product.query.get(id)
            if p and cart[sid]['quantity'] + 1 <= p.stock_quantity:
                cart[sid]['quantity'] += 1
            else:
                flash('Số lượng vượt quá tồn kho hiện tại.', 'warning')
        elif action == 'decrease':
            cart[sid]['quantity'] -= 1
            if cart[sid]['quantity'] <= 0:
                del cart[sid]
        elif action == 'delete':
            del cart[sid]

    session['cart'] = cart
    return redirect(url_for('main.view_cart'))


@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('main.home'))

    total = sum(i['price'] * i['quantity'] for i in cart.values())

    if request.method == 'POST':
        # 1. Final Stock Check & Deduction (Kiểm tra và Trừ kho lần cuối)
        for pid, item in cart.items():
            product = Product.query.get(int(pid))

            # Check nếu sản phẩm bị xóa hoặc ẩn trong lúc đang mua
            if not product or not product.is_active:
                flash(f"Sản phẩm {item['name']} đã ngừng kinh doanh.", "danger")
                return redirect(url_for('main.view_cart'))

            # Check số lượng
            if product.stock_quantity < item['quantity']:
                flash(f"Sản phẩm {item['name']} không đủ hàng (Còn: {product.stock_quantity}). Vui lòng cập nhật giỏ.",
                      "danger")
                return redirect(url_for('main.view_cart'))

        # 2. Tạo đơn hàng
        order = Order(
            user_id=current_user.id,
            total_price=total,
            address=request.form.get('address'),
            phone=request.form.get('phone'),
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()  # Lấy order ID trước khi commit

        # 3. Trừ kho & Tạo chi tiết đơn
        for pid, item in cart.items():
            product = Product.query.get(int(pid))
            product.stock_quantity -= item['quantity']  # TRỪ KHO THỰC TẾ

            db.session.add(OrderDetail(
                order_id=order.id,
                product_id=int(pid),
                product_name=item['name'],
                quantity=item['quantity'],
                price=item['price']
            ))

        db.session.commit()
        session.pop('cart', None)  # Xóa giỏ hàng
        flash('Đặt hàng thành công! Đơn hàng đang chờ xử lý.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('checkout.html', cart=cart, total=total)


# --- TRADE-IN & CANCELLATION ---

@main_bp.route('/trade-in', methods=['GET', 'POST'])
@login_required
def trade_in():
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        condition = request.form.get('condition')

        # Validate Upload File
        if 'image' not in request.files:
            flash('Vui lòng chọn ảnh!', 'danger')
            return redirect(request.url)

        file = request.files['image']
        is_valid, error_msg = validate_image_file(file)

        if not is_valid:
            flash(error_msg, 'danger')
            return redirect(request.url)

        # Save File
        filename = secure_filename(f"tradein_{int(time.time())}_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        req = TradeInRequest(
            user_id=current_user.id,
            device_name=device_name,
            condition=condition,
            image_proof=f"/static/uploads/{filename}",
            status='Pending'
        )
        db.session.add(req)
        db.session.commit()
        flash('Đã gửi yêu cầu định giá. Chúng tôi sẽ phản hồi sớm!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('tradein.html')


@main_bp.route('/order/cancel/<int:id>')
@login_required
def cancel_order_user(id):
    order = Order.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if order.status == 'Pending':
        # HOÀN KHO KHI HỦY
        for detail in order.details:
            product = Product.query.get(detail.product_id)
            if product:
                product.stock_quantity += detail.quantity

        order.status = 'Cancelled'
        db.session.commit()
        flash('Đã hủy đơn hàng và hoàn lại kho.', 'success')
    else:
        flash('Đơn hàng đã được xử lý, không thể tự hủy. Vui lòng liên hệ Admin.', 'warning')

    return redirect(url_for('main.dashboard'))


# --- Compare Page ---
@main_bp.route('/compare', methods=['GET', 'POST'])
def compare_page():
    products = Product.query.filter_by(is_active=True).all()
    result, p1, p2 = None, None, None
    if request.method == 'POST':
        p1 = Product.query.get(request.form.get('product1'))
        p2 = Product.query.get(request.form.get('product2'))
        if p1 and p2:
            result = cached_ai_call(get_comparison_result, p1.name, p1.price, p1.description, p2.name, p2.price,
                                    p2.description)
        else:
            flash("Vui lòng chọn 2 sản phẩm khác nhau!", "warning")
    return render_template('compare.html', products=products, result=result, p1=p1, p2=p2)


# --- API & Dashboard ---

@main_bp.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    msg = request.json.get('message', '').lower()

    # Rule-based simple responses
    keywords = {
        "xin chào": "Chào bạn! Chúc mừng năm mới!",
        "địa chỉ": "123 Đường Tết, Q1, TP.HCM",
        "giao hàng": "Giao hỏa tốc 2H."
    }
    for k, v in keywords.items():
        if k in msg: return jsonify({'response': v})

    # AI Fallback
    def chat_wrapper(m):
        return call_gemini_api(f"Khách hỏi: '{m}'. Trả lời ngắn gọn dưới 50 từ.")

    res = cached_ai_call(chat_wrapper, msg)
    return jsonify({'response': res or "Hệ thống đang bận."})


@main_bp.route('/dashboard')
@login_required
def dashboard():
    my_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_created.desc()).all()
    my_tradeins = TradeInRequest.query.filter_by(user_id=current_user.id).order_by(
        TradeInRequest.created_at.desc()).all()
    return render_template('dashboard.html', orders=my_orders, tradeins=my_tradeins)


@main_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    full_name = request.form.get('full_name')
    email = request.form.get('email')

    # Xử lý Upload Avatar
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file.filename != '':
            is_valid, err = validate_image_file(file)
            if is_valid:
                # Tạo tên file độc nhất để tránh trùng lặp
                filename = secure_filename(f"avatar_{current_user.id}_{int(time.time())}_{file.filename}")
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # Lưu đường dẫn vào DB
                current_user.avatar_url = f"/static/uploads/{filename}"
            else:
                flash(err, 'warning')

    if full_name:
        current_user.full_name = full_name

    # Lưu ý: Cập nhật email cần cẩn thận hơn (check trùng), ở đây làm đơn giản
    if email:
        current_user.email = email

    db.session.commit()
    flash('Cập nhật hồ sơ thành công!', 'success')
    return redirect(url_for('main.dashboard'))