from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, oauth
from app.models import User
from app.utils import get_serializer, send_reset_email_simulation
import random, string

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Xử lý quá trình đăng nhập của người dùng.
    Kiểm tra thông tin định danh và cấp quyền truy cập phiên làm việc (Session).
    """
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
    """
    Xử lý đăng ký tài khoản mới.
    Mã hóa mật khẩu an toàn (Hash) trước khi lưu vào cơ sở dữ liệu bảo mật.
    """
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
    """
    Đăng xuất người dùng hiện tại, dọn dẹp bộ nhớ đệm và xóa Cookie phiên làm việc.
    """
    logout_user()
    return redirect(url_for('main.home'))


# --- FORGOT PASSWORD ---

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Xử lý yêu cầu quên mật khẩu của người dùng.
    Tạo Token bảo mật có thời hạn và giả lập gửi Email khôi phục.
    """
    if current_user.is_authenticated: return redirect(url_for('main.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            # Tạo token hết hạn sau 15 phút (900s)
            s = get_serializer(current_app.config['SECRET_KEY'])
            token = s.dumps(email, salt='password-reset-salt')

            # Giả lập gửi email (Test link sẽ hiện ở Console của server)
            link = send_reset_email_simulation(email, token)

            flash(f'Yêu cầu đã được gửi! (DEMO: Check Console để lấy link reset)', 'info')
        else:
            flash('Email không tồn tại trong hệ thống.', 'warning')

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Xác thực Token khôi phục mật khẩu.
    Cho phép người dùng thiết lập lại mật khẩu mới nếu Token hợp lệ và chưa hết hạn.
    """
    if current_user.is_authenticated: return redirect(url_for('main.home'))

    s = get_serializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=900)
    except:
        flash('Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp.', 'danger')
        else:
            user = User.query.filter_by(email=email).first()
            if user:
                user.password = generate_password_hash(password)
                db.session.commit()
                flash('Mật khẩu đã được thay đổi. Vui lòng đăng nhập.', 'success')
                return redirect(url_for('auth.login'))

    return render_template('reset_password.html')

# --- GOOGLE OAUTH ---

@auth_bp.route('/login/google')
def login_google():
    """
    Khởi tạo luồng xác thực OAuth 2.0.
    Chuyển hướng người dùng sang cổng đăng nhập an toàn của Google.
    """
    # Chuyển hướng sang Google để xác thực
    # Lưu ý: url_for('auth.authorize_google') trỏ về hàm authorize_google bên dưới
    return oauth.google.authorize_redirect(url_for('auth.authorize_google', _external=True))


@auth_bp.route('/authorize/google')
def authorize_google():
    """
    Nhận phản hồi từ Google (Callback), trích xuất thông tin người dùng.
    Tự động tạo tài khoản mới nếu email này chưa từng tồn tại trong hệ thống.
    """
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