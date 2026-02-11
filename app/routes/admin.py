from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Product, User, Order, TradeInRequest
import json

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
def check_admin():
    if current_user.role != 'admin':
        abort(403)


# --- Dashboard ---
@admin_bp.route('/admin')
def dashboard():
    products = Product.query.order_by(Product.id.desc()).all()
    users = User.query.all()
    orders = Order.query.order_by(Order.date_created.desc()).all()
    tradeins = TradeInRequest.query.order_by(TradeInRequest.created_at.desc()).all()
    return render_template('admin_dashboard.html', products=products, users=users, orders=orders, tradeins=tradeins)


# --- Xử Lý Trạng Thái Đơn Hàng ---
@admin_bp.route('/admin/order/update/<int:id>/<status>')
def update_order_status(id, status):
    order = Order.query.get_or_404(id)
    old_status = order.status
    valid_statuses = ['Pending', 'Confirmed', 'Shipping', 'Completed', 'Cancelled']

    if status not in valid_statuses:
        flash('Trạng thái không hợp lệ.', 'danger')
        return redirect(url_for('admin.dashboard'))

    if old_status in ['Completed', 'Cancelled']:
        flash('Đơn hàng đã kết thúc, không thể thay đổi.', 'warning')
        return redirect(url_for('admin.dashboard'))

    # LOGIC HOÀN KHO: Nếu đơn bị hủy, cộng lại tồn kho cho sản phẩm
    if status == 'Cancelled' and old_status != 'Cancelled':
        for detail in order.details:
            product = Product.query.get(detail.product_id)
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
        name = request.form.get('name')
        brand = request.form.get('brand')
        price = int(request.form.get('price', 0))
        desc = request.form.get('description')
        img = request.form.get('image_url')
        cat = request.form.get('category', 'phone')
        is_sale = 'is_sale' in request.form
        sale_price = int(request.form.get('sale_price') or 0)
        is_active = 'is_active' in request.form

        # [FIX] Đảm bảo lấy stock_quantity từ form chính xác
        stock = int(request.form.get('stock_quantity', 10))

        new_product = Product(
            name=name, brand=brand, price=price, description=desc,
            image_url=img, category=cat, is_sale=is_sale, sale_price=sale_price,
            is_active=is_active, stock_quantity=stock
        )

        db.session.add(new_product)
        db.session.commit()
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
            product.price = int(request.form.get('price', 0))
            product.description = request.form.get('description')
            product.image_url = request.form.get('image_url')
            product.is_sale = 'is_sale' in request.form
            product.sale_price = int(request.form.get('sale_price') or 0)
            product.is_active = 'is_active' in request.form

            # [FIX] Cập nhật tồn kho từ form
            stock_val = request.form.get('stock_quantity')
            if stock_val is not None:
                product.stock_quantity = int(stock_val)

            # Cập nhật biến thể JSON
            colors_json = request.form.get('colors_json')
            versions_json = request.form.get('versions_json')
            if colors_json: product.colors = colors_json
            if versions_json: product.versions = versions_json

            db.session.commit()
            flash('Cập nhật thông tin và tồn kho thành công!', 'success')
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
    price = request.form.get('valuation_price', 0)
    note = request.form.get('admin_note', '')

    req = TradeInRequest.query.get_or_404(req_id)
    if action == 'approve':
        req.status = 'Approved'
        req.valuation_price = int(price)
        req.admin_note = note or "Đã định giá."
    elif action == 'reject':
        req.status = 'Rejected'
        req.admin_note = note or "Không đạt yêu cầu."

    db.session.commit()
    flash('Đã xử lý yêu cầu thu cũ.', 'success')
    return redirect(url_for('admin.dashboard'))