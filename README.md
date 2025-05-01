# DataSenseAI - Hệ Thống Chatbot Phân Tích Dữ Liệu Thông Minh

![React Badge](https://img.shields.io/badge/React-18-blue)
![TypeScript Badge](https://img.shields.io/badge/TypeScript-5.0-blue)
![TailwindCSS Badge](https://img.shields.io/badge/TailwindCSS-3.3-blue)
![Node.js Badge](https://img.shields.io/badge/Node.js-18-green)
![FastAPI Badge](https://img.shields.io/badge/FastAPI-0.104-green)
![Mistral Badge](https://img.shields.io/badge/Mistral-7B-purple)
![PyTorch Badge](https://img.shields.io/badge/PyTorch-2.1-orange)
![Prisma Badge](https://img.shields.io/badge/Prisma-5.3-pink)

Hệ thống chatbot phân tích dữ liệu toàn diện, tích hợp giao diện người dùng hiện đại (React + TypeScript + TailwindCSS) với backend AI mạnh mẽ (Mistral 7B) đã được fine-tune để tự động phân tích dữ liệu từ file CSV/XLSX.

## 📋 Tổng Quan

DataSenseAI cung cấp giải pháp đầy đủ để phân tích dữ liệu tự động với giao diện chat thân thiện. Người dùng có thể tải lên file CSV/XLSX, và hệ thống sẽ tự động làm sạch dữ liệu, tạo biểu đồ trực quan, đưa ra insights, và trả lời các câu hỏi về dữ liệu.

### 🌟 Tính Năng Chính

- **Phân tích dữ liệu tự động** từ file CSV/XLSX
- **Giao diện chat trực quan** với React & TailwindCSS
- **Làm sạch dữ liệu thông minh** tự động xử lý các vấn đề phổ biến
- **Trực quan hóa dữ liệu động** với các loại biểu đồ phù hợp
- **Phát hiện insights và xu hướng** tự động sử dụng AI
- **Hỗ trợ dự đoán** dựa trên dữ liệu lịch sử
- **Stream responses** từ model AI
- **Tối ưu hóa cho GPU 8GB** với 4-bit quantization
- **Responsive design** cho mọi thiết bị

## 🚀 Cài Đặt và Triển Khai

### Yêu Cầu Hệ Thống

- **Node.js**: v18 trở lên
- **Python**: v3.10 trở lên
- **GPU (khuyến nghị)**: CUDA 11.8+, 8GB+ VRAM

### Cài Đặt với Docker (khuyến nghị)

```bash
# Clone repository
git clone https://github.com/yourusername/datasense-ai.git
cd datasense-ai

# Chạy toàn bộ stack với Docker Compose
docker-compose up -d

# Chỉ chạy frontend & backend (không ML service)
docker-compose up -d client server
```

### Cài Đặt Thủ Công

#### 1. Cài Đặt Frontend

```bash
# Di chuyển đến thư mục client
cd apps/client

# Cài đặt dependencies
pnpm install

# Khởi chạy server development
pnpm dev
```

#### 2. Cài Đặt Backend

```bash
# Di chuyển đến thư mục server
cd apps/server

# Cài đặt dependencies
pnpm install

# Thiết lập Prisma
pnpm prisma generate

# Khởi chạy server development
pnpm dev
```

#### 3. Cài Đặt ML Service

```bash
# Di chuyển đến thư mục ml-service
cd apps/ai-service

# Tạo môi trường Python
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt

# Tải model (nếu cần)
python scripts/download_model.py

# Khởi chạy ML service
python -m app.main
```

## 🔧 Cấu Hình

### Biến Môi Trường

#### Client (.env)

```
VITE_API_URL=http://localhost:3000/api
VITE_WS_URL=ws://localhost:3000
```

#### Server (.env)

```
PORT=3000
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/datasense"
ML_SERVICE_URL=http://localhost:8000
```

#### ML Service (.env)

```
MODEL_CONFIG_PATH=configs/model_config.json
DEVICE=cuda
```

## 🧠 Fine-tuning Model

DataSenseAI sử dụng model Mistral 7B được fine-tune đặc biệt cho nhiệm vụ phân tích dữ liệu. Quy trình fine-tuning bao gồm:

1. **Thu thập dữ liệu**: Sử dụng dataset từ Hugging Face, Kaggle và GitHub chứa các mẫu phân tích dữ liệu và câu hỏi-trả lời
2. **Tiền xử lý dữ liệu**: Chuẩn hóa format câu hỏi-trả lời và tạo prompt template phù hợp
3. **Fine-tuning hiệu quả**: Sử dụng QLoRA để fine-tune trên GPU với ít tài nguyên
4. **Đánh giá**: Đánh giá mô hình trên tập dữ liệu test

### Để Fine-tune Lại Mô Hình:

```bash
cd apps/ml-service
python run_training.py
```

## 📊 Luồng Dữ Liệu

1. **Upload file**: User → Frontend → Backend → Temporary Storage
2. **Parse file**: Backend → Data Processing → Database
3. **Basic Analysis**: Backend → Automatically analyze and clean data
4. **ML Analysis**: Backend → ML Service → In-depth analysis → Database
5. **Visualization**: Backend → ML Service → Generate charts → Frontend
6. **Chat**: User → Frontend → Backend → ML Service → Stream response → Frontend

## 🛠️ API Endpoints

### Backend API

- `POST /api/files/upload` - Tải lên file để phân tích
- `GET /api/files/:id/summary` - Lấy tổng hợp dữ liệu của file
- `GET /api/files/:id/visualizations` - Lấy các biểu đồ cho file
- `POST /api/chat/:fileId/message` - Gửi tin nhắn chat
- `POST /api/analysis/:fileId/predict` - Tạo dự đoán dựa trên dữ liệu

### ML Service API

- `POST /analyze/insights` - Phân tích và tạo insights từ dữ liệu
- `POST /analyze/visualize` - Tạo biểu đồ và trực quan hóa dữ liệu
- `POST /analyze/predict` - Tạo dự đoán dựa trên dữ liệu
- `POST /chat/message` - Xử lý tin nhắn chat
- `POST /chat/stream` - Xử lý tin nhắn chat với phản hồi stream

## 🤝 Đóng Góp

Chúng tôi rất hoan nghênh mọi đóng góp! Hãy làm theo các bước sau:

1. Fork dự án
2. Tạo branch mới (`git checkout -b feature/amazing-feature`)
3. Commit thay đổi của bạn (`git commit -m 'Add some amazing feature'`)
4. Push lên branch (`git push origin feature/amazing-feature`)
5. Mở Pull Request

## 📜 Giấy Phép

Phân phối theo giấy phép MIT. Xem `LICENSE` để biết thêm thông tin.

## 📱 Screenshots

![Dashboard](docs/img/dashboard.png)
![Chat Interface](docs/img/chat.png)
![Data Analysis](docs/img/analysis.png)
![Visualizations](docs/img/visualizations.png)

## 🙏 Lời Cảm Ơn

- [Mistral AI](https://mistral.ai/) - Cung cấp mô hình nền tảng Mistral 7B
- [React](https://reactjs.org/) - Frontend framework
- [TailwindCSS](https://tailwindcss.com/) - Utility-first CSS framework
- [shadcn/ui](https://ui.shadcn.com/) - Thư viện UI components
- [Recharts](https://recharts.org/) - Thư viện biểu đồ
- [Node.js](https://nodejs.org/) - JavaScript runtime
- [Prisma](https://www.prisma.io/) - ORM for Node.js
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework for Python