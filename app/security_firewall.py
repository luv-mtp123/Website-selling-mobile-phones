import time
import re
from flask import request, abort, current_app
from flask_login import current_user


class MobileStoreFirewall:
    """
    Hệ thống Tường lửa Ứng dụng Web (WAF) tự xây dựng bằng Python thuần.
    - Rate Limiting: Chống DDoS bằng cách giới hạn số request / phút.
    - XSS / SQLi Prevention: Quét các ký tự đáng ngờ trong Form và URL.
    """

    def __init__(self, app=None):
        self.ip_records = {}  # Lưu trữ { '192.168.1.1': [time1, time2...] }
        self.blocked_ips = {}  # Lưu trữ { '192.168.1.1': unblock_time }

        # Cấu hình giới hạn
        self.MAX_REQUESTS_PER_MINUTE = 60  # Tối đa 60 request / phút
        self.BLOCK_TIME_SECONDS = 300  # Khóa IP 5 phút nếu vi phạm

        # Biểu thức chính quy (Regex) quét mã độc SQL Injection & XSS
        self.MALICIOUS_PATTERNS = re.compile(
            r"(<script.*?>.*?</script>)|"
            r"(SELECT\s+.*\s+FROM)|"
            r"(DROP\s+TABLE)|"
            r"(INSERT\s+INTO)|"
            r"(DELETE\s+FROM)|"
            r"(;\s*--)",
            re.IGNORECASE
        )

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Gắn Middleware tường lửa vào trước mỗi Request của Flask"""
        app.before_request(self.check_security)

    def _clean_old_records(self, current_time):
        """Dọn dẹp lịch sử request cũ để giải phóng RAM"""
        one_minute_ago = current_time - 60
        for ip in list(self.ip_records.keys()):
            self.ip_records[ip] = [t for t in self.ip_records[ip] if t > one_minute_ago]
            if not self.ip_records[ip]:
                del self.ip_records[ip]

    def _check_rate_limit(self, ip, current_time):
        """Kiểm tra xem IP này có đang Spam Request (DDoS) không"""
        # Nếu IP đang bị khóa, kiểm tra xem đã hết giờ phạt chưa
        if ip in self.blocked_ips:
            if current_time < self.blocked_ips[ip]:
                current_app.logger.warning(f"🛡️ FIREWALL: Chặn truy cập từ IP bị khóa {ip}")
                abort(429, description="Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau 5 phút.")
            else:
                del self.blocked_ips[ip]  # Hết giờ phạt -> Mở khóa

        # Ghi nhận request mới
        if ip not in self.ip_records:
            self.ip_records[ip] = []
        self.ip_records[ip].append(current_time)

        # Kiểm tra số lượng
        if len(self.ip_records[ip]) > self.MAX_REQUESTS_PER_MINUTE:
            self.blocked_ips[ip] = current_time + self.BLOCK_TIME_SECONDS
            del self.ip_records[ip]
            current_app.logger.error(f"🚨 FIREWALL: Phát hiện nghi vấn DDoS từ IP {ip}. Đã tự động BAN 5 phút.")
            abort(429, description="Phát hiện lưu lượng bất thường. Đã tạm khóa IP của bạn.")

    def _check_malicious_payload(self):
        """Quét toàn bộ URL Parameters và Form Data để tìm mã độc"""
        # Quét tham số trên URL (Ví dụ: /?q=<script>alert(1)</script>)
        for key, value in request.args.items():
            if self.MALICIOUS_PATTERNS.search(str(value)):
                current_app.logger.critical(
                    f"🚨 FIREWALL: Ngăn chặn XSS/SQLi Payload trong URL từ IP {request.remote_addr}")
                abort(403, description="Yêu cầu chứa ký tự không hợp lệ.")

        # Quét dữ liệu gửi lên qua Form (POST)
        if request.method == 'POST':
            for key, value in request.form.items():
                if self.MALICIOUS_PATTERNS.search(str(value)):
                    current_app.logger.critical(
                        f"🚨 FIREWALL: Ngăn chặn XSS/SQLi Payload trong Form từ IP {request.remote_addr}")
                    abort(403, description="Dữ liệu gửi lên chứa ký tự nghi ngờ vi phạm bảo mật.")

    def check_security(self):
        """Hàm chính thực thi các rào chắn bảo mật"""
        # Bỏ qua không kiểm tra các file ảnh, css, js tĩnh để không làm chậm web
        if request.path.startswith('/static/'):
            return
        # ---> [HOTFIX]: MỞ KHÓA (WHITELIST) CHO QUẢN TRỊ VIÊN VÀ LOCALHOST
        try:
            # Nếu là Admin đang thao tác -> Cho phép qua tường lửa vô điều kiện
            if current_user.is_authenticated and current_user.role == 'admin':
                return
        except Exception:
            pass

        ip = request.remote_addr

        # Bỏ qua kiểm tra nếu truy cập từ máy chủ nội bộ (Dev Test)
        if ip == '127.0.0.1':
            return

        current_time = time.time()

        # 1. Dọn dẹp RAM
        self._clean_old_records(current_time)

        # 2. Kiểm tra Spam (DDoS)
        self._check_rate_limit(ip, current_time)

        # 3. Kiểm tra Mã độc (SQLi/XSS)
        self._check_malicious_payload()