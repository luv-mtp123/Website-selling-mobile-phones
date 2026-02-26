import random
import time
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import User, Product, Order, OrderDetail, Comment
from werkzeug.security import generate_password_hash

app = create_app()


def run_stress_test(num_users=50, num_orders=200):
    """
    Kịch bản Stress Test: Tự động bơm hàng ngàn record vào Database
    để kiểm tra hiệu năng Load trang và thuật toán AI/Pandas.
    """
    print("=" * 60)
    print(f"🚀 BẮT ĐẦU KỊCH BẢN STRESS TEST HỆ THỐNG")
    print(f"Mục tiêu: Tạo {num_users} Users và {num_orders} Đơn hàng giả lập")
    print("=" * 60)

    start_time = time.time()

    with app.app_context():
        # 1. Tạo Users ảo
        print(f"⏳ Đang tạo {num_users} Users ảo...")
        users = []
        for i in range(num_users):
            u = User(
                username=f"stress_user_{i}",
                email=f"stress_{i}@mail.com",
                password=generate_password_hash("123456"),
                full_name=f"Khách hàng số {i}"
            )
            users.append(u)
        db.session.add_all(users)
        db.session.commit()

        # 2. Lấy danh sách sản phẩm hiện có để random
        products = Product.query.all()
        if not products:
            print("❌ Lỗi: Không có sản phẩm nào trong kho để tạo đơn hàng!")
            return

        # 3. Tạo Đơn hàng ảo rải rác trong 30 ngày qua
        print(f"⏳ Đang tạo {num_orders} Đơn hàng và Lịch sử giao dịch...")
        statuses = ['Pending', 'Completed', 'Cancelled']

        for i in range(num_orders):
            random_user = random.choice(users)
            random_status = random.choices(statuses, weights=[20, 70, 10])[0]

            # Tạo thời gian ngẫu nhiên trong 30 ngày qua
            random_days_ago = random.randint(0, 30)
            fake_date = datetime.now(timezone.utc) - timedelta(days=random_days_ago)

            # Chọn ngẫu nhiên 1-3 sản phẩm cho đơn hàng này
            items_to_buy = random.sample(products, random.randint(1, 3))
            total_money = sum(p.price for p in items_to_buy)

            order = Order(
                user_id=random_user.id,
                total_price=total_money,
                address=f"Số nhà {random.randint(1, 999)}, Quận {random.randint(1, 12)}",
                phone=f"09{random.randint(10000000, 99999999)}",
                status=random_status,
                payment_method='COD'
            )
            # Ép thời gian giả lập
            order.date_created = fake_date.replace(tzinfo=None)
            db.session.add(order)
            db.session.flush()  # Lấy order.id

            # Tạo chi tiết đơn hàng
            for p in items_to_buy:
                od = OrderDetail(
                    order_id=order.id, product_id=p.id,
                    product_name=p.name, quantity=1, price=p.price
                )
                db.session.add(od)

                # Tự động sinh bình luận nếu đơn hàng Completed
                if random_status == 'Completed' and random.random() > 0.5:
                    cmt = Comment(
                        user_id=random_user.id, product_id=p.id,
                        content=random.choice(
                            ["Máy dùng rất êm", "Pin hơi hẻo", "Thiết kế đẹp tuyệt", "Giao hàng nhanh!"]),
                        rating=random.randint(3, 5)
                    )
                    db.session.add(cmt)

        db.session.commit()

    end_time = time.time()
    print("=" * 60)
    print(f"✅ STRESS TEST HOÀN TẤT SAU {round(end_time - start_time, 2)} GIÂY!")
    print("Dữ liệu lớn đã được nạp. Hãy vào Admin Dashboard để xem biểu đồ Pandas hoạt động!")
    print("=" * 60)


if __name__ == "__main__":
    run_stress_test()