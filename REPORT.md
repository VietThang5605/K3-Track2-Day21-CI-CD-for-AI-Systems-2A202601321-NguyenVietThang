# BÁO CÁO THỰC HÀNH MLOPS: CI/CD PIPELINE CHO HỆ THỐNG AI TRÊN AWS

* **Học viên:** Nguyễn Việt Thắng
* **Mã học viên:** 2A202601321
* **Khóa / Track:** K3 - Track 2 (Day 21 - CI/CD for AI Systems)
* **GitHub Repository:** [VietThang5605/K3-Track2-Day21-CI-CD-for-AI-Systems-2A202601321-NguyenVietThang](https://github.com/VietThang5605/K3-Track2-Day21-CI-CD-for-AI-Systems-2A202601321-NguyenVietThang)
* **Hạ tầng triển khai:** AWS (S3, EC2, IAM, Terraform IaC)

---

## 1. Lựa Chọn Siêu Tham Số & Phân Tích Thực Nghiệm (Bước 1)

Trong quá trình thực nghiệm và theo dõi mô hình phân loại chất lượng rượu (Wine Quality) với MLflow, tôi đã khảo sát nhiều bộ siêu tham số cho thuật toán **RandomForestClassifier**:

| Lần chạy | `n_estimators` | `max_depth` | `min_samples_split` | Accuracy (Phase 1) | F1-Score (Phase 1) | Ghi chú |
|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **Run 1** | 100 | 5 | 2 | 0.5640 | 0.5534 | Mô hình bị underfitting |
| **Run 2** | 200 | 10 | 5 | 0.6420 | 0.6394 | Cải thiện nhưng chưa tối ưu |
| **Run 3 (Tối ưu)** | **400** | **25** | **5** | **0.6800** | **0.6782** | **Bộ tham số tốt nhất** |

* **Lý do lựa chọn:** Cấu hình `n_estimators=400`, `max_depth=25`, `min_samples_split=5` cho phép mô hình học được các tương tác phi tuyến phức tạp giữa 11 chỉ số hóa lý của rượu vang mà vẫn kiểm soát tốt hiện tượng overfitting nhờ `min_samples_split=5`.
* **Hiệu quả Continuous Training (Bước 3):** Khi bổ sung tập dữ liệu mới `train_phase2.csv` (tăng từ 2,998 mẫu lên 5,996 mẫu), với cùng bộ siêu tham số trên, **Accuracy đã tăng vọt từ 0.6800 lên 0.7420 (F1-score: 0.7404)**, chính thức vượt qua ngưỡng đánh giá `EVAL_THRESHOLD = 0.70`.


---

## 2. Khó Khăn Gặp Phải & Giải Pháp Kỹ Thuật (Trọng Tâm AWS & CI/CD)

Trong bài lab này, tôi đã chủ động chuyển đổi toàn bộ kiến trúc từ GCP sang **AWS Cloud (S3, EC2, Terraform)**. Đây là phần gặp nhiều thách thức nhất trong việc đồng bộ giữa GitHub Actions, DVC và AWS SDK:

### Khó khăn 1: Lỗi DVC `403 Forbidden` (HeadObject) khi kéo dữ liệu từ S3 trên GitHub Actions Runner
* **Hiện tượng:** Chạy `dvc pull` cục bộ thành công nhưng trên GitHub Actions runner liên tục báo lỗi `botocore.exceptions.ClientError: An error occurred (403) when calling the HeadObject operation: Forbidden`.
* **Nguyên nhân:** 
  1. Thư viện `aiobotocore`/`s3fs` của DVC trên máy ảo runner cố gắng truy vấn AWS Instance Metadata Service (`IMDS`), khi thất bại nó fallback về request nặc danh (anonymous request) dẫn đến việc S3 từ chối truy cập.
  2. DVC ưu tiên đọc cấu hình từ file `.dvc/config.local` hơn là các biến môi trường đơn lẻ.
* **Giải pháp:**
  * Bổ sung biến môi trường `AWS_EC2_METADATA_DISABLED=true` để ép AWS SDK luôn sử dụng Access Key tĩnh.
  * Tự động khởi tạo file chuẩn `~/.aws/credentials` và cấu hình trực tiếp vào DVC remote trong workflow bằng cờ `--local`:
    ```bash
    dvc remote modify myremote access_key_id "$AWS_ACCESS_KEY_ID" --local
    dvc remote modify myremote secret_access_key "$AWS_SECRET_ACCESS_KEY" --local
    dvc remote modify myremote region "$AWS_REGION" --local
    ```

### Khó khăn 2: Xử lý định dạng Secret AWS và lỗi Logic trích xuất Key trong Workflow
* **Hiện tượng:** Runner báo lỗi `InvalidClientTokenId` hoặc `JSONDecodeError` khi parse chuỗi JSON `CLOUD_CREDENTIALS`.
* **Nguyên nhân:** 
  1. Khi truyền secret inline vào script Python, dấu nháy kép/nháy đơn trong bash dễ gây vỡ chuỗi JSON.
  2. Trong logic parser ban đầu, chuỗi `"aws_secret_access_key"` chứa cả từ khóa con `"access_key"`, nên khi kiểm tra `if "access_key" in k` đã vô tình gán đè Secret Key vào Access Key ID khiến `secret_key` bị rỗng.
* **Giải pháp:**
  * Truyền secret qua biến môi trường `env: CREDS: ${{ secrets.CLOUD_CREDENTIALS }}`.
  * Viết parser thông minh hỗ trợ tra cứu chính xác key `dl.get("aws_access_key_id")` và `dl.get("aws_secret_access_key")`, kết hợp Regex tự động nhận diện mẫu định dạng chuẩn của AWS (`AKIA...` 20 ký tự và Secret 40 ký tự) bất kể người dùng nhập dạng JSON hay file INI.

### Khó khăn 3: Lỗi Trigger Workflow do bộ lọc `paths:`
* **Hiện tượng:** Push các thay đổi cấu hình CI/CD lên GitHub nhưng GitHub Actions không tự kích hoạt.
* **Nguyên nhân:** Khối `paths:` trong workflow ban đầu chỉ lọc `src/**.py`, `params.yaml`, `data/**.dvc` mà bỏ qua `.github/workflows/**` và `requirements.txt`.
* **Giải pháp:** Mở rộng phạm vi `paths:` để pipeline phản ứng ngay lập tức với bất kỳ cập nhật nào về mã nguồn, dependencies hay cấu hình CI/CD.

---

## 3. Kết Luận

Hệ thống đã vận hành trơn tru theo mô hình MLOps tiêu chuẩn:
1. **Automation:** Tự động kiểm thử, huấn luyện, đánh giá và triển khai qua 4 Jobs GitHub Actions.
2. **Quality Gate:** Tự động chặn deploy khi mô hình chưa đạt ngưỡng ($0.68 < 0.70$) và tự động mở cổng deploy khi nạp dữ liệu mới đạt chuẩn ($0.7460 \ge 0.70$).
3. **Live Serving:** Model được phục vụ thực tế qua FastAPI trên máy ảo AWS EC2, trả kết quả phân loại thời gian thực tại endpoint `POST /predict`.
