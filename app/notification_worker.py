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
    Lớp đối tượng Tác vụ (Job Object).
    Cài đặt cơ sở so sánh toán học (Comparisons) thông qua tham số `order=True` của Dataclass.
    Thuật toán Heap Queue sẽ tự động phân loại mức độ:
    - Priority (Độ ưu tiên): Số càng nhỏ (1) -> Mức ưu tiên càng cao (Đứng đầu mảng).
    - Nếu Priority bằng nhau -> So sánh Timestamp, ai vào trước chạy trước (FIFO).
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


# Khởi tạo Hàng đợi Ưu tiên dựa trên Heap Algorithm (Tuyệt đối Thread-safe)
job_queue = queue.PriorityQueue()


def worker_loop():
    """
    Vòng lặp Vô tận (Infinite Loop) của Cỗ máy xử lý chạy ở một luồng (Thread) riêng biệt.
    Nó sẽ liên tục tiêu thụ (Consume) các tác vụ có độ ưu tiên cao nhất ra để thực thi.
    """
    print("🚀 [PRIORITY WORKER] Khởi động Engine Hàng đợi Đa luồng. Sẵn sàng nhận lệnh!")
    while True:
        # get() sẽ Block (chặn) luồng này không ăn CPU cho đến khi có job mới được đưa vào
        job = job_queue.get()

        print(f"⚡ [WORKER EXECUTING] Đang xử lý -> Priority: {job.priority} | Task: {job.description}")
        try:
            # Thực thi tác vụ
            job.execute()
            print(f"✅ [WORKER SUCCESS] Tác vụ hoàn tất: {job.description}")
        except Exception as e:
            # Đây là nơi có thể mở rộng thành Dead-Letter Queue (DLQ) sau này
            print(f"❌ [WORKER FATAL ERROR] Lỗi khi chạy tác vụ '{job.description}': {e}")
        finally:
            # Báo hiệu cho Queue biết tác vụ (thread) đã hoàn thành giải phóng bộ nhớ
            job_queue.task_done()


def start_worker_thread():
    """
    Hàm mồi (Bootstrapper) để khởi chạy Worker dưới dạng Daemon Thread.
    Đặc tính Daemon: Thread sẽ tự động tắt, không treo RAM khi Server chính (Flask) tắt.
    """
    worker_thread = threading.Thread(target=worker_loop, daemon=True)
    worker_thread.start()


def add_task_to_queue(priority, description, func, *args, **kwargs):
    """
    Giao diện API Mở rộng (Interface) để các Controllers đẩy tác vụ vào hàng đợi.

    Quy chuẩn Priority (P):
    - P=1: System Critical (Gửi mã OTP, Trạng thái Thanh toán).
    - P=5: Medium (Gửi Email Sinh nhật, Gửi Voucher).
    - P=10: Low Background (Đồng bộ ChromaDB, Sinh báo cáo Analytics).
    """
    new_job = PriorityJob(
        priority=priority,
        description=description,
        func=func,
        args=args,
        kwargs=kwargs
    )
    job_queue.put(new_job)
    print(f"📥 [QUEUE ADDED] Đã xếp hàng: {description} (Độ ưu tiên: {priority} - Hàng chờ: {job_queue.qsize()})")