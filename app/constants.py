"""
Hệ thống Hằng số (Constants) trung tâm của MobileStore.
Gom cụm toàn bộ các hardcode string, danh sách từ khóa, trạng thái đơn hàng...
giúp mã nguồn tuân thủ nguyên tắc Clean Code (SOLID) và dễ dàng bảo trì.
"""

# ==========================================
# 1. TRẠNG THÁI ĐƠN HÀNG (ORDER STATUS)
# ==========================================
ORDER_STATUS_PENDING = 'Pending'
ORDER_STATUS_CONFIRMED = 'Confirmed'
ORDER_STATUS_SHIPPING = 'Shipping'
ORDER_STATUS_COMPLETED = 'Completed'
ORDER_STATUS_CANCELLED = 'Cancelled'

VALID_ORDER_STATUSES = [
    ORDER_STATUS_PENDING,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_SHIPPING,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CANCELLED
]

# ==========================================
# 2. TRẠNG THÁI THU CŨ ĐỔI MỚI (TRADE-IN)
# ==========================================
TRADEIN_STATUS_PENDING = 'Pending'
TRADEIN_STATUS_APPROVED = 'Approved'
TRADEIN_STATUS_REJECTED = 'Rejected'

# ==========================================
# 3. DANH MỤC SẢN PHẨM (CATEGORIES)
# ==========================================
CATEGORY_PHONE = 'phone'
CATEGORY_ACCESSORY = 'accessory'

# ==========================================
# 4. PHƯƠNG THỨC THANH TOÁN (PAYMENT METHODS)
# ==========================================
PAYMENT_METHOD_COD = 'cod'
PAYMENT_METHOD_BANKING = 'banking'

# ==========================================
# 5. TỪ KHÓA TÌM KIẾM & AI (AI KEYWORDS & STOP WORDS)
# ==========================================
# Danh sách các từ vô nghĩa / từ đệm cần loại bỏ trước khi AI/SQL xử lý
SEARCH_STOP_WORDS = [
    'mua', 'tìm', 'giá', 'rẻ', 'cho', 'cần', 'dưới', 'khoảng',
    'củ', 'triệu', 'điện', 'thoại', 'máy', 'tốt', 'đẹp', 'tôi',
    'muốn', 'chơi', 'game', 'chụp', 'ảnh'
]

# Danh sách từ khóa để nhận diện Phụ kiện
ACCESSORY_KEYWORDS = [
    'ốp', 'sạc', 'tai nghe', 'cáp', 'kính', 'cường lực',
    'giá đỡ', 'loa', 'dây đeo', 'airpods', 'buds'
]

# Danh sách từ khóa nhận diện Điện thoại
PHONE_KEYWORDS = [
    'điện thoại', 'máy', 'smartphone', 'phone'
]

# Map các biến thể tên hãng về tên chuẩn
BRAND_MAPPING = {
    'iphone': 'Apple',
    'apple': 'Apple',
    'samsung': 'Samsung',
    'oppo': 'Oppo',
    'xiaomi': 'Xiaomi',
    'vivo': 'Vivo',
    'realme': 'Realme',
    'asus': 'Asus',
    'google': 'Google'
}

# ==========================================
# 6. TỪ KHÓA CHATBOT TRẢ LỜI NHANH (QUICK REPLIES)
# ==========================================
CHATBOT_QUICK_REPLIES = {
    "địa chỉ": "📍 Địa chỉ cửa hàng: 123 Đường Tết, Q1, TP.HCM",
    "bảo hành": "🛡️ Chính sách bảo hành: 12 tháng chính hãng, 1 đổi 1 trong 30 ngày.",
    "giao hàng": "🚚 Giao hàng hỏa tốc trong 2h tại nội thành, 2-3 ngày với các tỉnh khác.",
    "trả góp": "💳 Cửa hàng hỗ trợ trả góp 0% qua thẻ tín dụng và công ty tài chính."
}


# ==========================================
# 7. THÔNG BÁO HỆ THỐNG (FLASH MESSAGES)
# ==========================================
class SystemMessages:
    # Giỏ hàng & Thanh toán
    CART_OUT_OF_STOCK = 'Hết hàng!'
    CART_EXCEED_STOCK = 'Quá số lượng tồn kho.'
    CART_ADD_SUCCESS = 'Đã thêm vào giỏ!'
    ORDER_SUCCESS = 'Đặt hàng thành công!'
    ORDER_ERROR = 'Lỗi xử lý đơn hàng.'
    ORDER_CANCEL_SUCCESS = 'Đã hủy đơn.'
    ORDER_EXPIRED = 'Giao dịch đã hết hạn vui lòng đặt lại.'

    # Sản phẩm & Đánh giá
    COMMENT_REPLY_SUCCESS = 'Đã gửi câu trả lời!'
    COMMENT_QA_SUCCESS = 'Đã gửi câu hỏi thành công!'
    COMMENT_REVIEW_SUCCESS = 'Cảm ơn bạn đã đánh giá!'
    PRODUCT_ADD_SUCCESS = 'Thêm sản phẩm thành công!'
    PRODUCT_UPDATE_SUCCESS = 'Cập nhật thông tin thành công!'
    PRODUCT_DELETE_SUCCESS = 'Đã xóa sản phẩm khỏi hệ thống.'

    # Người dùng & Quản trị
    TRADEIN_SUCCESS = 'Đã gửi yêu cầu định giá!'
    TRADEIN_PROCESSED = 'Đã xử lý yêu cầu thu cũ.'
    PROFILE_UPDATE_SUCCESS = 'Cập nhật thành công.'
    INVALID_STATUS = 'Trạng thái không hợp lệ.'
    ORDER_ENDED = 'Đơn hàng đã kết thúc, không thể thay đổi.'
    ORDER_REFUNDED = 'Đã hủy đơn và hoàn trả số lượng về kho.'

    # Cảnh báo AI
    AI_ERROR = 'Hệ thống AI đang quá tải hoặc lỗi kết nối. Vui lòng thử lại sau.'
    AI_BUSY = 'AI đang nghỉ Tết (Hết quota), bạn thử lại sau hoặc dùng tìm kiếm nhé! 🧧'