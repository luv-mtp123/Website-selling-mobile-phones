"""
Hệ thống Hàng đợi Đa luồng Ưu tiên (Priority Threading Queue).
Sử dụng cấu trúc dữ liệu PriorityQueue kết hợp với Lập trình Hướng Đối Tượng (OOP).
Cho phép hệ thống phân luồng tài nguyên xử lý: Tác vụ quan trọng (OTP, Thanh toán) sẽ
luôn được ưu tiên "chen hàng" chạy trước các tác vụ chạy nền (Sync Vector DB).
"""
import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Callable

@dataclass(order=True)
class PriorityJob:
    """
    Lớp đối tượng Tác vụ (Job Object) có thể tự so sánh độ ưu tiên.
    - Priority càng nhỏ (VD: 1) thì chạy càng sớm.
    - Cùng Priority thì so sánh Timestamp (Ai vào trước chạy trước - FIFO).
    """
    priority: int
    timestamp: float = field(default_factory=time.time, compare=True)
    description: str = field(compare=False, default="Unnamed Task")
    func: Callable = field(compare=False, default=None)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)

    def execute(self):
        """Kích hoạt thực thi hàm callback được đóng gói bên trong."""
        if self.func:
            self.func(*self.args, **self.kwargs)

# ==============================================================================
# ---> [CRITICAL FIX: Khôi phục Class BackgroundJobWorker để Test File Import] <---
# ==============================================================================
class BackgroundJobWorker:
    """
    Lớp quản lý Worker chạy nền.
    Được cấu trúc lại để tương thích ngược 100% với hệ thống cũ (__init__.py và test),
    nhưng bên trong lõi đã được nâng cấp lên Hàng đợi Ưu tiên (Priority Queue).
    """
    def __init__(self):
        self.job_queue = queue.PriorityQueue()
        self.worker_thread = None
        self._stop_event = threading.Event()  # Cờ tín hiệu dừng an toàn

    def worker_loop(self):
        print("🚀 [PRIORITY WORKER] Khởi động Engine Hàng đợi Đa luồng. Sẵn sàng nhận lệnh!")
        while not self._stop_event.is_set():
            try:
                # Đợi tối đa 1s để lấy job, nếu không có sẽ vòng lại kiểm tra _stop_event
                job = self.job_queue.get(timeout=1)
                print(f"⚡ [WORKER EXECUTING] Đang xử lý -> Priority: {job.priority} | Task: {job.description}")
                try:
                    job.execute()
                    print(f"✅ [WORKER SUCCESS] Tác vụ hoàn tất: {job.description}")
                except Exception as e:
                    print(f"❌ [WORKER FATAL ERROR] Lỗi khi chạy tác vụ '{job.description}': {e}")
                finally:
                    self.job_queue.task_done()
            except queue.Empty:
                continue

    def start_worker(self, app=None):
        """Kích hoạt luồng Daemon"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self._stop_event.clear()
            self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
            self.worker_thread.start()

    def stop_worker(self):
        """Dừng an toàn luồng Worker (Dùng cho quá trình TearDown của Test)"""
        self._stop_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=2)

    def add_job(self, func, *args, **kwargs):
        """Giao diện đẩy Task tương thích với hệ thống Test (như test_infrastructure.py)"""
        # Bóc tách tham số priority (nếu không có thì mặc định là 5)
        priority = kwargs.pop('priority', 5)
        description = kwargs.pop('description', getattr(func, '__name__', 'Unnamed Task'))

        new_job = PriorityJob(
            priority=priority,
            description=description,
            func=func,
            args=args,
            kwargs=kwargs
        )
        self.job_queue.put(new_job)
        print(f"📥 [QUEUE ADDED] Đã xếp hàng: {description} (Độ ưu tiên: {priority} - Hàng chờ: {self.job_queue.qsize()})")