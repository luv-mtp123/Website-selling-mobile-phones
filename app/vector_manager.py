import os
import chromadb
import google.generativeai as genai
from chromadb.utils import embedding_functions


class AIVectorManager:
    """
    Hệ thống quản lý Vector Database (ChromaDB) cao cấp cho tính năng RAG.
    Chịu trách nhiệm mã hóa ngôn ngữ tự nhiên thành Vector đa chiều.
    """

    def __init__(self, db_path="./chroma_db", collection_name="mobile_store_products"):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

        try:
            self.client = chromadb.PersistentClient(path=db_path)
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self._get_embedding_function()
            )
        except Exception as e:
            print(f"Vector DB Init Error: {e}")
            self.collection = None

    def _get_embedding_function(self):
        """Hàm nhúng (Embedding) độc quyền dùng model Google mới nhất"""

        class GeminiEmbed(embedding_functions.EmbeddingFunction):
            def __call__(self, input: list[str]) -> list[list[float]]:
                model = 'models/text-embedding-004'
                embeddings = []
                for text in input:
                    try:
                        res = genai.embed_content(model=model, content=text, task_type="retrieval_document")
                        embeddings.append(res['embedding'])
                    except Exception as e:
                        print(f"Google Embedding API Error: {e}")
                        # Trả về vector rỗng (768 chiều) nếu lỗi để không gãy hệ thống
                        embeddings.append([0.0] * 768)
                return embeddings

        return GeminiEmbed()

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
            "dimension": "768d (Google Standard)"
        }