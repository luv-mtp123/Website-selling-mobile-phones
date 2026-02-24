import threading
import queue
import time
from flask import current_app


class BackgroundJobWorker:
    """
    Hệ thống Hàng đợi (Message Queue) tự xây dựng dựa trên Threading.
    Mô hình Producer - Consumer.
    Giúp đẩy các tác vụ nặng (Gửi Email, Sync Vector DB, Nén File) chạy ngầm phía sau,
    đảm bảo giao diện web của người dùng không bao giờ bị đơ (lag).
    """
    _instance = None

    def __new__(cls):
        """Đảm bảo chỉ có 1 Worker duy nhất tồn tại (Singleton Pattern)"""
        if cls._instance is None:
            cls._instance = super(BackgroundJobWorker, cls).__new__(cls)
            cls._instance._init_queue()
        return cls._instance

    def _init_queue(self):
        """
        Khởi tạo Thread-Safe Queue.
        Tạo lập cờ trạng thái và thiết lập không gian quản lý tiến trình ngầm (Daemon Thread).
        """
        self.job_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None

    def start_worker(self, app):
        """Khởi động tiến trình dọn dẹp hàng đợi"""
        if self.is_running:
            return

        self.is_running = True
        # Gửi context của Flask vào Thread để có thể truy cập Database
        self.worker_thread = threading.Thread(target=self._process_queue, args=(app,))
        self.worker_thread.daemon = True  # Sẽ tự động chết khi tắt server chính
        self.worker_thread.start()
        app.logger.info("⚙️ Background Job Worker đã khởi động và sẵn sàng nhận tác vụ.")

    def add_job(self, task_function, *args, **kwargs):
        """
        Producer: Thêm một tác vụ mới vào hàng đợi chờ xử lý.
        Ví dụ: worker.add_job(send_email, 'user@mail.com', 'Hello')
        """
        job = {
            'func': task_function,
            'args': args,
            'kwargs': kwargs,
            'timestamp': time.time()
        }
        self.job_queue.put(job)

    def _process_queue(self, app):
        """Consumer: Liên tục lấy tác vụ ra xử lý từng cái một"""
        with app.app_context():
            while self.is_running:
                try:
                    # Lấy tác vụ ra khỏi hàng đợi (sẽ block tối đa 2 giây nếu hàng đợi trống)
                    job = self.job_queue.get(timeout=2.0)

                    func = job['func']
                    args = job['args']
                    kwargs = job['kwargs']

                    app.logger.info(f"▶️ Bắt đầu xử lý Job nền: {func.__name__}...")

                    # Thực thi hàm
                    func(*args, **kwargs)

                    app.logger.info(f"✅ Hoàn thành Job: {func.__name__}.")

                    # Báo hiệu đã xử lý xong
                    self.job_queue.task_done()

                except queue.Empty:
                    # Hàng đợi rỗng, tiếp tục vòng lặp
                    continue
                except Exception as e:
                    app.logger.error(f"❌ Lỗi khi xử lý Job nền: {str(e)}")

    def stop_worker(self):
        """Dừng worker an toàn"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join()