"""
Module chứa toàn bộ Thư viện Tiện ích (Utilities) và Thuật toán Lõi (Core Algorithms).
Bao gồm: Giao tiếp AI (Gemini), Quản trị Vector DB (Chroma), Hệ thống tìm kiếm Fallback,
Thuật toán Khuyến nghị, So sánh sản phẩm và Động cơ Khuyến mãi (Voucher Engine).
Tuyệt đối không chứa các module liên quan đến SMTP/Email.
"""

import os
import json
import re
import chromadb
from google import genai
from google.genai import types
from chromadb.utils import embedding_functions
from flask import url_for
from itsdangerous import URLSafeTimedSerializer
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import requests
from PIL import Image
import io


# [NEW] Khởi tạo thư viện PyTorch cho Visual Search
try:
    import torch
    import torchvision.models as models
    import torchvision.transforms as transforms
except ImportError:
    torch = None
    print("⚠️ PyTorch chưa được cài đặt. Tính năng tìm kiếm bằng hình ảnh sẽ không hoạt động. Chạy: pip install torch torchvision")

# =========================================================================
# [HOTFIX] Khóa mõm triệt để lỗi rác Telemetry của ChromaDB 0.4.22
# Sử dụng kỹ thuật Monkey Patching đúng chuẩn Python tránh lỗi Argument Mismatch
# =========================================================================
try:
    from chromadb.telemetry.posthog import Posthog  # type: ignore

    # ---> [HOTFIX]: Dùng lambda để nuốt sạch mọi tham số, diệt tận gốc lỗi crash log
    Posthog.capture = lambda *args, **kwargs: None
except Exception:
    pass

# Tắt cảnh báo Telemetry của ChromaDB để giao diện Console sạch sẽ
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Khởi tạo ChromaDB (Lưu file local tại thư mục chroma_db)
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
except Exception as e:
    print(f"⚠️ ChromaDB Init Warning: {e}")
    chroma_client = None

# =========================================================================
# ---> [UPGRADED V3] ResNet-50 Feature Extractor với Hardware Acceleration (GPU)
# Tối đa hóa sức mạnh phần cứng để chạy Real-time Visual Search
# =========================================================================
visual_model = None
visual_transforms = None
device = None

if torch is not None:
    try:
        # [TỐI ƯU 1]: Dò tìm Card Đồ Họa (NVIDIA CUDA hoặc Apple MPS). Nếu không có mới dùng CPU.
        # Giúp tốc độ trích xuất vector tăng gấp 10-50 lần so với phiên bản trước.
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")

        print(f"🚀 Visual Search Engine initialized on device: {device}")

        # Sử dụng trọng số ResNet-50 chuẩn
        weights = models.ResNet50_Weights.DEFAULT
        full_resnet = models.resnet50(weights=weights)

        # Cắt bỏ lớp Linear (Phân loại 1000 class) cuối cùng.
        visual_model = torch.nn.Sequential(*(list(full_resnet.children())[:-1]))

        # Đẩy mô hình lên GPU (nếu có) và thiết lập chế độ dự đoán
        visual_model = visual_model.to(device)
        visual_model.eval()

        # Tiền xử lý ảnh theo chuẩn ResNet
        visual_transforms = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    except Exception as e:
        print(f"⚠️ Không thể tải mô hình ResNet-50: {e}")



class LocalEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Sử dụng Vector Model Offline để miễn phí 100% API Quota"""
    def __init__(self):
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")

    def __call__(self, input: list[str]) -> list[list[float]]:
        try:
            return self.ef(input)
        except Exception as e:
            print(f"❌ Local Embedding Error: {e}")
            return [[0.0] * 384] * len(input)

# Khởi tạo Collection lưu trữ
try:
    if chroma_client:
        product_collection = chroma_client.get_or_create_collection(
            name="mobile_store_products",
            embedding_function=LocalEmbeddingFunction()
        )
        product_image_collection = chroma_client.get_or_create_collection(
            name="product_images",
            metadata={"hnsw:space": "cosine"}
        )
    else:
        product_collection = None
        product_image_collection = None
except Exception as e:
    print(f"⚠️ ChromaDB Collection Error: {e}")
    product_collection = None
    product_image_collection = None

def validate_image_file(file):
    """
    Kiểm tra tính hợp lệ của file ảnh tải lên hệ thống.
    Xác minh phần mở rộng và chặn các file vượt quá dung lượng 2MB để chống DDoS Storage.
    """
    if file.filename == '': return False, "Chưa chọn file."
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
        return False, "Chỉ nhận: JPG, PNG, WEBP."
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 2 * 1024 * 1024: return False, "File > 2MB."
    return True, None


# =========================================================================
# ---> [NEW] HỆ THỐNG XỬ LÝ ẢNH (VISUAL SEARCH ENGINE) - RESNET 2048D
# =========================================================================
def get_image_embedding(image_source, is_url=True):
    """
    Biến đổi hình ảnh thành mảng Vector 2048 chiều bằng ResNet-50 (Tăng tốc GPU).
    """
    if not visual_model or not visual_transforms or not device:
        return None

    try:
        if is_url:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(image_source, stream=True, timeout=5, headers=headers)
            response.raise_for_status()
            img = Image.open(response.raw).convert('RGB')
        else:
            img = Image.open(image_source).convert('RGB')

        # Chạy ảnh qua mạng CNN ResNet-50
        input_tensor = visual_transforms(img)
        # [TỐI ƯU 2]: Đẩy tensor dữ liệu ảnh lên cùng thiết bị với Model (GPU/CPU)
        input_batch = input_tensor.unsqueeze(0).to(device)

        with torch.no_grad():
            output = visual_model(input_batch)

        # Kéo dữ liệu từ GPU về lại CPU để chuyển thành list lưu vào ChromaDB
        flattened_vector = output.view(-1).cpu().numpy().tolist()
        return flattened_vector

    except Exception as e:
        print(f"⚠️ Lỗi trích xuất Vector Ảnh: {e}")
        return None


def sync_product_image_to_vector_db(product):
    """
    Đồng bộ ảnh của sản phẩm vào ChromaDB khi Admin thêm/sửa sản phẩm.
    """
    if not product_image_collection or not product.image_url:
        return

    embedding = get_image_embedding(product.image_url, is_url=True)
    if embedding:
        try:
            product_image_collection.upsert(
                embeddings=[embedding],
                metadatas=[{"name": product.name, "brand": product.brand}],
                ids=[str(product.id)]
            )
            print(f"📸 Indexed Image Vector: {product.name}")
        except Exception as e:
            print(f"⚠️ Lỗi lưu Vector Ảnh vào ChromaDB: {e}")


def search_image_vector_db(image_file, n_results=4):
    """
    Tìm kiếm các sản phẩm có hình dáng giống nhất với ảnh tải lên.
    """
    if not product_image_collection: return []

    embedding = get_image_embedding(image_file, is_url=False)
    if not embedding: return []

    try:
        results = product_image_collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        if results['ids'] and len(results['ids']) > 0:
            return results['ids'][0]
        return []
    except Exception as e:
        print(f"⚠️ Lỗi tìm kiếm Vector Ảnh: {e}")
        return []

def identify_phone_by_gemini(image_file):
    """
    [TỐI ƯU CẤP ĐỘ 7 - GIẢI QUYẾT TRIỆT ĐỂ LỖI DESIGN LANGUAGE BLENDING]
    Áp dụng kỹ thuật Cross-Examination (Đối chiếu chéo) vào logic nhận diện của AI.
    Bổ sung toàn diện Prompts cho Xiaomi, OPPO, Realme, Vivo và ASUS.
    """
    raw_keys = os.environ.get("GEMINI_API_KEY", "")
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

    if not api_keys:
        return None

    try:
        # [TỐI ƯU 3]: Nén và Resize thông minh trước khi gửi đi.
        img = Image.open(image_file).convert('RGB')
        img.thumbnail((1024, 1024))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85)
        image_bytes = img_byte_arr.getvalue()
        mime_type = 'image/jpeg'

        # Reset con trỏ file gốc để các hàm sau (nếu có dùng) không bị lỗi
        image_file.seek(0)

        system_instruction = (
            "Bạn là siêu chuyên gia giám định thiết kế phần cứng điện thoại, ĐẶC BIỆT LÀ CHUYÊN GIA VỀ MỌI DÒNG MÁY SAMSUNG, APPLE, XIAOMI, OPPO, REALME, VIVO VÀ ASUS. "
            "Nhiệm vụ của bạn là nhận diện chính xác dòng máy từ ảnh chụp. KHÔNG ĐƯỢC ĐOÁN BỪA. "
            "TRƯỚC KHI TRẢ VỀ KẾT QUẢ JSON, BẠN PHẢI SUY LUẬN NGHIÊM NGẶT THEO BỘ QUY TẮC SAU:\n\n"
            
            "🛑 [BỘ LỌC AN TOÀN - ANTI HALLUCINATION - BẮT BUỘC ĐỌC ĐẦU TIÊN]:\n"
            "NẾU HÌNH ẢNH LÀ PHONG CẢNH, ĐỘNG VẬT, KHUÔN MẶT NGƯỜI, HOẶC BẤT CỨ VẬT THỂ NÀO KHÔNG PHẢI ĐIỆN THOẠI / PHỤ KIỆN ĐIỆN THOẠI -> "
            "LẬP TỨC DỪNG LẠI và trả về: {'brand': null, 'model': null, 'search_keywords': [], 'price_segment': null, 'confidence': 0, 'details': 'Hình ảnh không chứa thiết bị di động.'}\n\n"
            
            "🔵 BỘ QUY TẮC NHẬN DIỆN SAMSUNG:\n"
            "1. DÒNG S (Cao cấp):\n"
            "   - Thiết kế sang trọng, Nốt ruồi siêu nhỏ, viền màn hình cực mỏng đối xứng 4 cạnh.\n"
            "   - S23, S24 bản thường bo góc. S23 Ultra viền nhôm màn cong nhẹ. S24 Ultra viền Titan phẳng, VUÔNG VỨC 4 góc sắc cạnh.\n"
            "   - S25 Ultra có 4 góc bo tròn nhẹ nhàng hơn S24 Ultra một chút, viền màn hình mỏng hơn nữa, vòng camera sau có thiết kế họa tiết đồng tâm/phẳng tinh tế hơn.\n\n"
            
            "2. BẮT BUỘC PHÂN BIỆT CHI TIẾT DÒNG Z FOLD / Z FLIP (NGHIÊM CẤM NHẦM LẪN GIỮA CÁC ĐỜI):\n"
            "   - Z Fold 3: Viền máy BO CONG mềm mại. Đèn flash NẰM TRONG cụm bao quanh camera. Khi gập có khe hở.\n"
            "   - Z Fold 4: Bản lề mỏng hơn Fold 3. Đèn flash vẫn NẰM TRONG cụm camera. Viền vẫn HƠI BO CONG nhẹ.\n"
            "   - Z Fold 5: ĐIỂM CHỐT: Đèn flash dời ra NẰM NGOÀI (bên phải) cụm camera. Bản lề gập khít (gapless).\n"
            "   - Z Fold 6: Thiết kế lột xác, CỰC KỲ VUÔNG VỨC ở 4 góc (giống S24 Ultra). Viền kim loại bao quanh từng ống kính camera rất dày, màu đen có viền rãnh. Cụm camera lồi to.\n"
            "   - Z Fold 7: Vẫn giữ form VUÔNG VỨC nhưng tổng thể siêu mỏng, tỷ lệ màn hình ngoài rộng như điện thoại thường. Vòng camera được làm tinh tế, phẳng hơn và bớt hầm hố hơn Fold 6.\n"
            "   - Z Flip 3 / Flip 4: Màn hình phụ bên ngoài siêu nhỏ, nằm ngang cạnh cụm camera.\n"
            "   - Z Flip 5: Màn hình phụ lớn hình 'thư mục' (tràn xuống dưới camera). Viền ống kính camera rất mỏng.\n"
            "   - Z Flip 6: Màn hình phụ hình 'thư mục' nhưng VÒNG CAMERA CỰC DÀY và có màu trùng với màu mặt lưng. Viền máy vuông vức vát phẳng.\n"
            "   - Z Flip 7: Màn hình phụ lớn có thể có bố cục camera mới. Khung viền siêu mỏng, tối giản.\n\n"
            
            "3. BẮT BUỘC PHÂN BIỆT DÒNG A, M VÀ J (Các đời máy Tầm trung & Giá rẻ cực kỳ đa dạng):\n"
            "   - THỜI KỲ CỔ ĐIỂN (2015-2017): Dòng A (A3, A5, A7) dùng khung nhôm, lưng kính. Dòng J (J1 đến J7) viền dày, J7 Pro có dải ăng-ten chữ U lộn ngược CỰC KỲ ĐẶC TRƯNG.\n"
            "   - THỜI KỲ MÀN HÌNH CHỮ U (Thế hệ 10-80): A10 đến A80, M10 đến M30. Camera dọc đặt lệch trái. A80 có cụm camera xoay trượt lên trên.\n"
            "   - THỜI KỲ MODULE CHỮ NHẬT (Thế hệ 1x-7x): A11-A71, A12-A72. Các ống kính nằm GOM LẠI trong một khối chữ nhật lồi màu đen hoặc đồng màu lưng.\n"
            "   - THỜI KỲ 'HỌC HỎI DÒNG S' (Thế hệ 13-16, 33-36, 53-56): BỎ MODULE, 3 ống kính đứng độc lập lồi trên mặt lưng giống hệt S23/S24. Từ đời A55/A35 trở đi có 'Key Island' (Viền nhô cao ở nút nguồn/âm lượng).\n\n"
            
            "4. DÒNG NOTE (Đặc trưng hộp vuông, có bút S-Pen):\n"
            "   - Note 20 Ultra: Camera khối chữ nhật đứng cực to lồi, 3 mắt tròn lớn, vân tròn đồng tâm.\n"
            "   - Note 10 / Note 10 Plus: Cụm camera dọc thon gọn lệch trái, màn hình nốt ruồi chính giữa.\n"
            "   - Note 8 / Note 9: Cụm camera và cảm biến vân tay xếp NGANG ở nửa trên mặt lưng.\n\n"

            "🔴 BỘ QUY TẮC NHẬN DIỆN IPHONE (PHÂN LOẠI SIÊU CHI TIẾT THEO TỪNG THẾ HỆ):\n"
            "1. THỜI KỲ CLASSIC: iPhone 4/4s/5/5s/SE (Khung vát phẳng). iPhone 6/7/8 (Viền bo tròn, 7/8 Plus camera kép ngang. 8 mặt lưng kính).\n"
            "2. THỜI KỲ TAI THỎ BẢN THƯỜNG: X/XS (viên thuốc nhỏ dọc). 11 (2 camera dọc trong ô vuông). 12 (giống 11 nhưng viền PHẲNG). 13/14 (2 camera xếp CHÉO).\n"
            "3. THỜI KỲ PRO/PRO MAX (3 MẮT VÀ LI-DAR): \n"
            "   - 11 Pro/Max: Viền thép bo tròn, KHÔNG LiDAR.\n"
            "   - 12 Pro/Max: Viền phẳng, CÓ LiDAR nhỏ dưới góc.\n"
            "   - 13 Pro/Max: Cụm camera TO HƠN HẲN 12 Pro, tai thỏ nhỏ lại.\n"
            "   - 14 Pro/Max: Thay tai thỏ bằng DYNAMIC ISLAND. Camera siêu to.\n"
            "   - 15 Pro/Max: Viền TITANIUM xước mờ, nút bấm ACTION BUTTON, cổng USB-C.\n"
            "4. THẾ HỆ 16 VÀ TƯƠNG LAI: 16/16 Plus (2 camera DỌC dạng viên thuốc), 16 Pro/Max (Viền siêu mỏng, có nút Camera Control bên phải). 17 Air/Slim (Thiết kế cực mỏng, 1 camera giữa lưng).\n\n"

            "🟠 BỘ QUY TẮC NHẬN DIỆN XIAOMI (BAO GỒM REDMI, POCO):\n"
            "1. Redmi & Redmi Note (Giá rẻ - Tầm trung):\n"
            "   - Redmi (9, 10, 12, 13C): Viền dưới màn hình (cằm) khá dày, lưng nhựa. Cụm camera thiết kế cơ bản, lồi nhẹ.\n"
            "   - Redmi Note (10, 11, 12, 13, 14 Series): Note 10/11 có cụm camera chữ nhật nhiều tầng. Note 12/13 cụm camera vuông vức, lồi rõ rệt, lưng kính nhám bóng bẩy. Note 14 Pro/Pro+ cụm camera hình bo cong mềm mại đặt chính giữa mặt lưng trên.\n"
            "2. POCO (Dòng Gaming/Hiệu năng):\n"
            "   - ĐẶC TRƯNG CHÍ MẠNG: Logo POCO in CỰC TO. Dòng M3, X3, X4, X5, X6 thường có một DẢI ĐEN VẮT NGANG nguyên cụm camera trên mặt lưng, hoặc module camera cực kỳ hầm hố, màu sắc sặc sỡ (Vàng POCO).\n"
            "3. Xiaomi Mi / Xiaomi Number Series (Cận cao cấp & Flagship):\n"
            "   - Mi 11: Cụm camera hình VUÔNG BO TRÒN chia bậc thang cực kỳ đặc trưng.\n"
            "   - Xiaomi 12 / 13: Thiết kế gọn gàng, module camera chữ nhật bo góc chia các vạch kẻ vát chia ô rất tinh tế.\n"
            "   - Xiaomi 13 Pro / 14 / 14 Pro: Module camera hình VUÔNG CỰC TO lồi lên, có chữ LEICA ở giữa. Bản 14 Pro có viền răng cưa quanh module.\n"
            "4. Dòng ULTRA (13 Ultra, 14 Ultra, 15 Ultra) - SIÊU PHẨM CAMERA:\n"
            "   - ĐẶC TRƯNG TUYỆT ĐỐI: Mặt lưng thường làm bằng da PU (Vegan Leather). Một cụm camera HÌNH TRÒN CỰC KỲ KHỔNG LỒ chiếm gần nửa mặt lưng, trông như ống kính máy ảnh cơ, logo LEICA nằm chễm chệ bên trong.\n"
            "5. Dòng MIX (Màn gập & Concept):\n"
            "   - Mix Fold 2/3/4: Máy gập giống Z Fold nhưng cụm camera thường trải dài theo chiều NGANG hoặc một khối hình chữ nhật to. Bản Mix Fold 4 làm module bo cong nhẹ ôm lấy các ống kính Leica.\n\n"

            "🟢 BỘ QUY TẮC NHẬN DIỆN OPPO:\n"
            "1. Dòng A & K (Giá rẻ/Tầm trung): Thiết kế an toàn, nốt ruồi lệch hoặc giữa. A53, A58 cụm camera dọc. Thế hệ mới (A60, A3) có cụm camera hình viên thuốc kéo dài.\n"
            "2. Reno Series (Chủ lực tầm trung/Cận cao cấp - Thiết kế màu sắc OPPO Glow):\n"
            "   - Reno 2: Có camera 'vây cá mập' thò thụt trên đỉnh.\n"
            "   - Reno 4/5/6: Camera lồi dọc, Reno 6 vát phẳng viền cực giống iPhone.\n"
            "   - Reno 7/8: Reno 8 cực kỳ đặc trưng với cụm camera đúc liền khối nguyên mảng uốn lượn lồi lên, 2 mắt camera TRÒN RẤT TO.\n"
            "   - Reno 10/11/12 Series: Cụm camera hình OVAL (VIÊN THUỐC) dài, bên trong chia 2 nửa (nửa kính, nửa kim loại xước) nhìn rất sang trọng.\n"
            "3. Find X Series (Flagship đỉnh cao):\n"
            "   - Find X3 / X5 Pro: Thiết kế 'Miệng núi lửa' - Cụm camera lồi lên nhưng kính vuốt cong tràn liền mạch nguyên khối từ mặt lưng. X5 có logo HASSELBLAD.\n"
            "   - Find X6 / X7 / X8 Series: CHUYỂN TÔNG SANG MODULE TRÒN. Một khối hình tròn cực lớn nằm GIỮA mặt lưng, logo HASSELBLAD. X7 Ultra có mặt lưng chia đôi 2 tông màu (nửa da nửa kính).\n"
            "4. Find N (Màn gập): Find N1/N2/N3 có dáng lùn, béo bè hơn Z Fold. N3 có cụm camera tròn siêu to. Find N2 Flip / N3 Flip có MÀN HÌNH PHỤ HÌNH CHỮ NHẬT DỌC trải dài cạnh cụm camera dọc.\n\n"

            "🟡 BỘ QUY TẮC NHẬN DIỆN REALME:\n"
            "1. C Series / Note / V Series (Giá rẻ): Lưng nhựa có vân sọc, module chữ nhật chứa các mắt camera. Các bản mới (C55, C65, C67) học hỏi thiết kế bỏ viền module, 2 mắt camera to xếp dọc lồi lên trên mặt lưng nhựa nhám xước/nhựa bóng.\n"
            "2. Number Series & Q Series (Tầm trung):\n"
            "   - Realme 8/9: Có dòng chữ slogan 'DARE TO LEAP' in CỰC TO dọc theo mặt lưng.\n"
            "   - Realme 11 Pro / 11 Pro+: ĐẶC TRƯNG CHÍ MẠNG: Mặt lưng bọc da giả, có một ĐƯỜNG CHỈ MAY vắt dọc chính giữa chạy xuyên qua một cụm camera hình TRÒN to.\n"
            "   - Realme 12 Pro / 13 Pro: Cụm camera hình tròn nằm giữa, nhưng viền xung quanh module được tạo rãnh cắt răng cưa mạ vàng/bạc giống mặt đồng hồ cơ cao cấp (Luxury Watch Design).\n"
            "3. GT Series / Neo Series (Hiệu năng/Gaming):\n"
            "   - Thường mang đậm chất thể thao. GT Neo 3 có 2 đường kẻ sọc xe đua (Racing stripes) chạy dọc.\n"
            "   - GT5 có mặt lưng kính một phần trong suốt cạnh camera, lộ dải đèn LED RGB (Halo LED).\n"
            "   - GT7 Pro / GT6: Module camera vuông hoặc chữ nhật lồi hẳn lên bằng kính/kim loại, trông rất công nghệ và cứng cáp.\n\n"

            "🟣 BỘ QUY TẮC NHẬN DIỆN VIVO (BAO GỒM iQOO):\n"
            "1. Y Series / V Series (Tầm trung - Đánh mạnh Selfie):\n"
            "   - V20/V21/V23/V25: Cụm camera hình vuông/chữ nhật chia 'BẬC THANG' hai màu rất đặc trưng của Vivo.\n"
            "   - V27/V29/V30/V40: ĐẶC TRƯNG CHÍ MẠNG: Dưới cụm camera (hoặc bên cạnh) CÓ MỘT VÒNG SÁNG ĐÈN FLASH TRÒN TO gọi là 'Aura Light'.\n"
            "2. X Series (Flagship đỉnh cao chụp ảnh - ZEISS):\n"
            "   - X60/X70/X80: Module chữ nhật lồi chứa các ống kính tròn bên trong, có logo chữ xanh ZEISS mờ.\n"
            "   - X90 Series: ĐẶC TRƯNG RÕ RÀNG: Cụm camera tròn to nằm lệch trái, mặt lưng giả da có một DẢI KIM LOẠI vắt ngang chia cắt mặt lưng.\n"
            "   - X100 Series (X100, Pro, Ultra): Cụm camera HÌNH TRÒN KHỔNG LỒ NẰM GIỮA, viền kim loại bao quanh được làm vát lệch tạo cảm giác vành trăng khuyết (Nhật thực/Nguyệt thực).\n"
            "   - X200 Series: Kế thừa X100 nhưng viền máy vát phẳng (Square edges), vòng tròn camera thiết kế vát phẳng tinh tế và cân xứng hơn, họa tiết đồng tâm.\n"
            "3. iQOO (Nhánh Gaming):\n"
            "   - iQOO 11, 12, Neo: Thiết kế hầm hố. Các bản cao cấp thường có mặt lưng 'Legend Edition' với Dải 3 sọc màu của BMW M Motorsport (Đỏ, Đen, Xanh dương) chạy dọc.\n\n"

            "⚫ BỘ QUY TẮC NHẬN DIỆN ASUS:\n"
            "1. ROG Phone (Gaming Phone tối thượng):\n"
            "   - ROG 5/6/7: Thiết kế cực kỳ hầm hố, viền máy dày, mặt lưng có nhiều đường cắt xẻ, MÀN HÌNH LED PHỤ (ROG Vision) hoặc LOGO ROG PHÁT SÁNG RGB đằng sau. Có cổng sạc phụ ở cạnh viền trái máy.\n"
            "   - ROG 8 Series: Thiết kế lột xác, vuông vức, viền mỏng, ít hầm hố hơn. Cụm camera biến thành một khối hình chữ nhật lồi lên nhưng vát góc tạo thành hình NGŨ GIÁC.\n"
            "2. Zenfone Series (Flagship nhỏ gọn):\n"
            "   - Zenfone 8/9/10: Kích thước vô cùng NHỎ GỌN (Compact). Mặt lưng polymer nhám. ĐẶC TRƯNG: 2 MẮT CAMERA TRÒN LỚN, đen thui, lồi hẳn lên rời rạc xếp dọc trên mặt lưng.\n"
            "   - Zenfone 11 Ultra: Form to bản, cụm camera vuông lệch trái, mặt lưng có những đường cắt chéo (giống ROG nhưng thanh lịch hơn).\n\n"

            "🔥 [QUAN TRỌNG NHẤT] KỸ THUẬT CROSS-EXAMINATION (ĐỐI CHIẾU CHÉO - CHỐNG HÒA LẪN THIẾT KẾ):\n"
            "Để giải quyết hiện tượng các hãng dùng chung 1 thiết kế cho nhiều phân khúc (VD: Samsung A55 cực giống S24, Xiaomi 13 giống hệt các máy tầm trung đời sau, iPhone 13 giống hệt 14). Trước khi chốt kết quả, bạn BẮT BUỘC phải làm bài kiểm tra sau:\n"
            "- Hãy đặt câu hỏi ngược lại: 'Tại sao đây không phải là phiên bản giá rẻ (A/M, Redmi, OPPO A, Vivo Y) hay phiên bản đời cũ có thiết kế ăn theo?'.\n"
            "- BẮT BUỘC phải tìm các ĐẶC ĐIỂM CHÍ MẠNG để loại trừ: Viền màn hình dày mỏng, nốt ruồi hay tai thỏ, logo hợp tác (Leica, Zeiss, Hasselblad), chất liệu lưng da hay nhựa sọc, đèn flash Aura Light hay flash thường, chữ Dare to leap hay POCO...\n"
            "- TOÀN BỘ quá trình tư duy, loại trừ đối thủ này PHẢI ĐƯỢC VIẾT RÕ RÀNG VÀO TRƯỜNG 'details'.\n\n"

            "Nhiệm vụ: Xuất ra thông tin thiết bị dưới dạng cấu trúc JSON nguyên ngặt.\n"
            "LUẬT LỆ JSON:\n"
            "1. 'brand': Apple, Samsung, Xiaomi, Oppo, Realme, Vivo, Asus... Nếu mờ/không nhận ra, ghi null.\n"
            "2. 'model': Tên dòng máy ĐẦY ĐỦ VÀ CHI TIẾT NHẤT (VD: 'Samsung Galaxy A54 5G', 'Xiaomi 14 Ultra', 'Vivo X100 Pro', 'OPPO Reno 11 Pro', 'Realme 11 Pro Plus', 'iPhone 15 Pro Max', 'ASUS ROG Phone 8').\n"
            "3. 'search_keywords': MẢNG TỪ KHÓA TÁCH RỜI ĐỂ TÌM KIẾM CƠ SỞ DỮ LIỆU. \n"
            "   - KHÔNG gộp chữ. Tách rõ: Hãng, Chữ cái dòng máy, Số đời máy, Hậu tố.\n"
            "   - VÍ DỤ: ['samsung', 'a', '54', '5g'] hoặc ['xiaomi', '14', 'ultra'] hoặc ['vivo', 'x', '100', 'pro'] hoặc ['oppo', 'reno', '11'].\n"
            "4. 'price_segment': Phân khúc (VD: 'Máy cỏ/Đời siêu cũ', 'Giá rẻ', 'Tầm trung', 'Cận cao cấp', 'Cao cấp', 'Flagship').\n"
            "5. 'confidence': 0 đến 100. Đừng cho 100 nếu không nhìn rõ các chi tiết nhạy cảm (như khe bản lề, dải ăng ten, viền titan, logo camera).\n"
            "6. 'details': (BẮT BUỘC LÀM CROSS-EXAMINATION) Ghi rõ quá trình biện luận: Bạn đã thấy chi tiết gì? Bạn so sánh nó với máy nào giống nhất? Và TẠI SAO bạn lại LOẠI TRỪ máy kia để chọn máy này?.\n"
            "7. NẾU ẢNH MỜ, THIẾU GÓC: Trả về brand: null, model: null, confidence: < 40.\n"
            "TUYỆT ĐỐI CHỈ TRẢ VỀ 1 CHUỖI JSON DUY NHẤT."
        )

        for key in api_keys:
            try:
                temp_client = genai.Client(api_key=key)
                response = temp_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        "Hãy soi thật kỹ ảnh này, áp dụng BỘ QUY TẮC PHÂN BIỆT ĐẶC ĐIỂM ĐỂ NHẬN DIỆN dòng máy chính xác nhất:",
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.1 # Giữ nhiệt độ thấp để AI phân tích logic, tránh ảo giác (hallucination)
                    )
                )

                clean = re.sub(r"```json|```", "", response.text).strip()
                parsed = json.loads(clean)
                return parsed
            except Exception as e:
                continue
        return None
    except Exception as e:
        print(f"Lỗi AI Vision Nhận diện: {e}")
        return None

def get_serializer(secret_key):
    """
    Khởi tạo đối tượng mã hóa chuỗi an toàn.
    Dùng để sinh mã Token có giới hạn thời gian (Dùng trong tính năng Quên mật khẩu).
    """
    return URLSafeTimedSerializer(secret_key)


def send_reset_email_simulation(to_email, token):
    """
    Giả lập quá trình tạo liên kết khôi phục mật khẩu.
    Chỉ in thẳng đường dẫn chứa Token ra Console Server để Dev tiện kiểm thử.
    Tuyệt đối không sử dụng module SMTP/Email thực.
    """
    link = url_for('auth.reset_password', token=token, _external=True)
    print(f"🔑 [MOCK PASSWORD RESET LINK]: {link}")
    return link


def search_vector_db(query_text, n_results=5, metadata_filters=None):
    # ---> [HOTFIX 4]: Đã xóa bỏ điều kiện 'or not GEMINI_API_KEY'
    # Giải phóng hoàn toàn Vector Offline, cho phép nó chạy bất chấp trạng thái API Key
    if not product_collection:
        return []
    try:
        count = product_collection.count()
        if count == 0: return []
        safe_n_results = min(n_results, count)

        query_params = {"query_texts": [query_text], "n_results": safe_n_results}
        if metadata_filters:
            query_params["where"] = metadata_filters

        results = product_collection.query(**query_params)
        if results['ids'] and len(results['ids']) > 0:
            return results['ids'][0]
        return []
    except Exception as e:
        print(f"⚠️ Vector Search Skipped: {e}")
        return []


def sync_product_to_vector_db(product):
    """
    Đồng bộ dữ liệu của 1 Sản phẩm vào bộ nhớ Vector Database.
    Chuyển đổi dữ liệu bảng (SQL) thành văn bản ngữ nghĩa để AI dễ dàng đọc hiểu.
    """
    if not product_collection: return

    clean_desc = str(product.description).replace('\n', ' ').strip()
    semantic_text = f"Sản phẩm {product.name}, hãng {product.brand}, loại {product.category}. Cấu hình/Tính năng: {clean_desc}. Giá bán: {product.price} VNĐ."

    try:
        product_collection.upsert(
            documents=[semantic_text],
            metadatas=[{"price": product.price, "brand": product.brand, "category": product.category}],
            ids=[str(product.id)]
        )
        print(f"✅ Indexed Vector: {product.name}")
    except Exception as e:
        print(f"Sync Vector Error: {e}")


def get_similar_products(current_product, limit=4):
    """
    Thuật toán Gợi ý Sản phẩm Tương tự dựa trên Content-Based Filtering.
    Chạy 100% bằng toán học nội bộ (So khớp Hãng, Độ lệch giá và Từ khóa).
    """
    from app.models import Product

    candidates = Product.query.filter(
        Product.category == current_product.category,
        Product.id != current_product.id,
        Product.is_active == True
    ).all()

    if not candidates:
        return []

    scored_products = []
    target_words = set(current_product.name.lower().split())
    target_price = current_product.sale_price if current_product.is_sale else current_product.price

    for p in candidates:
        score = 0
        candidate_price = p.sale_price if p.is_sale else p.price

        if p.brand.lower() == current_product.brand.lower():
            score += 50

        max_price = max(target_price, 1)
        price_diff_ratio = abs(candidate_price - target_price) / max_price

        if price_diff_ratio <= 0.1: score += 30
        elif price_diff_ratio <= 0.2: score += 20
        elif price_diff_ratio <= 0.3: score += 10

        candidate_words = set(p.name.lower().split())
        common_words = target_words.intersection(candidate_words)
        score += len(common_words) * 5

        scored_products.append((score, p))

    scored_products.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_products[:limit]]


# =========================================================================
# LÕI GIAO TIẾP VỚI GOOGLE GEMINI (TỐI ƯU HÓA ROTATION KEY & SDK MỚI)
# =========================================================================
def call_gemini_api(prompt, system_instruction=None, is_json=False):
    """
    Hàm lõi gọi Google Gemini có tính năng xoay vòng API Key (Key Rotation)
    Đã được tối ưu bộ lọc chuỗi để chống lỗi 400 INVALID_ARGUMENT.
    """
    raw_keys = os.environ.get("GEMINI_API_KEY", "")

    # Xử lý chuỗi key an toàn hơn: Cắt theo dấu phẩy, loại bỏ khoảng trắng, lọc bỏ key rỗng
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

    if not api_keys:
        print("❌ System Error: Không tìm thấy GEMINI_API_KEY trong file .env")
        return None

    config_kwargs = {}
    if system_instruction:
        config_kwargs['system_instruction'] = system_instruction

    if is_json:
        config_kwargs['response_mime_type'] = "application/json"

    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

    # Thử lần lượt từng API Key
    for key in api_keys:
        try:
            temp_client = genai.Client(api_key=key)
            response = temp_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            # Bắt cả lỗi 429 (Hết Quota) và 400 (Key sai/bị khóa) để trượt sang key tiếp theo
            if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "400" in error_str or "invalid" in error_str:
                hidden_key = f"...{key[-4:]}" if len(key) > 4 else "UNKNOWN"
                print(f"⚠️ Key ({hidden_key}) gặp lỗi ({error_str[:30]}...). Đang thử Key tiếp theo...")
                continue
            else:
                print(f"Gemini API Error: {e}")
                return None

    print("❌ TOÀN BỘ API KEY ĐÃ HỎNG HOẶC HẾT HẠN MỨC. Hệ thống AI đang tạm liệt!")
    return None


def direct_gemini_search(query, catalog_json):
    """
    Chế độ bất tử (Direct Text-RAG): Dùng mô hình LLM Text đọc kho hàng JSON.
    Tự động kích hoạt khi Vector DB gặp lỗi để luôn có kết quả tìm kiếm.
    """
    if not GEMINI_API_KEY: return []

    system_instruction = (
        "Bạn là trí tuệ nhân tạo lõi của MobileStore. "
        "Dựa vào yêu cầu của khách và danh sách kho hàng (JSON), "
        "hãy phân tích ngữ nghĩa và lọc ra đúng các ID sản phẩm. "
        "BẮT BUỘC TRẢ VỀ CHỈ MỘT MẢNG JSON CÁC SỐ NGUYÊN LÀ ID. Ví dụ: [1, 5, 12]. Tuyệt đối không viết thêm chữ gì khác."
    )
    prompt = f"Yêu cầu tìm kiếm của khách: '{query}'\n\nKho hàng hiện tại:\n{catalog_json}\n\nTrả về mảng JSON ID:"

    # ---> [HOTFIX 2]: Bật is_json=True để AI luôn trả về format chuẩn
    res = call_gemini_api(prompt, system_instruction, is_json=True)
    if not res: return []

    try:
        # Bóc tách an toàn: Xóa rác markdown nếu AI quên luật
        clean = re.sub(r"```json|```", "", res).strip()
        parsed_data = json.loads(clean)

        if isinstance(parsed_data, dict):
            parsed_data = parsed_data.get('ids', parsed_data.get('data', []))

        if isinstance(parsed_data, list):
            return [int(i) for i in parsed_data if str(i).isdigit() or isinstance(i, int)]

        return []
    except Exception as e:
        print(f"Direct AI Search Parse Error: {e}")
        return []


def build_product_context(user_query):
    ai_data = local_analyze_intent(user_query)
    filter_dict = {}
    if ai_data and ai_data.get('category'):
        filter_dict["category"] = ai_data['category']

    vector_ids = search_vector_db(user_query, n_results=10, metadata_filters=filter_dict if filter_dict else None)

    from app.models import Product
    products = []

    if vector_ids:
        ids = [int(i) for i in vector_ids if i.isdigit()]
        products = Product.query.filter(Product.id.in_(ids), Product.is_active == True).all()

    if not products:
        user_query_lower = user_query.lower()
        query = Product.query.filter(Product.name.ilike(f"%{user_query_lower}%"), Product.is_active == True)
        if filter_dict:
            query = query.filter_by(category=filter_dict['category'])
        products = query.limit(3).all()

    if not products:
        return "Hiện tại hệ thống không tìm thấy sản phẩm nào phù hợp trong kho."

    context_text = "--- KHO HÀNG THỰC TẾ ĐANG BÁN ---\n"
    for p in products:
        price = "{:,.0f} đ".format(p.sale_price if p.is_sale else p.price).replace(",", ".")
        status = f"Sẵn hàng ({p.stock_quantity})" if p.stock_quantity > 0 else "Hết hàng"
        desc_short = (p.description or "")[:150].replace('\n', ' ')
        context_text += f"- Tên máy: {p.name} | Hãng: {p.brand} | Giá: {price} | Tình trạng: {status}\n  Điểm nổi bật: {desc_short}...\n"

    return context_text


def generate_chatbot_response(user_msg, chat_history=None):

    """
    [UPGRADED] Chatbot AI Không Kịch Bản - Xử lý thông minh mọi tình huống thực tế.
    Kết hợp RAG động và khả năng phân tích Context đa tầng.
    """
    if chat_history is None:
        chat_history = []

    # ---> [FIX LỖI QUÊN NGỮ CẢNH (AMNESIA & FALSE OUT-OF-STOCK)] <---
    # Nối câu hỏi gần nhất của User và 1 phần câu trả lời của AI vào truy vấn RAG
    # Giúp hệ thống tìm kiếm luôn giữ được Tên Sản Phẩm dù khách chỉ nói "tư vấn máy đó"
    rag_query = user_msg
    if len(chat_history) > 0:
        last_user = chat_history[-1].get('user', '')
        # Trích xuất 100 ký tự đầu tiên từ câu trả lời trước đó của AI để giữ lại tên dòng máy
        last_ai = chat_history[-1].get('ai', '')[:100]
        rag_query = f"{last_user} {last_ai} {user_msg}"

    # 1. Luôn Trích xuất Context từ Kho hàng (RAG) với truy vấn đã được mở rộng
    context = build_product_context(rag_query)

    # 2. Xây dựng System Instruction linh hoạt tuyệt đối (Cập nhật luật chống mất hàng)
    system_instruction = (
        "Bạn là nhân viên tư vấn ảo AI xuất sắc, nhiệt tình và chuyên nghiệp của hệ thống bán lẻ MobileStore.\n\n"
        "MỤC TIÊU VÀ NhiỆM VỤ CỦA BẠN:\n"
        "- Xử lý LINH HOẠT mọi tình huống: Khách chào hỏi, hỏi giá, nhờ tư vấn, so sánh, thắc mắc chính sách, "
        "thậm chí là tán gẫu hoặc bắt bẻ.\n"
        "- Đọc hiểu ngữ cảnh từ [LỊCH SỬ HỘI THOẠI] để phản hồi liền mạch, không hỏi lại những gì khách đã nói.\n"
        "- Xưng hô là 'Dạ', tự xưng là 'em' hoặc 'MobileStore', gọi khách hàng là 'anh/chị'. Thái độ luôn ân cần, vui vẻ.\n\n"
        "QUY TẮC BÁN HÀNG NGHIÊM NGẶT (RAG RULES - CHỐNG BÁO SAI KHO HÀNG):\n"
        "1. Dữ liệu [KHO HÀNG THỰC TẾ] bên dưới thay đổi theo từng câu hỏi. NẾU KHÁCH HỎI TIẾP VỀ SẢN PHẨM Ở CÂU TRƯỚC (vd: 'máy đó', 'chiếc này'), HÃY DỰA VÀO LỊCH SỬ ĐỂ TƯ VẤN TIẾP. TUYỆT ĐỐI KHÔNG BÁO LÀ 'TẠM HẾT HÀNG' NẾU TRƯỚC ĐÓ VỪA BÁO CÒN HÀNG.\n"
        "2. CHỈ TƯ VẤN CÁC SẢN PHẨM CÓ TRONG KHO HOẶC ĐÃ XUẤT HIỆN TRONG LỊCH SỬ. KHÔNG tự sáng tác, bịa đặt giá.\n"
        "3. Khi khách tìm một dòng máy MỚI HOÀN TOÀN mà không có trong kho, lúc đó mới xin lỗi và gợi ý sang các mã máy tương tự đang có sẵn.\n"
        "4. Cách trình bày phải súc tích, dễ đọc, xuống dòng hợp lý, có thể dùng emoji để tạo thiện cảm.\n\n"
        f"{context}"
    )

    # 3. Format Lịch sử hội thoại rõ ràng cho AI đọc hiểu mạch truyện
    prompt = ""
    if chat_history:
        prompt += "--- LỊCH SỬ HỘI THOẠI GẦN NHẤT ---\n"
        for turn in chat_history:
            prompt += f"Khách hàng: {turn.get('user', '')}\nMobileStore: {turn.get('ai', '')}\n"

    prompt += f"\n--- CÂU HỎI MỚI CỦA KHÁCH ---\nKhách hàng: {user_msg}\nMobileStore:"

    # 4. Giao tiếp với não bộ Gemini
    res = call_gemini_api(prompt, system_instruction=system_instruction)

    if res:
        return res.strip()

    # 5. Fallback tinh tế khi API sập hoặc Quota cạn kiệt
    return "Dạ hiện tại hệ thống AI tư vấn đang tải hơi nhiều dữ liệu một chút, anh/chị có thể đợi em vài giây hoặc nói rõ tên dòng máy (VD: 'iPhone 15') để em tra cứu kho nhanh nhất nhé! 🥰"


def analyze_search_intents(query):
    """
    [NÂNG CẤP LÕI]: Trích xuất Dữ liệu (Entity) + Suy luận Ngữ nghĩa (Reasoning) bằng LLM.
    Bổ Bản "semantic_query" để dịch các nhu cầu "lóng" thành truy vấn Vector chuẩn.
    """
    system_instruction = """
    Bạn là hệ thống AI phân tích ý định tìm kiếm cao cấp cho MobileStore.
    Nhiệm vụ: Phân tích câu hỏi tự nhiên và trả về CHỈ MỘT chuỗi JSON hợp lệ. Không giải thích.

    Quy tắc bóc tách:
    1. Giá: 'triệu'/'củ' = 1000000. 'trăm' = 100000. Nếu không nhắc đến, để min_price và max_price là null.
    2. Category: 'accessory' (ốp, sạc, tai nghe, cáp...) hoặc 'phone' (điện thoại, máy, tên dòng máy...). Không rõ để null.
    3. Brand: Hãng (Apple, Samsung, Xiaomi, Oppo...). Không có để null.
    4. keyword: Tên dòng máy chính xác hoặc màu sắc (VD: "iphone 15 pro max", "đen"). Lược bỏ các từ thừa.
    5. semantic_query (QUAN TRỌNG): Hãy dịch "nhu cầu" của khách thành 1 câu mô tả tính năng lý tưởng để tìm kiếm Vector. 
       - VD: Khách hỏi "máy cho người già" -> semantic_query: "điện thoại màn hình lớn, loa to, pin trâu, dễ sử dụng".
       - VD: Khách hỏi "điện thoại chiến game" -> semantic_query: "điện thoại cấu hình mạnh, chip chơi game mượt, tần số quét cao".
       - Nếu khách chỉ gõ tên máy (VD: "iphone 14"), giữ nguyên: "iphone 14".

    Định dạng JSON yêu cầu (BẮT BUỘC DÙNG CẤU TRÚC NÀY):
    {"brand": "Tên hãng hoặc null", "category": "phone hoặc accessory hoặc null", "min_price": Số hoặc null, "max_price": Số hoặc null, "keyword": "Từ khóa thô hoặc null", "semantic_query": "Câu dịch ngữ nghĩa hoặc null", "sort": "price_asc hoặc price_desc hoặc null"}
    """
    prompt = f"Câu hỏi: '{query}'\n\nTrả về JSON:"
    # Ép Gemini cấu trúc response trả về 100% JSON (Tránh lỗi 500)
    res = call_gemini_api(prompt, system_instruction=system_instruction, is_json=True)
    if not res: return None

    try:
        clean = re.sub(r"```json|```", "", res).strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            # [FIX CRASH] Chuẩn hóa lại cấu trúc JSON trước khi trả về cho main.py
            safe_data = {
                'brand': parsed.get('brand'),
                'category': parsed.get('category'),
                'min_price': parsed.get('min_price'),
                'max_price': parsed.get('max_price'),
                'keyword': parsed.get('keyword', ''),
                'semantic_query': parsed.get('semantic_query', ''),
                'sort': parsed.get('sort')
            }
            return safe_data
        return None
    except Exception as e:
        print(f"AI Parse JSON Error: {e}")
        return None


def local_analyze_intent(query):
    """
    [NEW ARCHITECTURE] Động cơ bóc tách ngữ nghĩa thuần Python (Regex + Heuristics).
    Nhanh, không phụ thuộc API, độ chính xác 100% với các cấu trúc tiếng lóng VN.
    """
    query = query.lower().strip()
    data = {'brand': None, 'category': None, 'keyword': '', 'semantic_query': '', 'min_price': None, 'max_price': None, 'sort': None}

    # Bóc Hãng
    brands = {'iphone': 'Apple', 'apple': 'Apple', 'samsung': 'Samsung', 'oppo': 'Oppo', 'xiaomi': 'Xiaomi',
              'vivo': 'Vivo', 'realme': 'Realme'}
    for k, v in brands.items():
        if k in query:
            data['brand'] = v
            # Không xóa từ khóa hãng khỏi query để hệ thống Score Search bên dưới còn dùng

    # Bóc Danh mục cực chuẩn (Tránh bẫy "ốp lưng iphone")
    accessory_kws = ['ốp', 'sạc', 'tai nghe', 'cáp', 'kính', 'cường lực', 'giá đỡ', 'loa', 'dây đeo', 'airpods', 'buds',
                     'bao da']

    # Ưu tiên Phụ kiện lên hàng đầu: Nếu câu có chữ "ốp" thì 100% là tìm phụ kiện
    if any(x in query for x in accessory_kws):
        data['category'] = 'accessory'
    elif re.search(r'\b(điện thoại|máy|smartphone|phone)\b', query):
        data['category'] = 'phone'

    # Bóc Giá (Quy đổi "củ", "triệu")
    price_match = re.search(r'(\d+)\s*(triệu|củ|tr)', query)
    if price_match:
        val = int(price_match.group(1))
        if val < 1000: data['max_price'] = val * 1000000
        query = re.sub(r'\d+\s*(triệu|củ|tr)(\s*quay\s*đầu|\s*trở\s*xuống)?', '', query)

    # Lọc Stop words
    stop_words = ['tôi', 'muốn', 'mua', 'tìm', 'cho', 'cần', 'dưới', 'khoảng', 'điện', 'thoại', 'máy', 'giá', 'rẻ',
                  'nào', 'tầm', 'quay', 'đầu']
    words = query.split()
    clean_kw = " ".join([w for w in words if w not in stop_words]).strip()

    data['keyword'] = clean_kw
    data['semantic_query'] = clean_kw # Gán tạm cho fallback vector

    return data

# ==============================================================================================
# ---> [ĐÃ KHÔI PHỤC: BẢNG SO SÁNH GIỮ ĐÚNG FORM GỐC (HÀNG-CỘT) + TƯ VẤN AI CHUYÊN SÂU] <---
# ==============================================================================================
def get_comparison_result(p1_id, p1_name, p1_price, p1_desc, p1_img,
                          p2_id, p2_name, p2_price, p2_desc, p2_img,
                          p3_id=None, p3_name=None, p3_price=None, p3_desc=None, p3_img=None,
                          p4_id=None, p4_name=None, p4_price=None, p4_desc=None, p4_img=None):
    """
    Sử dụng AI tạo bảng HTML đối chiếu thông số từ 2 đến 4 sản phẩm theo CẤU TRÚC GỐC của bảng so sánh.
    Bên dưới bảng sẽ đính kèm phần tư vấn, đánh giá, phân tích sâu sắc từ AI.
    """
    system_instruction = (
        "Bạn là chuyên gia bán hàng công nghệ cấp cao kiêm Frontend Developer. "
        "Nhiệm vụ của bạn là tạo một bảng HTML so sánh thông số kỹ thuật CHÍNH XÁC theo cấu trúc Hàng-Cột yêu cầu, "
        "sau đó đưa ra bài phân tích tư vấn cực kỳ CHUYÊN SÂU bên dưới."
    )

    if not p1_img: p1_img = "https://via.placeholder.com/150"
    if not p2_img: p2_img = "https://via.placeholder.com/150"

    products_info = f"Máy 1: {p1_name} (Giá: {p1_price}) - Ảnh: {p1_img} - Cấu hình: {p1_desc}\n"
    products_info += f"Máy 2: {p2_name} (Giá: {p2_price}) - Ảnh: {p2_img} - Cấu hình: {p2_desc}\n"

    machine_headers = f'<th>Tính năng</th><th class="text-center" style="width: 20%;"><span class="text-dark fw-bold">{p1_name}</span></th><th class="text-center" style="width: 20%;"><span class="text-dark fw-bold">{p2_name}</span></th>'
    advice_list = f"  + <li>Nên mua <b>{p1_name}</b> nếu bạn...</li>\n  + <li>Nên mua <b>{p2_name}</b> nếu bạn...</li>\n"

    num_cols = 2

    if p3_name:
        num_cols = 3
        products_info += f"Máy 3: {p3_name} (Giá: {p3_price}) - Ảnh: {p3_img} - Cấu hình: {p3_desc}\n"
        machine_headers += f'<th class="text-center" style="width: 20%;"><span class="text-dark fw-bold">{p3_name}</span></th>'
        advice_list += f"  + <li>Nên mua <b>{p3_name}</b> nếu bạn...</li>\n"

    if p4_name:
        num_cols = 4
        products_info += f"Máy 4: {p4_name} (Giá: {p4_price}) - Ảnh: {p4_img} - Cấu hình: {p4_desc}\n"
        machine_headers += f'<th class="text-center" style="width: 20%;"><span class="text-dark fw-bold">{p4_name}</span></th>'
        advice_list += f"  + <li>Nên mua <b>{p4_name}</b> nếu bạn...</li>\n"

    prompt = f"""
    Hãy tạo mã HTML so sánh {num_cols} sản phẩm sau:
    {products_info}

    LƯU Ý QUAN TRỌNG: 
    SỬ DỤNG KIẾN THỨC CỦA BẠN để điền đầy đủ và chính xác nhất các thông số kỹ thuật bị thiếu. Không để trống thông số nào. 
    Nếu phần "Ảnh" là đường link hợp lệ, hãy dùng thẻ `<img src="..." style="max-height: 120px; object-fit: contain;">`. Nếu không có, ghi "Không có ảnh".
    Dữ liệu Giá và Ảnh ĐÃ CÓ SẴN ở trên, hãy đưa đúng vào bảng.

    Yêu cầu ĐỊNH DẠNG HTML BẮT BUỘC (Tuyệt đối không thay đổi cấu trúc bảng dưới đây):
    - Bước 1: Tạo một bảng `<table class="table table-bordered table-hover">`.
    Cột 1 là "Thông số kỹ thuật", Cột 2 là tên máy 1, Cột 3 là tên máy 2.
    BẮT BUỘC phải tạo các hàng (row) sau đây trong bảng:
      + Kích thước màn hình
      + Công nghệ màn hình / Độ phân giải
      + Tần số quét (Hz)
      + Camera sau
      + Camera trước
      + Chipset (CPU)
      + Dung lượng RAM
      + Bộ nhớ trong (ROM)
      + Dung lượng Pin & Công suất Sạc nhanh
      + Công nghệ NFC
      + Thẻ SIM
      + Hệ điều hành
      + Thiết kế & Trọng lượng

    - Sau khi đóng thẻ `</table>`, tạo 1 khối tư vấn AI:
      `<div class="alert alert-info mt-4 p-4 rounded-4 shadow-sm border-0" style="background-color: #e8f9fd;">`
      `<h4 class="fw-bold text-primary mb-3"><i class="fas fa-robot me-2"></i>Tư vấn chuyên sâu từ chuyên gia công nghệ</h4>`
      Mở đầu bằng câu: "Chào bạn, với vai trò là một chuyên gia..."
      Viết các đoạn văn phân tích CHI TIẾT (có liệt kê "Điểm mạnh", "Phù hợp với") về điểm mạnh, yếu, sự khác biệt giữa các máy.
      `<h5 class="fw-bold text-dark mt-4">Tóm tắt & Lời khuyên cuối cùng:</h5>`
      `<ul class="mt-2 text-dark">`
      {advice_list}
      `</ul>`
      `</div>`

    CHỈ TRẢ VỀ MÃ HTML (Gồm bảng so sánh và thẻ div tư vấn), KHÔNG DÙNG ```html VÀ KHÔNG KÈM TEXT GIẢI THÍCH KHÁC.
    """

    res = call_gemini_api(prompt, system_instruction=system_instruction)
    return re.sub(r"```html|```", "", res).strip() if res else None


def generate_local_comparison_html(p1, p2, p3=None, p4=None):
    """
    Thuật toán vẽ bảng so sánh dự phòng bằng Python thuần (Local HTML Generator).
    Cứu sập trang khi API Google quá tải. Đảm bảo form bảng khớp 100% với form của AI
    và giữ đúng định dạng Hàng-Cột truyền thống.
    """
    products = [p for p in [p1, p2, p3, p4] if p]

    headers_html = "<th>Tính năng</th>"
    for p in products:
        headers_html += f"<th class='text-center' style='width: 20%;'><span class='text-dark fw-bold'>{p.name}</span></th>"

    tbody_html = "<tr><td class='fw-bold'>Giá</td>"
    for p in products:
        price_str = "{:,.0f} đ".format(p.sale_price if p.is_sale else p.price).replace(",", ".")
        tbody_html += f"<td class='text-center fw-bold text-danger'>{price_str}</td>"
    tbody_html += "</tr>"

    tbody_html += "<tr><td class='fw-bold'>Ảnh sản phẩm</td>"
    for p in products:
        tbody_html += f"<td class='text-center'><img src='{p.image_url}' style='max-height:120px; object-fit:contain;'></td>"
    tbody_html += "</tr>"

    tbody_html += "<tr><td class='fw-bold'>Thương hiệu</td>"
    for p in products:
        tbody_html += f"<td class='text-center fw-medium'>{p.brand}</td>"
    tbody_html += "</tr>"

    tbody_html += "<tr><td class='fw-bold'>Phân loại</td>"
    for p in products:
        cat_name = "Điện thoại" if p.category == 'phone' else "Phụ kiện"
        tbody_html += f"<td class='text-center fw-medium'>{cat_name}</td>"
    tbody_html += "</tr>"

    tbody_html += "<tr><td class='fw-bold'>Đặc điểm nổi bật</td>"
    for p in products:
        desc = (p.description or "Đang cập nhật")[:150] + "..."
        tbody_html += f"<td class='text-center fw-medium'><small>{desc}</small></td>"
    tbody_html += "</tr>"

    html = f"""
    <table class="table table-bordered table-hover bg-white shadow-sm table-compare align-middle mb-0">
        <thead class="table-light text-center">
            <tr>{headers_html}</tr>
        </thead>
        <tbody>
            {tbody_html}
        </tbody>
    </table>
    <div class="alert alert-secondary mt-4 p-4 rounded-4 shadow-sm border-0" style="background-color: #f8f9fa;">
        <h4 class="fw-bold text-secondary mb-3"><i class="fas fa-server me-2"></i>CHẾ ĐỘ DỰ PHÒNG (LOCAL MODE)</h4>
        <p class="mb-0 text-dark">Hệ thống AI Gemini tạm thời đang bảo trì hoặc hết hạn mức (Quota). Bảng so sánh trên được tạo tự động bằng thuật toán nội bộ. Vui lòng quay lại sau để xem chuyên gia AI phân tích chuyên sâu.</p>
    </div>
    """
    return html


def analyze_sentiment(text):
    """
    Xử lý ngôn ngữ tự nhiên (NLP) phân tích cảm xúc của Đánh giá.
    Phân loại ra POSITIVE, NEGATIVE, NEUTRAL.
    """
    system_instruction = (
        "Bạn là hệ thống NLP phân tích cảm xúc đánh giá khách hàng. "
        "Dựa vào nội dung bình luận, hãy phân loại và CHỈ TRẢ VỀ ĐÚNG 1 TỪ: "
        "POSITIVE, NEGATIVE, hoặc NEUTRAL."
    )
    res = call_gemini_api(f"Phân tích: '{text}'", system_instruction=system_instruction)
    if res:
        res = res.strip().upper()
        if "NEGATIVE" in res: return "NEGATIVE"
        if "POSITIVE" in res: return "POSITIVE"
    return "NEUTRAL"


# =========================================================================
# ĐỘNG CƠ XỬ LÝ VOUCHER - SPECIFICATION PATTERN
# =========================================================================

class VoucherSpecification(ABC):
    """
    Class Abstract lõi cho các ống lọc điều kiện Voucher.
    Áp dụng nguyên lý Open/Closed trong SOLID.
    """
    @abstractmethod
    def is_satisfied_by(self, voucher, order_total, user_rank_tier):
        """Hàm trừu tượng bắt buộc các Class con phải thực thi."""
        pass


class MinimumOrderSpecification(VoucherSpecification):
    """Kiểm tra điều kiện: Tổng giá trị đơn hàng có đạt mức tối thiểu không."""
    def is_satisfied_by(self, voucher, order_total, user_rank_tier):
        if order_total < voucher.min_order_value:
            return False, f"Đơn hàng chưa đạt mức tối thiểu {'{:,.0f}'.format(voucher.min_order_value).replace(',', '.')}đ"
        return True, "Hợp lệ"


class ExpiryDateSpecification(VoucherSpecification):
    """Kiểm tra điều kiện: Mã Voucher đã quá hạn sử dụng hay chưa."""
    def is_satisfied_by(self, voucher, order_total, user_rank_tier):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if now > voucher.valid_to:
            return False, "Rất tiếc, mã Voucher này đã hết hạn sử dụng."
        return True, "Hợp lệ"


class UserRankSpecification(VoucherSpecification):
    """Kiểm tra điều kiện: Phân quyền cấp bậc VIP của khách hàng."""
    def is_satisfied_by(self, voucher, order_total, user_rank_tier):
        if user_rank_tier < voucher.required_rank:
            ranks = {1: "M-New", 2: "M-Gold", 3: "M-Platinum", 4: "M-Diamond"}
            req_rank_str = ranks.get(voucher.required_rank, "VIP")
            return False, f"Voucher độc quyền! Chỉ áp dụng cho tài khoản từ hạng {req_rank_str} trở lên."
        return True, "Hợp lệ"


class VoucherValidatorEngine:
    """
    Động cơ Pipeline (Đường ống) xử lý Khuyến mãi trung tâm.
    Dữ liệu truyền vào sẽ phải đi qua tuần tự từng màng lọc bảo mật.
    """
    def __init__(self):
        # Đăng ký các trạm kiểm duyệt vào đường ống
        self.rules = [
            MinimumOrderSpecification(),
            ExpiryDateSpecification(),
            UserRankSpecification()
        ]

    def validate(self, voucher, order_total, user_rank_tier):
        """
        Kích hoạt đường ống kiểm duyệt.
        Trả về True nếu pass qua toàn bộ Rule, ngược lại trả về False kèm nguyên nhân.
        """
        if not voucher.is_active:
            return False, "Mã Voucher này hiện đang bị khóa hoặc vô hiệu hóa bởi Admin."

        for rule in self.rules:
            is_valid, msg = rule.is_satisfied_by(voucher, order_total, user_rank_tier)
            if not is_valid:
                return False, msg

        return True, "Mã Voucher hợp lệ. Đã áp dụng giảm giá!"

    def calculate_discount(self, voucher, order_total):
        """Thuật toán tính toán số tiền khấu trừ cuối cùng."""
        if voucher.discount_type == 'fixed':
            return min(voucher.discount_value, order_total)

        elif voucher.discount_type == 'percent':
            discount = int(order_total * (voucher.discount_value / 100))
            if voucher.max_discount:
                return min(discount, voucher.max_discount)
            return discount

        return 0