from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Product, User, Order, TradeInRequest, OrderDetail
import json
from app.utils import sync_product_to_vector_db

# [NEW: Import các thư viện Data Science và xử lý file]
import pandas as pd
import io

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
def check_admin():
    if current_user.role != 'admin':
        abort(403)


@admin_bp.route('/admin')
def dashboard():
    products = Product.query.order_by(Product.id.desc()).all()
    users = User.query.all()
    orders = Order.query.options(joinedload(Order.user)).order_by(Order.date_created.desc()).all()
    tradeins = TradeInRequest.query.options(joinedload(TradeInRequest.user)).order_by(
        TradeInRequest.created_at.desc()).all()

    total_revenue = db.session.query(func.sum(Order.total_price)).filter(Order.status == 'Completed').scalar() or 0

    # [REFACTOR] Đếm trực tiếp trong DB thay vì truyền array sang HTML dùng `|length`
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
        Order.status == 'Completed',
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
    ).join(Order).filter(Order.status == 'Completed').group_by(OrderDetail.product_name).order_by(
        desc('total_qty')).limit(5).all()

    # =========================================================================
    # [NEW: TÍCH HỢP DATA SCIENCE VỚI PANDAS LẤY INSIGHT]
    # =========================================================================
    best_month_product = "Chưa có dữ liệu"
    peak_hour = "Chưa có dữ liệu"

    # Lấy dữ liệu thô từ DB
    completed_orders = db.session.query(
        Order.id, Order.date_created, OrderDetail.product_name, OrderDetail.quantity
    ).join(OrderDetail).filter(Order.status == 'Completed').all()

    if completed_orders:
        # Chuyển đổi thành Pandas DataFrame
        df = pd.DataFrame(completed_orders, columns=['order_id', 'date_created', 'product_name', 'quantity'])

        # Đảm bảo cột date_created là định dạng datetime
        df['date_created'] = pd.to_datetime(df['date_created'])

        # INSIGHT 1: Khung giờ khách hàng chốt đơn nhiều nhất (Peak Hour)
        df['hour'] = df['date_created'].dt.hour
        if not df['hour'].empty:
            peak_hour_val = df['hour'].mode()[0]  # Lấy giờ xuất hiện nhiều nhất (mode)
            peak_hour = f"{peak_hour_val}:00 - {peak_hour_val + 1}:00"

        # INSIGHT 2: Sản phẩm bán chạy nhất trong THÁNG HIỆN TẠI
        current_month = datetime.now().month
        current_year = datetime.now().year

        # Lọc df theo tháng và năm hiện tại
        this_month_df = df[
            (df['date_created'].dt.month == current_month) & (df['date_created'].dt.year == current_year)]

        if not this_month_df.empty:
            # Dùng GroupBy phân tích nhóm
            top_product_series = this_month_df.groupby('product_name')['quantity'].sum().sort_values(ascending=False)
            if not top_product_series.empty:
                best_month_product = f"{top_product_series.index[0]} ({top_product_series.iloc[0]} máy)"
    # =========================================================================

    return render_template(
        'admin_dashboard.html',
        products=products,
        users=users,
        orders=orders,
        tradeins=tradeins,
        total_revenue=total_revenue,
        total_orders_count=total_orders_count,
        total_products_count=total_products_count,
        total_users_count=total_users_count,
        status_data=status_data,
        chart_dates=json.dumps(chart_dates),
        chart_revenues=json.dumps(chart_revenues),
        top_products=top_products,
        best_month_product=best_month_product,  # [NEW] Truyền biến
        peak_hour=peak_hour  # [NEW] Truyền biến
    )


# =========================================================================
# [NEW: ROUTE XUẤT BÁO CÁO DOANH THU CHUYÊN NGHIỆP VỚI PANDAS & OPENPYXL]
# =========================================================================
@admin_bp.route('/admin/export/report')
@login_required
def export_revenue_report():
    if current_user.role != 'admin':
        abort(403)

    # 1. Query toàn bộ đơn hàng hoàn thành kèm thông tin Khách
    orders = db.session.query(
        Order.id, Order.date_created, Order.total_price, Order.payment_method, Order.status,
        User.full_name, User.username
    ).outerjoin(User, Order.user_id == User.id).filter(Order.status == 'Completed').order_by(
        Order.date_created.desc()).all()

    if not orders:
        flash("Chưa có đơn hàng nào hoàn thành để xuất báo cáo.", "warning")
        return redirect(url_for('admin.dashboard'))

    # 2. Xử lý dữ liệu bằng Pandas
    df = pd.DataFrame(orders,
                      columns=['Mã Đơn', 'Ngày Đặt', 'Tổng Tiền', 'Thanh Toán', 'Trạng Thái', 'Tên Khách', 'Username'])

    # Làm sạch dữ liệu Khách hàng (Ưu tiên Full name, nếu không có dùng Username)
    df['Khách Hàng'] = df['Tên Khách'].combine_first(df['Username'])
    df = df.drop(columns=['Tên Khách', 'Username'])

    # Format lại Datetime
    df['Ngày Đặt'] = pd.to_datetime(df['Ngày Đặt']).dt.strftime('%d/%m/%Y %H:%M')

    # Sắp xếp lại thứ tự cột cho đẹp
    df = df[['Mã Đơn', 'Khách Hàng', 'Ngày Đặt', 'Thanh Toán', 'Tổng Tiền', 'Trạng Thái']]

    # 3. Render ra Excel In-memory (Không cần lưu file rác xuống ổ cứng máy chủ)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Báo Cáo Doanh Thu', index=False)

        # Tinh chỉnh giao diện Excel bằng OpenPyXL
        worksheet = writer.sheets['Báo Cáo Doanh Thu']

        # Định dạng cột Tiền (Cột E / Index 5)
        for row in range(2, len(df) + 2):
            cell = worksheet.cell(row=row, column=5)
            cell.number_format = '#,##0 "VNĐ"'

        # Tự động dãn cột (Auto-fit Column Width)
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

    # Tên file động theo thời gian xuất
    timestamp = datetime.now().strftime("%d%m%Y_%H%M")
    filename = f"Bao_Cao_Doanh_Thu_Thang_{datetime.now().month}_{timestamp}.xlsx"

    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# =========================================================================


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


@admin_bp.route('/admin/product/add', methods=['POST'])
def add_product():
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

        flash(f'Thêm sản phẩm {name} thành công!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi thêm sản phẩm: {str(e)}', 'danger')

    return redirect(url_for('admin.dashboard'))


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

            colors_json = request.form.get('colors_json')
            versions_json = request.form.get('versions_json')
            if colors_json: product.colors = colors_json
            if versions_json: product.versions = versions_json

            db.session.commit()
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