import os
import shutil
import tarfile
from datetime import datetime


def backup_database():
    """
    Công cụ sao lưu toàn bộ cơ sở dữ liệu (Database) và file Upload của hệ thống.
    Giúp lập trình viên bảo vệ dữ liệu, tránh mất mát khi thao tác nhầm.
    """
    print("=" * 50)
    print("📦 BẮT ĐẦU QUÁ TRÌNH SAO LƯU DỮ LIỆU (BACKUP) 📦")
    print("=" * 50)

    # 1. Tạo thư mục chứa backup nếu chưa có
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"📁 Đã tạo thư mục chứa bản sao lưu: ./{backup_dir}")

    # Lấy thời gian hiện tại để đặt tên file (VD: backup_20260223_173000)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder_name = f"backup_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_folder_name)
    os.makedirs(backup_path)

    # 2. Tìm và copy file Database (SQLite)
    # Tùy cấu hình mà db có thể nằm ở thư mục gốc hoặc thư mục 'instance'
    db_paths = ["instance/mobilestore.db", "mobilestore.db", "instance/mobilestore.db", "mobilestore.db"]
    db_found = False

    for db_file in db_paths:
        if os.path.exists(db_file):
            shutil.copy2(db_file, backup_path)
            print(f"✅ Đã sao lưu thành công Database: {db_file}")
            db_found = True
            break

    if not db_found:
        print("⚠️ CẢNH BÁO: Không tìm thấy file Database (.db) nào!")

    # 3. Nén thư mục thành file ZIP để tiết kiệm dung lượng
    archive_name = os.path.join(backup_dir, f"MobileStore_Backup_{timestamp}")
    shutil.make_archive(archive_name, 'zip', backup_path)
    print(f"🗜️ Đã nén thành file: {archive_name}.zip")

    # 4. Dọn dẹp thư mục tạm
    shutil.rmtree(backup_path)

    print("=" * 50)
    print("🎉 QUÁ TRÌNH SAO LƯU HOÀN TẤT THÀNH CÔNG!")
    print(f"👉 File của bạn nằm tại: {archive_name}.zip")
    print("=" * 50)


if __name__ == "__main__":
    backup_database()