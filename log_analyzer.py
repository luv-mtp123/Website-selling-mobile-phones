import os
import re
from collections import Counter
from datetime import datetime


class ServerLogAnalyzer:
    """
    Hệ thống phân tích Nhật ký Máy chủ (Log Analyzer) thuần Python.
    Công cụ này quét thư mục 'logs', trích xuất dữ liệu bằng Regex để:
    1. Tìm ra các IP truy cập nhiều nhất (Phát hiện DDoS).
    2. Đếm số lượng lỗi hệ thống (Status 4xx, 5xx).
    3. Tìm ra các Endpoint (đường dẫn API) chạy chậm nhất để tối ưu.
    """

    # ---> [ĐÃ SỬA CHỖ NÀY: Trỏ đúng vào thư mục app/logs do Flask tạo ra] <---
    def __init__(self, log_dir="app/logs"):
        self.log_dir = log_dir
        self.log_file = os.path.join(self.log_dir, "access.log")

        # Regex bắt định dạng: IP: 127.0.0.1 | POST /login | Status: 302 | Time: 106.9ms
        self.log_pattern = re.compile(
            r"IP:\s*(?P<ip>[\d\.]+)\s*\|\s*(?P<method>[A-Z]+)\s*(?P<path>\S+)\s*\|\s*Status:\s*(?P<status>\d+)\s*\|\s*Time:\s*(?P<time>[\d\.]+)ms"
        )

    def run_analysis(self):
        """
        Đọc và phân tích file log hệ thống, thống kê IP truy cập,
        mã trạng thái HTTP và lọc ra các API có thời gian phản hồi chậm nhất.
        """
        print("=" * 60)
        print(f"📊 BẮT ĐẦU PHÂN TÍCH LOG MÁY CHỦ ({datetime.now().strftime('%d/%m/%Y %H:%M')})")
        print("=" * 60)

        if not os.path.exists(self.log_file):
            print(f"❌ Không tìm thấy file log tại: {self.log_file}")
            print("Hãy khởi động web (py run.py) và truy cập vài trang để hệ thống sinh ra log.")
            return

        ip_counter = Counter()
        status_counter = Counter()
        slowest_requests = []
        total_requests = 0

        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                match = self.log_pattern.search(line)
                if match:
                    total_requests += 1
                    data = match.groupdict()

                    ip_counter[data['ip']] += 1
                    status_counter[data['status']] += 1

                    # Lưu lại thời gian phản hồi
                    try:
                        resp_time = float(data['time'])
                        slowest_requests.append({
                            'path': f"{data['method']} {data['path']}",
                            'time': resp_time,
                            'ip': data['ip']
                        })
                    except ValueError:
                        pass

        if total_requests == 0:
            print("⚠️ File log hiện tại đang trống hoặc không có định dạng hợp lệ.")
            return

        # Sắp xếp để lấy Top API chậm nhất
        slowest_requests.sort(key=lambda x: x['time'], reverse=True)
        top_slow = slowest_requests[:5]

        # In Báo cáo
        print(f"📌 TỔNG SỐ REQUEST ĐÃ XỬ LÝ: {total_requests}\n")

        print("🚨 TOP 5 IP TRUY CẬP NHIỀU NHẤT (Dấu hiệu Spam/DDoS):")
        for ip, count in ip_counter.most_common(5):
            print(f"   - {ip}: {count} requests")

        print("\n📈 THỐNG KÊ MÃ TRẠNG THÁI (HTTP STATUS):")
        for status, count in status_counter.most_common():
            symbol = "✅" if status.startswith('2') or status.startswith('3') else "❌"
            print(f"   - Status {status}: {count} lần {symbol}")

        print("\n🐌 TOP 5 API CHẠY CHẬM NHẤT (Cần tối ưu code):")
        for req in top_slow:
            print(f"   - {req['time']}ms | {req['path']} (Gửi từ IP: {req['ip']})")

        print("=" * 60)
        print("💡 Gợi ý: Chạy lệnh này định kỳ để rà soát sức khỏe bảo mật của Server.")


if __name__ == "__main__":
    analyzer = ServerLogAnalyzer()
    analyzer.run_analysis()