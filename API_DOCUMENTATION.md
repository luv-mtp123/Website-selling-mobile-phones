# 📚 TÀI LIỆU API HỆ THỐNG MOBILESTORE

> **Được tự động sinh ra bởi `api_doc_builder.py` lúc 08:52 24/02/2026**
> Đây là tài liệu tóm tắt toàn bộ các đường dẫn (Endpoints) đang hoạt động trong hệ thống.

---

## 📂 Module: `ADMIN`

### 🔹 Endpoint: `/admin`
- **HTTP Method:** `GET`
- **Function:** `dashboard()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/admin/export/report`
- **HTTP Method:** `GET`
- **Function:** `export_revenue_report()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/admin/order/update/<int:id>/<status>`
- **HTTP Method:** `GET`
- **Function:** `update_order_status()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/admin/product/add`
- **HTTP Method:** `POST`
- **Function:** `add_product()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/admin/product/edit/<int:id>`
- **HTTP Method:** `GET, POST`
- **Function:** `edit_product()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/admin/product/delete/<int:id>`
- **HTTP Method:** `GET`
- **Function:** `delete_product()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/admin/tradein/update`
- **HTTP Method:** `POST`
- **Function:** `update_tradein()`
- **Mô tả:** Không có mô tả chi tiết.

---

## 📂 Module: `AUTH`

### 🔹 Endpoint: `/login`
- **HTTP Method:** `GET, POST`
- **Function:** `login()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/register`
- **HTTP Method:** `GET, POST`
- **Function:** `register()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/logout`
- **HTTP Method:** `GET`
- **Function:** `logout()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/forgot-password`
- **HTTP Method:** `GET, POST`
- **Function:** `forgot_password()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/reset-password/<token>`
- **HTTP Method:** `GET, POST`
- **Function:** `reset_password()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/login/google`
- **HTTP Method:** `GET`
- **Function:** `login_google()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/authorize/google`
- **HTTP Method:** `GET`
- **Function:** `authorize_google()`
- **Mô tả:** Không có mô tả chi tiết.

---

## 📂 Module: `MAIN`

### 🔹 Endpoint: `/`
- **HTTP Method:** `GET`
- **Function:** `home()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/product/<int:id>`
- **HTTP Method:** `GET`
- **Function:** `product_detail()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/product/<int:id>/comment`
- **HTTP Method:** `POST`
- **Function:** `add_comment()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/cart`
- **HTTP Method:** `GET`
- **Function:** `view_cart()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/cart/add/<int:id>`
- **HTTP Method:** `POST`
- **Function:** `add_to_cart()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/cart/update/<int:id>/<action>`
- **HTTP Method:** `GET`
- **Function:** `update_cart()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/checkout`
- **HTTP Method:** `GET, POST`
- **Function:** `checkout()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/payment/qr/<int:order_id>`
- **HTTP Method:** `GET`
- **Function:** `payment_qr()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/api/payment/check/<int:order_id>`
- **HTTP Method:** `GET`
- **Function:** `check_payment_status()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/test/simulate-bank-success/<int:order_id>`
- **HTTP Method:** `GET`
- **Function:** `simulate_bank_success()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/trade-in`
- **HTTP Method:** `GET, POST`
- **Function:** `trade_in()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/order/cancel/<int:id>`
- **HTTP Method:** `GET`
- **Function:** `cancel_order_user()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/compare`
- **HTTP Method:** `GET, POST`
- **Function:** `compare_page()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/dashboard`
- **HTTP Method:** `GET`
- **Function:** `dashboard()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/profile/update`
- **HTTP Method:** `POST`
- **Function:** `update_profile()`
- **Mô tả:** Không có mô tả chi tiết.

### 🔹 Endpoint: `/api/chatbot`
- **HTTP Method:** `POST`
- **Function:** `chatbot_api()`
- **Mô tả:** Không có mô tả chi tiết.

---

