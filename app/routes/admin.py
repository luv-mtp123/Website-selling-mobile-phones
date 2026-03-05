"""
Module Controller dành riêng cho Quản trị viên (Admin).
Chứa toàn bộ nghiệp vụ quản lý hệ thống: Xem báo cáo Data Science, Quản lý kho hàng,
Duyệt thu cũ đổi mới, Kiểm duyệt bình luận và Quản lý/Phát hành các chiến dịch Voucher.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import json
import pandas as pd
import io

# Import Extensions & Models
from app.extensions import db
from app.models import Product, User, Order, TradeInRequest, OrderDetail, Comment, Voucher

# Import Lõi tiện ích
from app.utils import sync_product_to_vector_db, sync_product_image_to_vector_db # ---> [NEW]

# Import Hằng số hệ thống
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
    Middleware bức tường lửa (Firewall) cục bộ cho Admin Blueprint.
    Tự động chặn (abort 403) nếu phát hiện request đến từ người dùng không phải Quản trị viên.
    """
    if current_user.role != 'admin':
        abort(403)


@admin_bp.route('/admin')
def dashboard():
    """
    Trang tổng quan (Dashboard) hệ thống điều hành của Quản trị viên.
    Thực hiện hàng loạt truy vấn phức tạp để render biểu đồ doanh thu, thống kê đơn hàng,
    phân tích người dùng, quản lý Voucher và trích xuất Insight bằng Pandas.
    """
    products = Product.query.order_by(Product.id.desc()).all()
    users = User.query.all()
    orders = Order.query.options(joinedload(Order.user)).order_by(Order.date_created.desc()).all()
    tradeins = TradeInRequest.query.options(joinedload(TradeInRequest.user)).order_by(
        TradeInRequest.created_at.desc()).all()
    comments = Comment.query.options(joinedload(Comment.user), joinedload(Comment.product)).order_by(
        Comment.created_at.desc()).all()

    # Lấy toàn bộ Voucher để Admin quản lý (Bao gồm cả mã đang khóa)
    vouchers = Voucher.query.order_by(Voucher.id.desc()).all()

    total_revenue = db.session.query(func.sum(Order.total_price)).filter(
        Order.status == ORDER_STATUS_COMPLETED).scalar() or 0
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
        chart_revenues.append(rev_map.get(d_str, 0))

    top_products = db.session.query(
        OrderDetail.product_name,
        func.sum(OrderDetail.quantity).label('total_qty')
    ).join(Order).filter(Order.status == ORDER_STATUS_COMPLETED).group_by(OrderDetail.product_name).order_by(
        desc('total_qty')).limit(5).all()

    # Phân tích Data Science lấy Insight từ Dữ liệu Lớn bằng Pandas
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
        products=products, users=users, orders=orders, tradeins=tradeins, comments=comments,
        vouchers=vouchers,
        total_revenue=total_revenue, total_orders_count=total_orders_count,
        total_products_count=total_products_count, total_users_count=total_users_count,
        status_data=status_data, chart_dates=json.dumps(chart_dates), chart_revenues=json.dumps(chart_revenues),
        top_products=top_products, best_month_product=best_month_product, peak_hour=peak_hour
    )


@admin_bp.route('/admin/export/report')
@login_required
def export_revenue_report():
    """
    Trích xuất Báo cáo Doanh thu định dạng Excel (.xlsx).
    Sử dụng Pandas và Openpyxl xử lý trong bộ nhớ đệm In-Memory (BytesIO)
    giúp không bị nghẽn ổ cứng, format cột tự động.
    """
    orders = db.session.query(
        Order.id, Order.date_created, Order.total_price, Order.payment_method, Order.status,
        User.full_name, User.username
    ).outerjoin(User, Order.user_id == User.id).filter(Order.status == ORDER_STATUS_COMPLETED).order_by(
        Order.date_created.desc()).all()

    if not orders:
        flash("Chưa có đơn hàng nào hoàn thành.", "warning")
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
            worksheet.cell(row=row, column=5).number_format = '#,##0 "VNĐ"'
        for col in worksheet.columns:
            max_length = max((len(str(cell.value)) for cell in col), default=0)
            worksheet.column_dimensions[col[0].column_letter].width = (max_length + 3)

    output.seek(0)
    filename = f"Bao_Cao_Doanh_Thu_Thang_{datetime.now().month}_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@admin_bp.route('/admin/order/update/<int:id>/<status>')
def update_order_status(id, status):
    """
    Quy trình cập nhật trạng thái vòng đời của Đơn hàng.
    Có chứa cơ chế phòng ngự (Safeguard) tự động hoàn trả số lượng lại kho
    nếu Admin thao tác chuyển đơn hàng về trạng thái Hủy.
    """
    order = Order.query.options(joinedload(Order.details)).get_or_404(id)
    old_status = order.status

    if status not in VALID_ORDER_STATUSES:
        flash(SystemMessages.INVALID_STATUS, 'danger')
        return redirect(url_for('admin.dashboard'))

    if old_status in [ORDER_STATUS_COMPLETED, ORDER_STATUS_CANCELLED]:
        flash(SystemMessages.ORDER_ENDED, 'warning')
        return redirect(url_for('admin.dashboard'))

    if status == ORDER_STATUS_CANCELLED and old_status != ORDER_STATUS_CANCELLED:
        for detail in order.details:
            product = db.session.get(Product, detail.product_id)
            if product: product.stock_quantity += detail.quantity
        flash(SystemMessages.ORDER_REFUNDED, 'info')

    order.status = status
    db.session.commit()
    flash(f'Cập nhật thành công: {status}', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/product/add', methods=['POST'])
def add_product():
    """
    Nghiệp vụ thêm mới Sản phẩm vào kho hàng.
    Sau khi lưu vào Relational DB, hệ thống tự kích hoạt Trigger
    đồng bộ hóa Vector DB để cập nhật bộ não AI ngay lập tức.
    """
    try:
        new_p = Product(
            name=request.form.get('name'), brand=request.form.get('brand'),
            price=request.form.get('price', default=0, type=int),
            description=request.form.get('description'), image_url=request.form.get('image_url'),
            category=request.form.get('category', 'phone'),
            is_sale='is_sale' in request.form,
            sale_price=request.form.get('sale_price', default=0, type=int),
            is_active='is_active' in request.form,
            stock_quantity=request.form.get('stock_quantity', default=10, type=int)
        )
        db.session.add(new_p)
        db.session.commit()
        sync_product_to_vector_db(new_p)
        sync_product_image_to_vector_db(new_p)  # ---> [NEW] Cập nhật Vector Ảnh
        flash(SystemMessages.PRODUCT_ADD_SUCCESS, 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi thêm sản phẩm: {e}', 'danger')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    """
    Chỉnh sửa thông tin, giá, thuộc tính của một sản phẩm.
    Hỗ trợ xử lý JSON mảng cho màu sắc/phiên bản động.
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
            sync_product_image_to_vector_db(product)  # ---> [NEW] Cập nhật Vector Ảnh

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
    Nghiệp vụ xóa vĩnh viễn Sản phẩm.
    Sẽ kích hoạt xóa theo chuỗi (Cascade Delete) loại bỏ toàn bộ Comment liên đới.
    """
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash(SystemMessages.PRODUCT_DELETE_SUCCESS, 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/tradein/update', methods=['POST'])
def update_tradein():
    """
    Phê duyệt hoặc Từ chối yêu cầu Thu cũ lên đời (Trade-in) từ Khách hàng.
    Cập nhật giá thẩm định và lưu trữ phản hồi của chuyên viên.
    """
    req_id = request.form.get('id')
    action = request.form.get('action')
    price = request.form.get('valuation_price', default=0, type=int)
    note = request.form.get('admin_note', '').strip()

    req = TradeInRequest.query.get_or_404(req_id)
    if action == 'approve':
        req.status = TRADEIN_STATUS_APPROVED
        req.valuation_price = price
    elif action == 'reject':
        req.status = TRADEIN_STATUS_REJECTED

    req.admin_note = note or "Đã xử lý."
    db.session.commit()
    flash(SystemMessages.TRADEIN_PROCESSED, 'success')
    return redirect(url_for('admin.dashboard'))


# =========================================================================
# BỘ API QUẢN LÝ ĐỘNG CƠ KHUYẾN MÃI (VOUCHER RULE ENGINE)
# =========================================================================

@admin_bp.route('/admin/voucher/add', methods=['POST'])
def add_voucher():
    """
    Nghiệp vụ: Tạo Chiến dịch Khuyến mãi (Voucher) mới.
    Admin nạp đầu vào từ form HTML, hệ thống lưu trữ vào CSDL với các quy tắc
    chặt chẽ để khách hàng có thể săn mã và áp dụng.
    """
    try:
        code = request.form.get('code', '').strip().upper()
        if Voucher.query.filter_by(code=code).first():
            flash(f'Mã Voucher {code} đã tồn tại!', 'danger')
            return redirect(url_for('admin.dashboard'))

        valid_to_str = request.form.get('valid_to')
        valid_to_date = datetime.strptime(valid_to_str, '%Y-%m-%dT%H:%M') if valid_to_str else (
                    datetime.now() + timedelta(days=30))

        new_voucher = Voucher(
            code=code,
            discount_type=request.form.get('discount_type', 'percent'),
            discount_value=request.form.get('discount_value', type=int),
            max_discount=request.form.get('max_discount', type=int) or None,
            min_order_value=request.form.get('min_order_value', type=int, default=0),
            valid_to=valid_to_date,
            required_rank=request.form.get('required_rank', type=int, default=1),
            description=request.form.get('description', ''),
            icon=request.form.get('icon', 'fas fa-ticket-alt'),
            color_theme=request.form.get('color_theme', 'danger'),
            is_active=True
        )
        db.session.add(new_voucher)
        db.session.commit()
        flash(f'Phát hành thành công mã giảm giá: {code}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi tạo Voucher: {str(e)}', 'danger')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/voucher/toggle/<int:id>')
def toggle_voucher(id):
    """
    Nghiệp vụ: Tạm khóa hoặc Mở khóa lại một mã giảm giá khẩn cấp.
    Đóng vai trò như công tắc An toàn khi mã bị tuồn ra ngoài sai quy định.
    """
    voucher = Voucher.query.get_or_404(id)
    voucher.is_active = not voucher.is_active
    db.session.commit()
    status_msg = "Mở khóa" if voucher.is_active else "Đã khóa"
    flash(f'{status_msg} mã Voucher {voucher.code} thành công!', 'info')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/voucher/delete/<int:id>')
def delete_voucher(id):
    """
    Nghiệp vụ: Thu hồi (Xóa vĩnh viễn) mã giảm giá khỏi hệ thống.
    """
    voucher = Voucher.query.get_or_404(id)
    code = voucher.code
    db.session.delete(voucher)
    db.session.commit()
    flash(f'Đã thu hồi vĩnh viễn mã Voucher {code}.', 'success')
    return redirect(url_for('admin.dashboard'))