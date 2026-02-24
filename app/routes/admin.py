from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.extensions import db

from app.models import Product, User, Order, TradeInRequest, OrderDetail, Comment
import json
from app.utils import sync_product_to_vector_db

import pandas as pd
import io

# ---> [NEW] IMPORT HẰNG SỐ HỆ THỐNG <---
from app.constants import (
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CANCELLED,
    VALID_ORDER_STATUSES,
    TRADEIN_STATUS_APPROVED,
    TRADEIN_STATUS_REJECTED,
    SystemMessages
)

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
def check_admin():
    """
    Middleware kiểm tra quyền quản trị viên.
    Sẽ tự động chặn (abort 403) nếu người dùng hiện tại không phải là admin.
    """
    if current_user.role != 'admin':
        abort(403)


@admin_bp.route('/admin')
def dashboard():
    """
    Trang tổng quan (Dashboard) của Quản trị viên.
    Hiển thị biểu đồ doanh thu, thống kê đơn hàng, phân tích người dùng,
    và các thuật toán tìm ra khung giờ vàng chốt đơn (Sử dụng Pandas).
    """
    products = Product.query.order_by(Product.id.desc()).all()
    users = User.query.all()
    orders = Order.query.options(joinedload(Order.user)).order_by(Order.date_created.desc()).all()
    tradeins = TradeInRequest.query.options(joinedload(TradeInRequest.user)).order_by(
        TradeInRequest.created_at.desc()).all()

    comments = Comment.query.options(joinedload(Comment.user), joinedload(Comment.product)).order_by(
        Comment.created_at.desc()).all()

    # Sử dụng Hằng số thay vì text cứng 'Completed'
    total_revenue = db.session.query(func.sum(Order.total_price)).filter(Order.status == ORDER_STATUS_COMPLETED).scalar() or 0

    total_orders_count = Order.query.count()
    total_products_count = Product.query.count()
    total_users_count = User.query.count()

    status_stats = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    status_data = {stat[0]: stat[1] for stat in status_stats}

    seven_days_ago = datetime.now() - timedelta(days=6)
    revenue_chart_query = db.session.query(
        func.date(Order.date_created),
        func.sum(Order.total_price)
    ).filter(
        Order.status == ORDER_STATUS_COMPLETED,
        Order.date_created >= seven_days_ago
    ).group_by(func.date(Order.date_created)).all()

    chart_dates = []
    chart_revenues = []
    rev_map = {str(r[0]): r[1] for r in revenue_chart_query}

    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        d_str = d.strftime('%Y-%m-%d')
        chart_dates.append(d.strftime('%d/%m'))
        total = 0
        for key, val in rev_map.items():
            if str(key).startswith(d_str):
                total = val
                break
        chart_revenues.append(total)

    top_products = db.session.query(
        OrderDetail.product_name,
        func.sum(OrderDetail.quantity).label('total_qty')
    ).join(Order).filter(Order.status == ORDER_STATUS_COMPLETED).group_by(OrderDetail.product_name).order_by(
        desc('total_qty')).limit(5).all()

    best_month_product = "Chưa có dữ liệu"
    peak_hour = "Chưa có dữ liệu"

    completed_orders = db.session.query(
        Order.id, Order.date_created, OrderDetail.product_name, OrderDetail.quantity
    ).join(OrderDetail).filter(Order.status == ORDER_STATUS_COMPLETED).all()

    if completed_orders:
        df = pd.DataFrame(completed_orders, columns=['order_id', 'date_created', 'product_name', 'quantity'])
        df['date_created'] = pd.to_datetime(df['date_created'])

        df['hour'] = df['date_created'].dt.hour
        if not df['hour'].empty:
            peak_hour_val = df['hour'].mode()[0]
            peak_hour = f"{peak_hour_val}:00 - {peak_hour_val + 1}:00"

        current_month = datetime.now().month
        current_year = datetime.now().year

        this_month_df = df[
            (df['date_created'].dt.month == current_month) & (df['date_created'].dt.year == current_year)]

        if not this_month_df.empty:
            top_product_series = this_month_df.groupby('product_name')['quantity'].sum().sort_values(ascending=False)
            if not top_product_series.empty:
                best_month_product = f"{top_product_series.index[0]} ({top_product_series.iloc[0]} máy)"

    return render_template(
        'admin_dashboard.html',
        products=products,
        users=users,
        orders=orders,
        tradeins=tradeins,
        comments=comments,
        total_revenue=total_revenue,
        total_orders_count=total_orders_count,
        total_products_count=total_products_count,
        total_users_count=total_users_count,
        status_data=status_data,
        chart_dates=json.dumps(chart_dates),
        chart_revenues=json.dumps(chart_revenues),
        top_products=top_products,
        best_month_product=best_month_product,
        peak_hour=peak_hour
    )


@admin_bp.route('/admin/export/report')
@login_required
def export_revenue_report():
    """
    Xuất báo cáo doanh thu dưới dạng file Excel (.xlsx).
    Sử dụng thư viện Pandas và Openpyxl để định dạng tiền tệ và độ rộng cột tự động.
    """
    if current_user.role != 'admin':
        abort(403)

    orders = db.session.query(
        Order.id, Order.date_created, Order.total_price, Order.payment_method, Order.status,
        User.full_name, User.username
    ).outerjoin(User, Order.user_id == User.id).filter(Order.status == ORDER_STATUS_COMPLETED).order_by(
        Order.date_created.desc()).all()

    if not orders:
        flash("Chưa có đơn hàng nào hoàn thành để xuất báo cáo.", "warning")
        return redirect(url_for('admin.dashboard'))

    df = pd.DataFrame(orders,
                      columns=['Mã Đơn', 'Ngày Đặt', 'Tổng Tiền', 'Thanh Toán', 'Trạng Thái', 'Tên Khách', 'Username'])

    df['Khách Hàng'] = df['Tên Khách'].combine_first(df['Username'])
    df = df.drop(columns=['Tên Khách', 'Username'])
    df['Ngày Đặt'] = pd.to_datetime(df['Ngày Đặt']).dt.strftime('%d/%m/%Y %H:%M')
    df = df[['Mã Đơn', 'Khách Hàng', 'Ngày Đặt', 'Thanh Toán', 'Tổng Tiền', 'Trạng Thái']]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Báo Cáo Doanh Thu', index=False)
        worksheet = writer.sheets['Báo Cáo Doanh Thu']
        for row in range(2, len(df) + 2):
            cell = worksheet.cell(row=row, column=5)
            cell.number_format = '#,##0 "VNĐ"'

        for col in worksheet.columns:
            max_length = 0
            column_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 3)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    output.seek(0)
    timestamp = datetime.now().strftime("%d%m%Y_%H%M")
    filename = f"Bao_Cao_Doanh_Thu_Thang_{datetime.now().month}_{timestamp}.xlsx"

    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@admin_bp.route('/admin/order/update/<int:id>/<status>')
def update_order_status(id, status):
    """
    Cập nhật trạng thái của đơn hàng.
    Nếu chuyển từ trạng thái khác sang Đã Hủy (Cancelled), hệ thống sẽ tự động hoàn trả số lượng sản phẩm lại vào kho.
    """
    order = Order.query.options(joinedload(Order.details)).get_or_404(id)
    old_status = order.status
    valid_statuses = VALID_ORDER_STATUSES

    if status not in valid_statuses:
        flash(SystemMessages.INVALID_STATUS, 'danger')
        return redirect(url_for('admin.dashboard'))

    if old_status in [ORDER_STATUS_COMPLETED, ORDER_STATUS_CANCELLED]:
        flash(SystemMessages.ORDER_ENDED, 'warning')
        return redirect(url_for('admin.dashboard'))

    if status == ORDER_STATUS_CANCELLED and old_status != ORDER_STATUS_CANCELLED:
        for detail in order.details:
            product = db.session.get(Product, detail.product_id)
            if product:
                product.stock_quantity += detail.quantity
        flash(SystemMessages.ORDER_REFUNDED, 'info')

    order.status = status
    db.session.commit()
    flash(f'Cập nhật đơn hàng thành công: {status}', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/product/add', methods=['POST'])
def add_product():
    """
    Thêm mới một sản phẩm vào hệ thống.
    Ghi nhận dữ liệu vào CSDL SQLite và đồng thời đồng bộ hóa Vector Embeddings lên ChromaDB.
    """
    try:
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

        sync_product_to_vector_db(new_product)

        flash(f'{SystemMessages.PRODUCT_ADD_SUCCESS} ({name})', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi thêm sản phẩm: {str(e)}', 'danger')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    """
    Chỉnh sửa thông tin của một sản phẩm đã có.
    Hỗ trợ chỉnh sửa thông tin JSON (Colors, Versions) và tự động đồng bộ lại Vector Search.
    """
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

            colors_json = request.form.get('colors_json')
            versions_json = request.form.get('versions_json')
            if colors_json: product.colors = colors_json
            if versions_json: product.versions = versions_json

            db.session.commit()
            sync_product_to_vector_db(product)

            flash(SystemMessages.PRODUCT_UPDATE_SUCCESS, 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

    colors_list = json.loads(product.colors) if product.colors else []
    versions_list = json.loads(product.versions) if product.versions else []

    return render_template('admin_edit.html', product=product, colors_list=colors_list, versions_list=versions_list)


@admin_bp.route('/admin/product/delete/<int:id>')
def delete_product(id):
    """
    Xóa vĩnh viễn một sản phẩm khỏi CSDL.
    Các bình luận liên kết sẽ tự động bị xóa theo tính năng Cascade Delete-Orphan.
    """
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash(SystemMessages.PRODUCT_DELETE_SUCCESS, 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/tradein/update', methods=['POST'])
def update_tradein():
    """
    Cập nhật trạng thái của yêu cầu Thu cũ Đổi mới.
    Cho phép Admin định giá máy cũ hoặc từ chối kèm theo ghi chú công khai cho người dùng.
    """
    req_id = request.form.get('id')
    action = request.form.get('action')
    price = request.form.get('valuation_price', default=0, type=int)
    note = request.form.get('admin_note', '').strip()

    req = TradeInRequest.query.get_or_404(req_id)
    if action == 'approve':
        req.status = TRADEIN_STATUS_APPROVED
        req.valuation_price = price
        req.admin_note = note or "Đã định giá."
    elif action == 'reject':
        req.status = TRADEIN_STATUS_REJECTED
        req.admin_note = note or "Không đạt yêu cầu."

    db.session.commit()
    flash(SystemMessages.TRADEIN_PROCESSED, 'success')
    return redirect(url_for('admin.dashboard'))