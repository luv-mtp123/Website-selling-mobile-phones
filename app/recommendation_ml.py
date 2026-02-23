import pandas as pd
import numpy as np
from app.extensions import db
from app.models import Order, OrderDetail, Product


class MLRecommender:
    """
    Hệ thống Gợi ý Sản phẩm dựa trên Machine Learning (Collaborative Filtering).
    Sử dụng thuật toán Item-Item Similarity (Độ tương đồng giữa các vật phẩm).
    Thuật toán này phân tích hàng ngàn giỏ hàng để tìm ra quy luật mua sắm ẩn.
    """

    def __init__(self, app):
        self.app = app

    def build_item_similarity_matrix(self):
        """Xây dựng ma trận tương quan giữa tất cả các sản phẩm"""
        with self.app.app_context():
            # 1. Lấy tất cả dữ liệu chi tiết đơn hàng
            details = db.session.query(
                OrderDetail.order_id,
                OrderDetail.product_id,
                OrderDetail.quantity
            ).all()

            if not details:
                return pd.DataFrame()

            df = pd.DataFrame(details, columns=['order_id', 'product_id', 'quantity'])

            # 2. Tạo ma trận User-Item (Giỏ hàng - Sản phẩm)
            # Hàng là order_id, Cột là product_id, Giá trị là số lượng (1 nếu có mua, 0 nếu không)
            basket_matrix = df.pivot_table(index='order_id', columns='product_id', values='quantity', fill_value=0)

            # =========================================================================
            # ---> [ĐÃ SỬA CHỖ NÀY: Dùng toán học mảng thay cho hàm applymap bị khai tử] <---
            # =========================================================================
            # Đưa về dạng nhị phân (Chỉ quan tâm có mua hay không, không quan tâm số lượng)
            basket_matrix = (basket_matrix > 0).astype(int)
            # =========================================================================

            # 3. Tính toán Item-Item Similarity Matrix bằng phép nhân ma trận Dot Product
            # Tính số lần 2 sản phẩm xuất hiện cùng nhau trong cùng 1 giỏ hàng
            item_similarity = basket_matrix.T.dot(basket_matrix)

            # Reset đường chéo (Sản phẩm tự so sánh với chính nó = 0)
            # ---> [ĐÃ SỬA CHỖ NÀY: Trích xuất mảng copy để tránh lỗi read-only array trên Pandas mới] <---
            similarity_array = item_similarity.to_numpy(copy=True)
            np.fill_diagonal(similarity_array, 0)

            # Gắn mảng đã sửa lại vào DataFrame Pandas ban đầu
            item_similarity = pd.DataFrame(
                similarity_array,
                index=item_similarity.index,
                columns=item_similarity.columns
            )

            return item_similarity

    def get_frequently_bought_together(self, product_id, top_n=4):
        """Trả về Top N sản phẩm thường được mua kèm với Product ID truyền vào"""
        similarity_matrix = self.build_item_similarity_matrix()

        if similarity_matrix.empty or product_id not in similarity_matrix.columns:
            return []

        # Lấy cột tương ứng với product_id, sắp xếp giảm dần
        similar_items = similarity_matrix[product_id].sort_values(ascending=False)

        # Chỉ lấy những sản phẩm có độ tương đồng > 0 (Từng được mua chung ít nhất 1 lần)
        recommended_ids = similar_items[similar_items > 0].head(top_n).index.tolist()

        # Ánh xạ từ ID ra tên sản phẩm thực tế
        recommendations = []
        with self.app.app_context():
            for p_id in recommended_ids:
                prod = db.session.get(Product, int(p_id))
                if prod and prod.is_active:
                    recommendations.append({
                        'id': prod.id,
                        'name': prod.name,
                        'price': prod.price,
                        'image_url': prod.image_url,
                        'confidence_score': int(similar_items[p_id])  # Số lần mua chung
                    })

        return recommendations

    def generate_ml_report(self):
        """Báo cáo đánh giá hiệu năng của thuật toán ML"""
        matrix = self.build_item_similarity_matrix()
        if matrix.empty:
            return "Chưa đủ dữ liệu để huấn luyện (Training)."

        total_products = len(matrix.columns)
        total_relations = (matrix > 0).sum().sum()

        return f"Đã huấn luyện xong mô hình. Phân tích {total_products} sản phẩm với {total_relations} mối quan hệ tương quan."