"""
Hệ thống Custom Exceptions cho MobileStore.
Định nghĩa các lỗi chuyên biệt (Domain-Specific Errors) thay vì dùng Exception chung chung.
Giúp dễ dàng phân loại lỗi, try-catch chính xác và log lỗi chuyên nghiệp.
"""

class MobileStoreBaseException(Exception):
    """Lớp Exception cơ sở cho toàn bộ dự án MobileStore"""
    def __init__(self, message="Đã xảy ra lỗi hệ thống."):
        self.message = message
        super().__init__(self.message)

# ==========================================
# Nhóm 1: Lỗi liên quan đến Sản phẩm & Giỏ hàng
# ==========================================
class OutOfStockError(MobileStoreBaseException):
    """Văng lỗi khi Khách hàng mua số lượng lớn hơn Tồn kho thực tế"""
    def __init__(self, product_name, available_qty):
        msg = f"Sản phẩm '{product_name}' chỉ còn {available_qty} chiếc trong kho."
        super().__init__(msg)

class ProductNotFoundError(MobileStoreBaseException):
    """Văng lỗi khi cố gắng thao tác với sản phẩm đã bị xóa hoặc ẩn"""
    def __init__(self, product_id):
        msg = f"Không tìm thấy sản phẩm có ID: {product_id}."
        super().__init__(msg)

# ==========================================
# Nhóm 2: Lỗi liên quan đến Thanh toán & Đơn hàng
# ==========================================
class OrderExpiredError(MobileStoreBaseException):
    """Văng lỗi khi Đơn hàng Pending quá thời gian quy định (QR hết hạn)"""
    def __init__(self, order_id):
        msg = f"Giao dịch thanh toán cho Đơn hàng #{order_id} đã hết hạn."
        super().__init__(msg)

class InvalidPaymentMethodError(MobileStoreBaseException):
    """Văng lỗi khi Phương thức thanh toán bị can thiệp sai lệch"""
    def __init__(self, method):
        msg = f"Phương thức thanh toán '{method}' không được hỗ trợ."
        super().__init__(msg)

# ==========================================
# Nhóm 3: Lỗi liên quan đến AI và Hệ thống
# ==========================================
class GeminiAPIQuotaError(MobileStoreBaseException):
    """Văng lỗi khi Google AI bị hết lượt hoặc mất kết nối"""
    def __init__(self):
        msg = "Hệ thống AI đang quá tải hoặc hết Quota. Vui lòng thử lại sau."
        super().__init__(msg)

class InvalidTradeInImageError(MobileStoreBaseException):
    """Văng lỗi khi file Upload thu cũ không hợp lệ (Dung lượng cao, sai định dạng)"""
    def __init__(self):
        msg = "Ảnh thiết bị thu cũ không hợp lệ. Vui lòng tải lên ảnh JPG/PNG dưới 2MB."
        super().__init__(msg)