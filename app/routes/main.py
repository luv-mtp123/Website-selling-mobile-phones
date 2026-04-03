"""
Module Main Controller điều phối các nghiệp vụ chính dành cho Khách hàng (User/Guest).
Bao gồm: Tìm kiếm thông minh (Hybrid Search), Giỏ hàng, Đặt hàng (Checkout),
Trang chi tiết sản phẩm, Dashboard M-Member và Áp dụng Voucher (Khuyến mãi).
"""

import os
import time
import json
import hashlib
import re
import urllib.parse  # ---> [NEW: Thêm thư viện để encode URL an toàn]
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, func, desc

# Import Extensions & Models
from app.extensions import db, csrf
from app.models import Product, Order, OrderDetail, AICache, TradeInRequest, Comment, Voucher

# Import Hằng số cấu hình hệ thống
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

# Import Thư viện tiện ích & Thuật toán lõi
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
    get_similar_products,
    generate_local_comparison_html,
    VoucherValidatorEngine,
    search_image_vector_db,
    identify_phone_by_gemini  # ---> [HOTFIX] Bổ sung Import AI đọc tên máy
)

main_bp = Blueprint('main', __name__)


def cached_ai_call(func, *args):
    """
    Trình bọc (Wrapper) lưu trữ kết quả gọi API AI vào Cache Database.
    Giảm tải API Quota và tăng tốc độ xử lý câu trả lời lên gấp 10 lần nhờ mã băm (MD5).
    """
    try:
        cache_key_content = f"{func.__name__}_{str(args)}_v239_final"
        key = hashlib.md5(cache_key_content.encode()).hexdigest()

        cached = AICache.query.filter_by(prompt_hash=key).first()
        if cached:
            try:
                # ---> [HOTFIX] Bóc tách rác Markdown bảo vệ Cache an toàn tuyệt đối
                text_data = re.sub(r"```json|```", "", cached.response_text).strip()
                if text_data.startswith('{') and text_data.endswith('}'):
                    return json.loads(text_data)
                elif text_data.startswith('[') and text_data.endswith(']'):
                    return json.loads(text_data)
                return text_data
            except Exception:
                return cached.response_text
    except Exception as e:
        print(f"Cache Error: {e}")

    # Thực thi API thực tế nếu không có Cache
    res = func(*args)

    if res:
        try:
            val = json.dumps(res) if isinstance(res, (dict, list)) else str(res)
            if not AICache.query.filter_by(prompt_hash=key).first():
                db.session.add(AICache(prompt_hash=key, response_text=val))
                db.session.commit()
        except Exception:
            pass
    return res


def build_chroma_filter(ai_data):
    """
    Chuyển đổi dữ liệu phân tích ý định tìm kiếm thành định dạng metadata filter (JSON).
    Phục vụ cho chức năng Hybrid Search của ChromaDB.
    """
    if not ai_data:
        return None
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


# =======================================================================================
# ---> [NEW: HELPER CALCULATE USER RANK] <---
# Khắc phục lỗi bảo mật: Tự động tính hạng thẻ từ Backend để chống thao túng (Spoofing)
# =======================================================================================
def _calculate_user_rank(user_id):
    """
    Thuật toán kế toán tính toán Cấp bậc VIP của Người dùng dựa trên tổng chi tiêu.
    Được sử dụng chung cho việc hiển thị Dashboard và xác thực Voucher.
    Tránh việc lặp lại mã (DRY - Don't Repeat Yourself).
    """
    completed_orders = Order.query.filter_by(user_id=user_id, status=ORDER_STATUS_COMPLETED).all()
    total_spent = sum(o.total_price for o in completed_orders)

    rank_tier = 1
    rank_name = "M-New"

    if total_spent >= 50000000:
        rank_tier = 4
        rank_name = "M-Diamond"
    elif total_spent >= 20000000:
        rank_tier = 3
        rank_name = "M-Platinum"
    elif total_spent >= 5000000:
        rank_tier = 2
        rank_name = "M-Gold"

    return rank_tier, rank_name, total_spent
# =======================================================================================


@main_bp.route('/')
def home():
    q = request.args.get('q', '').strip()
    brand_arg = request.args.get('brand', '')
    sort_arg = request.args.get('sort', '')

    ai_msg = ""
    products = []

    base_query = Product.query.filter_by(is_active=True)
    ai_data = None  # Cần lưu lại ai_data để dùng cho lớp Fallback phía dưới

    if q and len(q.split()) >= 1:
        # ---> [NÂNG CẤP]: TRUE HYBRID AI SEARCH (Kết hợp Keyword + Vector Semantic)
        ai_data = analyze_search_intents(q)

        if ai_data and (ai_data.get('keyword') or ai_data.get('brand') or ai_data.get('category') or ai_data.get('semantic_query')):
            ai_msg = "🧠 Hybrid AI Search (Gemini + Vector)"
        else:
            ai_data = local_analyze_intent(q)
            ai_msg = "⚡ Smart Search (Tốc độ cao)"

        query = base_query

        if brand_arg:
            ai_data['brand'] = brand_arg

        # 1. LỌC CỨNG (HARD FILTERS)
        if ai_data.get('brand'):
            if ai_data.get('category') == 'accessory':
                query = query.filter(
                    or_(Product.brand.ilike(f"%{ai_data['brand']}%"), Product.brand.ilike("%Phụ kiện%")))
            else:
                query = query.filter(Product.brand.ilike(f"%{ai_data['brand']}%"))
            ai_msg += f" | Hãng: {ai_data['brand']}"

        if ai_data.get('category'):
            query = query.filter(Product.category == ai_data['category'])

        if ai_data.get('max_price'):
            query = query.filter(Product.price <= int(ai_data['max_price']))

        products_pool = query.all()

        # 2. ĐỘNG CƠ TÌM KIẾM LAI ĐA TRỌNG SỐ (HYBRID SCORING ENGINE)
        # Kết hợp chấm điểm Từ khóa (Chính xác) + Điểm Ngữ nghĩa VectorDB (Linh hoạt)
        if ai_data.get('keyword') or ai_data.get('semantic_query'):
            search_kws = set((ai_data.get('keyword') or q).lower().split())
            scored_products = []

            # --- Gọi Vector DB để lấy Danh sách ID phù hợp ngữ nghĩa nhất ---
            semantic_query = ai_data.get('semantic_query') or ai_data.get('keyword') or q
            # Chú ý: Vector Search rất mạnh trong việc hiểu "nhu cầu" (chụp ảnh đẹp, pin trâu)
            semantic_ids = search_vector_db(semantic_query, n_results=10)

            for p in products_pool:
                score = 0
                name_lower = p.name.lower()
                desc_lower = (p.description or "").lower()

                # TÍNH ĐIỂM 1: Keyword Match (Đảm bảo gõ đúng tên máy thì phải lên Top 1)
                match_count = 0
                for kw in search_kws:
                    if kw in name_lower:
                        score += 150  # Khớp tên máy -> Điểm tuyệt đối
                        match_count += 1
                    elif kw in desc_lower:
                        score += 20   # Khớp mô tả -> Điểm phụ

                # Thưởng thêm nếu khớp nguyên cụm từ khóa liên tiếp trong tên
                if ai_data.get('keyword') and ai_data['keyword'].lower() in name_lower:
                    score += 300

                # TÍNH ĐIỂM 2: Vector Semantic Boost (Sức mạnh AI thực sự)
                # Dù không khớp chữ nào, nhưng VectorDB bảo giống -> Vẫn được cộng điểm
                if str(p.id) in semantic_ids:
                    rank = semantic_ids.index(str(p.id))
                    # Top 1 Vector được +100đ, Top 10 được +10đ
                    score += (10 - rank) * 10

                # Đưa vào list nếu có bất kỳ điểm số nào (Từ khóa hoặc Ngữ nghĩa)
                if score > 0:
                    p.match_score = score
                    scored_products.append(p)

            # Sắp xếp theo tổng điểm giảm dần
            scored_products.sort(key=lambda x: x.match_score, reverse=True)
            products = scored_products
        else:
            products = products_pool

    # LỚP FALLBACK (SQL THUẦN) NẾU TÌM KIẾM AI THẤT BẠI
    if not products and q:
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
        # ---> [HOTFIX]: Đồng bộ Stop Words mới cho Chế độ Strict Mode (Test Case 5)
        stop_words_fallback = ['mua', 'tìm', 'giá', 'rẻ', 'cho', 'cần', 'dưới', 'khoảng', 'củ', 'triệu', 'điện',
                               'thoại', 'máy', 'tôi', 'muốn', 'nào', 'tầm', 'quay', 'đầu']
        keywords = [w for w in search_words if w.lower() not in stop_words_fallback]

        if keywords:
            conditions = []
            for word in keywords:
                conditions.append(or_(
                    Product.name.ilike(f"%{word}%"),
                    Product.description.ilike(f"%{word}%")
                ))

            products = fallback_query.filter(or_(*conditions)).all()
            if products:
                ai_msg = "🔍 Tìm kiếm mở rộng (Strict Mode)"

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


# =========================================================================
# ---> [UPGRADED] ROUTE: TÌM KIẾM BẰNG HÌNH ẢNH (VISUAL SEARCH) TỐI ƯU 3 TẦNG
# =========================================================================
@main_bp.route('/search/image', methods=['POST'])
def search_by_image():
    if 'visual_image' not in request.files:
        flash("Chưa có ảnh được chọn.", "warning")
        return redirect(url_for('main.home'))

    file = request.files['visual_image']
    is_valid, msg = validate_image_file(file)
    if not is_valid:
        flash(msg, "danger")
        return redirect(url_for('main.home'))

    # BƯỚC 1: Dùng AI Gemini Đọc và Tách Bạch Cấu Trúc Ảnh
    ai_data = identify_phone_by_gemini(file)
    products = []
    ai_message = ""

    brand = None
    model = None

    # [FIX LỖI CRASH 500]: Ép kiểu an toàn nếu AI trả về List [{...}] thay vì Dict {...}
    if isinstance(ai_data, list):
        ai_data = ai_data[0] if len(ai_data) > 0 else {}

    if ai_data and isinstance(ai_data, dict) and ai_data.get('model'):
        brand = ai_data.get('brand')
        model = str(ai_data.get('model')).strip()
        confidence = int(ai_data.get('confidence', 0))
        # [NEW]: Lấy mảng từ khóa để search linh hoạt
        search_keywords = ai_data.get('search_keywords', [])

        # ---> [GIẢI QUYẾT LỖI TẠI ĐÂY]: ÁP DỤNG NGƯỠNG CẮT (CONFIDENCE THRESHOLD)
        # Nếu AI không tự tin (< 50%), KHÔNG ĐƯỢC tin vào kết quả đoán bừa của nó.
        # Xóa ngay model để ép hệ thống rơi xuống Tầng 3 (Dùng Vector DB ResNet50 quét bằng hình ảnh).
        if confidence < 50:
             flash(f"Ảnh mờ, AI không chắc chắn tên máy (Tự tin: {confidence}%). Hệ thống đang chuyển sang quét hình dáng quang học.", "warning")
             brand = None
             model = None
             search_keywords = []

        # Nếu AI tự tin nó biết chữ (model != None), thì mới đi tìm bằng SQL
        if model:
            base_query = Product.query.filter_by(is_active=True, category='phone')

            # --- [TẦNG 1 MỚI]: TÌM KIẾM LINH HOẠT VỚI LOGIC (AND) ---
            if brand:
                base_query = base_query.filter(Product.brand.ilike(f"%{brand}%"))

            if not search_keywords and model:
                search_keywords = model.split()

            conditions = []
            for kw in search_keywords:
                if brand and kw.lower() == brand.lower(): continue  # Bỏ qua chữ hãng vì đã lọc trên
                if len(kw) == 1 and not kw.isalnum(): continue
                conditions.append(Product.name.ilike(f"%{kw}%"))

            if conditions:
                exact_products_raw = base_query.filter(and_(*conditions)).all()
            else:
                exact_products_raw = []

            strict_products = []
            if exact_products_raw:
                # ---> THUẬT TOÁN FINGERPRINT MATCHING (BAO PHỦ MỌI HÃNG) <---
                model_lower = model.lower() if model else " ".join([k.lower() for k in search_keywords])

                # Danh sách biến thể (Bắt buộc khớp 2 chiều bằng XOR Logic)
                word_modifiers = [
                    'pro', 'max', 'plus', 'ultra', 'ti', 'fe', 'se', 'mini',
                    'fold', 'flip', 'edge', 'lite', 'classic', 'neo', 'narzo',
                    'play', 'active', 'zoom', 'note', 'pad', 'tab', 'gt'
                ]
                strict_modifiers = set(word_modifiers + list('abcdefghijklmnopqrstuvwxyz'))

                for p in exact_products_raw:
                    p_name_lower = p.name.lower()
                    is_valid = True

                    # 1. Đồng bộ dữ liệu đặc thù và loại bỏ hoàn toàn rác RAM/ROM/Mạng
                    p_name_clean = p_name_lower.replace('promax', 'pro max').replace('+', ' plus ')
                    model_clean = model_lower.replace('promax', 'pro max').replace('+', ' plus ')

                    # Quét bay mọi con số liên quan đến dung lượng để tránh làm nhiễu số thế hệ máy
                    storage_pattern = r'\b\d{1,4}\s*(?:gb|tb|mb|g|t)\b|\b(?:5g|4g|ram|rom)\b'
                    p_name_clean = re.sub(storage_pattern, '', p_name_clean)
                    model_clean = re.sub(storage_pattern, '', model_clean)

                    # 2. Tách rời chữ và số CẢ 2 CHIỀU (VD: S24 -> S 24, 13T -> 13 T)
                    db_base = re.sub(r'([a-z])(\d)', r'\1 \2', p_name_clean)
                    db_base = re.sub(r'(\d)([a-z])', r'\1 \2', db_base)

                    ai_base = re.sub(r'([a-z])(\d)', r'\1 \2', model_clean)
                    ai_base = re.sub(r'(\d)([a-z])', r'\1 \2', ai_base)

                    db_tokens = set(db_base.split())
                    ai_tokens = set(ai_base.split())

                    # 3. CHẶN ĐỨNG SAI LỆCH BIẾN THỂ (XOR LOGIC)
                    for mod in strict_modifiers:
                        if (mod in ai_tokens) != (mod in db_tokens):
                            is_valid = False
                            break

                    if not is_valid:
                        continue

                    # 4. KHỚP MÃ SỐ THẾ HỆ (SUBSET MATCH)
                    db_numbers = set(re.findall(r'\b\d+\b', db_base))
                    ai_numbers = set(re.findall(r'\b\d+\b', ai_base))

                    if not ai_numbers.issubset(db_numbers):
                        is_valid = False

                    if is_valid:
                        strict_products.append(p)

            if strict_products:
                # Nếu tìm thấy chính xác bản máy đó trong shop -> Chỉ hiển thị nó!
                products = strict_products
                ai_message = f"🎯 Đã nhận diện: {brand or ''} {model} (Độ tin cậy: {confidence}%). Chỉ hiển thị dòng máy chính xác!"
            else:
                products = []  # Trả về rỗng để giao diện hiển thị "Không tìm thấy"
                price_segment = ai_data.get('price_segment', 'Không xác định')

                ai_message = (
                    f"🎯 Đã nhận diện thiết bị: <b>{brand or ''} {model}</b><br>"
                    f"🏷️ Phân loại AI: <b>{price_segment}</b><br>"
                    f"❌ <b>Kết quả:</b> Rất tiếc, sản phẩm này hiện <b>KHÔNG CÓ</b> sẵn trong cửa hàng của chúng tôi."
                )

    # --- [TẦNG 3]: VISUAL VECTOR FALLBACK CHỈ CHẠY KHI AI MÙ CHỮ, KHÔNG NHẬN DIỆN ĐƯỢC TÊN MÁY ---
    # Nhờ bản vá ở trên (model = None khi tự tin thấp), tầng này nay sẽ được GỌI THÀNH CÔNG cứu vớt người dùng!
    if not products and not model:
        file.seek(0) # Trả con trỏ file về 0
        matched_ids = search_image_vector_db(file, n_results=5)

        if matched_ids:
            ids = [int(i) for i in matched_ids if i.isdigit()]
            shape_similar_products = Product.query.filter(Product.id.in_(ids), Product.is_active == True).all()

            shape_similar_products.sort(key=lambda p: ids.index(p.id) if p.id in ids else 999)

            if brand:
                same_brand_shape = [p for p in shape_similar_products if p.brand and p.brand.lower() == brand.lower()]

                if same_brand_shape:
                    products = same_brand_shape[:4]
                    ai_message = f"📷 AI không nhận diện được tên chuẩn. Đã quét theo BỐ CỤC CAMERA gợi ý {len(products)} thiết bị {brand}."
                else:
                    products = shape_similar_products[:4]
                    ai_message = f"📷 AI không tìm thấy tên chính xác. Gợi ý các máy có CỤM CAMERA / HÌNH DÁNG tương đồng nhất."
            else:
                products = shape_similar_products[:4]
                ai_message = "📷 Không thể nhận diện tên. Đã tự động lọc các máy có cụm camera hoặc mặt lưng giống với ảnh nhất."
        else:
            flash("Ảnh quá mờ hoặc không có thiết bị di động, không thể nhận diện được.", "warning")
            return redirect(url_for('main.home'))

    brands = [b[0] for b in db.session.query(Product.brand).distinct().all()]
    hot_products = Product.query.filter_by(is_active=True, is_sale=True).limit(4).all()

    return render_template(
        'home.html',
        products=products,
        brands=brands,
        search_query="",
        ai_message=ai_message,
        hot_products=hot_products
    )



@main_bp.route('/product/<int:id>')
def product_detail(id):
    """
    Xử lý truy xuất thông tin chi tiết một sản phẩm.
    Tích hợp thuật toán Collaborative Filtering (Gợi ý mua kèm phụ kiện)
    và Content-Based Recommendation (Gợi ý máy tương tự).
    """
    p = Product.query.filter_by(id=id, is_active=True).first_or_404()
    try:
        p.colors_list = json.loads(p.colors) if p.colors else []
        p.versions_list = json.loads(p.versions) if p.versions else []
    except Exception:
        p.colors_list, p.versions_list = [], []

    # 1. Tìm tất cả các OrderID đã từng chứa sản phẩm này (Ngăn lỗi SAWarning của SQLAlchemy)
    related_order_ids_query = db.session.query(OrderDetail.order_id).filter_by(product_id=id)

    # 2. Tìm các sản phẩm Phụ kiện xuất hiện nhiều nhất trong các Giỏ hàng trên
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

    # Fallback: Nếu không có dữ liệu ML, lấy 4 phụ kiện ngẫu nhiên đang Active
    if not recs:
        recs = Product.query.filter(Product.category == 'accessory', Product.is_active == True).limit(4).all()

    # Thuật toán điểm tương đồng (Máy cùng hãng, cùng hạng giá)
    similar_prods = get_similar_products(p, limit=4)

    all_products = Product.query.filter(
        Product.is_active == True,
        Product.category == p.category,
        Product.id != p.id
    ).all()

    # Tách biệt Bình luận Đánh giá (Review) và Hỏi đáp (Q&A)
    comments = Comment.query.options(joinedload(Comment.user)).filter(
        Comment.product_id == id, Comment.parent_id == None, Comment.rating > 0
    ).order_by(Comment.created_at.desc()).all()

    questions = Comment.query.options(joinedload(Comment.user)).filter_by(
        product_id=id, parent_id=None, rating=0
    ).order_by(Comment.created_at.desc()).all()

    # Tính toán Thống kê Đánh giá (Rating Engine)
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

    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = p in current_user.favorites

    return render_template('detail.html', product=p, all_products=all_products, recommendations=recs,
                           similar_products=similar_prods, comments=comments, questions=questions,
                           rating=rating_stats, is_favorited=is_favorited)


@main_bp.route('/product/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    """
    Lưu trữ bình luận, đánh giá hoặc câu hỏi của Khách hàng vào Cơ sở dữ liệu.
    Hỗ trợ luồng trả lời trực tiếp (Nested Reply) cho Admin.
    """
    content = request.form.get('content', '').strip()
    is_question = request.form.get('is_question') == 'true'
    parent_id = request.form.get('parent_id', type=int)

    if is_question or parent_id:
        final_rating = 0  # Câu hỏi/Trả lời không yêu cầu xếp hạng sao
    else:
        rating = request.form.get('rating', default=5, type=int)
        if rating not in [1, 2, 3, 4, 5]:
            rating = 5
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

        # Gọi AI phân tích cảm xúc (Sentiment Analysis) ngầm dưới nền
        if not parent_id and not is_question:
            import threading
            threading.Thread(target=analyze_sentiment, args=(content,), daemon=True).start()

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
    Render giao diện Giỏ hàng (Cart).
    Tính toán tổng tiền dựa trên bộ nhớ đệm Session tạm thời của người dùng.
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
    Cập nhật dữ liệu Sản phẩm vào Giỏ hàng nội bộ (Session Storage).
    Chặn đứng hành vi thêm vào giỏ nếu số lượng yêu cầu vượt quá tồn kho thực tế (Inventory).
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
    Điều chỉnh số lượng (+/-) hoặc xóa hẳn sản phẩm khỏi Giỏ hàng trong Session.
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
            if cart[sid]['quantity'] <= 0:
                del cart[sid]
        elif action == 'delete':
            del cart[sid]
    session['cart'] = cart
    return redirect(url_for('main.view_cart'))


@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """
    Xử lý luồng Đặt hàng an toàn (Checkout Process).
    - Tích hợp động cơ Voucher (Giảm giá trực tiếp vào Hóa đơn).
    - Áp dụng Pessimistic Locking (`with_for_update`) trên SQLAlchemy để khóa Row,
      đảm bảo không bao giờ xảy ra lỗi Bán Lố (Race Condition Overselling).
    """
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('main.home'))

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

            # =====================================================================
            # [SECURITY FIX]: XÁC THỰC LẠI VOUCHER Ở BACKEND TRƯỚC KHI TRỪ TIỀN
            # Ngăn chặn hacker sửa HTML để mua hàng giá 0đ
            # =====================================================================
            voucher_code = request.form.get('voucher_code', '').strip().upper()
            discount_amount = 0

            if voucher_code:
                voucher = Voucher.query.filter_by(code=voucher_code).first()
                if voucher:
                    user_rank_tier, _, _ = _calculate_user_rank(current_user.id)
                    engine = VoucherValidatorEngine()
                    is_valid, _ = engine.validate(voucher, total, user_rank_tier)

                    if is_valid:
                        discount_amount = engine.calculate_discount(voucher, total)

            # Đảm bảo tổng tiền không bao giờ bị âm
            final_total = max(0, total - discount_amount)
            # =====================================================================

            # Locking Database tránh xung đột giao dịch
            for i in final_items:
                prod = db.session.query(Product).filter_by(id=i['p'].id).with_for_update().first()
                if not prod or prod.stock_quantity < i['qty']:
                    flash(f"Sản phẩm {i['p'].name} không đủ hàng.", 'danger')
                    db.session.rollback()
                    return redirect(url_for('main.view_cart'))
                prod.stock_quantity -= i['qty']

            # Tạo đơn hàng với mức giá đã được chiết khấu
            order = Order(
                user_id=current_user.id,
                total_price=final_total,
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
    Kết nối API Cổng thanh toán VietQR.
    Tạo bộ đếm ngược (Countdown) cho các đơn hàng Chuyển khoản, tự động thu hồi
    nếu khách không thanh toán kịp trong 3 phút.
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
    # ---> [FIX LỖI URL CỦA VIETQR]:
    # 1. Mã hóa khoảng trắng để đảm bảo đường dẫn hợp lệ
    # 2. Xóa bỏ cú pháp Markdown rác trong chuỗi f-string bị dính trước đó
    account_name = urllib.parse.quote("MOBILE STORE")
    content = urllib.parse.quote(f"THANHTOAN DONHANG {order.id}")

    qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={order.total_price}&addInfo={content}&accountName={account_name}"

    return render_template('payment_qr.html', order=order, qr_url=qr_url, remaining_seconds=int(remaining_seconds))


@main_bp.route('/api/payment/check/<int:order_id>')
@login_required
def check_payment_status(order_id):
    """
    API hỗ trợ Long-Polling cho giao diện người dùng.
    Liên tục quét Database để xác nhận giao dịch chuyển khoản đã thành công chưa.
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
    Endpoint (Sandbox) giả lập tín hiệu ngân hàng trả về thành công.
    Phục vụ cho các Tester thao tác mà không cần chuyển tiền thực tế.
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
    Cổng tiếp nhận yêu cầu Thu Cũ Đổi Mới.
    Có tích hợp Middleware quét định dạng tệp tải lên để phòng ngừa mã độc.
    """
    if request.method == 'POST':
        if 'image' not in request.files:
            return redirect(request.url)

        file = request.files['image']
        is_valid, msg = validate_image_file(file)
        if not is_valid:
            flash(msg, 'danger')
            return redirect(request.url)

        filename = secure_filename(f"tradein_{current_user.id}_{int(time.time())}.jpg")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        db.session.add(TradeInRequest(
            user_id=current_user.id,
            device_name=request.form.get('device_name'),
            condition=request.form.get('condition'),
            image_proof=f"/static/uploads/{filename}"
        ))
        db.session.commit()
        flash(SystemMessages.TRADEIN_SUCCESS, 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('tradein.html')


@main_bp.route('/order/cancel/<int:id>')
@login_required
def cancel_order_user(id):
    """
    Cho phép Khách hàng tự hủy đơn hàng Pending.
    Bao gồm thủ tục Kế toán ngược: Hoàn trả số lượng hàng bị giam vào Kho chính.
    """
    order = Order.query.options(joinedload(Order.details)).filter_by(id=id, user_id=current_user.id).first_or_404()
    if order.status == ORDER_STATUS_PENDING:
        for d in order.details:
            p = db.session.get(Product, d.product_id)
            if p:
                p.stock_quantity += d.quantity
        order.status = ORDER_STATUS_CANCELLED
        db.session.commit()
        flash(SystemMessages.ORDER_CANCEL_SUCCESS, 'success')
    return redirect(url_for('main.dashboard'))


# =========================================================================
# ---> [NEW: BẢO VỆ ROUTE & ÁP DỤNG HẠN MỨC SỬ DỤNG AI Theo Rank] <---
# =========================================================================
@main_bp.route('/compare', methods=['GET', 'POST'])
@login_required  # <-- Khách phải đăng nhập mới được vào
@csrf.exempt
def compare_page():
    """
    Trung tâm Phân tích Sản phẩm (Đấu trường AI).
    Tự động gọi Google Gemini phân tích đa chiều lên tới 4 thiết bị cùng lúc.
    Sẽ kích hoạt Lõi Logic Local (Local Fallback HTML) nếu AI bị sập hoặc quá tải.
    """
    products = Product.query.filter_by(is_active=True).all()
    res = None
    selected_prods = []

    if request.method == 'POST':
        try:
            # ---> BƯỚC 1: KIỂM TRA VÀ RESET QUOTA THEO NGÀY
            today_date = datetime.now(timezone.utc).date()
            if current_user.last_compare_date != today_date:
                current_user.daily_compare_count = 0
                current_user.last_compare_date = today_date
                db.session.commit()

            # Lấy hạng thẻ (1: M-New, 2: M-Gold, 3: M-Platinum, 4: M-Diamond)
            rank_tier, _, _ = _calculate_user_rank(current_user.id)

            # Cấu hình Quota bảo vệ 4 API Key
            limit_map = {1: 2, 2: 5, 3: 10, 4: 30}
            max_attempts = limit_map.get(rank_tier, 2)

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

                    # ---> BƯỚC 2: QUYẾT ĐỊNH CHO GỌI API TAT ÉP DÙNG LOCAL
                    if current_user.daily_compare_count >= max_attempts:
                        flash(f'Bạn đã dùng hết {max_attempts}/{max_attempts} lượt AI phân tích hôm nay. Hệ thống tự động chuyển sang Bảng Tiêu chuẩn.', 'warning')
                        res = generate_local_comparison_html(p1, p2, p3, p4)
                    else:
                        p1_price_str = "{:,.0f} đ".format(p1.sale_price if p1.is_sale else p1.price).replace(",", ".")
                        p2_price_str = "{:,.0f} đ".format(p2.sale_price if p2.is_sale else p2.price).replace(",", ".")

                        p3_id = p3.id if p3 else None
                        p3_name = p3.name if p3 else None
                        p3_price_str = "{:,.0f} đ".format(p3.sale_price if p3.is_sale else p3.price).replace(",", ".") if p3 else None
                        p3_desc = p3.description or "" if p3 else None
                        p3_img = p3.image_url if p3 else None

                        p4_id = p4.id if p4 else None
                        p4_name = p4.name if p4 else None
                        p4_price_str = "{:,.0f} đ".format(p4.sale_price if p4.is_sale else p4.price).replace(",", ".") if p4 else None
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
                            res = generate_local_comparison_html(p1, p2, p3, p4)
                        else:
                            # Chỉ trừ lượt Quota nếu hệ thống gọi AI thành công!
                            current_user.daily_compare_count += 1
                            db.session.commit()

        except ValueError:
            flash('Dữ liệu sản phẩm không hợp lệ', 'danger')

    return render_template('compare.html', products=products, result=res, selected_prods=selected_prods)


@main_bp.route('/api/toggle-favorite/<int:id>', methods=['POST'])
@login_required
@csrf.exempt
def toggle_favorite_api(id):
    """
    Cung cấp API cho phép Client thêm/xóa Sản phẩm Yêu thích bằng công nghệ AJAX.
    """
    p = Product.query.get_or_404(id)

    if p in current_user.favorites:
        current_user.favorites.remove(p)
        status = 'removed'
    else:
        current_user.favorites.append(p)
        status = 'added'

    db.session.commit()
    return jsonify({'status': status})


@main_bp.route('/api/apply-voucher', methods=['POST'])
@login_required
@csrf.exempt
def apply_voucher_api():
    """
    API Dành cho Khách hàng: Cung cấp mã Voucher đang có để được giảm giá.
    Sẽ đẩy mã Code qua hệ thống VoucherValidatorEngine (Design Pattern: Specification).
    Để bảo mật, hệ thống sẽ tự động tính toán lại Rank của User trực tiếp từ Database.
    """
    code = request.json.get('code', '').strip().upper()
    order_total = request.json.get('total', 0)

    # [SECURITY FIX] Tính toán lại Rank trực tiếp từ DB thay vì nhận từ Frontend
    user_rank_tier, _, _ = _calculate_user_rank(current_user.id)

    if not code:
        return jsonify({'success': False, 'message': 'Vui lòng nhập mã giảm giá!'})

    voucher = Voucher.query.filter_by(code=code).first()
    if not voucher:
        return jsonify({'success': False, 'message': 'Mã giảm giá không tồn tại hoặc sai chính tả.'})

    # Nạp Động cơ Xác thực đa điều kiện
    engine = VoucherValidatorEngine()
    is_valid, message = engine.validate(voucher, order_total, user_rank_tier)

    if not is_valid:
        return jsonify({'success': False, 'message': message})

    # Tính toán con số hoàn hảo
    discount_amount = engine.calculate_discount(voucher, order_total)

    return jsonify({
        'success': True,
        'message': message,
        'discount_amount': discount_amount,
        'new_total': order_total - discount_amount
    })


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Hệ sinh thái thông tin Cá nhân (M-Member Dashboard).
    Hiển thị thông tin Hạng thẻ VIP (RFM Model), Đơn hàng, Lịch sử Thu Cũ và
    kho Voucher do Admin phân phối.
    """
    my_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_created.desc()).all()
    my_tradeins = TradeInRequest.query.filter_by(user_id=current_user.id).order_by(
        TradeInRequest.created_at.desc()).all()

    pending_orders = sum(1 for o in my_orders if o.status == ORDER_STATUS_PENDING)
    total_orders = len(my_orders)

    # Sử dụng chung Helper Logic để đồng bộ với Checkout/Voucher
    rank_tier, rank_name, total_spent = _calculate_user_rank(current_user.id)

    if rank_tier == 4:
        next_rank = "Đã Đạt Cấp Tối Đa"
        needed_for_next = 0
        progress_percent = 100
    elif rank_tier == 3:
        next_rank = "M-Diamond"
        needed_for_next = 50000000 - total_spent
        progress_percent = 75 + ((total_spent - 20000000) / 30000000) * 25
    elif rank_tier == 2:
        next_rank = "M-Platinum"
        needed_for_next = 20000000 - total_spent
        progress_percent = 50 + ((total_spent - 5000000) / 15000000) * 25
    else:
        next_rank = "M-Gold"
        needed_for_next = 5000000 - total_spent
        progress_percent = (total_spent / 5000000) * 25

    member_stats = {
        'total_spent': total_spent,
        'pending_orders': pending_orders,
        'total_orders': total_orders,
        'rank_tier': rank_tier,
        'rank': rank_name,
        'next_rank': next_rank,
        'needed_for_next': needed_for_next,
        'progress_percent': progress_percent
    }

    # Lấy các mã khuyến mãi ĐANG KÍCH HOẠT hiển thị cho Khách hàng lựa chọn
    vouchers = Voucher.query.filter_by(is_active=True).all()

    return render_template('dashboard.html', orders=my_orders, tradeins=my_tradeins, member=member_stats, vouchers=vouchers)


@main_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Cho phép cập nhật thông tin họ tên (và các Profile fields khác)."""
    full_name = request.form.get('full_name')
    if full_name:
        current_user.full_name = full_name
    db.session.commit()
    flash(SystemMessages.PROFILE_UPDATE_SUCCESS, 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/api/chatbot', methods=['POST'])
@csrf.exempt
def chatbot_api():
    """
    Kênh giao tiếp Server-side với Bot AI Tư vấn Bán hàng.
    Bảo toàn ngữ cảnh Session, tránh đứt đoạn hội thoại của người dùng.
    """
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({'response': "Mời bạn hỏi ạ!"})

    try:
        chat_history = session.get('chat_history', [])

        # Giao phó toàn bộ tin nhắn cho hàm generate_chatbot_response
        response = generate_chatbot_response(msg, chat_history)
        final_response = response or SystemMessages.AI_BUSY

        # ---> [ĐÃ SỬA LỖI TẠI ĐÂY] <---
        # Lưu cuộc hội thoại mới vào lịch sử (Chỉ trích xuất 150 ký tự đầu để làm ngữ cảnh)
        # Giúp tiết kiệm cực kỳ nhiều dung lượng bộ nhớ Session Cookie
        short_ai_response = final_response[:150] + "..." if len(final_response) > 150 else final_response
        chat_history.append({'user': msg, 'ai': short_ai_response})

        # GIẢM BỘ NHỚ: Chỉ cho phép bot nhớ 3 câu thay vì 8 câu
        if len(chat_history) > 3:
            chat_history = chat_history[-3:]

        session['chat_history'] = chat_history

        return jsonify({'response': final_response})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({'response': "Lỗi kết nối AI."})