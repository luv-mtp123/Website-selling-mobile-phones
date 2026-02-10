from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, oauth
from app.models import User
import random, string

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Nếu đã đăng nhập thì chuyển về trang chủ
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            # Kiểm tra xem user có phải admin không để chuyển hướng phù hợp
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.home'))

        flash('Sai thông tin đăng nhập.', 'danger')
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại.', 'danger')
        else:
            new_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                full_name=username
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Đăng ký thành công! Hãy đăng nhập.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))


# --- GOOGLE OAUTH ---

@auth_bp.route('/login/google')
def login_google():
    # Chuyển hướng sang Google để xác thực
    # Lưu ý: url_for('auth.authorize_google') trỏ về hàm authorize_google bên dưới
    return oauth.google.authorize_redirect(url_for('auth.authorize_google', _external=True))


@auth_bp.route('/authorize/google')
def authorize_google():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        email = user_info['email']

        user = User.query.filter_by(email=email).first()

        # Nếu chưa có tài khoản -> Tự động đăng ký
        if not user:
            base_name = email.split('@')[0]
            # Tạo mật khẩu ngẫu nhiên cho user Google
            random_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

            user = User(
                username=base_name,
                email=email,
                password=generate_password_hash(random_pass),  # Mật khẩu ngẫu nhiên bảo mật
                full_name=user_info.get('name', base_name),
                role='user'
            )
            db.session.add(user)
            db.session.commit()

        login_user(user)
        return redirect(url_for('main.home'))

    except Exception as e:
        print(f"Google Login Error: {e}")
        flash('Lỗi đăng nhập Google. Vui lòng thử lại.', 'danger')
        return redirect(url_for('auth.login'))