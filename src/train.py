import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

EVAL_THRESHOLD = 0.70

if "MLFLOW_TRACKING_URI" not in os.environ:
    mlflow.set_tracking_uri("sqlite:///mlflow.db")


def train(
    params: dict,
    data_path: str = "data/train_phase1.csv",
    eval_path: str = "data/eval.csv",
) -> float:
    """
    Huấn luyện mô hình và ghi nhận kết quả vào MLflow.
    Hỗ trợ đa thuật toán: RandomForest, ExtraTrees, HistGradientBoosting, GradientBoosting, LogisticRegression.
    """

    # 1. Đọc dữ liệu huấn luyện và đánh giá
    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    # 2. Tách đặc trưng (X) và nhãn (y)
    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    # 3. Kiểm tra phân phối nhãn dữ liệu và cảnh báo Data Drift (Bonus 5)
    total_samples = len(df_train)
    class_counts = df_train["target"].value_counts().to_dict()
    class_distribution = {
        int(k): round(float(v / total_samples), 4)
        for k, v in sorted(class_counts.items())
    }

    print("=" * 70)
    print("      KIỂM TRA PHÂN PHỐI NHÃN DỮ LIỆU & DATA DRIFT (BONUS 5)         ")
    print("=" * 70)
    print(f"Tổng số mẫu huấn luyện : {total_samples}")
    drift_warnings = []
    for cls, ratio in class_distribution.items():
        pct = ratio * 100
        count = class_counts.get(cls, 0)
        print(f"  • Lớp {cls}: {count} mẫu ({pct:.2f}%)")
        if ratio < 0.10:
            msg = f"WARNING: Class {cls} represents only {pct:.2f}% of data (< 10%). Significant data imbalance / drift detected!"
            drift_warnings.append(msg)
            print(f"    ⚠️  {msg}")

    if not drift_warnings:
        print("  ✅ Tất cả các lớp đều chiếm >= 10% dữ liệu. Phân phối cân bằng tốt.")
    print("=" * 70)

    # 4. Lựa chọn thuật toán dựa trên tham số model_type
    model_type = params.get("model_type", "random_forest")
    clf_params = {k: v for k, v in params.items() if k != "model_type"}

    if model_type == "hist_gradient_boosting":
        model = HistGradientBoostingClassifier(
            max_iter=clf_params.get("n_estimators", 300),
            max_depth=clf_params.get("max_depth", 15),
            learning_rate=clf_params.get("learning_rate", 0.08),
            random_state=42,
        )
    elif model_type == "extra_trees":
        model = ExtraTreesClassifier(
            n_estimators=clf_params.get("n_estimators", 400),
            max_depth=clf_params.get("max_depth", 25),
            min_samples_split=clf_params.get("min_samples_split", 3),
            random_state=42,
        )
    elif model_type == "gradient_boosting":
        model = GradientBoostingClassifier(
            n_estimators=clf_params.get("n_estimators", 200),
            max_depth=clf_params.get("max_depth", 6),
            learning_rate=clf_params.get("learning_rate", 0.08),
            random_state=42,
        )
    elif model_type == "logistic_regression":
        model = LogisticRegression(
            C=clf_params.get("C", 1.0),
            max_iter=1000,
            random_state=42,
        )
    else:
        # Mặc định: RandomForestClassifier
        model = RandomForestClassifier(**clf_params, random_state=42)

    with mlflow.start_run():

        # 5. Ghi nhận các siêu tham số, model_type và phân phối dữ liệu vào MLflow
        mlflow.log_param("model_type", model_type)
        mlflow.log_params(params)
        for cls, ratio in class_distribution.items():
            mlflow.log_metric(f"class_{cls}_ratio", ratio)

        # 6. Huấn luyện mô hình
        model.fit(X_train, y_train)

        # 7. Dự đoán trên tập đánh giá và tính accuracy, weighted f1-score
        preds = model.predict(X_eval)
        acc = float(accuracy_score(y_eval, preds))
        f1 = float(f1_score(y_eval, preds, average="weighted"))

        # 8. Ghi nhận metrics và artifact model vào MLflow
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)
        mlflow.sklearn.log_model(model, "model")

        # 9. Tạo báo cáo chi tiết: Precision, Recall theo từng lớp và Confusion Matrix (Bonus 3)
        target_names = ["Lop 0 (Thap)", "Lop 1 (Trung Binh)", "Lop 2 (Cao)"]
        cls_report = classification_report(y_eval, preds, target_names=target_names, zero_division=0)
        cm = confusion_matrix(y_eval, preds)

        report_text = (
            f"======================================================================\n"
            f"                   BÁO CÁO ĐÁNH GIÁ HIỆU SUẤT MÔ HÌNH                  \n"
            f"======================================================================\n"
            f"Thuật toán        : {model_type}\n"
            f"Tổng mẫu đánh giá : {len(y_eval)}\n"
            f"Độ chính xác      : {acc:.4f}\n"
            f"Weighted F1-Score : {f1:.4f}\n\n"
            f"--- CHI TIẾT THEO TỪNG LỚP (PRECISION, RECALL, F1) ---\n"
            f"{cls_report}\n\n"
            f"--- CONFUSION MATRIX (MA TRẬN NHẦM LẪN) ---\n"
            f"{cm}\n"
            f"======================================================================\n"
        )

        # 10. Lưu metrics và report ra thư mục outputs (Bonus 3 & Bonus 5)
        os.makedirs("outputs", exist_ok=True)
        metrics_payload = {
            "accuracy": acc,
            "f1_score": f1,
            "class_distribution": class_distribution,
            "drift_warnings": drift_warnings,
        }
        with open("outputs/metrics.json", "w") as f:
            json.dump(metrics_payload, f, indent=4)

        with open("outputs/report.txt", "w", encoding="utf-8") as f:
            f.write(report_text)

        print(report_text)

        # 11. Lưu mô hình ra file models/model.pkl
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/model.pkl")

    return acc




if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)

