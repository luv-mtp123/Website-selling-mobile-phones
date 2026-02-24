import os
import ast
import re
import time
from datetime import datetime

import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class QualityASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.missing_docstrings = []
        self.bad_function_names = []
        self.bad_variable_names = []

    def visit_FunctionDef(self, node):
        """Xử lý kiểm tra Node định nghĩa hàm trong AST để tìm lỗi PEP8"""
        # Kiểm tra xem hàm có docstring (chú thích) không
        if not ast.get_docstring(node):
            # Bỏ qua các hàm init hoặc repr nội bộ
            if not node.name.startswith("__"):
                self.missing_docstrings.append((node.lineno, node.name))

        # [UPDATED] Bỏ qua kiểm tra tên với các hàm Override chuẩn của thư viện (Whitelist)
        whitelist = ['setUp', 'tearDown', 'setUpClass', 'tearDownClass']
        is_ast_visitor = node.name.startswith('visit_')

        # Kiểm tra chuẩn đặt tên hàm (phải là snake_case)
        if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
            if node.name not in whitelist and not is_ast_visitor:
                self.bad_function_names.append((node.lineno, node.name))

        self.generic_visit(node)

    def visit_Assign(self, node):
        """Phân tích các biến được gán giá trị để kiểm tra chuẩn đặt tên"""
        # Kiểm tra chuẩn đặt tên biến (không dùng CamelCase cho biến thông thường)
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                # Bỏ qua hằng số IN_HOA
                if not var_name.isupper():
                    if not re.match(r'^[a-z_][a-z0-9_]*$', var_name):
                        self.bad_variable_names.append((node.lineno, var_name))
        self.generic_visit(node)


class CodeQualityScorer:
    """Hệ thống Custom Linter chấm điểm chất lượng mã nguồn Python"""

    def __init__(self, root_dir="."):
        self.root_dir = root_dir
        self.ignore_dirs = ['.venv', 'venv', 'env', '__pycache__', '.git', 'migrations']
        self.total_lines = 0
        self.total_files = 0

        # Bảng lưu trữ chi tiết vị trí lỗi
        self.detailed_errors = []

    def calculate_score(self):
        """Thực thi quét toàn bộ dự án và tính điểm PEP8"""
        print(f"{Colors.HEADER}{Colors.BOLD}=" * 70)
        print(f"⚖️ HỆ THỐNG CUSTOM LINTER: CHẤM ĐIỂM CHẤT LƯỢNG MÃ NGUỒN (PEP8)")
        print("=" * 70 + f"{Colors.ENDC}")
        time.sleep(0.5)

        total_missing_docs = 0
        total_bad_funcs = 0
        total_bad_vars = 0

        for subdir, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(subdir, file)
                    self.total_files += 1

                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            lines = content.split('\n')
                            self.total_lines += len(lines)

                            tree = ast.parse(content)
                            visitor = QualityASTVisitor()
                            visitor.visit(tree)

                            # Ghi nhận chi tiết lỗi vào danh sách
                            for lineno, name in visitor.missing_docstrings:
                                self.detailed_errors.append(
                                    f"{Colors.WARNING}[Thiếu Docstring]{Colors.ENDC} Dòng {lineno} tại {filepath} -> Hàm {Colors.CYAN}'{name}'{Colors.ENDC}")
                            for lineno, name in visitor.bad_function_names:
                                self.detailed_errors.append(
                                    f"{Colors.FAIL}[Sai tên Hàm]{Colors.ENDC} Dòng {lineno} tại {filepath} -> {Colors.CYAN}'{name}'{Colors.ENDC} (Sửa thành snake_case)")
                            for lineno, name in visitor.bad_variable_names:
                                self.detailed_errors.append(
                                    f"{Colors.FAIL}[Sai tên Biến]{Colors.ENDC} Dòng {lineno} tại {filepath} -> {Colors.CYAN}'{name}'{Colors.ENDC} (Sửa thành snake_case)")

                            total_missing_docs += len(visitor.missing_docstrings)
                            total_bad_funcs += len(visitor.bad_function_names)
                            total_bad_vars += len(visitor.bad_variable_names)

                    except Exception:
                        pass  # Bỏ qua lỗi cú pháp nếu có

        # In chi tiết lỗi nếu có
        if self.detailed_errors:
            print(f"\n{Colors.BLUE}🔍 DANH SÁCH CÁC VỊ TRÍ CẦN REFACTOR:{Colors.ENDC}")
            for err in self.detailed_errors:
                print(f"  - {err}")

        # Thuật toán tính điểm (Base 100)
        base_score = 100.0

        # Trừ điểm (Penalty)
        penalty_doc = total_missing_docs * 0.5  # Mỗi hàm thiếu mô tả trừ 0.5 điểm
        penalty_func = total_bad_funcs * 1.0  # Sai tên hàm trừ 1 điểm
        penalty_var = total_bad_vars * 0.2  # Sai tên biến trừ 0.2 điểm

        total_penalty = penalty_doc + penalty_func + penalty_var
        final_score = max(0.0, base_score - total_penalty)

        # In báo cáo
        print(f"\n{Colors.CYAN}📊 THỐNG KÊ QUY MÔ DỰ ÁN:{Colors.ENDC}")
        print(f"   - Tổng số file Python: {self.total_files}")
        print(f"   - Tổng số dòng code : {self.total_lines} lines")

        print(f"\n{Colors.WARNING}⚠️ CÁC VI PHẠM CHUẨN PEP8 (Clean Code):{Colors.ENDC}")
        print(f"   - Hàm thiếu Docstring mô tả : {total_missing_docs} lỗi (-{penalty_doc}đ)")
        print(f"   - Tên hàm không chuẩn (CamelCase) : {total_bad_funcs} lỗi (-{penalty_func}đ)")
        print(f"   - Tên biến không chuẩn : {total_bad_vars} lỗi (-{penalty_var}đ)")

        print(f"\n{Colors.HEADER}{Colors.BOLD}=" * 70)
        if final_score >= 90:
            color = Colors.GREEN
            rank = "A+ (EXCELLENT) 🌟"
        elif final_score >= 70:
            color = Colors.BLUE
            rank = "B (GOOD) 👍"
        else:
            color = Colors.FAIL
            rank = "C (NEEDS REFACTOR) 🛠️"

        print(f"🏆 TỔNG ĐIỂM CHẤT LƯỢNG: {color}{final_score:.1f} / 100.0{Colors.ENDC}")
        print(f"🎖️ XẾP HẠNG: {color}{rank}{Colors.ENDC}")
        print("=" * 70 + f"{Colors.ENDC}")


if __name__ == "__main__":
    scorer = CodeQualityScorer()
    scorer.calculate_score()