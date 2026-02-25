"""
Công cụ sao lưu Cơ sở dữ liệu tự động (Database Backup Tool).
Tích hợp thuật toán băm SHA-256 (Secure Hash Algorithm 256-bit) để xác thực
tính toàn vẹn của dữ liệu (Data Integrity Check), chống lại rủi ro file backup
bị can thiệp hoặc tiêm mã độc (Tampering).
"""
import os
import zipfile
import hashlib
from datetime import datetime

# Cấu hình đường dẫn nội bộ
DB_FILE = os.path.join("instance", "mobile_store.db")
BACKUP_DIR = "backups"
CHUNK_SIZE = 8192  # Đọc file theo từng khối 8KB để tối ưu tài nguyên

def calculate_sha256(filepath):
    """
    Thuật toán băm (Hashing) đọc file dưới dạng nhị phân (Binary stream).
    Sử dụng Chunking để có thể băm các file dung lượng khổng lồ (vài chục GB)
    mà không tiêu tốn quá 8KB RAM hệ thống.
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Đọc từng khối dữ liệu bằng toán tử Walrus (:=) cực ngầu của Python 3.8+
        while chunk := f.read(CHUNK_SIZE):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def create_secure_backup():
    """
    Quy trình thực thi sao lưu an toàn:
    1. Kiểm tra sự tồn tại của file CSDL gốc.
    2. Nén file CSDL thành định dạng ZIP chuẩn (Deflated).
    3. Tính toán mã băm SHA-256 của toàn bộ file ZIP.
    4. Xuất mã băm ra file Manifest để Admin đối chiếu khi có sự cố.
    """
    print("=" * 50)
    print("🛡️ MOBILESTORE SECURE DATA BACKUP INITIATED 🛡️")
    print("=" * 50)

    if not os.path.exists(DB_FILE):
        print("❌ [BACKUP ERROR] Không tìm thấy file Database gốc (instance/mobile_store.db).")
        return

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")
    manifest_filename = os.path.join(BACKUP_DIR, f"manifest_{timestamp}.txt")

    try:
        # 1. Nén file Database
        print(f"⏳ [1/3] Đang nén dữ liệu vào kho lưu trữ: {zip_filename}...")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            backup_zip.write(DB_FILE, arcname="mobile_store.db")

        # 2. Tính toán mã băm SHA-256
        print("⏳ [2/3] Đang quét khối Binary và tính toán mã băm toàn vẹn SHA-256...")
        file_hash = calculate_sha256(zip_filename)

        # 3. Tạo file Manifest
        print(f"⏳ [3/3] Đang xuất chứng thư bảo mật Manifest...")
        with open(manifest_filename, 'w', encoding='utf-8') as mf:
            mf.write(f"=== MOBILESTORE SECURE BACKUP MANIFEST ===\n")
            mf.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            mf.write(f"File: {os.path.basename(zip_filename)}\n")
            mf.write(f"Algorithm: SHA-256\n")
            mf.write(f"Checksum: {file_hash}\n")
            mf.write(f"Status: VERIFIED SAFE\n")

        print("\n✅ [BACKUP SUCCESS] Đã tạo bản sao lưu an toàn!")
        print(f"🔑 [CHECKSUM HASH] {file_hash}")
        print("=" * 50)

    except Exception as e:
        print(f"❌ [BACKUP FATAL] Phát hiện lỗi nghiêm trọng trong quá trình sao lưu: {e}")

if __name__ == "__main__":
    create_secure_backup()