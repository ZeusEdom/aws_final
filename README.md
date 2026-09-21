# 🌩️ Serverless Weather Telemetry Dashboard (AWS)

![AWS Architecture](https://img.shields.io/badge/AWS-Serverless-orange?style=for-the-badge&logo=amazon-aws)
![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

Dự án **Serverless Weather Telemetry Dashboard** thu thập, xử lý và hiển thị dữ liệu thời tiết real-time của các thành phố tại Việt Nam và quốc tế sử dụng kiến trúc hoàn toàn **Serverless trên AWS** (S3, DynamoDB, Lambda, API Gateway, EventBridge).

---

## 🏛️ Kiến Trúc Hệ Thống (Architecture)

```
[ OpenWeatherMap API ]
          ▲
          │ (REST API Call - 30 phút/lần)
          │
  [ EventBridge Schedule ] ──► [ Lambda: weather-fetcher ]
                                         │
                                         ▼ (PutItem + TTL)
                                 [ Amazon DynamoDB ]
                                         ▲
                                         │ (Query)
                                         │
  [ User Browser ] ──► [ Amazon S3 ] ──► [ API Gateway ] ──► [ Lambda: weather-api-handler ]
   (Static Web)         (Static Hosting)  (HTTP API /weather)
```

### Thành phần chính:
1. **Amazon S3**: Host Frontend Dashboard (Static Website Hosting).
2. **Amazon API Gateway (HTTP API)**: Cung cấp endpoint công khai `GET /weather` có bật CORS.
3. **AWS Lambda (`weather-api-handler`)**: Đọc dữ liệu lịch sử và telemetry mới nhất từ DynamoDB.
4. **AWS Lambda (`weather-fetcher`)**: Tự động gọi OpenWeatherMap API cho 10 thành phố và ghi dữ liệu vào DynamoDB.
5. **Amazon EventBridge**: Trigger `rate(30 minutes)` tự động kích hoạt `weather-fetcher`.
6. **Amazon DynamoDB**: Lưu trữ NoSQL với Partition Key `city`, Sort Key `timestamp` và tự động dọn dẹp bằng `TTL`.

---

## 📂 Cấu Trúc Thư Mục (Project Structure)

```
aws/
├── index.html              # Frontend Single-Page App (IBM Plex Mono + Fraunces Dark UI)
├── lambda_fetcher.py       # Code AWS Lambda cào dữ liệu thời tiết & ghi DynamoDB
├── lambda_api_handler.py   # Code AWS Lambda API Handler phục vụ Frontend
├── iam_policies.json       # Định nghĩa IAM Policies chuẩn Least Privilege
├── template.yaml           # Infrastructure as Code (AWS SAM / CloudFormation)
├── HUONG_DAN_TRIEN_KHAI.md # Hướng dẫn triển khai từng bước qua AWS Console
└── README.md               # Tài liệu dự án
```

---

## 🚀 Hướng Dẫn Triển Khai Nhanh (Deployment Guide)

### Cách 1: Tự Động Bằng AWS SAM (Infrastructure as Code)
```bash
# 1. Build stack
sam build

# 2. Deploy lên AWS
sam deploy --guided
```

### Cách 2: Thủ Công Qua AWS Console (Chụp hình cho Báo cáo)
Tham khảo chi tiết từng bước tại [HUONG_DAN_TRIEN_KHAI.md](file:///HUONG_DAN_TRIEN_KHAI.md).

1. **DynamoDB**: Tạo bảng `WeatherData` (PK: `city` [String], SK: `timestamp` [Number], On-demand, TTL: `ttl`).
2. **IAM Roles**: Tạo `weather-fetcher-role` (Write Policy) và `weather-api-role` (Read Policy).
3. **Lambda Fetcher**: Tạo function `weather-fetcher` (Python 3.12), dán code từ `lambda_fetcher.py`, thêm env vars (`OWM_API_KEY`, `TABLE_NAME`, `CITIES`), timeout 15s.
4. **EventBridge**: Thêm trigger `rate(30 minutes)` cho `weather-fetcher`.
5. **Lambda API Handler**: Tạo function `weather-api-handler`, dán code từ `lambda_api_handler.py`, env var (`TABLE_NAME`), timeout 10s.
6. **API Gateway**: Tạo HTTP API `weather-dashboard-api`, route `GET /weather`, bật CORS (`*`), copy Invoke URL.
7. **S3 Static Website**: Thêm Invoke URL vào `index.html`, bật Static Website Hosting trên S3 bucket, set Public Read Policy và Upload `index.html`.

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)

- **Cloud Platform**: Amazon Web Services (AWS Free Tier Ready - $0/tháng)
- **Backend Services**: AWS Lambda, DynamoDB, API Gateway, EventBridge, IAM, CloudWatch
- **Frontend**: HTML5, Modern CSS, SVG Data Visualization, Vanilla JS (No Framework dependency)
- **External API**: OpenWeatherMap Weather & Forecast API
- **IaC**: AWS SAM (Serverless Application Model) / CloudFormation

---

## 👨‍💻 Tác Giả (Author)

- **Dự án**: Serverless Weather Telemetry Station
- **Báo cáo Thực tập**: FCAJ AWS Internship Program

---
*Distributed under the MIT License.*
