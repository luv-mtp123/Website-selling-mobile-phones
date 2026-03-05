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

### ---> [ĐÃ SỬA CHỖ NÀY: Import thêm các hàm mới cho Chiến dịch 1] <--- ###
from app.utils import (
    get_comparison_result, local_analyze_intent, build_product_context,
    analyze_sentiment, direct_gemini_search, generate_local_comparison_html,
    search_image_vector_db, get_image_embedding  # ---> [NEW] Import thêm hàm Visual Search
)
from flask import session


class AIFeaturesTestCase(unittest.TestCase):
    """
    Test Suite chuyên sâu cho các tính năng AI & Logic thông minh:
    1. Local Intelligence (Fallback khi mất mạng/hết quota)
    2. RAG (Retrieval-Augmented Generation) - AI đọc DB
    3. Chatbot Memory (Hội thoại theo ngữ cảnh)
    4. Product Comparison (So sánh)
    5. Sentiment Analysis (Phân tích cảm xúc)
    6. Recommendation System (Gợi ý mua kèm & Gợi ý tương tự)
    7. Direct Text-RAG Search (Bypass Vector DB 404)
    8. Direct Text-RAG Search Edge Cases (Bắt lỗi AI ảo giác)
    9. Local Comparison Fallback (Chống sập trang 500)
    10. Extreme Edge Cases (Bẫy từ khóa, Xử lý chuỗi rác)
    """

    def setUp(self):
        """
        Khởi tạo DB ảo trên RAM và nạp dữ liệu từ điển cho AI.
        """
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
        """
        Hủy DB và xóa kết nối sau khi hoàn thành chuỗi test AI.
        """
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_sample_data(self):
        """Tạo dữ liệu mẫu đa dạng để test khả năng hiểu của AI và Thuật toán"""
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

        # Lưu ID để xài cho bài Test số 6 và số 7
        self.p1_id = p1.id
        self.p2_id = p2.id
        self.p3_id = p3.id

        ### ---> [NEW: GIẢ LẬP HÀNH VI NGƯỜI DÙNG ĐỂ TEST THUẬT TOÁN GỢI Ý (RECOMMENDATION)] <--- ###
        # Tạo 1 User giả
        u1 = User(username='testuser', email='test@mail.com', password='123', full_name='Test User')
        db.session.add(u1)
        db.session.commit()
        # Lắp ghép trí nhớ (Memory)
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

        # Case 3: Bẫy phân loại (Có tên hãng điện thoại nhưng thực chất là tìm phụ kiện)
        query_trap = "Ốp lưng dành cho Samsung S24 Ultra"
        result_trap = local_analyze_intent(query_trap)
        self.assertEqual(result_trap['brand'], 'Samsung')
        self.assertEqual(result_trap['category'], 'accessory')  # Phải nhận ra là 'accessory'

        # Case 4: Đọc hiểu từ lóng giá tiền ("triệu")
        query_price_1 = "Tôi muốn mua điện thoại Samsung chơi game tốt giá 10 triệu"
        result_price_1 = local_analyze_intent(query_price_1)
        self.assertEqual(result_price_1['brand'], 'Samsung')
        self.assertEqual(result_price_1['category'], 'phone')
        self.assertEqual(result_price_1['max_price'], 10000000)  # Phải quy đổi đúng 10 triệu

        # Case 5: Đọc hiểu từ lóng đàm thoại ("củ")
        query_price_2 = "Kiếm điện thoại 15 củ quay đầu"
        result_price_2 = local_analyze_intent(query_price_2)
        self.assertEqual(result_price_2['max_price'], 15000000)  # Phải quy đổi đúng 15 triệu
        self.assertEqual(result_price_2['category'], 'phone')

        # Case 6: Cực ngắn, chỉ gõ mỗi 1 chữ phụ kiện
        query_short = "ốp"
        result_short = local_analyze_intent(query_short)
        self.assertEqual(result_short['category'], 'accessory')
        self.assertEqual(result_short['keyword'], 'ốp')

        # Case 7: Gài bẫy phụ kiện nhưng để tên hãng ở tít phía sau
        query_trap_2 = "Tai nghe bluetooth xài chung với Xiaomi"
        result_trap_2 = local_analyze_intent(query_trap_2)
        self.assertEqual(result_trap_2['category'], 'accessory')
        self.assertEqual(result_trap_2['brand'], 'Xiaomi')

        # Case 8: Khách chỉ gõ tên dòng máy, không có chữ "điện thoại"
        query_phone = "iphone 15"
        result_phone = local_analyze_intent(query_phone)
        self.assertIsNone(result_phone['category'])
        self.assertEqual(result_phone['brand'], 'Apple')

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

            # Lấy arguments mà code đã gọi call_gemini_api
            args, kwargs = mock_gemini.call_args
            prompt_text = args[0]  # The prompt string is the first positional argument

            # ---> [ĐÃ SỬA LỖI MOCK]: Cập nhật Assert khớp với Prompt Memory mới nhất trong utils.py <---
            self.assertIn("LỊCH SỬ HỘI THOẠI", prompt_text)
            self.assertIn("iPhone 15 giá bao nhiêu?", prompt_text)

    # ==============================================================================
    # ---> [NEW] TEST CƠ CHẾ GIỚI HẠN BỘ NHỚ (COOKIE OPTIMIZATION) <---
    # ==============================================================================
    @patch('app.utils.call_gemini_api')
    def test_chatbot_memory_limit_and_truncation(self, mock_gemini):
        """
        Kiểm tra cơ chế chống tràn Session Cookie:
        1. Chỉ lưu tối đa 3 cuộc hội thoại.
        2. Cắt ngắn câu trả lời của AI xuống 150 ký tự.
        """
        print("\n[AI Test 3.2] Testing Chatbot Memory Limit (Max 3 turns, 150 chars)...")

        # Giả lập AI trả lời một câu rất dài (> 150 ký tự)
        long_response = "A" * 200
        mock_gemini.return_value = long_response

        with self.client:
            # Bắn 4 request liên tục để vượt quá giới hạn 3
            for i in range(4):
                self.client.post('/api/chatbot', json={'message': f'Câu hỏi {i}'})

            # Lấy Session từ Flask
            history = session.get('chat_history', [])

            # 1. Đảm bảo độ dài lịch sử bị khóa ở mức 3 (vứt bỏ 'Câu hỏi 0')
            self.assertEqual(len(history), 3)
            self.assertEqual(history[0]['user'], 'Câu hỏi 1')
            self.assertEqual(history[-1]['user'], 'Câu hỏi 3')

            # 2. Đảm bảo câu trả lời của AI đã bị cắt ngắn (150 ký tự + "...")
            self.assertTrue(len(history[-1]['ai']) <= 153)
            self.assertTrue(history[-1]['ai'].endswith("..."))

    # ==============================================================================
    # ---> [NEW] BỔ SUNG TEST LUỒNG CHÀO HỎI (GREETING BYPASS) <---
    # ==============================================================================
    @patch('app.utils.call_gemini_api')
    def test_chatbot_super_memory_context(self, mock_gemini):
        """
        Kiểm tra tính năng Super Memory và Mở rộng truy vấn (Query Expansion).
        Mục tiêu: Đảm bảo AI luôn được nạp KHO HÀNG THỰC TẾ và tự động nối ngữ cảnh
        từ các câu hội thoại trước đó để không bị ảo giác báo sai hết hàng.
        """
        print("\n[AI Test 3.1] Testing Chatbot Super Memory & Query Expansion...")
        mock_gemini.return_value = "Dạ sản phẩm đó đang sẵn hàng ạ! 🌸"

        with self.client:
            # Giả lập khách hàng đang hỏi tiếp nối bằng đại từ nhân xưng
            self.client.post('/api/chatbot', json={'message': 'tư vấn cho mình máy đó đi'})

            args, kwargs = mock_gemini.call_args
            system_instruction = kwargs.get('system_instruction')
            if not system_instruction and len(args) > 1:
                system_instruction = args[1]

            if system_instruction is None:
                system_instruction = ""

            # Đảm bảo RAG luôn được kích hoạt (KHO HÀNG THỰC TẾ) kể cả câu hỏi ngắn
            self.assertIn("KHO HÀNG THỰC TẾ", system_instruction)
            # Đảm bảo luật RAG chống báo sai kho hàng được đưa vào Prompt
            self.assertIn("TUYỆT ĐỐI KHÔNG BÁO LÀ 'TẠM HẾT HÀNG' NẾU TRƯỚC ĐÓ VỪA BÁO CÒN HÀNG", system_instruction)

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

        # ---> [SỬA LỖI MOCK]: Gọi theo cấu trúc Argument mới truyền hình ảnh và ID <---
        get_comparison_result(
            1, "iPhone A", "100.000 đ", "Desc A", "img_A.jpg",
            2, "Samsung B", "90.000 đ", "Desc B", "img_B.jpg"
        )

        # Kiểm tra Prompt gửi đi
        args, _ = mock_gemini.call_args
        sent_prompt = args[0]

        self.assertIn("iPhone A", sent_prompt)
        self.assertIn("Samsung B", sent_prompt)

        # ---> [ĐÃ SỬA CHỖ NÀY: Cập nhật Assert cho khớp với Prompt mới trong utils.py] <---
        self.assertIn("CHỈ TRẢ VỀ MÃ HTML", sent_prompt)  # Kiểm tra instruction quan trọng

    # --- TEST 5: SENTIMENT ANALYSIS ---
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

    # --- TEST 6: RECOMMENDATION SYSTEM ---
    def test_recommendation_system(self):
        """
        Kiểm tra thuật toán Khuyến nghị hệ thống:
        1. Phụ Kiện mua kèm (Collaborative Filtering)
        2. Sản phẩm tương tự (Content-Based Algorithmic)
        """
        print("\n[AI Test 6] Testing Dual Recommendation Systems...")

        # Truy cập vào trang chi tiết sản phẩm p1 (iPhone 15)
        with self.client:
            response = self.client.get(f'/product/{self.p1_id}')
            html_data = response.data.decode('utf-8')

            # 1. Đảm bảo tính năng Gợi ý Mua kèm đã chạy và hiển thị Ốp lưng
            self.assertIn("Phụ Kiện Gợi Ý Mua Kèm", html_data)
            self.assertIn("Ốp lưng iPhone 15", html_data)

            # 2. Đảm bảo Thuật toán Toán học Sản phẩm tương tự đã chạy
            self.assertIn("Sản Phẩm Tương Tự", html_data)
            # YÊU CẦU MỚI: Vì đã nâng cấp thuật toán, Samsung A05 LÀ ĐIỆN THOẠI DUY NHẤT CÒN LẠI
            # nên chắc chắn nó phải được hiện ra làm "Sản phẩm tương tự"
            self.assertIn("Samsung Galaxy A05", html_data)

    # --- TEST 7: DIRECT TEXT-RAG FALLBACK ---
    @patch('app.utils.GEMINI_API_KEY', 'dummy_key')
    @patch('app.utils.call_gemini_api')
    def test_direct_text_rag_fallback(self, mock_gemini):
        """
        Kiểm tra tính năng Direct Gemini Search (Tìm kiếm bằng Text khi Vector bị lỗi 404).
        """
        print("\n[AI Test 7] Testing Direct Text-RAG Fallback (Bypass Vector DB 404)...")

        # ---> [FIX LỖI JSON Parse]: Hàm utils.py hiện tại parse thẳng kết quả, không còn cắt rác markdown
        mock_gemini.return_value = f"[{self.p2_id}]"

        # Giả lập kho hàng được chuyển thành JSON để gửi cho AI đọc
        catalog_mock = '[{"id": %d, "name": "iPhone 15 Pro Max", "price": 35000000}, {"id": %d, "name": "Samsung Galaxy A05", "price": 3000000}]' % (
            self.p1_id, self.p2_id)

        # Test Case 5: Truy vấn khó, đòi hỏi hiểu ngữ nghĩa (Mười lăm củ quay đầu)
        query = "Kiếm em đt nào pin trâu giá mười lăm củ quay đầu"

        # Gọi hàm mới thêm ở utils.py (direct_gemini_search)
        result_ids = direct_gemini_search(query, catalog_mock)

        # Đảm bảo AI bóc tách đúng JSON array ra thành list các số nguyên (Integer)
        self.assertIsInstance(result_ids, list)
        self.assertEqual(len(result_ids), 1)
        self.assertEqual(result_ids[0], self.p2_id)  # Đảm bảo trả về đúng ID của máy Samsung A05 giá rẻ

    # --- TEST 8: DIRECT TEXT-RAG EDGE CASES ---
    @patch('app.utils.GEMINI_API_KEY', 'dummy_key')
    @patch('app.utils.call_gemini_api')
    def test_direct_text_rag_fallback_edge_cases(self, mock_gemini):
        """
        Kiểm tra hệ thống xử lý thế nào khi AI không tìm thấy sản phẩm hoặc trả về văn bản lỗi thay vì JSON.
        """
        print("\n[AI Test 8] Testing Direct Text-RAG Fallback (Edge Cases)...")
        catalog_mock = '[{"id": %d, "name": "iPhone 15 Pro Max", "price": 35000000}]' % self.p1_id

        # Edge Case 1: AI không tìm thấy máy nào phù hợp (VD khách tìm Nokia nhưng kho chỉ có iPhone)
        # ---> [FIX LỖI JSON Parse]: Cập nhật định dạng chuẩn thay cho markdown rác
        mock_gemini.return_value = "[]"
        result_empty = direct_gemini_search("Điện thoại Nokia đập đá", catalog_mock)
        self.assertIsInstance(result_empty, list)
        self.assertEqual(len(result_empty), 0)

        # Edge Case 2: AI bị "ảo giác" (hallucination), trả về văn bản trò chuyện thay vì format mảng ID JSON
        mock_gemini.return_value = "Dạ chào bạn, hiện tại cửa hàng không có sản phẩm này ạ."
        result_malformed = direct_gemini_search("tìm máy bay trực thăng", catalog_mock)

        # Hàm của chúng ta phải đủ mạnh để bắt lỗi (try/except) đoạn văn bản này và trả về rỗng một cách an toàn
        self.assertIsInstance(result_malformed, list)
        self.assertEqual(len(result_malformed), 0)

    # ==============================================================================
    # ---> [NEW: CHIẾN DỊCH 1 - TĂNG CƯỜNG TEST EDGE CASES CHO PYTHON BACKEND] <---
    # ==============================================================================

    # --- TEST 9: LOCAL COMPARISON FALLBACK (Python Thuần) ---
    def test_local_comparison_fallback(self):
        """
        Kiểm tra chức năng tự cứu (Local Fallback) khi So sánh đa máy.
        Mục tiêu: Đảm bảo khi Google AI sập, Python thuần tự động kích hoạt
        để vẽ bảng HTML mà không văng lỗi 500.
        """
        print("\n[AI Test 9] Testing Local Comparison Fallback HTML Generator...")
        p1 = db.session.get(Product, self.p1_id)
        p2 = db.session.get(Product, self.p2_id)
        p3 = db.session.get(Product, self.p3_id)

        # Gọi trực tiếp hàm lõi dự phòng
        html_output = generate_local_comparison_html(p1, p2, p3)

        # Đảm bảo bảng HTML chứa đủ tên của 3 sản phẩm
        self.assertIn("iPhone 15 Pro Max", html_output)
        self.assertIn("Samsung Galaxy A05", html_output)
        self.assertIn("Ốp lưng iPhone 15", html_output)

        # Cảnh báo an toàn phải được hiển thị
        self.assertIn("CHẾ ĐỘ DỰ PHÒNG", html_output)
        self.assertIn("Hệ thống AI Gemini tạm thời đang bảo trì", html_output)

    # --- TEST 10: EDGE CASES FOR INTENT PARSING (Phòng thủ lỗi Logic) ---
    def test_intent_parsing_edge_cases(self):
        """
        Kiểm tra các kịch bản dị biệt (Edge Cases) khi phân tích câu hỏi người dùng.
        Mục tiêu: Tăng mức độ phủ sóng code (Code Coverage) và chặn đứng bug tiềm ẩn.
        """
        print("\n[AI Test 10] Testing Intent Parsing Edge Cases (Robustness)...")

        # Kịch bản 1: Khách hàng chỉ nhập khoảng trắng (Không được sập Regex)
        res_empty = local_analyze_intent("      ")
        self.assertEqual(res_empty['keyword'], "")
        self.assertIsNone(res_empty['category'])

        # Kịch bản 2: Khách hàng nhập toàn từ khóa vô nghĩa (stop words)
        res_stop = local_analyze_intent("tôi muốn mua cho cần dưới khoảng")
        self.assertEqual(res_stop['keyword'], "")

        # Kịch bản 3: Khách hàng nhập số tiền khổng lồ vượt quá giới hạn thông thường
        res_huge = local_analyze_intent("tìm điện thoại 100 củ")
        self.assertEqual(res_huge['max_price'], 100000000)
        self.assertEqual(res_huge['category'], 'phone')

        # Kịch bản 4: Gõ sai khoảng cách (không có dấu cách giữa số và chữ "triệu")
        res_no_space = local_analyze_intent("điện thoại 12triệu")
        self.assertEqual(res_no_space['max_price'], 12000000)
        
    # ==============================================================================
    # ---> [NEW] TEST TÍNH NĂNG TÌM KIẾM BẰNG HÌNH ẢNH (VISUAL SEARCH) <---
    # ==============================================================================
    @patch('app.utils.product_image_collection')
    @patch('app.utils.get_image_embedding')
    def test_visual_search_logic(self, mock_get_embedding, mock_collection):
        """
        Kiểm tra luồng Tìm kiếm bằng hình ảnh (Visual AI).
        Mục tiêu: Đảm bảo thuật toán gọi đúng hàm nhúng (Embedding MobileNetV2)
        và xử lý an toàn khi ChromaDB không tìm thấy kết quả hoặc file ảnh lỗi.
        """
        print("\n[AI Test 11] Testing Visual AI Search Flow...")

        # Kịch bản 1: AI nhúng ảnh thành Vector thành công, ChromaDB tìm được ảnh giống
        mock_get_embedding.return_value = [0.1, 0.2, 0.3] # Giả lập vector đặc trưng
        mock_collection.query.return_value = {'ids': [[str(self.p1_id), str(self.p3_id)]]}

        # Giả lập tham số image_file
        fake_image = "dummy_image.jpg"
        matched_ids = search_image_vector_db(fake_image, n_results=2)

        self.assertEqual(len(matched_ids), 2)
        self.assertEqual(matched_ids[0], str(self.p1_id))

        # Kịch bản 2: AI không nhận diện được ảnh (Vector = None) -> Trả về mảng rỗng
        mock_get_embedding.return_value = None
        empty_ids = search_image_vector_db("bad_image.jpg")
        self.assertEqual(len(empty_ids), 0)

        # Kịch bản 3: Bộ sưu tập chưa được khởi tạo (Database sập) -> Bắt lỗi Try/Catch an toàn
        with patch('app.utils.product_image_collection', None):
            mock_get_embedding.return_value = [0.1]
            safe_empty = search_image_vector_db("test.jpg")
            self.assertEqual(len(safe_empty), 0)

if __name__ == '__main__':
    print("🚀 Đang chạy bộ kiểm thử chuyên sâu cho AI...")
    unittest.main()