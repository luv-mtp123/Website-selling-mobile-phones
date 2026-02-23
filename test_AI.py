import sys
import os

# [CRITICAL FIX] Thêm thư mục gốc vào đường dẫn hệ thống để Python tìm thấy 'app'
# Giúp chạy được lệnh 'python test_AI.py' ngay từ trong thư mục test hoặc thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import json
from unittest.mock import patch, MagicMock
from app import create_app, db

### ---> [ĐÃ SỬA CHỖ NÀY: Import thêm User, Order, OrderDetail để tạo Data Test Gợi ý] <--- ###
from app.models import User, Product, Order, OrderDetail

### ---> [ĐÃ SỬA CHỖ NÀY: Import thêm hàm analyze_sentiment] <--- ###
from app.utils import get_comparison_result, local_analyze_intent, build_product_context, analyze_sentiment
from flask import session


class AIFeaturesTestCase(unittest.TestCase):
    """
    Test Suite chuyên sâu cho các tính năng AI & Logic thông minh:
    1. Local Intelligence (Fallback khi mất mạng/hết quota)
    2. RAG (Retrieval-Augmented Generation) - AI đọc DB
    3. Chatbot Memory (Hội thoại theo ngữ cảnh)
    4. Product Comparison (So sánh)
    5. Sentiment Analysis (Phân tích cảm xúc)
    6. Recommendation System (Gợi ý mua kèm)
    """

    def setUp(self):
        # Cấu hình test dùng DB trên RAM (nhanh, sạch)
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()
        self.create_sample_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_sample_data(self):
        """Tạo dữ liệu mẫu đa dạng để test khả năng hiểu của AI"""
        # 1. Điện thoại giá cao
        p1 = Product(name='iPhone 15 Pro Max', brand='Apple', price=35000000, category='phone',
                     description='Titan tự nhiên, chip A17', stock_quantity=10, is_active=True)
        # 2. Điện thoại giá rẻ
        p2 = Product(name='Samsung Galaxy A05', brand='Samsung', price=3000000, category='phone',
                     description='Pin trâu giá rẻ', stock_quantity=20, is_active=True)
        # 3. Phụ kiện
        p3 = Product(name='Ốp lưng iPhone 15', brand='Apple', price=500000, category='accessory',
                     description='Chống sốc', stock_quantity=50, is_active=True)

        db.session.add_all([p1, p2, p3])
        db.session.commit()

        # Lưu ID để xài cho bài Test số 6
        self.p1_id = p1.id
        self.p3_id = p3.id

        ### ---> [NEW: GIẢ LẬP HÀNH VI NGƯỜI DÙNG ĐỂ TEST THUẬT TOÁN GỢI Ý (RECOMMENDATION)] <--- ###
        # Tạo 1 User giả
        u1 = User(username='testuser', email='test@mail.com', password='123', full_name='Test User')
        db.session.add(u1)
        db.session.commit()

        # Tạo 1 Order: Khách mua iPhone 15 (p1) CÙNG VỚI Ốp lưng (p3)
        o1 = Order(user_id=u1.id, total_price=35500000, address='HCM', phone='0123', status='Completed')
        db.session.add(o1)
        db.session.commit()

        # Chi tiết giỏ hàng
        od1 = OrderDetail(order_id=o1.id, product_id=p1.id, product_name=p1.name, quantity=1, price=p1.price)
        od2 = OrderDetail(order_id=o1.id, product_id=p3.id, product_name=p3.name, quantity=1, price=p3.price)
        db.session.add_all([od1, od2])
        db.session.commit()
        ### ----------------------------------------------------------------------------------- ###

    # --- TEST 1: LOCAL INTELLIGENCE (Logic nội bộ) ---
    def test_local_search_intent_parsing(self):
        """
        Kiểm tra logic 'Local Fallback' (Phân tích câu hỏi bằng Regex/Logic thường).
        Mục tiêu: Đảm bảo hệ thống vẫn thông minh khi không có Google AI.
        """
        print("\n[AI Test 1] Testing Local Search Intent (Regex Logic)...")

        # Case 1: Tìm theo giá và loại ("điện thoại dưới 5 triệu")
        query = "điện thoại dưới 5 triệu"
        result = local_analyze_intent(query)  # Gọi hàm logic nội bộ

        self.assertEqual(result['category'], 'phone')
        self.assertEqual(result['max_price'], 5000000)
        self.assertIsNone(result['brand'])  # Không nhắc đến hãng

        # Case 2: Tìm theo Hãng và Phụ kiện ("ốp lưng iphone")
        query = "ốp lưng iphone"
        result = local_analyze_intent(query)

        self.assertEqual(result['brand'], 'Apple')  # Map từ 'iphone' -> 'Apple'
        self.assertEqual(result['category'], 'accessory')  # Map từ 'ốp' -> 'accessory'

    # --- TEST 2: RAG CONTEXT (AI đọc dữ liệu DB) ---
    def test_rag_context_building(self):
        """
        Kiểm tra hàm `build_product_context`.
        Mục tiêu: Đảm bảo dữ liệu gửi cho AI là dữ liệu thật từ Database, không bịa đặt.
        """
        print("\n[AI Test 2] Testing RAG Context Building...")

        # Giả sử khách hỏi về "Samsung"
        context = build_product_context("Samsung")

        # Kiểm tra nội dung context gửi cho AI
        self.assertIn("Samsung Galaxy A05", context)  # Phải tìm thấy sản phẩm
        # [QUAN TRỌNG] Kiểm tra định dạng giá tiền Việt Nam (dấu chấm)
        self.assertIn("3.000.000 đ", context)
        self.assertNotIn("iPhone 15 Pro Max", context)  # Không được trộn lẫn Apple vào

    # --- TEST 3: CHATBOT MEMORY & INTEGRATION (Mocking) ---
    @patch('app.utils.call_gemini_api')
    def test_chatbot_memory_flow(self, mock_gemini):
        """
        Kiểm tra luồng hội thoại có nhớ ngữ cảnh (Session Memory).
        """
        print("\n[AI Test 3] Testing Chatbot Memory & Session...")

        # Setup Mock AI Response
        mock_gemini.return_value = "AI Response"

        # Bước 1: Khách hỏi câu 1
        with self.client:
            self.client.post('/api/chatbot', json={'message': 'iPhone 15 giá bao nhiêu?'})

            # Kiểm tra Session đã lưu lịch sử chưa
            self.assertIn('chat_history', session)
            history = session['chat_history']
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]['user'], 'iPhone 15 giá bao nhiêu?')

            # Bước 2: Khách hỏi câu 2 (Câu hỏi nối tiếp "Nó")
            self.client.post('/api/chatbot', json={'message': 'Nó có màu gì?'})

            # Kiểm tra Session cập nhật
            history = session['chat_history']
            self.assertEqual(len(history), 2)
            self.assertEqual(history[1]['user'], 'Nó có màu gì?')

            # [QUAN TRỌNG] Kiểm tra Prompt gửi đi lần 2 phải chứa lịch sử lần 1
            # Lấy arguments mà code đã gọi call_gemini_api
            args, kwargs = mock_gemini.call_args
            prompt_text = args[0]  # The prompt string is the first positional argument

            # Prompt gửi đi phải chứa câu hỏi cũ để AI hiểu từ "Nó"
            self.assertIn("LỊCH SỬ HỘI THOẠI", prompt_text)
            self.assertIn("iPhone 15 giá bao nhiêu?", prompt_text)

    # --- TEST 4: COMPARISON LOGIC (So sánh) ---
    @patch('app.utils.call_gemini_api')
    def test_comparison_prompt_structure(self, mock_gemini):
        """
        Kiểm tra hàm so sánh sản phẩm.
        Mục tiêu: Đảm bảo prompt sinh ra đúng định dạng yêu cầu HTML.
        """
        print("\n[AI Test 4] Testing Comparison Prompt...")

        # Mock trả về HTML giả
        mock_gemini.return_value = "<table>Mock Table</table>"

        get_comparison_result(
            "iPhone A", 100, "Desc A",
            "Samsung B", 90, "Desc B"
        )

        # Kiểm tra Prompt gửi đi
        args, _ = mock_gemini.call_args
        sent_prompt = args[0]

        self.assertIn("iPhone A", sent_prompt)
        self.assertIn("Samsung B", sent_prompt)
        # [ĐÃ SỬA]: Thay đổi từ "Chỉ trả về code HTML" thành một cụm từ thực sự tồn tại
        # trong chuỗi prompt được định nghĩa tại app/utils.py
        self.assertIn("CHỈ TRẢ VỀ MÃ HTML", sent_prompt)  # Kiểm tra instruction quan trọng

    ### ============================================================================== ###
    ### ---> [NEW: TEST 5 - KIỂM TRA PHÂN TÍCH CẢM XÚC ĐÁNH GIÁ CỦA AI] <--- ###
    @patch('app.utils.call_gemini_api')
    def test_sentiment_analysis(self, mock_gemini):
        """
        Kiểm tra hệ thống đọc và phân loại cảm xúc (NLP) từ comment.
        """
        print("\n[AI Test 5] Testing Sentiment Analysis (Phân tích cảm xúc NLP)...")

        # Kịch bản 1: AI phát hiện bình luận CHÊ (Negative)
        mock_gemini.return_value = "NEGATIVE"
        res_bad = analyze_sentiment("Máy quá tệ, giật lag, pin hụt như uống nước lã!")
        self.assertEqual(res_bad, "NEGATIVE")

        # Kịch bản 2: AI phát hiện bình luận KHEN (Positive)
        mock_gemini.return_value = "POSITIVE"
        res_good = analyze_sentiment("Sản phẩm dùng rất ngon, nhân viên nhiệt tình, 10 điểm!")
        self.assertEqual(res_good, "POSITIVE")

        # Kịch bản 3: AI phát hiện bình luận TRUNG LẬP (Neutral)
        mock_gemini.return_value = "NEUTRAL"
        res_neutral = analyze_sentiment("Tôi mới mua, chưa xài nhiều nên chưa rõ.")
        self.assertEqual(res_neutral, "NEUTRAL")

    ### ---> [NEW: TEST 6 - KIỂM TRA THUẬT TOÁN GỢI Ý MUA KÈM (MARKET BASKET)] <--- ###
    def test_recommendation_system(self):
        """
        Kiểm tra thuật toán Collaborative Filtering.
        Mục tiêu: Khi truy cập iPhone 15, hệ thống phải phát hiện ra trong quá khứ
        có người từng mua iPhone 15 kèm Ốp lưng, từ đó gợi ý cái Ốp lưng ra giao diện.
        """
        print("\n[AI Test 6] Testing Collaborative Filtering (Recommendation System)...")

        # Truy cập vào trang chi tiết sản phẩm p1 (iPhone 15)
        with self.client:
            response = self.client.get(f'/product/{self.p1_id}')
            html_data = response.data.decode('utf-8')

            # Kiểm tra xem giao diện có render khối "Phụ Kiện Gợi Ý Mua Kèm" hay không
            self.assertIn("Phụ Kiện Gợi Ý Mua Kèm", html_data)

            # Kiểm tra xem "Ốp lưng iPhone 15" có được moi lên để gợi ý hay không
            # (Vì ở hàm create_sample_data, chúng ta đã giả lập o1 mua kèm 2 món này)
            self.assertIn("Ốp lưng iPhone 15", html_data)

            # Đảm bảo điện thoại khác KHÔNG BỊ lọt vào danh sách phụ kiện
            self.assertNotIn("Samsung Galaxy A05", html_data)
    ### ============================================================================== ###


if __name__ == '__main__':
    print("🚀 Đang chạy bộ kiểm thử chuyên sâu cho AI...")
    unittest.main()