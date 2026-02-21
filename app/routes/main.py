import os
import time
import json
import hashlib
import re
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_

# Import Extensions & Models
from app.extensions import db, csrf
from app.models import Product, Order, OrderDetail, AICache, TradeInRequest, Comment

# [FIX] Import local_analyze_intent từ utils (đã chuyển hàm này sang utils)
from app.utils import (
    analyze_search_intents,
    local_analyze_intent,
    get_comparison_result,
    call_gemini_api,
    validate_image_file,
    build_product_context,
    generate_chatbot_response,
    search_vector_db # [NEW] Bổ sung hàm Vector Search
)

main_bp = Blueprint('main', __name__)

# --- AI Cache Helper ---
def cached_ai_call(func, *args):
    try:
        # [FIX] Đổi key suffix sang v10 để hệ thống xóa bỏ bộ nhớ đệm (cache) lỗi cũ
        cache_key_content = str(args) + "_v10_hybrid_search"
        key = hashlib.md5(cache_key_content.encode()).hexdigest()

        cached = AICache.query.filter_by(prompt_hash=key).first()
        if cached:
            # Kiểm tra xem cache có phải là JSON hay text thường
            # Đặc biệt với so sánh (HTML), ta trả về text trực tiếp
            try:
                # Nếu là JSON (cho search intent)
                if '{' in cached.response_text and '}' in cached.response_text:
                    return json.loads(cached.response_text)
                return cached.response_text
            except:
                return cached.response_text
    except Exception as e:
        print(f"Cache Error: {e}")

    # Gọi hàm thực thi (Call API)
    res = func(*args)

    # Nếu thành công thì lưu cache
    if res:
        try:
            val = json.dumps(res) if isinstance(res, (dict, list)) else str(res)
            # Chỉ lưu nếu chưa tồn tại
            if not AICache.query.filter_by(prompt_hash=key).first():
                db.session.add(AICache(prompt_hash=key, response_text=val))
                db.session.commit()
        except:
            pass
    return res


# =========================================================
# ROUTES CHÍNH
# =========================================================

@main_bp.route('/')
def home():
    q = request.args.get('q', '').strip()
    brand_arg = request.args.get('brand', '')
    sort_arg = request.args.get('sort', '')

    ai_msg = ""
    products = []

    # Query gốc
    base_query = Product.query.filter_by(is_active=True)

    # ---------------------------------------------------------
    # 1. XỬ LÝ TÌM KIẾM (AI + LOCAL FALLBACK)
    # ---------------------------------------------------------
    if q and len(q.split()) >= 1 and not brand_arg:
        ai_data = None

        # Chỉ gọi AI nếu query dài >= 2 từ (tiết kiệm quota)
        if len(q.split()) >= 2:
            ai_data = cached_ai_call(analyze_search_intents, q)

        # [QUAN TRỌNG] Nếu AI trả về None (do lỗi 429/Quota), dùng Local Logic
        if not ai_data:
            print("⚠️ AI Quota Limit/Error -> Chuyển sang Phân tích Nội bộ (Local)")
            ai_data = local_analyze_intent(q)
            if ai_data:
                ai_msg = "🔍 Tìm kiếm thông minh (Local Mode)"

        # Áp dụng bộ lọc từ dữ liệu phân tích (AI hoặc Local)
        if ai_data:
            query = base_query

            # Lọc Hãng
            if ai_data.get('brand'):
                query = query.filter(Product.brand.ilike(f"%{ai_data['brand']}%"))
                ai_msg += f" | Hãng: {ai_data['brand']}"

            # Lọc Loại
            if ai_data.get('category'):
                query = query.filter(Product.category.ilike(f"{ai_data['category']}"))
                cat_vn = "Điện thoại" if ai_data['category'] == 'phone' else "Phụ kiện"
                ai_msg += f" | Loại: {cat_vn}"

            # Lọc Keyword (Tìm trong Tên hoặc Mô tả)
            if ai_data.get('keyword'):
                kw = ai_data['keyword']
                # [HYBRID SEARCH] Dùng Vector DB để hiểu ngữ nghĩa từ lóng (như "pin trâu")
                vector_ids = search_vector_db(kw, n_results=20)

                if vector_ids:
                    # Nếu Vector hiểu được, ép CSDL chỉ tìm trong các ID phù hợp ngữ nghĩa
                    ids = [int(i) for i in vector_ids if i.isdigit()]
                    query = query.filter(Product.id.in_(ids))
                else:
                    # Nếu Vector DB lỗi/không bật, quay về tìm chuỗi thông thường
                    query = query.filter(or_(
                        Product.name.ilike(f"%{kw}%"),
                        Product.description.ilike(f"%{kw}%")
                    ))
                ai_msg += f" | Yêu cầu: {kw}"

            # Lọc Giá
            if ai_data.get('min_price'):
                query = query.filter(Product.price >= int(ai_data['min_price']))
            if ai_data.get('max_price'):
                query = query.filter(Product.price <= int(ai_data['max_price']))

            # Sort
            if ai_data.get('sort'):
                sort_arg = ai_data['sort']

            products = query.all()

    # ---------------------------------------------------------
    # 2. FALLBACK CUỐI CÙNG (Nếu cả AI và Local Logic đều không ra kết quả)
    # ---------------------------------------------------------
    if not products and q:
        # [NEW FALLBACK] Thử tìm kiếm toàn bộ câu bằng Vector Search (Ngữ nghĩa)
        vector_ids = search_vector_db(q, n_results=8)
        if vector_ids:
            ids = [int(i) for i in vector_ids if i.isdigit()]
            products = base_query.filter(Product.id.in_(ids)).all()
            if products:
                ai_msg = "🧠 Kết quả theo ngữ nghĩa (Vector AI)"

        # Nếu Vector DB vẫn không ra, dùng tìm kiếm từ khóa (ĐỔI OR THÀNH AND)
        if not products:
            search_words = q.split()
            # Bổ sung thêm các từ rác cần loại bỏ
            stop_words = ['mua', 'tìm', 'giá', 'rẻ', 'cho', 'cần', 'dưới', 'khoảng', 'củ', 'triệu']
            keywords = [w for w in search_words if w.lower() not in stop_words]

        if keywords:
            # [QUAN TRỌNG] Dùng 'and_' thay vì 'or_' để tránh hiện kết quả rác
            # Phải chứa cả từ "samsung" VÀ chữ "pin" thì mới hiển thị
            conditions = [Product.name.ilike(f"%{word}%") for word in keywords]
            products = base_query.filter(and_(*conditions)).all()
            if products:
                ai_msg = "🔍 Kết quả tương tự (Tìm kiếm mở rộng)"
    # ---------------------------------------------------------
    # 3. TRƯỜNG HỢP MẶC ĐỊNH
    # ---------------------------------------------------------
    elif not q:
        query = base_query
        if brand_arg:
            query = query.filter(Product.brand == brand_arg)
        products = query.all()

    # 4. Sắp xếp kết quả
    if products:
        if sort_arg == 'price_asc':
            products.sort(key=lambda x: x.sale_price if x.is_sale else x.price)
        elif sort_arg == 'price_desc':
            products.sort(key=lambda x: x.sale_price if x.is_sale else x.price, reverse=True)

    # Dữ liệu bổ trợ
    brands = [b[0] for b in db.session.query(Product.brand).distinct().all()]
    hot_products = Product.query.filter_by(is_active=True, is_sale=True).limit(4).all()

    return render_template(
        'home.html',
        products=products,
        brands=brands,
        search_query=q,
        ai_message=ai_msg,
        hot_products=hot_products
    )


@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart: return redirect(url_for('main.home'))

    total = sum(item['price'] * item['quantity'] for item in cart.values())
    final_items = []

    for pid, item in cart.items():
        p = db.session.get(Product, int(pid))
        if p and p.is_active:
            price = p.sale_price if p.is_sale else p.price
            final_items.append({'p': p, 'qty': item['quantity'], 'price': price})

    if request.method == 'POST':
        try:
            payment_method = request.form.get('payment', 'cod')

            for i in final_items:
                prod = db.session.query(Product).filter_by(id=i['p'].id).with_for_update().first()
                if not prod or prod.stock_quantity < i['qty']:
                    flash(f"Sản phẩm {i['p'].name} không đủ hàng.", 'danger')
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

            if payment_method == 'banking':
                return redirect(url_for('main.payment_qr', order_id=order.id))

            flash('Đặt hàng thành công!', 'success')
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            print(f"Checkout Error: {e}")
            flash('Lỗi xử lý đơn hàng.', 'danger')
            return redirect(url_for('main.view_cart'))

    return render_template('checkout.html', cart=cart, total=total)


# --- CÁC ROUTE KHÁC ---

@main_bp.route('/product/<int:id>')
def product_detail(id):
    p = Product.query.filter_by(id=id, is_active=True).first_or_404()
    try:
        p.colors_list = json.loads(p.colors) if p.colors else []
        p.versions_list = json.loads(p.versions) if p.versions else []
    except:
        p.colors_list, p.versions_list = [], []
    recs = Product.query.filter(Product.category == 'accessory', Product.is_active == True).limit(4).all()
    comments = Comment.query.options(joinedload(Comment.user)).filter_by(product_id=id).order_by(
        Comment.created_at.desc()).all()
    return render_template('detail.html', product=p, recommendations=recs, comments=comments)


@main_bp.route('/product/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    content = request.form.get('content', '').strip()
    rating = request.form.get('rating', default=5, type=int)
    if rating not in [1, 2, 3, 4, 5]: rating = 5
    if content:
        db.session.add(Comment(user_id=current_user.id, product_id=id, content=content, rating=rating))
        db.session.commit()
        flash('Cảm ơn bạn đã đánh giá!', 'success')
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
        flash('Hết hàng!', 'danger')
        return redirect(request.referrer)
    cart = session.get('cart', {})
    sid = str(id)
    if cart.get(sid, {}).get('quantity', 0) + 1 > p.stock_quantity:
        flash(f'Kho chỉ còn {p.stock_quantity} sản phẩm.', 'warning')
        return redirect(request.referrer)

    if sid in cart:
        cart[sid]['quantity'] += 1
    else:
        cart[sid] = {'name': p.name, 'price': p.sale_price if p.is_sale else p.price, 'image': p.image_url,
                     'quantity': 1}

    session['cart'] = cart
    flash('Đã thêm vào giỏ!', 'success')
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
                flash('Quá số lượng tồn kho.', 'warning')
        elif action == 'decrease':
            cart[sid]['quantity'] -= 1
            if cart[sid]['quantity'] <= 0: del cart[sid]
        elif action == 'delete':
            del cart[sid]
    session['cart'] = cart
    return redirect(url_for('main.view_cart'))


@main_bp.route('/payment/qr/<int:order_id>')
@login_required
def payment_qr(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if order.status != 'Pending':
        flash('Đơn hàng này đã được xử lý hoặc hết hạn.', 'info')
        return redirect(url_for('main.dashboard'))

    expiration_time = order.date_created + timedelta(minutes=3)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    remaining_seconds = (expiration_time - now_naive).total_seconds()

    if remaining_seconds <= 0:
        flash('Giao dịch đã hết hạn vui lòng đặt lại.', 'warning')
        return redirect(url_for('main.dashboard'))

    bank_id = "MB"
    account_no = "9999999999"
    account_name = "MOBILE STORE"
    content = f"THANHTOAN DONHANG {order.id}"
    # [FIX] Đã sửa đường dẫn QR Code: Loại bỏ markdown syntax thừa []()
    qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={order.total_price}&addInfo={content}&accountName={account_name}"

    return render_template('payment_qr.html', order=order, qr_url=qr_url, remaining_seconds=int(remaining_seconds))


@main_bp.route('/api/payment/check/<int:order_id>')
@login_required
def check_payment_status(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return jsonify({'status': 'error'})

    expiration_time = order.date_created + timedelta(minutes=3)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    is_expired = now_naive > expiration_time

    if is_expired and order.status == 'Pending':
        return jsonify({'status': 'Expired'})

    return jsonify({'status': order.status})


@main_bp.route('/test/simulate-bank-success/<int:order_id>')
def simulate_bank_success(order_id):
    if not current_user.is_authenticated:
        return "Vui lòng đăng nhập để test"
    order = db.session.get(Order, order_id)
    if order and order.status == 'Pending':
        order.status = 'Confirmed'
        db.session.commit()
        return f"<h1>[SIMULATION] Đã nhận tiền thành công cho đơn {order_id}!</h1><p>Quay lại tab thanh toán để xem kết quả.</p>"
    return "Đơn hàng không tồn tại hoặc đã xử lý."


@main_bp.route('/trade-in', methods=['GET', 'POST'])
@login_required
def trade_in():
    if request.method == 'POST':
        if 'image' not in request.files: return redirect(request.url)
        file = request.files['image']
        is_valid, msg = validate_image_file(file)
        if not is_valid:
            flash(msg, 'danger')
            return redirect(request.url)

        filename = secure_filename(f"tradein_{current_user.id}_{int(time.time())}.jpg")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        db.session.add(TradeInRequest(user_id=current_user.id, device_name=request.form.get('device_name'),
                                      condition=request.form.get('condition'),
                                      image_proof=f"/static/uploads/{filename}"))
        db.session.commit()
        flash('Đã gửi yêu cầu định giá!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('tradein.html')


@main_bp.route('/order/cancel/<int:id>')
@login_required
def cancel_order_user(id):
    order = Order.query.options(joinedload(Order.details)).filter_by(id=id, user_id=current_user.id).first_or_404()
    if order.status == 'Pending':
        for d in order.details:
            p = db.session.get(Product, d.product_id)
            if p: p.stock_quantity += d.quantity
        order.status = 'Cancelled'
        db.session.commit()
        flash('Đã hủy đơn.', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/compare', methods=['GET', 'POST'])
def compare_page():
    products = Product.query.filter_by(is_active=True).all()
    res, p1, p2 = None, None, None

    if request.method == 'POST':
        try:
            id1 = request.form.get('product1')
            id2 = request.form.get('product2')

            if not id1 or not id2:
                flash('Vui lòng chọn đủ 2 sản phẩm để so sánh', 'warning')
            else:
                p1 = db.session.get(Product, int(id1))
                p2 = db.session.get(Product, int(id2))

                if p1 and p2:
                    # [FALLBACK] Nếu AI lỗi 429, hiển thị thông báo
                    res = cached_ai_call(get_comparison_result, p1.name, p1.price, p1.description or "", p2.name,
                                         p2.price, p2.description or "")
                    if not res:
                        res = "<div class='alert alert-warning'>Hệ thống AI đang quá tải hoặc lỗi kết nối. Vui lòng so sánh dựa trên thông số hiển thị bên trên.</div>"
        except ValueError:
            flash('Dữ liệu sản phẩm không hợp lệ', 'danger')

    return render_template('compare.html', products=products, result=res, p1=p1, p2=p2)


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
    if full_name: current_user.full_name = full_name
    db.session.commit()
    flash('Cập nhật thành công.', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/api/chatbot', methods=['POST'])
@csrf.exempt
def chatbot_api():
    msg = request.json.get('message', '').strip()
    if not msg: return jsonify({'response': "Mời bạn hỏi ạ!"})

    # 1. Rule-based Response (Luôn chạy được)
    keywords = {"địa chỉ": "📍 123 Đường Tết, Q1, TP.HCM", "bảo hành": "🛡️ 12 tháng chính hãng."}
    for k, v in keywords.items():
        if k in msg.lower(): return jsonify({'response': v})

    # 2. AI Response with MEMORY (Session)
    try:
        # [NEW] Lấy lịch sử chat từ Session
        chat_history = session.get('chat_history', [])

        # Gọi hàm AI có truyền lịch sử
        response = generate_chatbot_response(msg, chat_history)
        final_response = response or "AI đang nghỉ Tết (Hết quota), bạn thử lại sau hoặc dùng tìm kiếm nhé! 🧧"

        # [NEW] Cập nhật lịch sử
        chat_history.append({'user': msg, 'ai': final_response})

        # Giữ lại 4 cặp hội thoại (8 câu) gần nhất để tiết kiệm Session & Token
        if len(chat_history) > 4:
            chat_history = chat_history[-4:]

        # Lưu lại vào Session
        session['chat_history'] = chat_history

        return jsonify({'response': final_response})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({'response': "Lỗi kết nối AI."})