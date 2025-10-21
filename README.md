<div align="center">

# 🏫 KSSV-DNU  
### *Hệ Thống Quản Lý Ký Túc Xá Đại Nam – Digital Transformation Project*

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-Latest-DA3B01?style=for-the-badge&logo=databricks&logoColor=white)](https://www.sqlalchemy.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)


<img src="logoDaiNam.png" width="200"/>

**Hệ thống chuyển đổi số quản lý khách sạn sinh viên Đại Nam – kết hợp AI & IoT để số hóa toàn bộ quy trình vận hành**

[🚀 Demo](#-demo) • [✨ Tính Năng](#-tính-năng) • [🏗️ Kiến Trúc](#-kiến-trúc-hệ-thống) • [⚙️ Cài Đặt](#-cài-đặt) • [📖 API Docs](#-api-documentation)

---

</div>

## 🎯 Giới Thiệu

**KTX-DNU** là hệ thống **chuyển đổi số** phục vụ quản lý ký túc xá Đại Nam, hỗ trợ tự động hóa các quy trình truyền thống như:
- Đăng ký – check-in / check-out sinh viên  
- Gửi phản ánh sự cố (điện, nước, thiết bị, vệ sinh, internet, khác)  
- Xử lý ưu tiên và phân loại sự cố bằng **AI tiếng Việt (PhoBERT)**  
- Thông báo, theo dõi và thống kê vận hành KTX  
- Quản trị nhiều vai trò: **Sinh viên / Quản lý / Admin**

---

## ✨ Tính Năng

### 👩‍🎓 1. Quản Lý Sinh Viên
- Đăng ký tài khoản (do quản lý cấp)  
- Cập nhật hồ sơ, phòng, giường, tòa nhà  
- Check-in, check-out online  
- Gửi yêu cầu thay đổi thông tin cá nhân

### ⚙️ 2. Quản Lý Sự Cố
- Sinh viên gửi phản ánh kèm hình ảnh  
- AI PhoBERT tự động **phân loại loại sự cố** (`điện`, `nước`, `internet`, `thiết bị`, `vệ sinh`, `khác`)  
- AI xác định **mức độ ưu tiên** (`normal`, `high`, `urgent`)  
- Gửi cảnh báo cho quản lý phụ trách tòa nhà  
- Theo dõi trạng thái xử lý: pending, in_progress, done

### 🤖 3. AI Phân Tích & Gợi Ý
- Mô hình **PhoBERT** fine-tune trên dữ liệu KTX-DNU  
- Pipeline AI gồm:  
  - `text_preprocess_kssv.py`  
  - `train_phobert.py`  
  - `predictor.py`  
- API `/ai/predict` → dự đoán loại sự cố và mức ưu tiên  
- Kết quả hiển thị realtime trên giao diện admin

### 📊 4. Quản Trị Hệ Thống
- Admin dashboard quản lý sinh viên, sự cố, yêu cầu check-in/out  
- Giao diện tách biệt cho **Admin** và **Student**  
- CRUD users, reports, checkins  
- Xuất dữ liệu CSV, thống kê lỗi, tra cứu nhanh  
- Giao diện hiện đại, responsive

### 🔔 5. Thông Báo & IoT
- Hệ thống có thể mở rộng gửi cảnh báo sự cố qua **Telegram Bot / Email**  
- Tích hợp **ESP32-CAM** để giám sát phòng và phát hiện chuyển động  
- Khi phát hiện chuyển động bất thường → gửi cảnh báo AI

---

## 🛠️ Công Nghệ Sử Dụng

| Thành Phần | Công Nghệ | Mục Đích |
|-------------|------------|-----------|
| 🐍 **Python** | 3.12+ | Ngôn ngữ chính |
| ⚡ **FastAPI** | Latest | Backend REST API |
| 🧮 **SQLAlchemy + SQLite** | Latest | ORM & Database |
| 🧠 **PhoBERT / Transformers** | HuggingFace | Mô hình AI tiếng Việt |
| 💾 **Pandas / scikit-learn** | Latest | Xử lý dữ liệu AI |
| 💻 **HTML / CSS / JS** | Frontend UI | Giao diện sinh viên & admin |
| 🧰 **Uvicorn** | Latest | ASGI server |
| ☁️ **Git LFS** | Latest | Lưu trữ model AI lớn |
| 📦 **dotenv** | Latest | Cấu hình môi trường |

---

# KTX-DNU – Hệ thống Quản lý Ký túc xá (AI & IoT)

> Dự án môn **AI & IoT – Chuyển đổi số ký túc xá** tại **Đại học Đại Nam**.  
> Ứng dụng FastAPI + AI (PhoBERT) để quản lý báo cáo sự cố, dự đoán loại & mức độ ưu tiên, và cung cấp dashboard quản trị.

---

## ⚙️ Cài đặt

### 1️⃣ Yêu cầu
- Python 3.12+
- FastAPI, Uvicorn, SQLAlchemy
- HuggingFace Transformers
- File `.env` chứa `GEMINI_API_KEY` hoặc model nội bộ

> Gợi ý `.env` tối thiểu:
```env
# API sinh phản hồi tự động
GEMINI_API_KEY=your_api_key_here
```

---

### 2️⃣ Tạo môi trường ảo & cài dependency
```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt (Windows)
venv\Scripts\activate

# Kích hoạt (Mac/Linux)
source venv/bin/activate

# Cài các thư viện cần thiết
pip install -r requirements.txt
```

---

### 3️⃣ Chạy Backend (FastAPI)
```bash
# Di chuyển đến thư mục backend
cd backend

# Chạy server FastAPI
uvicorn main:app --reload
```

> 🔗 Sau khi chạy, truy cập:  
> http://127.0.0.1:8000/docs → Xem tài liệu API (Swagger UI)  
> http://127.0.0.1:8000 → Backend đang hoạt động

---

### 4️⃣ Chạy Frontend (HTML/JS)
```bash
# Di chuyển đến thư mục frontend
cd frontend

# Cách 1: Dùng Python server tích hợp sẵn
python -m http.server 5500

# Cách 2: Nếu dùng VSCode có Live Server, chỉ cần nhấn “Go Live”
```

> 🔗 Sau khi chạy, truy cập:  
> http://localhost:5500/student.html → Giao diện Sinh viên  
> http://localhost:5500/admin.html → Giao diện Quản trị  

---

### ✅ Tóm tắt nhanh

| Thành phần | Lệnh khởi động | Ghi chú |
|-------------|----------------|---------|
| **Backend (FastAPI)** | `uvicorn main:app --reload` | Cổng mặc định `8000` |
| **Frontend (HTML)** | `python -m http.server 5500` | Cổng tùy chỉnh `5500` |

---

## 📖 API Documentation

| Method | Endpoint           | Mô tả                               |
|:------:|--------------------|--------------------------------------|
| POST   | `/auth/login`      | Đăng nhập                            |
| GET    | `/users`           | Lấy danh sách người dùng            |
| POST   | `/reports`         | Tạo mới báo cáo sự cố               |
| GET    | `/reports`         | Lấy danh sách sự cố                 |
| POST   | `/ai/predict`      | Dự đoán loại & độ ưu tiên sự cố     |
| GET    | `/checkins`        | Danh sách yêu cầu check-in/out      |
| GET    | `/uploads/{file}`  | Xem ảnh hoặc file upload            |

> Lưu ý: Chi tiết tham số & schema tham khảo trực tiếp tại **/docs**.

---

## 📚 Dự án AI
- **Dữ liệu huấn luyện:** `Data.csv`, `Datakssv.csv`
- **Model sử dụng:** `vinai/phobert-base`
- **Script chính:**
  - `backend/ai/train_phobert.py` – Huấn luyện mô hình
  - `backend/ai/predictor.py` – Dự đoán realtime
  - `backend/ai/text_preprocess_kssv.py` – Tiền xử lý tiếng Việt

> Ví dụ chạy nhanh:
```bash
# Huấn luyện
python backend/ai/train_phobert.py

# Dự đoán nhanh (CLI)
python -m backend.ai.predictor "ống nước tầng 2 bị vỡ, đang tràn ra hành lang"
```

---

## 🚀 Roadmap
- Tự động phản hồi bằng **Gemini / BartPho**
- Tích hợp **cảnh báo Telegram Bot**
- **Dashboard AI** thống kê lỗi theo thời gian
- Lưu trữ dữ liệu **đám mây (Cloud Storage)**

---

## 👨‍💻 Tác giả
- **Nguyễn Anh Tuấn** – Đại học Đại Nam  
- **Email:** tuanvtv2004@gmail.com

<div align="center">

⭐ Nếu bạn thấy dự án hữu ích, hãy cho 1 star nhé! ⭐


</div>
```
