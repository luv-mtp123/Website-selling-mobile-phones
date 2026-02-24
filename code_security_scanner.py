import os
import ast
import time
from datetime import datetime

# =========================================================================
# Ép Terminal của Windows đọc được Emoji và Màu sắc UTF-8
# =========================================================================
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        # ---> [PATCHED]: Đã thay thế hàm nguy hiểm os.system('color')
        # Sử dụng ctypes tương tác trực tiếp với Kernel32 API an toàn tuyệt đối
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


# Bảng màu hiển thị Console
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class SecurityAstVisitor(ast.NodeVisitor):
    """
    Phân tích Cây cú pháp trừu tượng (AST) của Python để tìm các lỗ hổng.
    Thay vì dùng Regex dễ bị đánh lừa bởi comment, AST sẽ thực sự "đọc hiểu" code.
    """

    def __init__(self, filename):
        self.filename = filename
        self.vulnerabilities = []

        # Danh sách các hàm nguy hiểm nếu dùng sai cách
        self.dangerous_functions = ['eval', 'exec', 'os.system', 'subprocess.Popen']

        # Danh sách các từ khóa thường bị dev sơ ý gán cứng (hardcode) mật khẩu
        self.sensitive_keywords = ['password', 'secret', 'api_key', 'token', 'credentials']

    def add_vuln(self, line_no, vuln_type, description, severity="HIGH"):
        self.vulnerabilities.append({
            "line": line_no,
            "type": vuln_type,
            "desc": description,
            "severity": severity
        })

    def visit_Call(self, node):
        """Quét các lời gọi hàm (Function Calls)"""
        # Kiểm tra gọi hàm nguy hiểm
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.dangerous_functions:
                self.add_vuln(node.lineno, "DANGEROUS_FUNCTION",
                              f"Phát hiện sử dụng hàm nguy hiểm: '{func_name}()'. Có thể dẫn đến lỗi RCE.", "CRITICAL")
        elif isinstance(node.func, ast.Attribute):
            func_name = f"{node.func.value.id}.{node.func.attr}" if isinstance(node.func.value,
                                                                               ast.Name) else node.func.attr
            if func_name in self.dangerous_functions:
                self.add_vuln(node.lineno, "DANGEROUS_FUNCTION",
                              f"Phát hiện sử dụng module hệ thống nguy hiểm: '{func_name}()'", "CRITICAL")

        # Kiểm tra bật Debug Mode trong Flask
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'run':
            for kw in node.keywords:
                if kw.arg == 'debug' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.add_vuln(node.lineno, "DEBUG_MODE_ENABLED",
                                  "Phát hiện 'app.run(debug=True)'. Nguy hiểm nếu chạy trên môi trường Production.",
                                  "HIGH")

        self.generic_visit(node)

    def visit_Assign(self, node):
        """Quét các phép gán biến (Variable Assignments) để tìm Hardcode Secrets"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                # Nếu tên biến nhạy cảm và giá trị gán là một chuỗi ký tự cứng
                if any(sec in var_name for sec in self.sensitive_keywords):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        # Bỏ qua nếu là biến môi trường get từ os.environ
                        if len(node.value.value) > 3:  # Chỉ cảnh báo nếu chuỗi có vẻ là thật
                            self.add_vuln(node.lineno, "HARDCODED_SECRET",
                                          f"Lộ lọt thông tin nhạy cảm: Biến '{target.id}' được gán cứng chuỗi văn bản.",
                                          "CRITICAL")

        self.generic_visit(node)


class DevSecOpsScanner:
    """Hệ thống Quét toàn bộ Thư mục dự án"""

    def __init__(self, root_dir="."):
        self.root_dir = root_dir
        self.ignore_dirs = ['.venv', 'venv', 'env', '__pycache__', '.git', '.github', 'migrations']
        self.total_files_scanned = 0
        self.total_issues_found = 0

    def scan_project(self):
        print(f"{Colors.HEADER}{Colors.BOLD}=" * 70)
        print(f"🛡️ HỆ THỐNG DEV-SEC-OPS: TỰ ĐỘNG QUÉT LỖ HỔNG MÃ NGUỒN PYTHON 🛡️")
        print(f"Bắt đầu lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + f"{Colors.ENDC}")
        time.sleep(1)

        for subdir, dirs, files in os.walk(self.root_dir):
            # Bỏ qua các thư mục không cần thiết
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(subdir, file)
                    self.analyze_file(filepath)

        print(f"\n{Colors.HEADER}{Colors.BOLD}=" * 70)
        print(f"📊 TỔNG KẾT CHIẾN DỊCH QUÉT BẢO MẬT:")
        print(f"- Tổng số file Python đã quét: {Colors.CYAN}{self.total_files_scanned}{Colors.ENDC} files")

        if self.total_issues_found == 0:
            print(f"- Tình trạng: {Colors.GREEN}✅ CLEAN (Không phát hiện lỗ hổng nghiêm trọng nào){Colors.ENDC}")
            print(f"Dự án của bạn đạt chuẩn Clean Code và Security mức độ xuất sắc!")
        else:
            print(
                f"- Tình trạng: {Colors.WARNING}⚠️ CẢNH BÁO (Phát hiện {self.total_issues_found} nguy cơ tiềm ẩn){Colors.ENDC}")
            print(f"Vui lòng xem lại các log màu đỏ phía trên để tiến hành vá lỗi (Patching).")
        print("=" * 70 + f"{Colors.ENDC}")

    def analyze_file(self, filepath):
        self.total_files_scanned += 1

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code_content = f.read()

            # Xây dựng Cây cú pháp AST
            tree = ast.parse(code_content)

            # Đưa Cây cú pháp vào Hệ thống giám định
            visitor = SecurityAstVisitor(filepath)
            visitor.visit(tree)

            if visitor.vulnerabilities:
                print(f"\n{Colors.WARNING}📄 Đang quét file: {filepath}... PHÁT HIỆN VẤN ĐỀ!{Colors.ENDC}")
                for vuln in visitor.vulnerabilities:
                    self.total_issues_found += 1
                    color = Colors.FAIL if vuln['severity'] == 'CRITICAL' else Colors.WARNING
                    print(
                        f"  {color}[{vuln['severity']}] Dòng {vuln['line']}: {vuln['type']} - {vuln['desc']}{Colors.ENDC}")
            else:
                # Hiển thị tiến trình mượt mà
                print(f"{Colors.GREEN}✔️ OK:{Colors.ENDC} {filepath}")

        except SyntaxError:
            print(f"{Colors.FAIL}❌ LỖI CÚ PHÁP:{Colors.ENDC} {filepath} (File này có lỗi Python không thể biên dịch)")
        except Exception as e:
            print(f"{Colors.FAIL}❌ LỖI HỆ THỐNG:{Colors.ENDC} Không thể quét {filepath}: {str(e)}")


if __name__ == "__main__":
    scanner = DevSecOpsScanner()
    scanner.scan_project()