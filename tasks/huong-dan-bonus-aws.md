# HƯỚNG DẪN CHI TIẾT 5 THÁCH THỨC NÂNG CAO (BONUS) TRÊN AWS
*(Tối đa 20 điểm cộng - Nâng tổng điểm lên 100/100)*

Tài liệu này hướng dẫn chi tiết từng bước thực hiện 5 bài Bonus theo đúng kiến trúc **AWS (S3, EC2, Terraform)** và **MLflow / GitHub Actions**.

---

## MỤC LỤC
1. [Bonus 1: Tracking MLflow Từ Xa Với DagsHub (4 điểm)](#bonus-1-tracking-mlflow-từ-xa-với-dagshub-4-điểm)
2. [Bonus 2: Thí Nghiệm Với Nhiều Thuật Toán (4 điểm)](#bonus-2-thí-nghiệm-với-nhiều-thuật-toán-4-điểm)
3. [Bonus 3: Báo Cáo Hiệu Suất Tự Động (4 điểm)](#bonus-3-báo-cáo-hiệu-suất-tự-động-4-điểm)
4. [Bonus 4: Hoàn Trả Về Phiên Bản Trước (Model Rollback) (4 điểm)](#bonus-4-hoàn-trả-về-phiên-bản-trước-model-rollback-4-điểm)
5. [Bonus 5: Cảnh Báo Lệch Lạc Dữ Liệu (Data Drift Check) (4 điểm)](#bonus-5-cảnh-báo-lệch-lạc-dữ-liệu-data-drift-check-4-điểm)

---

# BONUS 1: Tracking MLflow Từ Xa Với DagsHub (4 điểm)

### 🎯 Mục tiêu
Thay vì chỉ lưu MLflow ở máy cục bộ (`sqlite:///mlflow.db`), ta kết nối MLflow tới **DagsHub Tracking Server** (server MLflow miễn phí trên đám mây). Mỗi khi GitHub Actions chạy hoặc chạy máy local, kết quả đều được đồng bộ lên DagsHub để xem từ bất kỳ đâu.

### 📝 Các bước thực hiện:

#### Bước 1.1: Tạo tài khoản và Repo trên DagsHub
1. Truy cập [https://dagshub.com](https://dagshub.com) $\rightarrow$ Đăng ký / Đăng nhập bằng tài khoản GitHub của bạn.
2. Bấm **Create** $\rightarrow$ **Migrate / Connect Repo** $\rightarrow$ Chọn repository `K3-Track2-Day21-CI-CD-for-AI-Systems-2A202601321-NguyenVietThang`.
3. Sau khi kết nối, vào tab **Remote** $\rightarrow$ chọn **MLflow Tracking**:
   * Bạn sẽ thấy đường dẫn có dạng:
     `https://dagshub.com/<YOUR_USERNAME>/K3-Track2-Day21-CI-CD-for-AI-Systems-2A202601321-NguyenVietThang.mlflow`
   * Bấm **Generate Token** để lấy Access Token (hoặc dùng mật khẩu tài khoản DagsHub).

#### Bước 1.2: Cấu hình Secrets trên GitHub
Vào GitHub Repo $\rightarrow$ **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** $\rightarrow$ Thêm 3 Secrets:
1. `MLFLOW_TRACKING_URI`: `https://dagshub.com/<YOUR_USERNAME>/<REPO_NAME>.mlflow`
2. `MLFLOW_TRACKING_USERNAME`: `<YOUR_DAGSHUB_USERNAME>`
3. `MLFLOW_TRACKING_PASSWORD`: `<YOUR_DAGSHUB_TOKEN_HOAC_PASSWORD>`

#### Bước 1.3: Cập nhật file `.github/workflows/mlops.yml`
Trong job `train`, truyền 3 biến môi trường MLflow:
```yaml
      - name: Train model
        env:
          MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
          MLFLOW_TRACKING_USERNAME: ${{ secrets.MLFLOW_TRACKING_USERNAME }}
          MLFLOW_TRACKING_PASSWORD: ${{ secrets.MLFLOW_TRACKING_PASSWORD }}
        run: python src/train.py
```

📸 **Ảnh chụp màn hình cần nộp:** Giao diện DagsHub MLflow UI hiển thị các runs thí nghiệm đã được sync lên cloud.

---

# BONUS 2: Thí Nghiệm Với Nhiều Thuật Toán (4 điểm)

### 🎯 Mục tiêu
Mở rộng `src/train.py` để hỗ trợ thêm các thuật toán khác ngoài `RandomForest`: **GradientBoostingClassifier** và **LogisticRegression**.

### 📝 Các bước thực hiện:

#### Bước 2.1: Cập nhật `params.yaml`
Thêm trường `model_type`:
```yaml
# Chọn 1 trong 3: random_forest, gradient_boosting, logistic_regression
model_type: "gradient_boosting"

# Tham số chung và riêng
n_estimators: 200
max_depth: 10
min_samples_split: 5
learning_rate: 0.1
C: 1.0
```

#### Bước 2.2: Cập nhật logic trong `src/train.py`
Mở `src/train.py` và thêm logic switch model:
```python
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

# Đọc model_type
model_type = params.get("model_type", "random_forest")

# Khởi tạo mô hình tương ứng
if model_type == "gradient_boosting":
    model = GradientBoostingClassifier(
        n_estimators=params.get("n_estimators", 100),
        max_depth=params.get("max_depth", 5),
        learning_rate=params.get("learning_rate", 0.1),
        random_state=42
    )
elif model_type == "logistic_regression":
    model = LogisticRegression(
        C=params.get("C", 1.0),
        max_iter=1000,
        random_state=42
    )
else:
    model = RandomForestClassifier(
        n_estimators=params.get("n_estimators", 400),
        max_depth=params.get("max_depth", 25),
        min_samples_split=params.get("min_samples_split", 5),
        random_state=42
    )

# Ghi log model_type vào MLflow
mlflow.log_param("model_type", model_type)
```

#### Bước 2.3: Chạy thực nghiệm cục bộ
Lần lượt đổi `model_type` trong `params.yaml` sang `gradient_boosting` và `logistic_regression` rồi chạy:
```bash
python src/train.py
```
Mở MLflow UI (`mlflow ui`) xem sự so sánh giữa các thuật toán.

📸 **Ảnh chụp màn hình cần nộp:** MLflow UI hiển thị cột `model_type` với ít nhất 2 thuật toán khác nhau kèm accuracy/f1-score.

---

# BONUS 3: Báo Cáo Hiệu Suất Tự Động (4 điểm)

### 🎯 Mục tiêu
Tự động tính **Confusion Matrix**, **Precision**, **Recall** cho từng lớp (0, 1, 2) và xuất ra file `outputs/report.txt`, sau đó upload thành Artifact trên GitHub Actions.

### 📝 Các bước thực hiện:

#### Bước 3.1: Thêm logic tạo báo cáo trong `src/train.py`
Trong hàm `train()` của `src/train.py`, sau khi tính metrics, bổ sung:
```python
from sklearn.metrics import classification_report, confusion_matrix

# Tạo classification report và confusion matrix
cls_report = classification_report(y_eval, y_pred, target_names=["thap (0)", "trung_binh (1)", "cao (2)"])
conf_matrix = confusion_matrix(y_eval, y_pred)

# Lưu báo cáo dạng text ra outputs/report.txt
report_content = f"""==================================================
           BÁO CÁO ĐÁNH GIÁ HIỆU SUẤT MÔ HÌNH
==================================================
Accuracy: {acc:.4f}
F1-Score: {f1:.4f}

--- CHI TIẾT THEO TỪNG LỚP (PRECISION & RECALL) ---
{cls_report}

--- CONFUSION MATRIX ---
{conf_matrix}
==================================================
"""

os.makedirs("outputs", exist_ok=True)
with open("outputs/report.txt", "w", encoding="utf-8") as f:
    f.write(report_content)

print(report_content)
```

#### Bước 3.2: Cập nhật artifact trong `.github/workflows/mlops.yml`
Trong job `train` của workflow, cập nhật bước lưu artifact:
```yaml
      - name: Save metrics and report as artifact
        uses: actions/upload-artifact@v4
        with:
          name: evaluation-reports
          path: |
            outputs/metrics.json
            outputs/report.txt
```

📸 **Ảnh chụp màn hình cần nộp:** Tab Artifacts của GitHub Actions tải về được file `report.txt` chứa Confusion Matrix và Precision/Recall.

---

# BONUS 4: Hoàn Trả Về Phiên Bản Trước (Model Rollback) (4 điểm)

### 🎯 Mục tiêu
Cơ chế bảo vệ nâng cao: Trước khi deploy, so sánh `accuracy` của model mới với model đang chạy trên production (lấy từ S3). Nếu model mới có accuracy **thấp hơn** model cũ $\rightarrow$ Hủy deploy để tránh làm giảm chất lượng hệ thống.

### 📝 Các bước thực hiện:

#### Bước 4.1: Lưu lại metrics của model lên S3 cùng với model
Trong job `train` của `.github/workflows/mlops.yml`, bổ sung upload file `metrics.json` lên S3:
```python
s3.upload_file("outputs/metrics.json", bucket_name, "models/latest/metrics.json")
```

#### Bước 4.2: Cập nhật Job `eval` trong `.github/workflows/mlops.yml` để so sánh với model cũ
```yaml
  eval:
    name: Eval
    needs: train
    runs-on: ubuntu-latest
    steps:
      - name: Authenticate to Cloud Storage (AWS)
        env:
          CREDS: ${{ secrets.CLOUD_CREDENTIALS }}
        run: |
          # Gán AWS credentials
          python -c "import os, json; creds=json.loads(os.environ['CREDS']); print(f'AWS_ACCESS_KEY_ID={creds[\"aws_access_key_id\"]}\nAWS_SECRET_ACCESS_KEY={creds[\"aws_secret_access_key\"]}\nAWS_DEFAULT_REGION={creds.get(\"aws_region\",\"ap-southeast-1\")}')" >> $GITHUB_ENV

      - name: Check eval gate and rollback safety
        env:
          BUCKET_NAME: ${{ secrets.CLOUD_BUCKET }}
        run: |
          python - <<'EOF'
          import sys, json, os, boto3

          new_acc = float("${{ needs.train.outputs.accuracy }}")
          threshold = 0.70
          bucket_name = os.environ.get("BUCKET_NAME", "")

          print(f"Current Model Accuracy: {new_acc:.4f} | Absolute Threshold: {threshold}")
          if new_acc < threshold:
              sys.exit(f"FAILED: Accuracy {new_acc:.4f} < {threshold}. Huỷ deploy.")

          # Kiểm tra model cũ trên S3
          s3 = boto3.client("s3")
          old_acc = 0.0
          try:
              s3.download_file(bucket_name, "models/latest/metrics.json", "/tmp/old_metrics.json")
              with open("/tmp/old_metrics.json") as f:
                  old_acc = json.load(f).get("accuracy", 0.0)
              print(f"Production Model Accuracy: {old_acc:.4f}")
          except Exception:
              print("No previous production metrics found on S3. First deployment.")

          # So sánh rollback gate
          if new_acc < old_acc:
              sys.exit(f"FAILED (ROLLBACK GATE): Model moi ({new_acc:.4f}) kem hon Model dang chay ({old_acc:.4f}). Tu choi deploy!")

          print("PASSED: Model moi dat nguong va tot hon/bang model cu. Cho phep deploy.")
          EOF
```

📸 **Ảnh chụp màn hình cần nộp:** Log của job Eval hiển thị dòng kiểm tra so sánh: `Current Model Accuracy vs Production Model Accuracy`.

---

# BONUS 5: Cảnh Báo Lệch Lạc Dữ Liệu (Data Drift Check) (4 điểm)

### 🎯 Mục tiêu
Kiểm tra phân phối nhãn (Class Distribution) trước khi train. Nếu bất kỳ lớp nào chiếm **dưới 10%** tổng số mẫu $\rightarrow$ In cảnh báo rõ ràng ra log và lưu tỷ lệ phân phối vào `outputs/metrics.json`.

### 📝 Các bước thực hiện:

#### Bước 5.1: Bổ sung logic kiểm tra phân phối trong `src/train.py`
Trong `src/train.py`, ngay sau khi load `df_train`, thêm đoạn kiểm tra:
```python
# 1. Kiểm tra phân phối dữ liệu (Data Distribution & Imbalance Check)
total_samples = len(df_train)
class_counts = df_train["target"].value_counts().to_dict()
class_dist = {int(k): round(v / total_samples, 4) for k, v in class_counts.items()}

print("--- KIỂM TRA PHÂN PHỐI DỮ LIỆU (DATA DRIFT / IMBALANCE) ---")
print(f"Tổng số mẫu: {total_samples}")
for cls, ratio in class_dist.items():
    pct = ratio * 100
    print(f"  * Class {cls}: {class_counts[cls]} mẫu ({pct:.2f}%)")
    if ratio < 0.10:
        print(f"  ⚠️ CẢNH BÁO: Class {cls} chiếm {pct:.2f}% (< 10%). Du lieu bi lech nhan dang ke!")

# 2. Ghi tỷ lệ phân phối vào MLflow và metrics.json
mlflow.log_dict(class_dist, "class_distribution.json")

metrics_data = {
    "accuracy": round(acc, 4),
    "f1_score": round(f1, 4),
    "class_distribution": class_dist
}
with open("outputs/metrics.json", "w") as f:
    json.dump(metrics_data, f, indent=2)
```

📸 **Ảnh chụp màn hình cần nộp:** Log terminal hoặc workflow in ra phần kiểm tra phân phối nhãn kèm cảnh báo tỷ lệ lớp.

---

## TỔNG KẾT BỘ ẢNH NỘP BÀI KHI LÀM BONUS:
1. `06_bonus1_dagshub_mlflow.png`: Giao diện DagsHub Tracking UI.
2. `07_bonus2_multiple_models.png`: MLflow UI hiển thị Random Forest vs Gradient Boosting.
3. `08_bonus3_classification_report.png`: File `report.txt` chứa Confusion Matrix tải từ Artifact.
4. `09_bonus4_rollback_gate.png`: Log so sánh accuracy model mới vs model cũ trên S3.
5. `10_bonus5_data_drift_check.png`: Log in kiểm tra phân phối nhãn và cảnh báo < 10%.
