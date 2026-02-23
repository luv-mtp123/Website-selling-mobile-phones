import time
import threading
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models import Order, Product, OrderDetail


def auto_cancel_expired_orders(app):
    """
    Hệ thống chạy ngầm (Background Task) của MobileStore.
    Nhiệm vụ: Cứ mỗi 5 phút sẽ quét Database một lần.
    Nếu phát hiện đơn hàng 'Pending' quá 15 phút mà khách chưa thanh toán,
    hệ thống sẽ tự động chuyển sang 'Cancelled' và hoàn lại số lượng vào Kho.
    """
    with app.app_context():
        print("⚙️ [BACKGROUND TASK] Hệ thống dọn dẹp đơn hàng rác đã khởi động...")
        while True:
            try:
                # Thời điểm 15 phút trước tính từ hiện tại
                expiration_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)

                # Tìm các đơn hàng Pending quá hạn
                expired_orders = Order.query.filter(
                    Order.status == 'Pending',
                    Order.date_created <= expiration_time
                ).all()

                if expired_orders:
                    print(f"🧹 [SYSTEM] Đang dọn dẹp {len(expired_orders)} đơn hàng quá hạn thanh toán...")
                    for order in expired_orders:
                        order.status = 'Cancelled'

                        # Hoàn lại số lượng tồn kho cho các sản phẩm trong đơn này
                        for detail in order.details:
                            product = db.session.get(Product, detail.product_id)
                            if product:
                                product.stock_quantity += detail.quantity
                                print(f"  -> Đã hoàn {detail.quantity} máy '{product.name}' về kho.")

                    db.session.commit()
                    print("✅ [SYSTEM] Dọn dẹp hoàn tất.")
            except Exception as e:
                db.session.rollback()
                print(f"❌ [BACKGROUND TASK ERROR]: {e}")

            # Ngủ 5 phút (300 giây) rồi quét lại
            time.sleep(300)


def start_background_tasks(app):
    """Kích hoạt luồng chạy ngầm để không làm treo Web Server"""
    thread = threading.Thread(target=auto_cancel_expired_orders, args=(app,))
    thread.daemon = True  # Daemon thread sẽ tự tắt khi tắt server
    thread.start()