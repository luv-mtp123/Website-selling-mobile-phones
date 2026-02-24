import os
import time
import zipfile
import pandas as pd
from datetime import datetime
from app import create_app
from app.extensions import db

# =========================================================================
# Ép Terminal của Windows đọc được Emoji và Màu sắc UTF-8
# =========================================================================
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class DataWarehouseExporter:
    """
    Hệ thống ETL (Extract, Transform, Load) nội bộ.
    Trích xuất dữ liệu từ SQLite, làm sạch bằng Pandas và xuất ra file CSV nén (ZIP).
    """

    def __init__(self):
        self.app = create_app()
        self.export_dir = "data_exports"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

    def format_phone_number(self, phone):
        """Làm sạch và chuẩn hóa số điện thoại về định dạng +84"""
        if pd.isna(phone) or not str(phone).strip():
            return "UNKNOWN"
        phone_str = str(phone).strip().replace(" ", "").replace(".", "")
        if phone_str.startswith("0"):
            return "+84" + phone_str[1:]
        elif phone_str.startswith("84"):
            return "+" + phone_str
        return phone_str

    def run_etl_pipeline(self):
        """
        Thực thi toàn bộ luồng ETL: Trích xuất (Extract), Làm sạch (Transform),
        và Lưu trữ (Load) dữ liệu thành tệp CSV nén.
        """
        print(f"{Colors.HEADER}{Colors.BOLD}=" * 70)
        print(f"📦 HỆ THỐNG DATA WAREHOUSE: TIẾN TRÌNH ETL (EXTRACT - TRANSFORM - LOAD)")
        print(f"Bắt đầu lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + f"{Colors.ENDC}")

        csv_files = []
        with self.app.app_context():
            # 1. EXTRACT (Trích xuất)
            print(f"{Colors.CYAN}⏳ [EXTRACT] Đang đọc dữ liệu từ Database...{Colors.ENDC}")
            time.sleep(0.5)

            try:
                users_df = pd.read_sql_table('user', db.engine)
                products_df = pd.read_sql_table('product', db.engine)
                orders_df = pd.read_sql_table('order', db.engine)

                # 2. TRANSFORM (Làm sạch & Chuyển đổi dữ liệu)
                print(f"{Colors.BLUE}⚙️ [TRANSFORM] Đang làm sạch dữ liệu (Data Cleansing)...{Colors.ENDC}")
                time.sleep(0.5)

                # Làm sạch bảng User
                if not users_df.empty:
                    # Viết hoa chữ cái đầu của tên
                    if 'full_name' in users_df.columns:
                        users_df['full_name'] = users_df['full_name'].str.title()
                    # Ẩn danh Email (Data Privacy)
                    users_df['email'] = users_df['email'].apply(
                        lambda e: f"{str(e)[:3]}***@***" if pd.notna(e) and '@' in str(e) else e)
                    # Xóa cột password hash
                    users_df = users_df.drop(columns=['password'], errors='ignore')

                # Làm sạch bảng Order
                if not orders_df.empty:
                    # Chuẩn hóa số điện thoại
                    if 'phone' in orders_df.columns:
                        orders_df['phone'] = orders_df['phone'].apply(self.format_phone_number)

                # 3. LOAD (Lưu trữ thành CSV)
                print(f"{Colors.GREEN}💾 [LOAD] Đang xuất file CSV chuẩn phân tích...{Colors.ENDC}")

                user_csv = os.path.join(self.export_dir, f"users_clean_{self.timestamp}.csv")
                users_df.to_csv(user_csv, index=False, encoding='utf-8-sig')
                csv_files.append(user_csv)

                product_csv = os.path.join(self.export_dir, f"products_clean_{self.timestamp}.csv")
                products_df.to_csv(product_csv, index=False, encoding='utf-8-sig')
                csv_files.append(product_csv)

                order_csv = os.path.join(self.export_dir, f"orders_clean_{self.timestamp}.csv")
                orders_df.to_csv(order_csv, index=False, encoding='utf-8-sig')
                csv_files.append(order_csv)

            except Exception as e:
                print(f"{Colors.FAIL}❌ LỖI TRÍCH XUẤT DATABASE: {e}{Colors.ENDC}")
                return

        # 4. ĐÓNG GÓI ZIP
        print(f"{Colors.WARNING}🗜️ Đang nén dữ liệu thành file ZIP bảo mật...{Colors.ENDC}")
        zip_filename = os.path.join(self.export_dir, f"DW_EXPORT_{self.timestamp}.zip")

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in csv_files:
                zipf.write(file, os.path.basename(file))
                os.remove(file)  # Xóa file csv gốc sau khi nén xong để dọn rác

        print(f"\n{Colors.HEADER}{Colors.BOLD}🎉 HOÀN TẤT! Dữ liệu đã sẵn sàng cho Data Analyst.{Colors.ENDC}")
        print(f"👉 Đường dẫn file: {zip_filename}")
        print("=" * 70)


if __name__ == "__main__":
    exporter = DataWarehouseExporter()
    exporter.run_etl_pipeline()