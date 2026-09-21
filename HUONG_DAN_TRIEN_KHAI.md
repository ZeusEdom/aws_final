# Hướng dẫn triển khai: Serverless Weather Dashboard (4 ngày, $0–$1)

Kiến trúc: **S3 (dashboard tĩnh) → API Gateway → Lambda (API) → DynamoDB ← Lambda (Fetcher) ← EventBridge (lịch) ← OpenWeatherMap API**

File đi kèm bạn cần dùng: `lambda_fetcher.py`, `lambda_api_handler.py`, `index.html`, `iam_policies.json`.

> Toàn bộ hướng dẫn dùng AWS Console (giao diện web), không cần biết code trước. Copy/paste đúng theo hướng dẫn là chạy được.

---

## NGÀY 0 (chuẩn bị trước, ~30 phút) — Tạo tài khoản

### Bước 1: Tạo tài khoản AWS
1. Vào https://aws.amazon.com → **Create an AWS Account**.
2. Nhập email, tên account, mật khẩu.
3. Nhập thông tin thẻ (Visa/Mastercard) — AWS yêu cầu để xác minh, **sẽ không bị trừ tiền** nếu bạn ở trong Free Tier.
4. Chọn gói **Basic Support (Free)**.
5. Xác minh số điện thoại (OTP).
6. Đăng nhập vào **AWS Management Console** bằng **Root user**.

### Bước 2: Đặt Billing Alert (RẤT QUAN TRỌNG — chỉ có $30)
1. Góc trên phải → click tên account → **Billing and Cost Management**.
2. Vào **Billing Preferences** → tick **Receive Billing Alerts** → Save.
3. Vào **AWS Budgets** (tìm ở ô search phía trên) → **Create budget**.
4. Chọn **Zero spend budget** hoặc **Cost budget**, đặt ngưỡng **$5** và **$20**, nhập email của bạn để nhận cảnh báo.
5. Save.

### Bước 3: Tạo IAM user (không dùng root user để làm việc)
1. Search "**IAM**" → **Users** → **Create user**.
2. Username: `weather-admin`.
3. Tick **Provide user access to AWS Management Console**.
4. Chọn **I want to create an IAM user** → đặt mật khẩu.
5. Bỏ tick "require password reset" (cho tiện, vì chỉ dùng cá nhân).
6. Ở bước Permissions → **Attach policies directly** → chọn **AdministratorAccess** (chỉ vì làm project cá nhân ngắn hạn, dễ debug hơn; sau khi xong project nên xóa/giảm quyền).
7. Create user → **lưu lại link đăng nhập Console** (dạng `https://<account-id>.signin.aws.amazon.com/console`).
8. Đăng xuất root, đăng nhập lại bằng user `weather-admin` vừa tạo.
9. Chọn **Region** cố định ở góc trên phải (ví dụ `Asia Pacific (Singapore) ap-southeast-1` — chọn gần bạn để độ trễ thấp) và **dùng region này cho toàn bộ project**.

### Bước 4: Lấy API key thời tiết (miễn phí)
1. Vào https://openweathermap.org/api → **Sign Up** (tài khoản free).
2. Sau khi verify email → vào **My API Keys** → copy API key (dạng chuỗi 32 ký tự).
3. Lưu ý: key mới có thể mất 10–60 phút để active, nên làm bước này **trước** khi qua Ngày 1.
4. Free tier: 1,000 calls/ngày, 60 calls/phút — quá đủ cho project này (Lambda chỉ gọi 1 lần mỗi 30 phút = 48 lần/ngày).

✅ Checklist cuối Ngày 0: có tài khoản AWS, có IAM user đăng nhập được, có Billing Alert, có API key OpenWeatherMap.

---

## NGÀY 1 — Tạo DynamoDB + Lambda Fetcher + lên lịch tự động

### Bước 1: Tạo bảng DynamoDB
1. Search "**DynamoDB**" → **Create table**.
2. Table name: `WeatherData`.
3. Partition key: `city` (String).
4. Sort key: `timestamp` (Number).
5. Table settings: chọn **Customize settings** → Read/write capacity: **On-demand** (không cần tính toán, free tier vẫn áp dụng cho mức dùng thấp).
6. Create table (đợi ~1 phút tới khi status = Active).

### Bước 2: Tạo IAM Role cho Lambda Fetcher
1. Search "**IAM**" → **Roles** → **Create role**.
2. Trusted entity: **AWS service** → Use case: **Lambda**.
3. Ở bước Permissions, search và tick:
   - `AWSLambdaBasicExecutionRole` (cho phép ghi log vào CloudWatch)
4. Đặt tên role: `weather-fetcher-role` → Create role.
5. Vào lại role vừa tạo → **Add permissions** → **Create inline policy** → chọn tab **JSON** → dán nội dung trong file `iam_policies.json`, phần `"FetcherDynamoDBWritePolicy"` (chỉ phần JSON đó, không phải cả file) → đặt tên `weather-fetcher-dynamodb-policy` → Create.

> Đây là nguyên tắc **Least Privilege** — Lambda chỉ được quyền ghi vào đúng bảng `WeatherData`, không có quyền gì khác trên tài khoản của bạn. Bạn sẽ ghi lý do này vào phần "Bảo mật cơ bản" của báo cáo.

### Bước 3: Tạo Lambda function (Fetcher)
1. Search "**Lambda**" → **Create function**.
2. Chọn **Author from scratch**.
3. Function name: `weather-fetcher`.
4. Runtime: **Python 3.12**.
5. Architecture: `x86_64`.
6. Permissions → **Use an existing role** → chọn `weather-fetcher-role`.
7. Create function.
8. Trong tab **Code**, xóa hết code mẫu, paste toàn bộ nội dung file `lambda_fetcher.py` vào.
9. Vào **Configuration → Environment variables** → **Edit → Add environment variable**:
   - Key: `OWM_API_KEY` → Value: API key OpenWeatherMap của bạn
   - Key: `TABLE_NAME` → Value: `WeatherData`
   - Key: `CITIES` → Value: `Hanoi,Ho Chi Minh City,Da Nang` (hoặc tên thành phố bạn muốn theo dõi, cách nhau bởi dấu phẩy)
10. Vào **Configuration → General configuration → Edit** → Timeout: đặt **15 seconds** (mặc định 3s không đủ vì phải gọi API ngoài).
11. Bấm **Deploy** (nút màu cam) ở tab Code để lưu code.
12. Test thử: tab **Test** → **Create new test event**, tên `test1`, để JSON mặc định `{}` → **Test**. Nếu thấy `"statusCode": 200` là thành công. Nếu lỗi, xem phần **Troubleshooting** ở cuối tài liệu.
13. Kiểm tra dữ liệu: vào DynamoDB → table `WeatherData` → **Explore table items** → phải thấy các dòng dữ liệu mới.

### Bước 4: Lên lịch tự động bằng EventBridge
1. Trong trang Lambda `weather-fetcher` → tab **Configuration** → **Triggers** → **Add trigger**.
2. Chọn **EventBridge (CloudWatch Events)**.
3. Chọn **Create a new rule**.
4. Rule name: `weather-fetch-schedule`.
5. Rule type: **Schedule expression** → nhập: `rate(30 minutes)`.
6. Add.

✅ Checklist cuối Ngày 1: DynamoDB có dữ liệu, Lambda fetcher chạy tự động mỗi 30 phút, không lỗi trong CloudWatch Logs.

---

## NGÀY 2 — Lambda API Handler + API Gateway

### Bước 1: Tạo IAM Role cho Lambda API
1. Lặp lại như Ngày 1 Bước 2, nhưng:
   - Tên role: `weather-api-role`
   - Inline policy dùng phần `"ApiDynamoDBReadPolicy"` trong file `iam_policies.json` (chỉ quyền **đọc** — `GetItem`, `Query`).

### Bước 2: Tạo Lambda function (API handler)
1. Lambda → **Create function** → tên `weather-api-handler` → Runtime Python 3.12 → Role: `weather-api-role`.
2. Paste nội dung `lambda_api_handler.py` vào tab Code.
3. Environment variables: `TABLE_NAME` = `WeatherData`.
4. Timeout: 10 seconds.
5. Deploy.

### Bước 3: Tạo API Gateway
1. Search "**API Gateway**" → **Create API** → chọn **HTTP API** (rẻ và đơn giản hơn REST API) → **Build**.
2. **Add integration** → Lambda → chọn function `weather-api-handler`.
3. API name: `weather-dashboard-api`.
4. Configure routes: method **GET**, path **/weather**.
5. Configure stages: giữ mặc định `$default` (auto-deploy = enabled).
6. Create.
7. Sau khi tạo xong, copy **Invoke URL** (dạng `https://xxxxx.execute-api.ap-southeast-1.amazonaws.com`) — bạn sẽ cần URL này ở Ngày 3.

### Bước 4: Bật CORS (bắt buộc, nếu không dashboard sẽ không gọi được API)
1. Trong API Gateway, chọn API `weather-dashboard-api` → **CORS** (menu bên trái).
2. **Configure**:
   - Access-Control-Allow-Origin: `*`
   - Access-Control-Allow-Methods: `GET`
   - Access-Control-Allow-Headers: `*`
3. Save.

### Bước 5: Test API
1. Mở trình duyệt, dán: `<Invoke-URL>/weather?city=Hanoi`
2. Phải thấy kết quả JSON chứa dữ liệu thời tiết. Nếu lỗi 500, xem CloudWatch Logs của `weather-api-handler`.

✅ Checklist cuối Ngày 2: gọi được API Gateway URL trên trình duyệt và thấy JSON dữ liệu thật.

---

## NGÀY 3 — Dashboard trên S3

### Bước 1: Sửa file `index.html`
1. Mở file `index.html` (đi kèm) bằng Notepad/VS Code.
2. Tìm dòng:
   ```js
   const API_URL = "REPLACE_WITH_YOUR_API_GATEWAY_URL";
   ```
3. Thay bằng Invoke URL bạn copy ở Ngày 2, ví dụ:
   ```js
   const API_URL = "https://xxxxx.execute-api.ap-southeast-1.amazonaws.com/weather";
   ```
4. Lưu file.

### Bước 2: Tạo bucket S3
1. Search "**S3**" → **Create bucket**.
2. Bucket name: phải **duy nhất toàn cầu**, ví dụ `weather-dashboard-<tên-bạn>-2026`.
3. Region: giống các dịch vụ trên.
4. **Bỏ tick** "Block all public access" (vì đây là website tĩnh công khai) → tick xác nhận cảnh báo.
5. Create bucket.

### Bước 3: Bật Static Website Hosting
1. Vào bucket vừa tạo → tab **Properties** → kéo xuống **Static website hosting** → **Edit**.
2. Chọn **Enable**.
3. Index document: `index.html`.
4. Save.
5. Ghi lại **Bucket website endpoint** (URL dạng `http://<bucket>.s3-website-ap-southeast-1.amazonaws.com`).

### Bước 4: Set Bucket Policy để cho phép public đọc
1. Tab **Permissions** → **Bucket policy** → **Edit** → dán:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::TEN-BUCKET-CUA-BAN/*"
    }
  ]
}
```
2. **Thay `TEN-BUCKET-CUA-BAN` bằng tên bucket thật của bạn.**
3. Save.

### Bước 5: Upload file
1. Tab **Objects** → **Upload** → chọn file `index.html` đã sửa → Upload.
2. Mở **Bucket website endpoint** trên trình duyệt → phải thấy dashboard hiển thị dữ liệu thời tiết thật.

✅ Checklist cuối Ngày 3: truy cập được dashboard qua URL public, thấy dữ liệu load từ API.

---

## NGÀY 4 — Monitoring, bảo mật, tối ưu, tài liệu hóa, clean-up

### Bước 1: CloudWatch Alarm (phần "Khả năng mở rộng và vận hành")
1. Search "**CloudWatch**" → **Alarms** → **Create alarm**.
2. **Select metric** → Lambda → By Function Name → chọn `weather-fetcher` → metric `Errors`.
3. Condition: Greater than **0**, trong 1 period 5 phút.
4. Notification: tạo SNS topic mới, tên `weather-alerts`, nhập email của bạn để nhận cảnh báo khi Lambda lỗi.
5. Create alarm → **kiểm tra email và click Confirm subscription** (SNS sẽ gửi email xác nhận).

### Bước 2: Review bảo mật (chụp màn hình để đưa vào báo cáo)
- Vào IAM → Roles → `weather-fetcher-role` và `weather-api-role` → chụp màn hình phần Permissions, chứng minh mỗi role chỉ có đúng quyền cần thiết (Least Privilege).
- Xác nhận không có Access Key nào bị hard-code trong code (kiểm tra lại `lambda_fetcher.py`, `lambda_api_handler.py` — chỉ dùng biến môi trường, IAM Role).

### Bước 3: Kiểm tra chi phí thực tế
1. Vào **Billing and Cost Management → Cost Explorer** (hoặc Bill hiện tại).
2. Chụp màn hình phần cost breakdown — thường sẽ hiển thị **$0.00** vì toàn bộ nằm trong Free Tier.

### Bước 4: Viết tài liệu song ngữ
Dùng chính nội dung Ngày 0–4 này (đã có sẵn cấu trúc) để điền vào các mục bắt buộc của báo cáo:
- **Proposal**: dùng phần kiến trúc + lý do chọn dịch vụ ở đầu tài liệu này.
- **Worklog (8 tuần)**: dồn 4 ngày làm thực tế vào Worklog theo tuần tương ứng (ví dụ nếu làm vào tuần 6–7 của kỳ thực tập, ghi rõ Week 6, Week 7...). Mỗi "ngày" ở trên có thể tách thành nhiều mục nhỏ trong worklog để mô tả chi tiết hơn công việc từng ngày.
- **Workshop**: copy toàn bộ các bước Ngày 0–3 (Overview, Prerequisite, kiến trúc, các bước thực hành, test, clean-up) — đây chính là phần "workshop kỹ thuật chính".
- Dịch sang tiếng Anh (mình có thể hỗ trợ dịch nếu bạn cần).

### Bước 5: Clean-up (làm sau khi đã chụp đủ ảnh/video demo, hoặc để lại nếu vẫn trong Free Tier và muốn giữ demo sống)
Nếu muốn **xóa hoàn toàn** để chắc chắn không phát sinh phí:
1. S3 → bucket → **Empty bucket** → sau đó **Delete bucket**.
2. API Gateway → xóa API `weather-dashboard-api`.
3. Lambda → xóa `weather-fetcher` và `weather-api-handler`.
4. EventBridge → xóa rule `weather-fetch-schedule` (thường tự xóa khi xóa Lambda trigger, kiểm tra lại trong **Amazon EventBridge → Rules**).
5. DynamoDB → xóa table `WeatherData` (chụp màn hình dữ liệu trước khi xóa nếu cần cho báo cáo).
6. CloudWatch → xóa Alarm `weather-fetcher-errors` (tên tự đặt ở bước tạo).
7. SNS → xóa topic `weather-alerts`.
8. IAM → có thể giữ lại role/user hoặc xóa nếu không dùng nữa.

> Nếu bạn vẫn còn thời gian sau khi nộp báo cáo và muốn giữ demo online cho người chấm xem trực tiếp, **không cần xóa ngay** — vì chi phí toàn bộ hệ thống này khi không có traffic gần như $0. Chỉ cần theo dõi Billing Alert bạn đã đặt ở Ngày 0.

✅ Checklist cuối Ngày 4: có Alarm hoạt động, có ảnh chụp bảo mật + chi phí, đã điền xong Proposal/Worklog/Workshop, đã clean-up (hoặc quyết định giữ lại có kiểm soát).

---

## Troubleshooting thường gặp

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| Lambda fetcher trả lỗi `KeyError` hoặc timeout | API key chưa active hoặc sai | Đợi thêm, kiểm tra lại `OWM_API_KEY` trong Environment variables |
| Lambda báo `AccessDeniedException` khi ghi DynamoDB | Role thiếu quyền | Kiểm tra lại inline policy đã gắn đúng ARN table chưa |
| API Gateway trả 500 | Lambda API lỗi hoặc sai tên bảng | Xem CloudWatch Logs của `weather-api-handler` |
| Dashboard không hiện dữ liệu, console báo lỗi CORS | Chưa bật CORS hoặc sai `API_URL` trong `index.html` | Kiểm tra lại Bước 4 Ngày 2 và Bước 1 Ngày 3 |
| Bucket S3 báo Access Denied khi mở website | Chưa tắt Block Public Access hoặc chưa set Bucket Policy | Kiểm tra lại Bước 2–3 Ngày 3 |
| Không thấy dữ liệu mới sau 30 phút | EventBridge rule chưa enable hoặc sai schedule | Vào EventBridge → Rules → kiểm tra status = Enabled |

---

## Ghi chú chi phí quan trọng
- Toàn bộ dịch vụ dùng (Lambda, API Gateway HTTP API, DynamoDB On-demand mức thấp, S3 dung lượng nhỏ, EventBridge, CloudWatch cơ bản, SNS email) **đều nằm trong AWS Free Tier 12 tháng** với mức sử dụng của project này.
- Chi phí duy nhất có thể phát sinh nếu bạn **quên xóa** tài nguyên sau nhiều tháng, hoặc vô tình bật NAT Gateway / Elastic IP không dùng — project này **không dùng** 2 dịch vụ đó nên an toàn.
- Với $30 ngân sách, thực tế bạn gần như sẽ không tiêu đồng nào nếu làm đúng theo hướng dẫn và có Billing Alert theo dõi.
