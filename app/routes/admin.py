from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc # [NEW] Import func để tính tổng, desc để sắp xếp
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Product, User, Order, TradeInRequest, OrderDetail
import json
from app.utils import sync_product_to_vector_db

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def check_admin():
    if current_user.role != 'admin':
        abort(403)

# --- Dashboard & Analytics ---
@admin_bp.route('/admin')
def dashboard():
    # 1. Dữ liệu cơ bản (Giữ nguyên logic cũ)
    products = Product.query.order_by(Product.id.desc()).all()
    users = User.query.all()
    orders = Order.query.options(joinedload(Order.user)).order_by(Order.date_created.desc()).all()
    tradeins = TradeInRequest.query.options(joinedload(TradeInRequest.user)).order_by(TradeInRequest.created_at.desc()).all()

    # 2. [NEW] THỐNG KÊ DOANH THU (Chỉ tính đơn Completed)
    total_revenue = db.session.query(func.sum(Order.total_price)).filter(Order.status == 'Completed').scalar() or 0
    
    # 3. [NEW] THỐNG KÊ ĐƠN HÀNG THEO TRẠNG THÁI (Cho biểu đồ tròn)
    # Kết quả trả về dạng: [('Pending', 5), ('Completed', 10), ...]
    status_stats = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    status_data = {stat[0]: stat[1] for stat in status_stats} # Chuyển về Dictionary

    # 4. [NEW] DOANH THU 7 NGÀY GẦN NHẤT (Cho biểu đồ đường)
    # Logic: Lấy đơn Completed trong 7 ngày qua, group theo ngày
    seven_days_ago = datetime.now() - timedelta(days=6)
    revenue_chart_query = db.session.query(
        func.date(Order.date_created), 
        func.sum(Order.total_price)
    ).filter(
        Order.status == 'Completed',
        Order.date_created >= seven_days_ago
    ).group_by(func.date(Order.date_created)).all()

    # Xử lý dữ liệu để vẽ biểu đồ (lấp đầy những ngày doanh thu = 0)
    chart_dates = []
    chart_revenues = []
    # Tạo map doanh thu từ query
    rev_map = {str(r[0]): r[1] for r in revenue_chart_query}
    
    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        d_str = d.strftime('%Y-%m-%d') # Format YYYY-MM-DD khớp với SQLite
        chart_dates.append(d.strftime('%d/%m')) # Label hiển thị: 15/02
        # SQLite trả về chuỗi ngày, cần so sánh khéo léo hoặc dùng python loop nếu DB nhỏ
        # Ở đây ta dùng logic đơn giản:
        total = 0
        for key, val in rev_map.items():
            if str(key).startswith(d_str): # Match ngày
                total = val
                break
        chart_revenues.append(total)

    # 5. [NEW] TOP 5 SẢN PHẨM BÁN CHẠY
    top_products = db.session.query(
        OrderDetail.product_name, 
        func.sum(OrderDetail.quantity).label('total_qty')
    ).join(Order).filter(Order.status == 'Completed').group_by(OrderDetail.product_name).order_by(desc('total_qty')).limit(5).all()

    return render_template(
        'admin_dashboard.html',
        products=products,
        users=users,
        orders=orders,
        tradeins=tradeins,
        total_revenue=total_revenue,
        status_data=status_data,
        chart_dates=json.dumps(chart_dates),
        chart_revenues=json.dumps(chart_revenues),
        top_products=top_products
    )


# --- Xử Lý Trạng Thái Đơn Hàng ---
@admin_bp.route('/admin/order/update/<int:id>/<status>')
def update_order_status(id, status):
    order = Order.query.options(joinedload(Order.details)).get_or_404(id)
    old_status = order.status
    valid_statuses = ['Pending', 'Confirmed', 'Shipping', 'Completed', 'Cancelled']

    if status not in valid_statuses:
        flash('Trạng thái không hợp lệ.', 'danger')
        return redirect(url_for('admin.dashboard'))

    if old_status in ['Completed', 'Cancelled']:
        flash('Đơn hàng đã kết thúc, không thể thay đổi.', 'warning')
        return redirect(url_for('admin.dashboard'))

    # LOGIC HOÀN KHO an toàn
    if status == 'Cancelled' and old_status != 'Cancelled':
        for detail in order.details:
            product = db.session.get(Product, detail.product_id)
            if product:
                product.stock_quantity += detail.quantity
        flash('Đã hủy đơn và hoàn trả số lượng về kho.', 'info')

    order.status = status
    db.session.commit()
    flash(f'Cập nhật đơn hàng thành công: {status}', 'success')
    return redirect(url_for('admin.dashboard'))


# --- Thêm Sản Phẩm ---
@admin_bp.route('/admin/product/add', methods=['POST'])
def add_product():
    try:
        # [FIX] Dùng type=int của Flask để tránh lỗi Crash Web (ValueError) khi Form rỗng
        name = request.form.get('name')
        brand = request.form.get('brand')
        price = request.form.get('price', default=0, type=int)
        desc = request.form.get('description')
        img = request.form.get('image_url')
        cat = request.form.get('category', 'phone')
        is_sale = 'is_sale' in request.form
        sale_price = request.form.get('sale_price', default=0, type=int)
        is_active = 'is_active' in request.form
        stock = request.form.get('stock_quantity', default=10, type=int)

        new_product = Product(
            name=name, brand=brand, price=price, description=desc,
            image_url=img, category=cat, is_sale=is_sale, sale_price=sale_price,
            is_active=is_active, stock_quantity=stock
        )

        db.session.add(new_product)
        db.session.commit()

        # [NEW] Đồng bộ ngay sang Vector DB
        sync_product_to_vector_db(new_product)

        flash(f'Thêm sản phẩm {name} thành công!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi thêm sản phẩm: {str(e)}', 'danger')

    return redirect(url_for('admin.dashboard'))


# --- Chỉnh Sửa Sản Phẩm ---
@admin_bp.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    product = Product.query.get_or_404(id)

    if request.method == 'POST':
        try:
            product.name = request.form.get('name')
            product.brand = request.form.get('brand')
            product.price = request.form.get('price', default=0, type=int)
            product.description = request.form.get('description')
            product.image_url = request.form.get('image_url')
            product.is_sale = 'is_sale' in request.form
            product.sale_price = request.form.get('sale_price', default=0, type=int)
            product.is_active = 'is_active' in request.form

            stock_val = request.form.get('stock_quantity', type=int)
            if stock_val is not None:
                product.stock_quantity = stock_val

            # Cập nhật biến thể JSON
            colors_json = request.form.get('colors_json')
            versions_json = request.form.get('versions_json')
            if colors_json: product.colors = colors_json
            if versions_json: product.versions = versions_json

            db.session.commit()

            # [NEW] Cập nhật lại Vector DB sau khi sửa
            sync_product_to_vector_db(product)

            flash('Cập nhật thông tin thành công!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

    colors_list = json.loads(product.colors) if product.colors else []
    versions_list = json.loads(product.versions) if product.versions else []

    return render_template('admin_edit.html', product=product, colors_list=colors_list, versions_list=versions_list)


@admin_bp.route('/admin/product/delete/<int:id>')
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Đã xóa sản phẩm khỏi hệ thống.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/tradein/update', methods=['POST'])
def update_tradein():
    req_id = request.form.get('id')
    action = request.form.get('action')
    price = request.form.get('valuation_price', default=0, type=int)
    note = request.form.get('admin_note', '').strip()

    req = TradeInRequest.query.get_or_404(req_id)
    if action == 'approve':
        req.status = 'Approved'
        req.valuation_price = price
        req.admin_note = note or "Đã định giá."
    elif action == 'reject':
        req.status = 'Rejected'
        req.admin_note = note or "Không đạt yêu cầu."

    db.session.commit()
    flash('Đã xử lý yêu cầu thu cũ.', 'success')
    return redirect(url_for('admin.dashboard'))