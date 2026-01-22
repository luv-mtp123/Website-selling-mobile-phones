from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Khởi tạo Database và Login Manager nhưng chưa gắn vào app ngay
db = SQLAlchemy()
login_manager = LoginManager()