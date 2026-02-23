from flask import Blueprint, render_template

# Khởi tạo Blueprint chuyên xử lý lỗi
errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(404)
def error_404(error):
    """Xử lý lỗi 404: Không tìm thấy trang"""
    # Trả về HTML kèm mã trạng thái 404
    return render_template('error.html',
                           error_code="404",
                           error_title="Không tìm thấy trang!",
                           error_msg="Trang bạn đang tìm kiếm không tồn tại, đã bị xóa hoặc sai đường dẫn."), 404

@errors_bp.app_errorhandler(403)
def error_403(error):
    """Xử lý lỗi 403: Không có quyền truy cập (Dùng cho Phân quyền Admin)"""
    return render_template('error.html',
                           error_code="403",
                           error_title="Truy cập bị từ chối!",
                           error_msg="Bạn không có quyền quản trị viên (Admin) để xem nội dung này."), 403

@errors_bp.app_errorhandler(500)
def error_500(error):
    """Xử lý lỗi 500: Lỗi máy chủ (Lỗi Code, Lỗi DB)"""
    return render_template('error.html',
                           error_code="500",
                           error_title="Lỗi máy chủ nội bộ!",
                           error_msg="Hệ thống đang gặp sự cố hoặc đang bảo trì. Vui lòng thử lại sau ít phút."), 500