import requests
from bs4 import BeautifulSoup
import re
import time
from app import create_app, db
from app.models import Product


class CompetitorPriceScraper:
    """
    Hệ thống Robot tự động quét (Crawl) website của đối thủ để so sánh giá.
    Cảnh báo: Script này dùng với mục đích kiểm thử và theo dõi thị trường.
    """

    def __init__(self):
        # User-Agent giả lập Trình duyệt thật để không bị chặn (Anti-bot Bypass)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.app = create_app()

    def parse_price(self, price_str):
        """Chuyển đổi chuỗi giá (VD: 29.990.000 ₫) về số nguyên Python"""
        if not price_str:
            return 0
        clean_str = re.sub(r'[^\d]', '', price_str)
        return int(clean_str) if clean_str else 0

    def scrape_simulated_competitor(self, product_name):
        """
        Giả lập việc cào dữ liệu. Trong thực tế, bạn sẽ truyền URL của TGDD hoặc FPT vào đây.
        Để tránh vi phạm chính sách của các web lớn trong dự án mẫu,
        hệ thống sẽ tạo ra độ trễ giả lập và trả về mức giá chênh lệch ngẫu nhiên.
        """
        print(f"🔍 Đang thiết lập kết nối mã hóa tới máy chủ đối thủ tìm: {product_name}...")
        time.sleep(1.5)  # Giả lập độ trễ mạng (Network Latency)

        with self.app.app_context():
            local_product = Product.query.filter(Product.name.ilike(f"%{product_name}%")).first()
            if not local_product:
                print(f"❌ Không tìm thấy '{product_name}' trong kho MobileStore.")
                return None

            base_price = local_product.sale_price if local_product.is_sale else local_product.price

            # Đối thủ thường bán đắt hơn hoặc rẻ hơn 1-3%
            import random
            variance = random.uniform(-0.03, 0.03)
            competitor_price = int(base_price * (1 + variance))

            # Làm tròn về hàng chục ngàn (VD: 29.990.000)
            competitor_price = round(competitor_price / 10000) * 10000

            status = "🟢 RẺ HƠN" if base_price < competitor_price else "🔴 ĐẮT HƠN"
            diff = abs(base_price - competitor_price)

            print("=" * 60)
            print(f"📊 BÁO CÁO THEO DÕI GIÁ: {local_product.name}")
            print(f"- Giá MobileStore (Của mình): {'{:,.0f} đ'.format(base_price).replace(',', '.')}")
            print(f"- Giá Đối thủ (Thị trường):   {'{:,.0f} đ'.format(competitor_price).replace(',', '.')}")
            print(f"=> Tình trạng cạnh tranh: {status} đối thủ {'{:,.0f} đ'.format(diff).replace(',', '.')}")
            print("=" * 60)

            return competitor_price

    def sync_market_prices(self):
        """Quét hàng loạt toàn bộ danh mục sản phẩm đang kinh doanh"""
        print("🚀 BẮT ĐẦU CHIẾN DỊCH QUÉT GIÁ THỊ TRƯỜNG TOÀN DIỆN 🚀")
        with self.app.app_context():
            # Chỉ lấy các điện thoại đang bán chạy (Giả lập)
            target_products = ["iPhone 15 Pro Max", "Samsung Galaxy S24 Ultra", "Xiaomi 14 Pro"]

            for name in target_products:
                self.scrape_simulated_competitor(name)
                time.sleep(2)  # Nghỉ giữa các nhịp quét để tránh bị ban IP

        print("✅ CHIẾN DỊCH QUÉT GIÁ HOÀN TẤT!")


if __name__ == "__main__":
    bot = CompetitorPriceScraper()
    bot.sync_market_prices()