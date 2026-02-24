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
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class FlaskRouteVisitor(ast.NodeVisitor):
    """
    Sử dụng Abstract Syntax Tree (AST) để đọc thẳng vào nhân code Python.
    Tìm kiếm các function được gắn decorator @route và trích xuất thông tin.
    """

    def __init__(self):
        self.routes = []

    def visit_FunctionDef(self, node):
        """Phân tích các hàm định nghĩa trong file"""
        docstring = ast.get_docstring(node)

        for decorator in node.decorator_list:
            # Tìm kiếm các decorator có dạng @blueprint.route(...)
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr == 'route':
                    path = "Unknown"
                    methods = ['GET']  # Mặc định của Flask là GET

                    # Lấy đường dẫn (URL Path)
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value

                    # Lấy phương thức (HTTP Methods)
                    for kw in decorator.keywords:
                        if kw.arg == 'methods' and isinstance(kw.value, ast.List):
                            methods = [elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)]

                    self.routes.append({
                        'func_name': node.name,
                        'path': path,
                        'methods': methods,
                        'docstring': docstring if docstring else "Không có mô tả chi tiết."
                    })

        self.generic_visit(node)


class APIDocumentationBuilder:
    """Hệ thống Quản lý và Khởi tạo Tài liệu Tự động"""

    def __init__(self, routes_dir="app/routes", output_file="API_DOCUMENTATION.md"):
        self.routes_dir = routes_dir
        self.output_file = output_file
        self.all_endpoints = {}

    def parse_directory(self):
        print(f"{Colors.HEADER}{Colors.BOLD}=" * 70)
        print(f"📜 HỆ THỐNG DOCUMENT AS CODE: TỰ ĐỘNG SINH TÀI LIỆU API 📜")
        print(f"Khởi chạy lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + f"{Colors.ENDC}")
        time.sleep(1)

        if not os.path.exists(self.routes_dir):
            print(f"{Colors.WARNING}❌ Không tìm thấy thư mục {self.routes_dir}!{Colors.ENDC}")
            return

        # Quét tất cả các file trong thư mục routes
        for filename in os.listdir(self.routes_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                filepath = os.path.join(self.routes_dir, filename)
                print(f"{Colors.CYAN}🔍 Đang phân tích file: {filename}...{Colors.ENDC}")
                time.sleep(0.3)  # Giả lập độ trễ tạo cảm giác chuyên nghiệp

                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                    visitor = FlaskRouteVisitor()
                    visitor.visit(tree)

                    if visitor.routes:
                        self.all_endpoints[filename] = visitor.routes
                        print(f"  {Colors.GREEN}✔️ Đã tìm thấy {len(visitor.routes)} endpoints.{Colors.ENDC}")

    def generate_markdown(self):
        print(f"\n{Colors.BLUE}✍️ Đang biên dịch thành file Markdown...{Colors.ENDC}")

        md_content = f"# 📚 TÀI LIỆU API HỆ THỐNG MOBILESTORE\n\n"
        md_content += f"> **Được tự động sinh ra bởi `api_doc_builder.py` lúc {datetime.now().strftime('%H:%M %d/%m/%Y')}**\n"
        md_content += f"> Đây là tài liệu tóm tắt toàn bộ các đường dẫn (Endpoints) đang hoạt động trong hệ thống.\n\n"
        md_content += "---\n\n"

        total_api = 0

        for filename, routes in self.all_endpoints.items():
            module_name = filename.replace('.py', '').upper()
            md_content += f"## 📂 Module: `{module_name}`\n\n"

            for route in routes:
                total_api += 1
                methods_str = ", ".join(route['methods'])
                md_content += f"### 🔹 Endpoint: `{route['path']}`\n"
                md_content += f"- **HTTP Method:** `{methods_str}`\n"
                md_content += f"- **Function:** `{route['func_name']}()`\n"
                md_content += f"- **Mô tả:** {route['docstring']}\n\n"

            md_content += "---\n\n"

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        print(f"{Colors.HEADER}{Colors.BOLD}=" * 70)
        print(f"🎉 HOÀN TẤT! Đã đóng gói thành công {total_api} APIs vào file {self.output_file}")
        print(f"Hãy mở file {self.output_file} để chiêm ngưỡng thành quả!")
        print("=" * 70 + f"{Colors.ENDC}")


if __name__ == "__main__":
    builder = APIDocumentationBuilder()
    builder.parse_directory()
    builder.generate_markdown()