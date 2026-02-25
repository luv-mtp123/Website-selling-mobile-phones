"""
Module quản lý các tác vụ định kỳ chạy ngầm (Background Tasks).
Tích hợp kỹ thuật tối ưu hóa bộ nhớ (Memory Optimization) bằng Python Generators
để xử lý dữ liệu lớn (Big Data) mà không gây tràn RAM (OOM - Out of Memory).
"""
import time
from datetime import datetime, timedelta, timezone
from app.extensions import db
from app.models import Order, Product
from flask import current_app


def get_expired_orders_chunked(app, chunk_size=50):
    """
    Python Generator (yield) để truy xuất dữ liệu theo từng phân đoạn (Chunking).
    Giúp giải phóng RAM ngay lập tức sau khi xử lý xong một lô dữ liệu nhỏ,
    thay vì kéo toàn bộ 100,000 bản ghi lên RAM cùng lúc bằng hàm .all().
    """
    with app.app_context():
        # Lấy mốc thời gian cách đây 15 phút
        expiration_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)
        offset = 0

        while True:
            # Dùng limit và offset để phân trang truy vấn (Database Pagination)
            chunk = Order.query.filter(
                Order.status == 'Pending',
                Order.date_created <= expiration_time
            ).limit(chunk_size).offset(offset).all()

            if not chunk:
                break

            yield chunk
            offset += chunk_size


def cleanup_expired_orders_task(app):
    """
    Tác vụ dọn dẹp các đơn hàng 'Pending' đã quá hạn thanh toán.
    Tự động hoàn trả tồn kho (Restock) để tránh tình trạng giam hàng ảo.
    """
    print("🔄 [TASK] Đang chạy luồng quét và dọn dẹp đơn hàng quá hạn...")
    total_cancelled = 0

    # Sử dụng Generator để duyệt qua từng lô đơn hàng (Tiết kiệm 90% RAM)
    for chunk in get_expired_orders_chunked(app):
        with app.app_context():
            for order in chunk:
                # Lặp qua chi tiết để hoàn lại số lượng tồn kho cho từng sản phẩm
                for detail in order.details:
                    p = db.session.get(Product, detail.product_id)
                    if p:
                        p.stock_quantity += detail.quantity

                order.status = 'Cancelled'
                total_cancelled += 1

            # Lưu thay đổi (Commit) theo từng đợt nhỏ để tránh Database Timeout
            db.session.commit()

    if total_cancelled > 0:
        print(f"✅ [TASK SUCCESS] Đã hủy tự động và hoàn kho thành công {total_cancelled} đơn hàng.")