import os
import time
import json
import hashlib
from datetime import datetime, timedelta, timezone # [UPDATE] Import time handling
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Product, Order, OrderDetail, AICache, TradeInRequest, Comment
# [UPDATE] Import thêm hàm build_product_context
from app.utils import analyze_search_intents, get_comparison_result, call_gemini_api, validate_image_file, build_product_context
# [FIX] Import thêm csrf để tắt bảo mật cho API Chatbot
from app.extensions import db, csrf

# [UPDATE] Import hàm xử lý Chatbot mới từ utils
from app.utils import (
    analyze_search_intents,
    get_comparison_result,
    validate_image_file,
    generate_chatbot_response # Hàm mới
)

main_bp = Blueprint('main', __name__)

# --- AI Cache Helper ---
def cached_ai_call(func, *args):
    try:
        # [UPDATE] Đổi sang key v4 (thay vì v3) để xóa cache lỗi cũ
        # Điều này ép hệ thống phải gọi lại Gemini để lấy bản HTML đầy đủ
        cache_key_content = str(args) + "_v4_comparison_fix"
        key = hashlib.md5(cache_key_content.encode()).hexdigest()

        cached = AICache.query.filter_by(prompt_hash=key).first()
        if cached:
            return json.loads(cached.response_text) if '{' in cached.response_text else cached.response_text
    except Exception as e:
        print(f"Cache Error: {e}")

    res = func(*args)
    if res:
        try:
            val = json.dumps(res) if isinstance(res, (dict, list)) else str(res)
            # Chỉ lưu vào DB nếu chưa tồn tại
            if not AICache.query.filter_by(prompt_hash=key).first():
                db.session.add(AICache(prompt_hash=key, response_text=val))
                db.session.commit()
        except Exception as e:
            print(f"Save Cache Error: {e}")
    return res

# --- Routes ---
@main_bp.route('/')
def home():
    q = request.args.get('q', '').strip()
    brand = request.args.get('brand', '')
    sort = request.args.get('sort', '')
    ai_msg = ""

    query = Product.query.filter_by(is_active=True)

    # Logic tìm kiếm thông minh
    if q and len(q.split()) > 2 and not brand:
        ai_data = cached_ai_call(analyze_search_intents, q)
        if ai_data:
            # 1. Lọc theo Hãng
            if ai_data.get('brand'):
                query = query.filter(Product.brand.contains(ai_data['brand']))
                ai_msg += f"Hãng: {ai_data['brand']}"

            # 2. [FIX QUAN TRỌNG] Lọc theo Loại sản phẩm (Category)
            # Phần này trước đây bị thiếu nên tìm điện thoại vẫn ra phụ kiện
            if ai_data.get('category'):
                query = query.filter(Product.category == ai_data['category'])
                cat_vn = "Điện thoại" if ai_data['category'] == 'phone' else "Phụ kiện"
                sep = " | " if ai_msg else ""
                ai_msg += f"{sep}Loại: {cat_vn}"

            # 3. [QUAN TRỌNG] Lọc theo Keyword cụ thể (ốp, sạc, tai nghe...)
            # Đây là phần sửa lỗi: tìm chính xác tên sản phẩm chứa từ khóa
            if ai_data.get('keyword'):
                kw = ai_data['keyword']
                query = query.filter(Product.name.ilike(f"%{kw}%"))
                sep = " | " if ai_msg else ""
                ai_msg += f"{sep}Tìm: '{kw}'"

            # 3. Lọc theo Giá
            if ai_data.get('min_price'):
                query = query.filter(Product.price >= ai_data['min_price'])
            if ai_data.get('max_price'):
                query = query.filter(Product.price <= ai_data['max_price'])

            # 4. Sắp xếp
            if ai_data.get('sort'):
                sort = ai_data['sort']

            if ai_msg:
                ai_msg = f"🔍 AI Smart Filter: {ai_msg}"
        else:
            # Fallback nếu AI không nhận diện được: Tìm theo tên thông thường
            query = query.filter(Product.name.contains(q))
    elif q:
        query = query.filter(Product.name.contains(q))

    # Bộ lọc thủ công (nếu user click chọn hãng trên menu)
    if brand: query = query.filter(Product.brand == brand)

    # Sắp xếp
    if sort == 'price_asc': query = query.order_by(Product.price.asc())
    elif sort == 'price_desc': query = query.order_by(Product.price.desc())
    else: query = query.order_by(Product.id.desc())

    products = query.all()
    brands = [b[0] for b in db.session.query(Product.brand).distinct().all()]
    hot_products = Product.query.filter_by(is_active=True, is_sale=True).limit(4).all()

    return render_template('home.html', products=products, brands=brands, search_query=q, ai_message=ai_msg, hot_products=hot_products)

@main_bp.route('/product/<int:id>')
def product_detail(id):
    p = Product.query.filter_by(id=id, is_active=True).first_or_404()
    try:
        p.colors_list = json.loads(p.colors) if p.colors else []
        p.versions_list = json.loads(p.versions) if p.versions else []
    except:
        p.colors_list, p.versions_list = [], []

    recs = Product.query.filter(Product.category == 'accessory', Product.is_active == True).limit(4).all()

    # [TỐI ƯU] Gộp query User để tránh N+1 khi hiển thị danh sách Comment
    comments = Comment.query.options(joinedload(Comment.user)).filter_by(product_id=id).order_by(Comment.created_at.desc()).all()

    return render_template('detail.html', product=p, recommendations=recs, comments=comments)

@main_bp.route('/product/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    content = request.form.get('content', '').strip()
    # [FIX] Tránh ValueError nếu User F12 sửa HTML
    rating = request.form.get('rating', default=5, type=int)
    if rating not in [1, 2, 3, 4, 5]: rating = 5

    if not content:
        flash('Vui lòng nhập nội dung bình luận', 'warning')
        return redirect(url_for('main.product_detail', id=id))

    comment = Comment(user_id=current_user.id, product_id=id, content=content, rating=rating)
    db.session.add(comment)
    db.session.commit()
    flash('Cảm ơn bạn đã đánh giá sản phẩm!', 'success')
    return redirect(url_for('main.product_detail', id=id))

@main_bp.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    total = sum(i['price'] * i['quantity'] for i in cart.values())
    return render_template('cart.html', cart=cart, total_amount=total)

@main_bp.route('/cart/add/<int:id>', methods=['POST'])
def add_to_cart(id):
    p = Product.query.filter_by(id=id, is_active=True).first_or_404()
    if p.stock_quantity <= 0:
        flash(f'Rất tiếc, {p.name} hiện đã hết hàng.', 'danger')
        return redirect(request.referrer or url_for('main.home'))

    cart = session.get('cart', {})
    sid = str(id)
    current_qty = cart[sid]['quantity'] if sid in cart else 0

    if current_qty + 1 > p.stock_quantity:
        flash(f'Kho chỉ còn {p.stock_quantity} sản phẩm.', 'warning')
        return redirect(request.referrer or url_for('main.home'))

    if sid in cart:
        cart[sid]['quantity'] += 1
    else:
        price = p.sale_price if p.is_sale else p.price
        cart[sid] = {'name': p.name, 'price': price, 'image': p.image_url, 'quantity': 1}

    session['cart'] = cart
    flash(f'Đã thêm {p.name} vào giỏ!', 'success')
    return redirect(request.referrer or url_for('main.home'))

@main_bp.route('/cart/update/<int:id>/<action>')
def update_cart(id, action):
    cart = session.get('cart', {})
    sid = str(id)

    if sid in cart:
        if action == 'increase':
            p = db.session.get(Product, id)
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
    if not cart: return redirect(url_for('main.home'))

    total = 0
    final_items = []
    for pid, item in cart.items():
        p = db.session.get(Product, int(pid))
        if p and p.is_active:
            price = p.sale_price if p.is_sale else p.price
            total += price * item['quantity']
            final_items.append({'p': p, 'qty': item['quantity'], 'price': price})

    if request.method == 'POST':
        try:
            payment_method = request.form.get('payment', 'cod')

            for i in final_items:
                prod = db.session.query(Product).filter_by(id=i['p'].id).with_for_update().first()
                if prod.stock_quantity < i['qty']:
                    flash(f"{prod.name} không đủ hàng.", 'danger')
                    db.session.rollback()
                    return redirect(url_for('main.view_cart'))
                prod.stock_quantity -= i['qty']

            order = Order(
                user_id=current_user.id,
                total_price=total,
                address=request.form.get('address'),
                phone=request.form.get('phone'),
                payment_method=payment_method,
                status='Pending'
            )
            db.session.add(order)
            db.session.flush()

            for i in final_items:
                db.session.add(
                    OrderDetail(order_id=order.id, product_id=i['p'].id, product_name=i['p'].name, quantity=i['qty'],
                                price=i['price']))

            db.session.commit()
            session.pop('cart', None)

            # Nếu chọn Banking, chuyển hướng sang trang QR
            if payment_method == 'banking':
                return redirect(url_for('main.payment_qr', order_id=order.id))

            flash('Đặt hàng thành công!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            print(e)
            flash('Lỗi xử lý đơn hàng.', 'danger')
            return redirect(url_for('main.view_cart'))

    return render_template('checkout.html', cart=cart, total=total)


# --- [FIXED] TRANG THANH TOÁN QR VỚI XỬ LÝ TIMEZONE ---
@main_bp.route('/payment/qr/<int:order_id>')
@login_required
def payment_qr(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if order.status != 'Pending':
        flash('Đơn hàng này đã được xử lý hoặc hết hạn.', 'info')
        return redirect(url_for('main.dashboard'))

    # Tính thời gian hết hạn (3 phút từ lúc tạo đơn)
    expiration_time = order.date_created + timedelta(minutes=3)

    # [FIX] Đồng bộ kiểu dữ liệu naive để trừ được cho nhau trong SQLite
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    remaining_seconds = (expiration_time - now_naive).total_seconds()

    if remaining_seconds <= 0:
        flash('Giao dịch đã hết hạn vui lòng đặt lại.', 'warning')
        return redirect(url_for('main.dashboard'))

    bank_id = "MB"
    account_no = "9999999999"
    account_name = "MOBILE STORE"
    content = f"THANHTOAN DONHANG {order.id}"
    qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={order.total_price}&addInfo={content}&accountName={account_name}"

    return render_template('payment_qr.html', order=order, qr_url=qr_url, remaining_seconds=int(remaining_seconds))


# --- [FIXED] API CHECK TRẠNG THÁI VỚI XỬ LÝ TIMEZONE ---
@main_bp.route('/api/payment/check/<int:order_id>')
@login_required
def check_payment_status(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return jsonify({'status': 'error'})

    # Kiểm tra hết hạn
    expiration_time = order.date_created + timedelta(minutes=3)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    is_expired = now_naive > expiration_time

    if is_expired and order.status == 'Pending':
        return jsonify({'status': 'Expired'})

    return jsonify({'status': order.status})


# --- [NEW] GIẢ LẬP WEBHOOK NGÂN HÀNG (DÀNH CHO TEST) ---
# Bạn truy cập link này trên tab khác để giả vờ tiền đã vào tài khoản
@main_bp.route('/test/simulate-bank-success/<int:order_id>')
def simulate_bank_success(order_id):
    if not current_user.is_authenticated:
        return "Vui lòng đăng nhập để test"

    order = db.session.get(Order, order_id)
    if order and order.status == 'Pending':
        order.status = 'Confirmed'  # Đánh dấu đã thanh toán
        db.session.commit()
        return f"<h1>[SIMULATION] Đã nhận tiền thành công cho đơn {order_id}!</h1><p>Quay lại tab thanh toán để xem kết quả.</p>"
    return "Đơn hàng không tồn tại hoặc đã xử lý."

@main_bp.route('/trade-in', methods=['GET', 'POST'])
@login_required
def trade_in():
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        condition = request.form.get('condition')

        if 'image' not in request.files:
            flash('Vui lòng chọn ảnh!', 'danger')
            return redirect(request.url)

        file = request.files['image']
        is_valid, error_msg = validate_image_file(file)

        if not is_valid:
            flash(error_msg, 'danger')
            return redirect(request.url)

        filename = secure_filename(f"tradein_{int(time.time())}_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        req = TradeInRequest(
            user_id=current_user.id, device_name=device_name,
            condition=condition, image_proof=f"/static/uploads/{filename}", status='Pending'
        )
        db.session.add(req)
        db.session.commit()
        flash('Đã gửi yêu cầu định giá. Chúng tôi sẽ phản hồi sớm!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('tradein.html')

@main_bp.route('/order/cancel/<int:id>')
@login_required
def cancel_order_user(id):
    order = Order.query.options(joinedload(Order.details)).filter_by(id=id, user_id=current_user.id).first_or_404()

    if order.status == 'Pending':
        for detail in order.details:
            product = db.session.get(Product, detail.product_id)
            if product: product.stock_quantity += detail.quantity

        order.status = 'Cancelled'
        db.session.commit()
        flash('Đã hủy đơn hàng và hoàn lại kho.', 'success')
    else:
        flash('Đơn hàng đã được xử lý, không thể tự hủy.', 'warning')

    return redirect(url_for('main.dashboard'))

@main_bp.route('/compare', methods=['GET', 'POST'])
def compare_page():
    products = Product.query.filter_by(is_active=True).all()
    result, p1, p2 = None, None, None
    if request.method == 'POST':
        p1 = db.session.get(Product, request.form.get('product1'))
        p2 = db.session.get(Product, request.form.get('product2'))
        if p1 and p2:
            result = cached_ai_call(get_comparison_result, p1.name, p1.price, p1.description, p2.name, p2.price, p2.description)
        else:
            flash("Vui lòng chọn 2 sản phẩm khác nhau!", "warning")
    return render_template('compare.html', products=products, result=result, p1=p1, p2=p2)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    my_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_created.desc()).all()
    my_tradeins = TradeInRequest.query.filter_by(user_id=current_user.id).order_by(TradeInRequest.created_at.desc()).all()
    return render_template('dashboard.html', orders=my_orders, tradeins=my_tradeins)

@main_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    full_name = request.form.get('full_name')
    email = request.form.get('email')

    if 'avatar' in request.files:
        file = request.files['avatar']
        if file.filename != '':
            is_valid, err = validate_image_file(file)
            if is_valid:
                filename = secure_filename(f"avatar_{current_user.id}_{int(time.time())}_{file.filename}")
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.avatar_url = f"/static/uploads/{filename}"
            else:
                flash(err, 'warning')

    if full_name: current_user.full_name = full_name
    if email: current_user.email = email

    db.session.commit()
    flash('Cập nhật hồ sơ thành công!', 'success')
    return redirect(url_for('main.dashboard'))

# --- [UPDATE] API CHATBOT SỬ DỤNG HÀM MỚI TỪ UTILS ---
@main_bp.route('/api/chatbot', methods=['POST'])
@csrf.exempt
def chatbot_api():
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({'response': "Mời bạn hỏi về điện thoại ạ! 📱"})

    # 1. Rule-based (Ưu tiên tốc độ)
    keywords = {
        "xin chào": "Chào bạn! Năm mới phát tài! 🧧 Shop có iPhone, Samsung giá tốt lắm, bạn cần tìm máy gì?",
        "địa chỉ": "📍 123 Đường Tết, Q1, TP.HCM (Mở xuyên Tết nha!)",
        "bảo hành": "🛡️ Máy chính hãng bảo hành 12 tháng, 1 đổi 1 trong 30 ngày đầu.",
        "giao hàng": "🚀 Giao hỏa tốc 2H nội thành, Freeship toàn quốc!"
    }
    for k, v in keywords.items():
        if k in msg.lower(): return jsonify({'response': v})

    # 2. AI Processing (Sử dụng hàm mới trong utils.py)
    try:
        response = generate_chatbot_response(msg)
        return jsonify({'response': response})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({'response': "AI đang bận ăn Tết, bạn thử lại sau xíu nha!"})