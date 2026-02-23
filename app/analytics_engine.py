import pandas as pd
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Order, OrderDetail, User


class SalesAnalyticsEngine:
    """
    Hệ thống Lõi Phân tích Dữ liệu Bán hàng chuyên sâu.
    Sử dụng Pandas để xử lý lượng lớn dữ liệu (Big Data) thay vì dùng SQL thuần.
    """

    def __init__(self, app):
        self.app = app

    def get_raw_order_dataframe(self):
        """Lấy toàn bộ dữ liệu đơn hàng thành DataFrame Pandas"""
        with self.app.app_context():
            orders = db.session.query(
                Order.id, Order.user_id, Order.total_price,
                Order.status, Order.date_created
            ).filter(Order.status == 'Completed').all()

            if not orders:
                return pd.DataFrame()

            df = pd.DataFrame(orders, columns=['order_id', 'user_id', 'total_price', 'status', 'date_created'])
            df['date_created'] = pd.to_datetime(df['date_created'])
            return df

    def calculate_customer_retention(self):
        """
        Tính toán Tỷ lệ giữ chân khách hàng (Customer Retention Rate).
        Khách hàng quay lại mua lần 2 được tính là Retained.
        """
        df = self.get_raw_order_dataframe()
        if df.empty:
            return "0%"

        # Đếm số lượng đơn hàng của từng User
        user_order_counts = df.groupby('user_id')['order_id'].count()

        # Những khách hàng mua từ 2 đơn trở lên
        returning_customers = user_order_counts[user_order_counts > 1].count()
        total_customers = user_order_counts.count()

        if total_customers == 0:
            return "0%"

        retention_rate = (returning_customers / total_customers) * 100
        return f"{retention_rate:.1f}%"

    def analyze_sales_trend_7_days(self):
        """Phân tích xu hướng tăng/giảm doanh thu 7 ngày qua"""
        df = self.get_raw_order_dataframe()
        if df.empty:
            return {'trend': 'neutral', 'percentage': 0}

        today = datetime.now()
        last_7_days = today - timedelta(days=7)
        previous_7_days = today - timedelta(days=14)

        # Doanh thu 7 ngày gần nhất
        recent_sales = df[(df['date_created'] >= last_7_days)]['total_price'].sum()
        # Doanh thu 7 ngày trước đó nữa
        past_sales = df[(df['date_created'] >= previous_7_days) & (df['date_created'] < last_7_days)][
            'total_price'].sum()

        if past_sales == 0:
            return {'trend': 'up', 'percentage': 100 if recent_sales > 0 else 0}

        growth = ((recent_sales - past_sales) / past_sales) * 100
        trend = 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'

        return {'trend': trend, 'percentage': round(abs(growth), 2)}

    def generate_rfm_analysis(self):
        """
        Phân tích RFM (Recency, Frequency, Monetary) để tìm Khách hàng VIP.
        Đây là thuật toán chuẩn của ngành Marketing & E-Commerce.
        """
        df = self.get_raw_order_dataframe()
        if df.empty:
            return []

        now = datetime.now()
        rfm = df.groupby('user_id').agg({
            'date_created': lambda x: (now - x.max()).days,  # Recency
            'order_id': 'count',  # Frequency
            'total_price': 'sum'  # Monetary
        }).rename(columns={'date_created': 'Recency', 'order_id': 'Frequency', 'total_price': 'Monetary'})

        # Lọc ra top 5 VIP (Chi nhiều tiền nhất và mua thường xuyên)
        top_vips = rfm.sort_values(by=['Monetary', 'Frequency'], ascending=False).head(5)

        vip_list = []
        with self.app.app_context():
            for uid, row in top_vips.iterrows():
                user = db.session.get(User, uid)
                if user:
                    vip_list.append({
                        'username': user.username,
                        'total_spent': row['Monetary'],
                        'orders_count': row['Frequency'],
                        'days_since_last_order': row['Recency']
                    })
        return vip_list