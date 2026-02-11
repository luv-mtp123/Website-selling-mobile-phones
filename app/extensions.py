from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# [FIX] Import đúng từ 'flask_client' thay vì 'base_client' để tương thích tốt nhất với Flask
from authlib.integrations.flask_client import OAuth

# 1. Khởi tạo Database SQLAlchemy
db = SQLAlchemy()

# 2. Khởi tạo LoginManager (Quản lý đăng nhập)
login_manager = LoginManager()

# [Optional] Cấu hình thông báo mặc định khi người dùng chưa đăng nhập truy cập trang kín
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."
login_manager.login_message_category = "warning" # Loại thông báo (info, success, warning, danger)

# 3. Khởi tạo OAuth (Dùng cho Google Login)
oauth = OAuth()