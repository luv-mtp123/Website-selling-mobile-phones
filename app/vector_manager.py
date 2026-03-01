import os
# Tắt Telemetry qua biến môi trường trước khi import chromadb để đảm bảo không rò rỉ log
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.utils import embedding_functions

# =========================================================================
# [HOTFIX] Khóa mõm triệt để lỗi rác Telemetry của ChromaDB 0.4.22
# Sử dụng kỹ thuật Monkey Patching đúng chuẩn Python tránh lỗi Argument Mismatch
# =========================================================================
try:
    from chromadb.telemetry.posthog import Posthog  # type: ignore

    def mock_capture(self, *args, **kwargs):
        pass

    Posthog.capture = mock_capture
except Exception:
    pass


class AIVectorManager:
    """
    Hệ thống quản lý Vector Database (ChromaDB) cao cấp cho tính năng RAG.
    Đã NÂNG CẤP LỚP 1: Chuyển sang mô hình nhúng (Embedding) Offline đa ngôn ngữ.
    Chạy bằng sức mạnh CPU Local, giải phóng 100% Quota của Google.
    """

    def __init__(self, db_path="./chroma_db", collection_name="mobile_store_products"):
        # Đã loại bỏ hoàn toàn việc gọi GEMINI_API_KEY vì không cần dùng Google cho Vector nữa
        try:
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=chromadb.Settings(anonymized_telemetry=False)
            )
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self._get_embedding_function()
            )
        except Exception as e:
            print(f"Vector DB Init Error: {e}")
            self.collection = None

    def _get_embedding_function(self):
        """Hàm nhúng (Embedding) Offline đa ngôn ngữ (Tiết kiệm 100% API Quota)"""

        class LocalEmbed(embedding_functions.EmbeddingFunction):
            def __init__(self):
                # Tải model đa ngôn ngữ cực nhẹ (~400MB) vào RAM, chạy siêu tốc trên máy
                self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")

            def __call__(self, input: list[str]) -> list[list[float]]:
                try:
                    return self.ef(input)
                except Exception as e:
                    print(f"Local Embedding API Error: {e}")
                    # Trả về vector rỗng (384 chiều) nếu lỗi để không gãy hệ thống
                    return [[0.0] * 384] * len(input)

        return LocalEmbed()

    def add_product_to_brain(self, product_id, name, brand, category, description, price):
        """Đưa kiến thức về 1 sản phẩm vào não bộ AI"""
        if not self.collection: return False

        # Tiền xử lý dữ liệu (Làm sạch chuỗi)
        clean_desc = str(description).replace('\n', ' ').strip()
        semantic_text = f"Sản phẩm {name}, hãng {brand}, loại {category}. Cấu hình/Tính năng: {clean_desc}. Giá bán: {price} VNĐ."

        try:
            self.collection.upsert(
                documents=[semantic_text],
                metadatas=[{"price": price, "brand": brand, "category": category}],
                ids=[str(product_id)]
            )
            return True
        except Exception as e:
            print(f"Failed to add to AI Brain: {e}")
            return False

    def check_brain_health(self):
        """Kiểm tra sức khỏe và dung lượng của não bộ AI"""
        if not self.collection:
            return {"status": "offline", "memory_count": 0}

        count = self.collection.count()
        return {
            "status": "online",
            "memory_count": count,
            "dimension": "384d (Local Sentence-Transformers)"
        }