from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Product, User, Order
import json

admin_bp = Blueprint('admin', __name__)


# --- Middleware: Kiểm tra quyền Admin ---
@admin_bp.before_request
@login_required
def check_admin():
    """Chặn truy cập nếu không phải Admin"""
    if current_user.role != 'admin':
        abort(403)  # Trả về lỗi Forbidden


# --- Dashboard ---
@admin_bp.route('/admin')
def dashboard():
    products = Product.query.all()
    users = User.query.all()
    orders = Order.query.all()
    return render_template('admin_dashboard.html', products=products, users=users, orders=orders)


# --- Thêm Sản Phẩm ---
@admin_bp.route('/admin/product/add', methods=['POST'])
def add_product():
    # Lấy dữ liệu từ Form
    name = request.form.get('name')
    brand = request.form.get('brand')
    price = request.form.get('price')
    desc = request.form.get('description')
    img = request.form.get('image_url')
    cat = request.form.get('category', 'phone')
    is_sale = bool(request.form.get('is_sale'))
    sale_price = request.form.get('sale_price') or 0

    new_product = Product(
        name=name, brand=brand, price=price, description=desc,
        image_url=img, category=cat, is_sale=is_sale, sale_price=sale_price
    )

    db.session.add(new_product)
    db.session.commit()
    flash('Thêm sản phẩm thành công!', 'success')
    return redirect(url_for('admin.dashboard'))


# --- Xóa Sản Phẩm ---
@admin_bp.route('/admin/product/delete/<int:id>')
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Đã xóa sản phẩm.', 'success')
    return redirect(url_for('admin.dashboard'))


# --- Sửa Sản Phẩm (Bao gồm Biến thể) ---
@admin_bp.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    product = Product.query.get_or_404(id)

    if request.method == 'POST':
        # Cập nhật thông tin cơ bản
        product.name = request.form.get('name')
        product.brand = request.form.get('brand')
        product.price = request.form.get('price')
        product.description = request.form.get('description')
        product.image_url = request.form.get('image_url')
        product.is_sale = 'is_sale' in request.form
        product.sale_price = request.form.get('sale_price')

        # [QUAN TRỌNG] Lưu cấu hình biến thể (JSON String)
        # Dữ liệu này được gửi từ Javascript ở trang admin_edit.html
        colors_json = request.form.get('colors_json')
        versions_json = request.form.get('versions_json')

        if colors_json: product.colors = colors_json
        if versions_json: product.versions = versions_json

        db.session.commit()
        flash('Cập nhật thành công!', 'success')
        return redirect(url_for('admin.dashboard'))

    # Chuẩn bị dữ liệu để hiển thị lên Form
    # Giải mã JSON thành List để Jinja2 render dễ dàng
    colors_list = []
    versions_list = []

    if product.colors:
        try:
            colors_list = json.loads(product.colors)
        except:
            colors_list = []

    if product.versions:
        try:
            versions_list = json.loads(product.versions)
        except:
            versions_list = []

    return render_template('admin_edit.html', product=product, colors_list=colors_list, versions_list=versions_list)