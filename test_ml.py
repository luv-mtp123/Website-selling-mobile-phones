from app import create_app
from app.recommendation_ml import MLRecommender


def run_ml_test():
    app = create_app()
    ml = MLRecommender(app)

    print("=" * 50)
    print("🧠 BẮT ĐẦU KIỂM TRA THUẬT TOÁN HỌC MÁY (ML)")
    print("=" * 50)

    # 1. Báo cáo tình trạng huấn luyện ma trận
    print("📊 BÁO CÁO HUẤN LUYỆN:")
    print(ml.generate_ml_report())
    print("-" * 50)

    # 2. Thử lấy gợi ý mua kèm cho Sản phẩm số 1 (Ví dụ iPhone 15)
    test_product_id = 1
    print(f"🎯 THỬ NGHIỆM TÌM SẢN PHẨM MUA KÈM VỚI SẢN PHẨM ID = {test_product_id}")

    recommendations = ml.get_frequently_bought_together(test_product_id)

    if not recommendations:
        print("-> Khách hàng chưa mua sản phẩm này kèm với bất kỳ món nào khác.")
    else:
        for item in recommendations:
            print(f" + Gợi ý: {item['name']} (Độ tự tin: {item['confidence_score']} lượt mua chung)")

    print("=" * 50)


if __name__ == "__main__":
    run_ml_test()