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
from sqlalchemy import or_, and_, func, desc

# Import Extensions & Models
from app.extensions import db, csrf
from app.models import Product, Order, OrderDetail, AICache, TradeInRequest, Comment

# ---> [NEW] IMPORT HẰNG SỐ HỆ THỐNG ĐỂ THAY THẾ HARDCODE <---
from app.constants import (
    ORDER_STATUS_PENDING,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_CONFIRMED,
    SEARCH_STOP_WORDS,
    CHATBOT_QUICK_REPLIES,
    SystemMessages,
    PAYMENT_METHOD_COD,
    PAYMENT_METHOD_BANKING
)

# Import Utils
from app.utils import (
    analyze_search_intents,
    local_analyze_intent,
    get_comparison_result,
    call_gemini_api,
    validate_image_file,
    build_product_context,
    generate_chatbot_response,
    search_vector_db,
    analyze_sentiment,
    direct_gemini_search,
    get_similar_products
)

main_bp = Blueprint('main', __name__)


# --- AI Cache Helper ---
def cached_ai_call(func, *args):
    """
    Trình bọc (Wrapper) lưu trữ kết quả gọi API AI vào Cache Database.
    Hỗ trợ hệ thống giảm tải API Quota và tăng tốc độ xử lý câu trả lời lên gấp 10 lần
    cho các câu hỏi trùng lặp nhờ thuật toán băm (MD5 Hash).
    """
    try:
        ### ---> [ĐÃ SỬA CHỖ NÀY: Nâng Version Cache để cập nhật giao diện CellphoneS 4 Sản Phẩm] <--- ###
        cache_key_content = f"{func.__name__}_{str(args)}_v64_multi_compare"
        key = hashlib.md5(cache_key_content.encode()).hexdigest()

        cached = AICache.query.filter_by(prompt_hash=key).first()
        if cached:
            try:
                text_data = cached.response_text.strip()
                if text_data.startswith('{') and text_data.endswith('}'):
                    return json.loads(text_data)
                elif text_data.startswith('[') and text_data.endswith(']'):
                    return json.loads(text_data)
                return text_data
            except:
                return cached.response_text
    except Exception as e:
        print(f"Cache Error: {e}")

    # Gọi hàm thực thi (Call API)
    res = func(*args)

    if res:
        try:
            val = json.dumps(res) if isinstance(res, (dict, list)) else str(res)
            if not AICache.query.filter_by(prompt_hash=key).first():
                db.session.add(AICache(prompt_hash=key, response_text=val))
                db.session.commit()
        except:
            pass
    return res


def build_chroma_filter(ai_data):
    """
    Chuyển đổi dữ liệu phân tích ý định tìm kiếm của người dùng thành
    định dạng siêu dữ liệu (Metadata filter) để phục vụ cho Hybrid Search trên ChromaDB.
    """
    if not ai_data: return None
    conditions = []
    if ai_data.get('category'):
        conditions.append({"category": ai_data['category']})
    if ai_data.get('brand'):
        conditions.append({"brand": ai_data['brand']})

    if len(conditions) == 1:
        return conditions[0]
    elif len(conditions) > 1:
        return {"$and": conditions}
    return None


# =========================================================
# ROUTES CHÍNH
# =========================================================

@main_bp.route('/')
def home():
    """
    Xử lý hiển thị Trang chủ của hệ thống.
    Tiếp nhận các truy vấn tìm kiếm AI phức tạp, kết hợp Vector Database
    để lọc sản phẩm chuẩn xác theo ngữ nghĩa và tầm giá.
    """
    q = request.args.get('q', '').strip()
    brand_arg = request.args.get('brand', '')
    sort_arg = request.args.get('sort', '')

    ai_msg = ""
    products = []

    base_query = Product.query.filter_by(is_active=True)
    ai_data = None

    if q and len(q.split()) >= 1 and not brand_arg:
        if len(q.split()) >= 2:
            ai_data = cached_ai_call(analyze_search_intents, q)

        if not ai_data:
            ai_data = local_analyze_intent(q)
            if ai_data and any(v for k, v in ai_data.items() if k not in ['sort'] and v is not None):
                ai_msg = "🔍 Phân tích nhu cầu (Local Mode)"
        else:
            ai_msg = "🤖 AI đã phân tích nhu cầu"

        if ai_data:
            query = base_query

            if ai_data.get('brand'):
                query = query.filter(Product.brand.ilike(f"%{ai_data['brand']}%"))
                if "Hãng" not in ai_msg: ai_msg += f" | Hãng: {ai_data['brand']}"

            if ai_data.get('category'):
                query = query.filter(Product.category.ilike(f"{ai_data['category']}"))

            if ai_data.get('min_price'):
                query = query.filter(Product.price >= int(ai_data['min_price']))

            if ai_data.get('max_price'):
                query = query.filter(Product.price <= int(ai_data['max_price']))

            if ai_data.get('keyword'):
                kw = ai_data['keyword'].strip()
                if kw:
                    chroma_filter = build_chroma_filter(ai_data)
                    vector_ids = search_vector_db(kw, n_results=20, metadata_filters=chroma_filter)

                    if vector_ids:
                        ids = [int(i) for i in vector_ids if i.isdigit()]
                        if ids:
                            query = query.filter(Product.id.in_(ids))
                            if "Ngữ nghĩa" not in ai_msg: ai_msg += f" | 🧠 Smart Search"
                        else:
                            vector_ids = []

                    if not vector_ids:
                        conditions = []
                        for word in kw.split():
                            conditions.append(or_(
                                Product.name.like(f"%{word}%"),
                                Product.name.like(f"%{word.capitalize()}%"),
                                Product.name.like(f"%{word.lower()}%"),
                                Product.name.like(f"%{word.title()}%")
                            ))
                        query = query.filter(and_(*conditions))

            if ai_data.get('sort'):
                sort_arg = ai_data['sort']

            products = query.all()

    if not products and q:
        catalog_for_ai = []
        for p in base_query.all():
            catalog_for_ai.append({
                "id": p.id, "name": p.name, "price": p.price,
                "category": p.category,
                "desc": (p.description or "")[:150]
            })

        cat_json = json.dumps(catalog_for_ai, ensure_ascii=False)
        flash_ids = cached_ai_call(direct_gemini_search, q, cat_json)

        if flash_ids and isinstance(flash_ids, list) and len(flash_ids) > 0:
            unsorted_products = base_query.filter(Product.id.in_(flash_ids)).all()
            products = sorted(unsorted_products, key=lambda x: flash_ids.index(x.id) if x.id in flash_ids else 999)
            if products:
                ai_msg = "🧠 Trí tuệ nhân tạo (Gemini Semantic Search)"
        else:
            fallback_query = base_query
            if ai_data and ai_data.get('category'):
                fallback_query = fallback_query.filter(Product.category.ilike(f"{ai_data['category']}"))
            if ai_data and ai_data.get('brand'):
                fallback_query = fallback_query.filter(Product.brand.ilike(f"%{ai_data['brand']}%"))

            if ai_data and ai_data.get('min_price'):
                fallback_query = fallback_query.filter(Product.price >= int(ai_data['min_price']))
            if ai_data and ai_data.get('max_price'):
                fallback_query = fallback_query.filter(Product.price <= int(ai_data['max_price']))

            search_words = q.split()
            stop_words = SEARCH_STOP_WORDS
            keywords = [w for w in search_words if w.lower() not in stop_words]

            if keywords:
                conditions = []
                for word in keywords:
                    conditions.append(or_(
                        Product.name.like(f"%{word}%"),
                        Product.name.like(f"%{word.capitalize()}%"),
                        Product.name.like(f"%{word.lower()}%"),
                        Product.name.like(f"%{word.title()}%")
                    ))

                products = fallback_query.filter(or_(*conditions)).all()
                if products:
                    ai_msg = "🔍 Tìm kiếm mở rộng (SQL Fallback)"

    elif not q:
        query = base_query
        if brand_arg:
            query = query.filter(Product.brand == brand_arg)
        products = query.all()

    if products:
        if sort_arg == 'price_asc':
            products.sort(key=lambda x: x.sale_price if x.is_sale and x.sale_price else x.price)
        elif sort_arg == 'price_desc':
            products.sort(key=lambda x: x.sale_price if x.is_sale and x.sale_price else x.price, reverse=True)

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


@main_bp.route('/product/<int:id>')
def product_detail(id):
    """
    Xử lý truy xuất thông tin chi tiết một sản phẩm.
    Tích hợp thuật toán Collaborative Filtering để gợi ý mua kèm phụ kiện.
    Tích hợp thêm Content-Based Recommendation (Thuật toán toán học gợi ý sản phẩm tương tự).
    """
    p = Product.query.filter_by(id=id, is_active=True).first_or_404()
    try:
        p.colors_list = json.loads(p.colors) if p.colors else []
        p.versions_list = json.loads(p.versions) if p.versions else []
    except:
        p.colors_list, p.versions_list = [], []

    related_order_ids_query = db.session.query(OrderDetail.order_id).filter_by(product_id=id)

    # 1. Gợi ý Phụ kiện mua kèm (Collaborative Filtering)
    recommendation_query = db.session.query(Product, func.sum(OrderDetail.quantity).label('total_bought')) \
        .join(OrderDetail, Product.id == OrderDetail.product_id) \
        .filter(OrderDetail.order_id.in_(related_order_ids_query)) \
        .filter(Product.id != id) \
        .filter(Product.category == 'accessory') \
        .filter(Product.is_active == True) \
        .group_by(Product.id) \
        .order_by(desc('total_bought')) \
        .limit(4).all()

    recs = [item[0] for item in recommendation_query]

    if not recs:
        recs = Product.query.filter(Product.category == 'accessory', Product.is_active == True).limit(4).all()

    similar_prods = get_similar_products(p, limit=4)

    # ==============================================================================================
    # ---> [ĐÃ SỬA CHỖ NÀY: Ép buộc cùng phân loại (cùng điện thoại hoặc phụ kiện) mới được so sánh] <---
    # ==============================================================================================
    all_products = Product.query.filter(
        Product.is_active == True,
        Product.category == p.category,
        Product.id != p.id
    ).all()

    comments = Comment.query.options(joinedload(Comment.user)).filter(
        Comment.product_id == id, Comment.parent_id == None, Comment.rating > 0
    ).order_by(Comment.created_at.desc()).all()

    questions = Comment.query.options(joinedload(Comment.user)).filter_by(
        product_id=id, parent_id=None, rating=0
    ).order_by(Comment.created_at.desc()).all()

    rating_stats = {
        'total': 0, 'avg': 0,
        'stars': {5: {'count': 0, 'pct': 0}, 4: {'count': 0, 'pct': 0}, 3: {'count': 0, 'pct': 0},
                  2: {'count': 0, 'pct': 0}, 1: {'count': 0, 'pct': 0}}
    }

    if comments:
        rating_stats['total'] = len(comments)
        sum_rating = sum(c.rating for c in comments)
        rating_stats['avg'] = round(sum_rating / rating_stats['total'], 1)

        for c in comments:
            if c.rating in rating_stats['stars']:
                rating_stats['stars'][c.rating]['count'] += 1

        for star in rating_stats['stars']:
            rating_stats['stars'][star]['pct'] = (rating_stats['stars'][star]['count'] / rating_stats['total']) * 100

    return render_template('detail.html', product=p, all_products=all_products, recommendations=recs,
                           similar_products=similar_prods, comments=comments, questions=questions,
                           rating=rating_stats)


@main_bp.route('/product/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    """
    Xử lý gửi bình luận hoặc câu hỏi từ người dùng lên hệ thống.
    Cho phép trả lời lồng nhau (Nested Replies) và tự động ghi nhận điểm đánh giá.
    """
    content = request.form.get('content', '').strip()

    is_question = request.form.get('is_question') == 'true'
    parent_id = request.form.get('parent_id', type=int)

    if is_question or parent_id:
        final_rating = 0
    else:
        rating = request.form.get('rating', default=5, type=int)
        if rating not in [1, 2, 3, 4, 5]: rating = 5
        final_rating = rating

    if content:
        new_comment = Comment(
            user_id=current_user.id,
            product_id=id,
            content=content,
            rating=final_rating,
            parent_id=parent_id
        )
        db.session.add(new_comment)
        db.session.commit()

        if not parent_id and not is_question:
            sentiment_result = analyze_sentiment(content)

        if parent_id:
            flash(SystemMessages.COMMENT_REPLY_SUCCESS, 'success')
        elif is_question:
            flash(SystemMessages.COMMENT_QA_SUCCESS, 'success')
        else:
            flash(SystemMessages.COMMENT_REVIEW_SUCCESS, 'success')

    if request.form.get('source') == 'admin':
        return redirect(url_for('admin.dashboard'))

    return redirect(url_for('main.product_detail', id=id))


@main_bp.route('/cart')
def view_cart():
    """
    Hiển thị giao diện Giỏ hàng.
    Lấy dữ liệu tạm thời từ phiên truy cập (Session) của khách hàng để tính toán tổng tiền.
    """
    cart = session.get('cart', {})
    total = 0
    enriched_cart = []

    for sid, item in cart.items():
        subtotal = item['price'] * item['quantity']
        total += subtotal

        item_copy = item.copy()
        item_copy['id'] = sid
        item_copy['subtotal'] = subtotal
        enriched_cart.append(item_copy)

    return render_template('cart.html', cart_items=enriched_cart, total_amount=total)


@main_bp.route('/cart/add/<int:id>', methods=['POST'])
def add_to_cart(id):
    """
    Xử lý thêm sản phẩm vào Giỏ hàng trong bộ nhớ đệm.
    Kiểm tra chặt chẽ số lượng tồn kho (Inventory) trước khi cho phép thêm.
    """
    p = Product.query.filter_by(id=id, is_active=True).first_or_404()
    if p.stock_quantity <= 0:
        flash(SystemMessages.CART_OUT_OF_STOCK, 'danger')
        return redirect(request.referrer)
    cart = session.get('cart', {})
    sid = str(id)
    if cart.get(sid, {}).get('quantity', 0) + 1 > p.stock_quantity:
        flash(SystemMessages.CART_EXCEED_STOCK, 'warning')
        return redirect(request.referrer)

    if sid in cart:
        cart[sid]['quantity'] += 1
    else:
        cart[sid] = {'name': p.name, 'price': p.sale_price if p.is_sale else p.price, 'image': p.image_url,
                     'quantity': 1}

    session['cart'] = cart
    flash(SystemMessages.CART_ADD_SUCCESS, 'success')
    return redirect(request.referrer or url_for('main.home'))


@main_bp.route('/cart/update/<int:id>/<action>')
def update_cart(id, action):
    """
    Cho phép khách hàng thay đổi số lượng hoặc xóa sản phẩm khỏi Giỏ hàng.
    Cập nhật trực tiếp vào Session lưu trữ.
    """
    cart = session.get('cart', {})
    sid = str(id)
    if sid in cart:
        if action == 'increase':
            p = db.session.get(Product, id)
            if p and cart[sid]['quantity'] + 1 <= p.stock_quantity:
                cart[sid]['quantity'] += 1
            else:
                flash(SystemMessages.CART_EXCEED_STOCK, 'warning')
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
    """
    Quy trình thanh toán chính thức (Checkout).
    Bảo vệ chống Race Condition bằng with_for_update() để trừ đúng tồn kho khi nhiều
    khách hàng cùng đặt một sản phẩm cùng lúc.
    """
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
            payment_method = request.form.get('payment', PAYMENT_METHOD_COD)

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
                status=ORDER_STATUS_PENDING
            )
            db.session.add(order)
            db.session.flush()

            for i in final_items:
                db.session.add(
                    OrderDetail(order_id=order.id, product_id=i['p'].id, product_name=i['p'].name, quantity=i['qty'],
                                price=i['price']))

            db.session.commit()
            session.pop('cart', None)

            if payment_method == PAYMENT_METHOD_BANKING:
                return redirect(url_for('main.payment_qr', order_id=order.id))

            flash(SystemMessages.ORDER_SUCCESS, 'success')
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            print(f"Checkout Error: {e}")
            flash(SystemMessages.ORDER_ERROR, 'danger')
            return redirect(url_for('main.view_cart'))

    return render_template('checkout.html', cart=cart, total=total)


@main_bp.route('/payment/qr/<int:order_id>')
@login_required
def payment_qr(order_id):
    """
    Hiển thị giao diện thanh toán chuyển khoản qua mã QR Động (VietQR).
    Hỗ trợ đồng hồ đếm ngược (Countdown) cho các giao dịch treo nhằm hủy và thu hồi hàng tự động.
    """
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if order.status != ORDER_STATUS_PENDING:
        flash(SystemMessages.ORDER_ENDED, 'info')
        return redirect(url_for('main.dashboard'))

    expiration_time = order.date_created + timedelta(minutes=3)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    remaining_seconds = (expiration_time - now_naive).total_seconds()

    if remaining_seconds <= 0:
        flash(SystemMessages.ORDER_EXPIRED, 'warning')
        return redirect(url_for('main.dashboard'))

    bank_id = "MB"
    account_no = "9999999999"
    account_name = "MOBILE STORE"
    content = f"THANHTOAN DONHANG {order.id}"
    qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={order.total_price}&addInfo={content}&accountName={account_name}"

    return render_template('payment_qr.html', order=order, qr_url=qr_url, remaining_seconds=int(remaining_seconds))


@main_bp.route('/api/payment/check/<int:order_id>')
@login_required
def check_payment_status(order_id):
    """
    API kiểm tra định kỳ (Polling) trạng thái thanh toán từ trình duyệt.
    Xác minh xem tiền đã vào tài khoản và đơn hàng đã sang trạng thái Xác nhận chưa.
    """
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return jsonify({'status': 'error'})

    expiration_time = order.date_created + timedelta(minutes=3)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    is_expired = now_naive > expiration_time

    if is_expired and order.status == ORDER_STATUS_PENDING:
        return jsonify({'status': 'Expired'})

    return jsonify({'status': order.status})


@main_bp.route('/test/simulate-bank-success/<int:order_id>')
def simulate_bank_success(order_id):
    """
    Môi trường kiểm thử giả lập (Sandbox) cho phép ép một đơn hàng
    đang treo sang trạng thái Đã Thanh Toán thành công mà không cần chuyển khoản thật.
    """
    if not current_user.is_authenticated:
        return "Vui lòng đăng nhập để test"
    order = db.session.get(Order, order_id)
    if order and order.status == ORDER_STATUS_PENDING:
        order.status = ORDER_STATUS_CONFIRMED
        db.session.commit()
        return f"<h1>[SIMULATION] Đã nhận tiền thành công cho đơn {order_id}!</h1><p>Quay lại tab thanh toán để xem kết quả.</p>"
    return "Đơn hàng không tồn tại hoặc đã xử lý."


@main_bp.route('/trade-in', methods=['GET', 'POST'])
@login_required
def trade_in():
    """
    Khu vực tiếp nhận yêu cầu Thu cũ Đổi mới.
    Cho phép khách hàng tải ảnh minh chứng tình trạng thiết bị cũ lên Server an toàn.
    """
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
        flash(SystemMessages.TRADEIN_SUCCESS, 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('tradein.html')


# ==============================================================================================
# ---> [NEW: ROUTER SO SÁNH NÂNG CẤP XỬ LÝ TỚI 4 SẢN PHẨM CÙNG LÚC] <---
# ==============================================================================================
@main_bp.route('/compare', methods=['GET', 'POST'])
@csrf.exempt
def compare_page():
    """
    Khu vực đấu trường So sánh Sản phẩm (Hỗ trợ tối đa 4 sản phẩm).
    Sử dụng thuật toán Gemini AI để sinh ra bảng đối chiếu tính năng CellphoneS Style.
    """
    products = Product.query.filter_by(is_active=True).all()
    res = None
    selected_prods = []

    if request.method == 'POST':
        try:
            id1 = request.form.get('product1')
            id2 = request.form.get('product2')
            id3 = request.form.get('product3')
            id4 = request.form.get('product4')

            if not id1 or not id2:
                flash('Vui lòng chọn ít nhất 2 sản phẩm để so sánh', 'warning')
            else:
                p1 = db.session.get(Product, int(id1))
                p2 = db.session.get(Product, int(id2))
                p3 = db.session.get(Product, int(id3)) if id3 else None
                p4 = db.session.get(Product, int(id4)) if id4 else None

                if p1 and p2:
                    selected_prods = [p for p in [p1, p2, p3, p4] if p is not None]

                    # Truyền Data động theo cấu trúc Tham số của utils
                    p1_price_str = "{:,.0f} đ".format(p1.sale_price if p1.is_sale else p1.price).replace(",", ".")
                    p2_price_str = "{:,.0f} đ".format(p2.sale_price if p2.is_sale else p2.price).replace(",", ".")

                    p3_id = p3.id if p3 else None
                    p3_name = p3.name if p3 else None
                    p3_price_str = "{:,.0f} đ".format(p3.sale_price if p3.is_sale else p3.price).replace(",",
                                                                                                         ".") if p3 else None
                    p3_desc = p3.description or "" if p3 else None
                    p3_img = p3.image_url if p3 else None

                    p4_id = p4.id if p4 else None
                    p4_name = p4.name if p4 else None
                    p4_price_str = "{:,.0f} đ".format(p4.sale_price if p4.is_sale else p4.price).replace(",",
                                                                                                         ".") if p4 else None
                    p4_desc = p4.description or "" if p4 else None
                    p4_img = p4.image_url if p4 else None

                    res = cached_ai_call(
                        get_comparison_result,
                        p1.id, p1.name, p1_price_str, p1.description or "", p1.image_url,
                        p2.id, p2.name, p2_price_str, p2.description or "", p2.image_url,
                        p3_id, p3_name, p3_price_str, p3_desc, p3_img,
                        p4_id, p4_name, p4_price_str, p4_desc, p4_img
                    )

                    if not res:
                        res = f"<div class='alert alert-warning'>{SystemMessages.AI_ERROR}</div>"
        except ValueError:
            flash('Dữ liệu sản phẩm không hợp lệ', 'danger')

    return render_template('compare.html', products=products, result=res, selected_prods=selected_prods)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Bảng điều khiển (Dashboard) của khách hàng đăng nhập.
    Bao gồm thống kê chi tiêu, hiển thị cấp bậc hội viên theo RFM Model và lịch sử giao dịch.
    """
    my_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_created.desc()).all()
    my_tradeins = TradeInRequest.query.filter_by(user_id=current_user.id).order_by(
        TradeInRequest.created_at.desc()).all()

    total_spent = sum(o.total_price for o in my_orders if o.status == ORDER_STATUS_COMPLETED)
    pending_orders = sum(1 for o in my_orders if o.status == ORDER_STATUS_PENDING)
    total_orders = len(my_orders)

    rank_tier = 1
    rank = "M-New"
    next_rank = "M-Gold"
    needed_for_next = 5000000 - total_spent
    progress_percent = (total_spent / 5000000) * 25

    if total_spent >= 50000000:
        rank_tier = 4;
        rank = "M-Diamond";
        next_rank = "Đã Đạt Cấp Tối Đa"
        needed_for_next = 0;
        progress_percent = 100
    elif total_spent >= 20000000:
        rank_tier = 3;
        rank = "M-Platinum";
        next_rank = "M-Diamond"
        needed_for_next = 50000000 - total_spent
        progress_percent = 75 + ((total_spent - 20000000) / 30000000) * 25
    elif total_spent >= 5000000:
        rank_tier = 2;
        rank = "M-Gold";
        next_rank = "M-Platinum"
        needed_for_next = 20000000 - total_spent
        progress_percent = 50 + ((total_spent - 5000000) / 15000000) * 25

    member_stats = {
        'total_spent': total_spent,
        'pending_orders': pending_orders,
        'total_orders': total_orders,
        'rank_tier': rank_tier,
        'rank': rank,
        'next_rank': next_rank,
        'needed_for_next': needed_for_next,
        'progress_percent': progress_percent
    }

    return render_template('dashboard.html', orders=my_orders, tradeins=my_tradeins, member=member_stats)


@main_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """
    Tiếp nhận và cập nhật thông tin họ tên, thông tin bảo mật của người dùng hiện tại.
    """
    full_name = request.form.get('full_name')
    if full_name: current_user.full_name = full_name
    db.session.commit()
    flash(SystemMessages.PROFILE_UPDATE_SUCCESS, 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/api/chatbot', methods=['POST'])
@csrf.exempt
def chatbot_api():
    """
    Endpoint giao tiếp với Bot tư vấn thông minh (Gemini AI).
    Sử dụng Session để ghi nhớ lịch sử hội thoại gần nhất giúp AI xử lý ngữ cảnh liền mạch.
    """
    msg = request.json.get('message', '').strip()
    if not msg: return jsonify({'response': "Mời bạn hỏi ạ!"})

    keywords = CHATBOT_QUICK_REPLIES
    for k, v in keywords.items():
        if k in msg.lower(): return jsonify({'response': v})

    try:
        chat_history = session.get('chat_history', [])
        response = generate_chatbot_response(msg, chat_history)
        final_response = response or SystemMessages.AI_BUSY

        chat_history.append({'user': msg, 'ai': final_response})

        if len(chat_history) > 4:
            chat_history = chat_history[-4:]

        session['chat_history'] = chat_history

        return jsonify({'response': final_response})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({'response': "Lỗi kết nối AI."})