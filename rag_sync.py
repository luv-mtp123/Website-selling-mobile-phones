from app import create_app, db, initialize_database
from app.models import Product
from app.utils import sync_product_to_vector_db

# Khởi tạo App Context để truy cập Database
app = create_app()


def sync_all():
    """
    Quét toàn bộ DB và đẩy vào Vector DB (ChromaDB).
    Chạy script này sau khi khởi tạo DB hoặc khi muốn re-index lại từ đầu.
    """
    with app.app_context():
        # Đảm bảo CSDL được tạo trước khi truy vấn, chống lỗi "no such table: product"
        initialize_database()

        print("🔄 Đang đồng bộ dữ liệu sang Vector Database (ChromaDB)...")
        products = Product.query.all()
        count = 0
        for p in products:
            # Chỉ đồng bộ sản phẩm đang hoạt động
            if p.is_active:
                sync_product_to_vector_db(p)
                count += 1
                # ---> [HOTFIX]: Đã tháo bỏ gông xiềng time.sleep(2.5) vì chạy Local không sợ tốn Quota!

        print(f"✅ Đã đồng bộ thành công {count} sản phẩm vào ChromaDB!")


if __name__ == "__main__":
    sync_all()