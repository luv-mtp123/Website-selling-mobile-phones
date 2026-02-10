from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Product, Order, OrderDetail, AICache
from app.utils import analyze_search_intents, get_comparison_result, call_gemini_api
import json
import hashlib

main_bp = Blueprint('main', __name__)


# --- Helper Cache AI ---
def cached_ai_call(func, *args):
    """
    Hàm wrapper giúp kiểm tra cache trước khi gọi API Gemini.
    Giúp tiết kiệm quota và tăng tốc độ phản hồi.
    """
    try:
        # Tạo key duy nhất dựa trên tham số đầu vào
        key_content = str(args)
        key = hashlib.md5(key_content.encode()).hexdigest()

        # 1. Kiểm tra trong Database
        cached = AICache.query.filter_by(prompt_hash=key).first()
        if cached:
            # Nếu có cache, trả về ngay (Parse JSON nếu cần)
            try:
                return json.loads(cached.response_text)
            except:
                return cached.response_text
    except Exception as e:
        print(f"⚠️ Cache Read Error: {e}")

    # 2. Nếu không có cache, gọi hàm API thực sự
    res = func(*args)

    # 3. Lưu kết quả vào Database
    if res:
        try:
            val = json.dumps(res) if isinstance(res, (dict, list)) else str(res)
            # Kiểm tra lại lần nữa để tránh lỗi trùng lặp
            if not AICache.query.filter_by(prompt_hash=key).first():
                new_cache = AICache(prompt_hash=key, response_text=val)
                db.session.add(new_cache)
                db.session.commit()
        except Exception as e:
            print(f"⚠️ Cache Write Error: {e}")
            db.session.rollback()

    return res


# --- Routes: Public Pages ---

@main_bp.route('/')
def home():
    q = request.args.get('q', '')
    brand = request.args.get('brand', '')
    sort = request.args.get('sort', '')
    ai_msg = ""
    query = Product.query

    # Logic Smart Search với Cache
    if q and len(q.split()) > 2 and not brand:
        ai_data = cached_ai_call(analyze_search_intents, q)

        if ai_data:
            if ai_data.get('brand'):
                query = query.filter(Product.brand.contains(ai_data['brand']))
                ai_msg += f"Hãng: {ai_data['brand']} "
            if ai_data.get('min_price'):
                query = query.filter(Product.price >= ai_data['min_price'])
                ai_msg += f"| > {ai_data['min_price']:,}đ "
            if ai_data.get('max_price'):
                query = query.filter(Product.price <= ai_data['max_price'])
                ai_msg += f"| < {ai_data['max_price']:,}đ "
            if ai_data.get('sort'):
                sort = ai_data['sort']

            if ai_msg:
                ai_msg = f"🔍 AI đã lọc: {ai_msg}"
        else:
            query = query.filter(Product.name.contains(q))
    elif q:
        query = query.filter(Product.name.contains(q))

    if brand:
        query = query.filter(Product.brand == brand)

    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.id.desc())

    products = query.all()
    brands = [b[0] for b in db.session.query(Product.brand).distinct().all()]

    return render_template('home.html', products=products, brands=brands, search_query=q, ai_message=ai_msg)


@main_bp.route('/product/<int:id>')
def product_detail(id):
    p = Product.query.get_or_404(id)

    # Parse JSON Colors & Versions
    try:
        p.colors_list = json.loads(p.colors) if p.colors else []
        p.versions_list = json.loads(p.versions) if p.versions else []
    except:
        p.colors_list = []
        p.versions_list = []

    # Logic Gợi ý sản phẩm (Recommendation)
    recs = []
    if p.category == 'phone':
        # Nếu xem điện thoại -> Gợi ý phụ kiện
        brand_accs = Product.query.filter_by(category='accessory', brand=p.brand).limit(2).all()
        general_accs = Product.query.filter_by(category='accessory', brand='Phụ kiện chung').limit(4).all()

        # Gộp danh sách, ưu tiên hàng hãng
        recs = list(brand_accs)
        rec_ids = {item.id for item in recs}
        for acc in general_accs:
            if acc.id not in rec_ids:
                recs.append(acc)
                rec_ids.add(acc.id)

        # Lấp đầy nếu thiếu
        if len(recs) < 4:
            others = Product.query.filter(Product.category == 'accessory', Product.id.notin_(rec_ids)).limit(4).all()
            recs.extend(others)

        recs = recs[:4]
    else:
        # Nếu xem phụ kiện -> Gợi ý sản phẩm cùng hãng
        recs = Product.query.filter(Product.brand == p.brand, Product.id != id).limit(4).all()
        if not recs:
            recs = Product.query.filter(Product.category == 'accessory', Product.id != id).limit(4).all()

    return render_template('detail.html', product=p, ai_suggestion="", recommendations=recs)


@main_bp.route('/compare', methods=['GET', 'POST'])
def compare_page():
    products = Product.query.all()
    result, p1, p2 = None, None, None

    if request.method == 'POST':
        p1 = Product.query.get(request.form.get('product1'))
        p2 = Product.query.get(request.form.get('product2'))

        if p1 and p2:
            # Sử dụng Cache cho tính năng so sánh
            result = cached_ai_call(
                get_comparison_result,
                p1.name, p1.price, p1.description,
                p2.name, p2.price, p2.description
            )
        else:
            flash("Vui lòng chọn 2 sản phẩm khác nhau!", "warning")

    return render_template('compare.html', products=products, result=result, p1=p1, p2=p2)


# --- Routes: Cart & Checkout ---

@main_bp.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    total = sum(i['price'] * i['quantity'] for i in cart.values())
    return render_template('cart.html', cart=cart, total_amount=total)


@main_bp.route('/cart/add/<int:id>', methods=['POST'])
def add_to_cart(id):
    p = Product.query.get_or_404(id)
    cart = session.get('cart', {})
    sid = str(id)

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
            cart[sid]['quantity'] += 1
        elif action == 'decrease':
            cart[sid]['quantity'] -= 1
            if cart[sid]['quantity'] <= 0: del cart[sid]
        elif action == 'delete':
            del cart[sid]

    session['cart'] = cart
    return redirect(url_for('main.view_cart'))


@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart: return redirect(url_for('main.home'))

    total = sum(i['price'] * i['quantity'] for i in cart.values())

    if request.method == 'POST':
        # Tạo đơn hàng
        order = Order(
            user_id=current_user.id,
            total_price=total,
            address=request.form.get('address'),
            phone=request.form.get('phone'),
            status='Completed'
        )
        db.session.add(order)
        db.session.flush()

        # Lưu chi tiết đơn hàng
        for pid, item in cart.items():
            db.session.add(OrderDetail(
                order_id=order.id,
                product_id=int(pid),
                product_name=item['name'],
                quantity=item['quantity'],
                price=item['price']
            ))

        db.session.commit()
        session.pop('cart', None)
        flash('Đặt hàng thành công!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('checkout.html', cart=cart, total=total)


# --- Routes: Chatbot & User ---

@main_bp.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    msg = request.json.get('message', '').lower()

    # Kịch bản cứng
    keywords = {
        "xin chào": "Chào bạn! Chúc mừng năm mới!",
        "địa chỉ": "123 Đường Tết, Q1, TP.HCM",
        "giao hàng": "Giao hỏa tốc 2H trong nội thành."
    }
    for k, v in keywords.items():
        if k in msg: return jsonify({'response': v})

    # Gọi AI (có cache)
    def chat_wrapper(m):
        return call_gemini_api(f"Khách hỏi: '{m}'. Trả lời ngắn gọn dưới 50 từ, thân thiện.")

    res = cached_ai_call(chat_wrapper, msg)
    return jsonify({'response': res or "Hệ thống đang bận, vui lòng thử lại sau."})


@main_bp.route('/dashboard')
@login_required
def dashboard():
    my_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_created.desc()).all()
    return render_template('dashboard.html', orders=my_orders)


@main_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    current_user.full_name = request.form.get('full_name')
    current_user.email = request.form.get('email')
    db.session.commit()
    flash('Cập nhật thành công', 'success')
    return redirect(url_for('main.dashboard'))