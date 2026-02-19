import unittest
import sys
import os


def run_all_tests():
    # Tự động tìm tất cả các file bắt đầu bằng 'test_' trong thư mục hiện tại
    loader = unittest.TestLoader()
    # Nếu file test nằm trong thư mục 'test/' thì đổi '.' thành './test'
    start_dir = '.'
    if os.path.exists('test') and os.path.isdir('test'):
        start_dir = './test'

    suite = loader.discover(start_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Trả về mã lỗi nếu test thất bại (để dùng trong CI/CD pipeline sau này)
    sys.exit(not result.wasSuccessful())


if __name__ == '__main__':
    print("🚀 ĐANG CHẠY TOÀN BỘ HỆ THỐNG KIỂM THỬ MOBILESTORE...")
    run_all_tests()