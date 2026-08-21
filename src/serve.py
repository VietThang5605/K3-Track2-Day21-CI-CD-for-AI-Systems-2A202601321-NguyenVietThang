import os
import boto3
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Wine Quality Inference Service")

# Đọc tên bucket và region từ biến môi trường
AWS_BUCKET = os.environ.get("AWS_BUCKET", os.environ.get("CLOUD_BUCKET", os.environ.get("GCS_BUCKET", "")))
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1"))
S3_MODEL_KEY = "models/latest/model.pkl"
MODEL_PATH = os.path.expanduser("~/models/model.pkl")


def download_model():
    """
    Tải file model.pkl từ AWS S3 về máy khi server khởi động.
    Sử dụng credentials từ môi trường (hoặc IAM Role / Access Keys trong systemd service).
    """
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    print(f"Downloading model from s3://{AWS_BUCKET}/{S3_MODEL_KEY} to {MODEL_PATH}...")
    
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.download_file(AWS_BUCKET, S3_MODEL_KEY, MODEL_PATH)
    print("Model đã được tải xuống thành công từ AWS S3.")


# Tải mô hình khi module được import (khởi động server)
# Biến SKIP_MODEL_LOAD có thể dùng khi chạy unit test cục bộ nếu cần
if os.environ.get("SKIP_MODEL_LOAD") != "1":
    download_model()
    model = joblib.load(MODEL_PATH)
else:
    model = None


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health():
    """
    Endpoint kiểm tra sức khỏe server.
    GitHub Actions gọi endpoint này sau khi deploy để xác nhận server đang chạy bình thường.
    """
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    """
    Endpoint suy luận chính.

    Đầu vào : JSON {"features": [f1, f2, ..., f12]}
    Đầu ra  : JSON {"prediction": <0|1|2>, "label": <"thap"|"trung_binh"|"cao">}

    Thứ tự 12 đặc trưng:
        fixed_acidity, volatile_acidity, citric_acid, residual_sugar,
        chlorides, free_sulfur_dioxide, total_sulfur_dioxide, density,
        pH, sulphates, alcohol, wine_type
    """
    # 1. Kiểm tra số lượng đặc trưng đầu vào (bắt buộc đúng 12 đặc trưng)
    if len(req.features) != 12:
        raise HTTPException(
            status_code=400,
            detail="Expected 12 features (wine quality)"
        )

    if model is None:
        raise HTTPException(
            status_code=500,
            detail="Model is not loaded."
        )

    # 2. Dự đoán nhãn chất lượng
    prediction = int(model.predict([req.features])[0])

    # 3. Ánh xạ nhãn số sang chuỗi mô tả
    label_map = {0: "thap", 1: "trung_binh", 2: "cao"}
    label = label_map.get(prediction, "khong_xac_dinh")

    # 4. Trả về kết quả dự đoán
    return {
        "prediction": prediction,
        "label": label
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

