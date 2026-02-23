import logging
from logging.handlers import RotatingFileHandler
import os
from flask import request
import time


class SystemAuditLogger:
    """
    Hệ thống ghi nhật ký (Logging) cấp độ Doanh nghiệp.
    Sử dụng RotatingFileHandler để file log không bao giờ bị quá tải dung lượng.
    Theo dõi: Thời gian phản hồi API, IP truy cập, và Cảnh báo bảo mật.
    """

    def __init__(self, app):
        self.app = app
        self.log_dir = os.path.join(app.root_path, 'logs')
        self._setup_logger()

    def _setup_logger(self):
        """Khởi tạo cấu trúc file Log"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # File log cho Web Traffic
        access_log_path = os.path.join(self.log_dir, 'access.log')
        # Tối đa 5MB mỗi file, giữ lại tối đa 10 file cũ
        access_handler = RotatingFileHandler(access_log_path, maxBytes=5 * 1024 * 1024, backupCount=10)
        access_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
        access_handler.setFormatter(access_formatter)
        access_handler.setLevel(logging.INFO)

        self.app.logger.addHandler(access_handler)
        self.app.logger.setLevel(logging.INFO)
        self.app.logger.info("MobileStore Audit Logging System Started.")

    def init_app_middlewares(self):
        """Gắn Middleware vào vòng đời của Flask (Trước và sau mỗi request)"""

        @self.app.before_request
        def before_request_logging():
            # Đánh dấu thời gian bắt đầu nhận request
            request.start_time = time.time()

        @self.app.after_request
        def after_request_logging(response):
            # Tính toán thời gian xử lý của Server
            if hasattr(request, 'start_time'):
                processing_time = round((time.time() - request.start_time) * 1000, 2)

                # Bỏ qua không log các file ảnh/css/js tĩnh để tránh rác log
                if not request.path.startswith('/static/'):
                    client_ip = request.remote_addr
                    method = request.method
                    path = request.path
                    status = response.status_code

                    log_msg = f"IP: {client_ip} | {method} {path} | Status: {status} | Time: {processing_time}ms"

                    if status >= 500:
                        self.app.logger.error(log_msg)
                    elif status >= 400:
                        self.app.logger.warning(log_msg)
                    else:
                        self.app.logger.info(log_msg)

            return response