# Bước 2 - Pipeline CI/CD Tự Động Với AWS (Amazon S3 + EC2)

Tài liệu này hướng dẫn chi tiết từng bước thực hiện **Bước 2** sử dụng hạ tầng **Amazon Web Services (AWS)** thay thế cho Google Cloud Platform (GCP).

---

## 1. Bảng Đối Chiếu AWS vs GCP

| Khái niệm | Mặc định bài lab (GCP) | Triển khai trên **AWS** |
| :--- | :--- | :--- |
| **Object Storage** | Google Cloud Storage (GCS) | **Amazon S3** |
| **Virtual Machine** | Compute Engine (GCE) | **EC2 Instance (Ubuntu 22.04 LTS)** |
| **CLI Quản trị** | `gcloud` / `gsutil` | `aws` CLI |
| **Python SDK** | `google-cloud-storage` | **`boto3`** |
| **DVC Remote Driver** | `dvc[gs]` | **`dvc[s3]`** |
| **Username trên VM** | `$USER` (GCP user) | **`ubuntu`** (mặc định trên EC2 Ubuntu) |

---

## 2.1 Tạo Amazon S3 Bucket

Tên bucket phải là duy nhất trên toàn cầu (toàn bộ AWS). Chọn region gần bạn (ví dụ: `ap-southeast-1` cho Singapore hoặc `us-east-1`).

```bash
# 1. Đặt biến môi trường
export AWS_REGION="ap-southeast-1"
export BUCKET_NAME="mlops-lab-wine-thangnv-$(date +%s)"
echo "Tên Bucket của bạn: $BUCKET_NAME"

# 2. Tạo S3 Bucket
aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION
```

> [!NOTE]
> Kiểm tra lại xem bucket đã được tạo thành công:
> ```bash
> aws s3 ls | grep $BUCKET_NAME
> ```

---

## 2.2 Tạo IAM Credentials (Access Key & Secret Key)

Cần một cặp **Access Key ID** và **Secret Access Key** có quyền đọc/ghi trên S3 bucket vừa tạo.

1. Đăng nhập vào **AWS Console** $\rightarrow$ dịch vụ **IAM** $\rightarrow$ **Users**.
2. Chọn user của bạn (hoặc tạo user mới `mlops-lab-user`) và gắn policy cho phép truy cập S3 (ví dụ `AmazonS3FullAccess` hoặc policy tùy chỉnh chỉ cho phép truy cập trên bucket `$BUCKET_NAME`).
3. Vào tab **Security credentials** $\rightarrow$ **Create access key** $\rightarrow$ chọn **Command Line Interface (CLI)**.
4. Lưu lại:
   - `AWS_ACCESS_KEY_ID`: Dạng `AKIA...`
   - `AWS_SECRET_ACCESS_KEY`: Dạng chuỗi bí mật dài.

5. Cài đặt các gói hỗ trợ S3 trong môi trường ảo máy local:
   ```bash
   uv pip install --python .venv "dvc[s3]" boto3
   ```

---

## 2.3 Cấu Hình DVC Với S3 Remote

Chạy các lệnh sau tại thư mục gốc của project:

```bash
# 1. Khởi tạo DVC (nếu chưa khởi tạo)
dvc init

# 2. Thiết lập S3 bucket làm default remote cho DVC
dvc remote add -d myremote s3://$BUCKET_NAME/dvc

# 3. Cấu hình region cho DVC remote
dvc remote modify myremote region $AWS_REGION

# 4. Thêm các file dữ liệu vào DVC tracking
dvc add data/train_phase1.csv
dvc add data/eval.csv
dvc add data/train_phase2.csv

# 5. Commit file con trỏ .dvc vào Git (không commit trực tiếp file CSV lớn)
git add data/*.dvc .dvc/config .gitignore
git commit -m "feat: track datasets with DVC on AWS S3"

# 6. Đẩy dữ liệu thực tế lên S3 Bucket
dvc push
```

> [!TIP]
> Kiểm tra dữ liệu trên S3:
> ```bash
> aws s3 ls s3://$BUCKET_NAME/dvc/
> ```

---

## 2.4 Tạo EC2 Instance Trên AWS (2 Cách Lựa Chọn)

Bạn có thể chọn **Cách 1 (Giao diện Web)** nếu muốn thao tác trực quan nhanh, hoặc **Cách 2 (Terraform - IaC)** nếu muốn tự động hóa hạ tầng chuẩn DevOps.

---

### Cách 1: Sử dụng Giao diện Web (AWS Console)

1. Đăng nhập vào **AWS Console** $\rightarrow$ Tìm và mở dịch vụ **EC2** $\rightarrow$ Nhấn **Launch instances**:
   - **Name:** `mlops-serve`
   - **Application and OS Images:** Chọn **Ubuntu** $\rightarrow$ Bản `Ubuntu Server 22.04 LTS (HVM), SSD Volume Type` (Free Tier eligible).
   - **Instance type:** `t2.micro` (hoặc `t3.micro` tùy theo Region).
   - **Key pair (login):** Nhấn *Create new key pair* (hoặc chọn key có sẵn):
     - Key pair name: `mlops-key`
     - Key pair type: `RSA`
     - Private key file format: `.pem`
     - Tải file `mlops-key.pem` về máy và lưu vào thư mục `~/.ssh/` rồi cấp quyền:
       ```bash
       chmod 400 ~/.ssh/mlops-key.pem
       ```
   - **Network settings (Firewall / Security Group):**
     - Chọn *Create security group*.
     - Tích chọn **Allow SSH traffic from** $\rightarrow$ Chọn `Anywhere` (`0.0.0.0/0`).
     - Nhấn nút **Add security group rule**:
       - Type: `Custom TCP`
       - Port range: `8000`
       - Source type: `Anywhere` (`0.0.0.0/0`) $\rightarrow$ *(Phục vụ endpoint API suy luận)*.
2. Nhấn nút màu cam **Launch instance**.
3. Vào danh sách **Instances**, đợi instance chuyển sang trạng thái *Running*, sao chép **Public IPv4 address** (ví dụ: `54.254.120.45`):
   ```bash
   export VM_HOST="<PUBLIC_IPV4_CUA_EC2>"
   ```

---

### Cách 2: Sử Dụng Terraform (Khuyến Nghị - Tự Động Hóa 100%)

> [!NOTE]
> **Terraform** là công cụ Infrastructure as Code (IaC) giúp bạn định nghĩa máy chủ EC2, tường lửa (Security Group) và Key Pair bằng code. Khi cần tạo mới chỉ cần 1 lệnh, và khi kết thúc lab chỉ cần 1 lệnh là dọn sạch tài nguyên.

#### Bước 2.4.1: Kiểm tra cài đặt Terraform
Chạy lệnh kiểm tra trên máy:
```bash
terraform version
```
*(Nếu chưa có, cài nhanh bằng Homebrew trên Mac: `brew install terraform`)*.

#### Bước 2.4.2: Chuẩn bị SSH Key
Nếu bạn chưa có SSH key `~/.ssh/id_rsa.pub` hoặc `~/.ssh/mlops_deploy.pub`, tạo nhanh một key:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/mlops_deploy -N "" -C "mlops-deploy-key"
```

#### Bước 2.4.3: Tạo file cấu hình Terraform
Tạo thư mục `infra/` và tạo file `infra/main.tf`:

```hcl
# 1. Cấu hình Terraform Provider cho AWS
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# 2. Khai báo Region (trùng với region bạn đã tạo S3 Bucket)
provider "aws" {
  region = "ap-southeast-1" # Đổi thành region của bạn nếu khác
}

# 3. Tự động tìm AMI Ubuntu 22.04 LTS mới nhất từ Canonical
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical ID chính chủ
}

# 4. Đăng ký SSH Public Key lên AWS EC2
resource "aws_key_pair" "deployer" {
  key_name   = "mlops-deploy-key"
  public_key = file("~/.ssh/mlops_deploy.pub") # Đường dẫn đến public key trên máy bạn
}

# 5. Tạo Security Group (Tường lửa cho phép Port 22 và Port 8000)
resource "aws_security_group" "mlops_sg" {
  name        = "mlops-serve-sg"
  description = "Cho phep SSH (port 22) va Inference API (port 8000)"

  # Cho phép kết nối SSH (Port 22)
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Cho phép kết nối API FastAPI (Port 8000)
  ingress {
    description = "FastAPI Inference API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Cho phép máy chủ EC2 kết nối ra ngoài Internet để cài thư viện
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "mlops-serve-sg"
  }
}

# 6. Khởi tạo EC2 Instance (t2.micro / Free tier)
resource "aws_instance" "mlops_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t2.micro"
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.mlops_sg.id]

  root_block_device {
    volume_size = 10 # 10 GB SSD
    volume_type = "gp3"
  }

  tags = {
    Name = "mlops-serve"
  }
}

# 7. In ra địa chỉ Public IP sau khi khởi tạo thành công
output "ec2_public_ip" {
  description = "Public IP cua may chu EC2 dung cho GitHub Actions Secrets"
  value       = aws_instance.mlops_server.public_ip
}
```

#### Bước 2.4.4: Chạy Terraform để tạo máy ảo
Tại terminal, chuyển vào thư mục `infra/`:
```bash
cd infra

# Khởi tạo provider
terraform init

# Xem trước các tài nguyên sẽ được tạo
terraform plan

# Áp dụng tạo hạ tầng (gõ 'yes' khi được hỏi)
terraform apply -auto-approve
```

Sau khi hoàn thành, terminal sẽ xuất ra:
```text
Outputs:
ec2_public_ip = "54.254.120.45"
```
Bạn lưu IP này vào biến môi trường:
```bash
export VM_HOST="54.254.120.45" # Thay bằng IP thực tế của bạn
cd ..
```

*(Mẹo: Khi làm xong toàn bộ bài lab, nếu muốn xóa máy EC2 để không tốn tài nguyên, bạn chỉ cần vào `infra/` và gõ `terraform destroy -auto-approve`)*.

---

## 2.5 Cấu Hình Ban Đầu Cho EC2 Instance

1. **SSH vào EC2 từ máy local:**
   - **Nếu dùng Terraform (Cách 2):**
     ```bash
     ssh -i ~/.ssh/mlops_deploy ubuntu@$VM_HOST
     ```
   - **Nếu dùng Console Web (Cách 1):**
     ```bash
     ssh -i ~/.ssh/mlops-key.pem ubuntu@$VM_HOST
     ```
   *(Lần đầu kết nối, terminal hỏi `Are you sure you want to continue connecting (yes/no)?`, bạn gõ `yes`)*.

2. **Cài đặt các thư viện cần thiết bên trong EC2:**
   ```bash
   sudo apt update && sudo apt install -y python3-pip
   pip3 install fastapi uvicorn scikit-learn joblib boto3
   mkdir -p ~/models ~/src
   ```

3. Thoát khỏi phiên SSH (`exit`).

---

## 2.6 Viết Mã Nguồn `src/serve.py` (Hỗ Trợ AWS S3)

Chỉnh sửa file `src/serve.py` ở local:

```python
import os
import boto3
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Wine Quality Inference Service")

AWS_BUCKET = os.environ.get("AWS_BUCKET", os.environ.get("CLOUD_BUCKET", ""))
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1"))
S3_MODEL_KEY = "models/latest/model.pkl"
MODEL_PATH = os.path.expanduser("~/models/model.pkl")


def download_model():
    """Tải file model.pkl từ AWS S3 về máy khi server khởi động."""
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    print(f"Downloading model from s3://{AWS_BUCKET}/{S3_MODEL_KEY} to {MODEL_PATH}...")
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.download_file(AWS_BUCKET, S3_MODEL_KEY, MODEL_PATH)
    print("Model downloaded successfully.")


# Tải mô hình khi khởi động server
if os.environ.get("SKIP_MODEL_LOAD") != "1":
    download_model()
    model = joblib.load(MODEL_PATH)
else:
    model = None


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health():
    """Endpoint kiểm tra sức khỏe server."""
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    """Endpoint suy luận chất lượng rượu vang từ 12 đặc trưng."""
    if len(req.features) != 12:
        raise HTTPException(
            status_code=400,
            detail="Expected exactly 12 features for wine quality prediction."
        )

    prediction = int(model.predict([req.features])[0])
    label_map = {0: "thap", 1: "trung_binh", 2: "cao"}
    label = label_map.get(prediction, "khong_xac_dinh")

    return {"prediction": prediction, "label": label}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Copy file `serve.py` lên EC2 (chạy từ máy local):**
- **Nếu dùng Terraform:**
  ```bash
  scp -i ~/.ssh/mlops_deploy src/serve.py ubuntu@$VM_HOST:~/src/serve.py
  ```
- **Nếu dùng Console Web:**
  ```bash
  scp -i ~/.ssh/mlops-key.pem src/serve.py ubuntu@$VM_HOST:~/src/serve.py
  ```

---

## 2.7 Cấu Hình Systemd Service Trên EC2

SSH lại vào EC2:
- **Nếu dùng Terraform:** `ssh -i ~/.ssh/mlops_deploy ubuntu@$VM_HOST`
- **Nếu dùng Console:** `ssh -i ~/.ssh/mlops-key.pem ubuntu@$VM_HOST`

Chạy lệnh sau trên EC2 (thay các giá trị trong dấu ngoặc `<...>` bằng thông tin thực của bạn):

```bash
sudo tee /etc/systemd/system/mlops-serve.service > /dev/null <<EOF
[Unit]
Description=MLOps Model Inference Server (AWS S3)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="AWS_BUCKET=<YOUR_BUCKET_NAME>"
Environment="AWS_DEFAULT_REGION=ap-southeast-1"
Environment="AWS_ACCESS_KEY_ID=<YOUR_AWS_ACCESS_KEY_ID>"
Environment="AWS_SECRET_ACCESS_KEY=<YOUR_AWS_SECRET_ACCESS_KEY>"
ExecStart=/usr/bin/python3 /home/ubuntu/src/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mlops-serve
exit
```

> [!NOTE]
> Chưa cần khởi động service ngay lúc này vì file model trên S3 sẽ được tạo tự động khi GitHub Actions chạy lần đầu.

---

## 2.8 Thiết Lập SSH Key Cho GitHub Actions Deploy

- **Nếu bạn đã dùng Terraform (Cách 2):** Bạn **KHÔNG CẦN LÀM BƯỚC NÀY** vì Terraform đã tự động đăng ký `~/.ssh/mlops_deploy.pub` vào EC2 ngay từ đầu! Bạn chuyển thẳng sang **Bước 2.9**.
- **Nếu bạn dùng Console Web (Cách 1):** Chạy 2 lệnh sau từ máy local để thêm public key deploy vào EC2:
  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/mlops_deploy -N "" -C "github-actions-deploy"
  cat ~/.ssh/mlops_deploy.pub | ssh -i ~/.ssh/mlops-key.pem ubuntu@$VM_HOST "cat >> ~/.ssh/authorized_keys"
  ```


---

## 2.9 Cấu Hình 5 Secrets Trên GitHub Repo

Vào GitHub Repository $\rightarrow$ **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** $\rightarrow$ **New repository secret**:

| Tên Secret | Hướng dẫn nhập giá trị |
| :--- | :--- |
| **`CLOUD_CREDENTIALS`** | Chuỗi JSON chứa Access Key AWS:<br>`{"aws_access_key_id":"AKIA...","aws_secret_access_key":"...","aws_region":"ap-southeast-1"}` |
| **`CLOUD_BUCKET`** | Tên S3 Bucket (ví dụ: `mlops-lab-wine-thangnv-1740000000`) |
| **`VM_HOST`** | Địa chỉ Public IP của EC2 (ví dụ: `54.254.120.45`) |
| **`VM_USER`** | `ubuntu` |
| **`VM_SSH_KEY`** | Toàn bộ nội dung file private key `~/.ssh/mlops_deploy` (bao gồm cả dòng `-----BEGIN OPENSSH PRIVATE KEY-----`) |

---

## 2.10 Hoàn Thiện Unit Test `tests/test_train.py`

Cập nhật `tests/test_train.py` với logic hoàn chỉnh:

```python
import os
import json
import numpy as np
import pandas as pd
from src.train import train

FEATURE_NAMES = [
    "fixed_acidity", "volatile_acidity", "citric_acid", "residual_sugar",
    "chlorides", "free_sulfur_dioxide", "total_sulfur_dioxide", "density",
    "pH", "sulphates", "alcohol", "wine_type",
]


def _make_temp_data(tmp_path):
    """Tạo dataset nhỏ với cùng schema Wine Quality để sử dụng trong test."""
    rng = np.random.default_rng(0)
    n = 200

    # 1. Tạo mảng X ngẫu nhiên kích thước (200, 12)
    X = rng.random((n, len(FEATURE_NAMES)))

    # 2. Tạo mảng nhãn y ngẫu nhiên trong [0, 3)
    y = rng.integers(0, 3, size=n)

    # 3. Tạo DataFrame
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["target"] = y

    # 4. Lưu train (160 dòng) và eval (40 dòng)
    train_path = str(tmp_path / "train.csv")
    eval_path = str(tmp_path / "eval.csv")
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)

    return train_path, eval_path


def test_train_returns_float(tmp_path):
    """Kiểm tra hàm train() trả về một số thực trong khoảng [0, 1]."""
    train_path, eval_path = _make_temp_data(tmp_path)
    acc = train({"n_estimators": 10, "max_depth": 3}, data_path=train_path, eval_path=eval_path)
    assert isinstance(acc, float)
    assert 0.0 <= acc <= 1.0


def test_metrics_file_created(tmp_path):
    """Kiểm tra file outputs/metrics.json được tạo sau khi huấn luyện."""
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "max_depth": 3},
        data_path=train_path,
        eval_path=eval_path,
    )
    assert os.path.exists("outputs/metrics.json")
    with open("outputs/metrics.json") as f:
        metrics = json.load(f)
    assert "accuracy" in metrics
    assert "f1_score" in metrics


def test_model_file_created(tmp_path):
    """Kiểm tra file models/model.pkl được tạo sau khi huấn luyện."""
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "max_depth": 3},
        data_path=train_path,
        eval_path=eval_path,
    )
    assert os.path.exists("models/model.pkl")
```

Chạy kiểm tra test cục bộ:
```bash
pytest tests/ -v
```

---

## 2.11 Viết Pipeline CI/CD `.github/workflows/mlops.yml` Cho AWS

Tạo file `.github/workflows/mlops.yml`:

```yaml
name: MLOps Pipeline

on:
  push:
    branches: [main]
    paths:
      - 'data/**.dvc'
      - 'src/**.py'
      - 'params.yaml'
  workflow_dispatch:

jobs:

  # JOB 1: Chạy Unit Tests
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install --upgrade pip setuptools<70
          pip install -r requirements.txt boto3 pytest

      - name: Run tests
        run: pytest tests/ -v

  # JOB 2: Pull DVC từ S3, Train Model, Upload Model lên S3
  train:
    name: Train
    needs: test
    runs-on: ubuntu-latest
    outputs:
      accuracy: ${{ steps.read_metrics.outputs.accuracy }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install --upgrade pip setuptools<70
          pip install -r requirements.txt "dvc[s3]" boto3

      - name: Configure AWS Credentials
        run: |
          echo "Setting up AWS credentials from secrets..."
          AWS_KEY=$(python -c "import json; creds=json.loads('${{ secrets.CLOUD_CREDENTIALS }}'); print(creds.get('aws_access_key_id', ''))")
          AWS_SECRET=$(python -c "import json; creds=json.loads('${{ secrets.CLOUD_CREDENTIALS }}'); print(creds.get('aws_secret_access_key', ''))")
          AWS_REG=$(python -c "import json; creds=json.loads('${{ secrets.CLOUD_CREDENTIALS }}'); print(creds.get('aws_region', 'ap-southeast-1'))")
          
          echo "AWS_ACCESS_KEY_ID=$AWS_KEY" >> $GITHUB_ENV
          echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET" >> $GITHUB_ENV
          echo "AWS_DEFAULT_REGION=$AWS_REG" >> $GITHUB_ENV

      - name: Pull data with DVC from S3
        run: dvc pull data/train_phase1.csv.dvc data/eval.csv.dvc

      - name: Train model
        run: python src/train.py

      - name: Read metrics
        id: read_metrics
        run: |
          ACC=$(python -c "import json; m = json.load(open('outputs/metrics.json')); print(m['accuracy'])")
          echo "accuracy=$ACC" >> $GITHUB_OUTPUT
          echo "Model Accuracy: $ACC"

      - name: Upload model to AWS S3
        run: |
          python - <<'EOF'
          import os
          import boto3

          bucket_name = "${{ secrets.CLOUD_BUCKET }}"
          s3_key = "models/latest/model.pkl"
          local_file = "models/model.pkl"

          s3 = boto3.client("s3")
          print(f"Uploading {local_file} to s3://{bucket_name}/{s3_key}...")
          s3.upload_file(local_file, bucket_name, s3_key)
          print("Upload completed successfully!")
          EOF

      - name: Save metrics as artifact
        uses: actions/upload-artifact@v4
        with:
          name: metrics
          path: outputs/metrics.json

  # JOB 3: Eval Gate (Đảm bảo Accuracy >= 0.70)
  eval:
    name: Eval
    needs: train
    runs-on: ubuntu-latest
    steps:
      - name: Check eval gate
        run: |
          python - <<'EOF'
          import sys

          accuracy = float("${{ needs.train.outputs.accuracy }}")
          threshold = 0.70

          print(f"Model Accuracy: {accuracy:.4f} | Required Threshold: {threshold}")
          if accuracy >= threshold:
              print("Eval Gate PASSED. Proceeding to deployment.")
          else:
              print(f"Eval Gate FAILED. Accuracy {accuracy:.4f} is below threshold {threshold}.")
              sys.exit(1)
          EOF

  # JOB 4: Deploy lên EC2 qua SSH
  deploy:
    name: Deploy
    needs: eval
    runs-on: ubuntu-latest
    steps:
      - name: SSH deploy to EC2
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VM_HOST }}
          username: ${{ secrets.VM_USER }}
          key: ${{ secrets.VM_SSH_KEY }}
          script: |
            echo "Restarting mlops-serve service on EC2..."
            sudo systemctl restart mlops-serve
            sleep 5
            
            echo "Verifying health endpoint..."
            HEALTH_STATUS=$(curl -s http://localhost:8000/health | grep '"status":"ok"' || true)
            if [ -n "$HEALTH_STATUS" ]; then
              echo "Deployment succeeded! Server is healthy."
            else
              echo "Deployment failed! Health check did not return ok."
              sudo systemctl status mlops-serve
              exit 1
            fi
```

---

## 2.12 Push Lên GitHub & Xác Nhận Triển Khai

1. Commit và push code lên nhánh `main`:
   ```bash
   git add .
   git commit -m "feat: complete Step 2 CI/CD pipeline for AWS"
   git push origin main
   ```

2. Vào tab **Actions** trên GitHub để theo dõi 4 jobs chạy tuần tự:
   $$\text{Test} \longrightarrow \text{Train} \longrightarrow \text{Eval} \longrightarrow \text{Deploy}$$

3. **Kiểm tra API trực tiếp trên EC2 từ máy local:**
   ```bash
   # Kiểm tra sức khỏe server
   curl http://$VM_HOST:8000/health
   # Kết quả: {"status":"ok"}

   # Gửi request dự đoán thử nghiệm (12 features)
   curl -X POST http://$VM_HOST:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"features": [7.4, 0.70, 0.00, 1.9, 0.076, 11.0, 34.0, 0.9978, 3.51, 0.56, 9.4, 0]}'
   # Kết quả: {"prediction": 0, "label": "thap"}
   ```
