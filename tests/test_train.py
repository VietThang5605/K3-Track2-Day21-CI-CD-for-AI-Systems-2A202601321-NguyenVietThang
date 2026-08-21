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
    """
    Tạo dataset nhỏ với cùng schema Wine Quality để sử dụng trong test.

    pytest cung cấp `tmp_path` là một thư mục tạm thời, tự động xóa sau khi test kết thúc.
    Hàm này dùng dữ liệu ngẫu nhiên nên không cần kết nối cloud hay tải file CSV thực.
    """
    rng = np.random.default_rng(0)
    n = 200

    # 1. Tạo mảng X có kích thước (n, len(FEATURE_NAMES)) với giá trị [0, 1)
    X = rng.random((n, len(FEATURE_NAMES)))

    # 2. Tạo mảng y gồm n phần tử nguyên ngẫu nhiên trong [0, 3)
    y = rng.integers(0, 3, size=n)

    # 3. Xây dựng DataFrame và thêm cột "target"
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["target"] = y

    # 4. Lưu 160 dòng đầu làm tập huấn luyện, 40 dòng cuối làm tập đánh giá
    train_path = str(tmp_path / "train.csv")
    eval_path = str(tmp_path / "eval.csv")
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)

    # 5. Trả về (train_path, eval_path)
    return train_path, eval_path


def test_train_returns_float(tmp_path):
    """Kiểm tra hàm train() trả về một số thực nằm trong [0.0, 1.0]."""
    train_path, eval_path = _make_temp_data(tmp_path)

    # 6. Gọi hàm train() với siêu tham số nhỏ và các đường dẫn file tạm vừa tạo
    acc = train(
        {"n_estimators": 10, "max_depth": 3},
        data_path=train_path,
        eval_path=eval_path,
    )

    # 7. Kiểm tra kết quả
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

    # 8. Kiểm tra file tồn tại và nội dung đúng định dạng
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

    # 9. Kiểm tra file model tồn tại
    assert os.path.exists("models/model.pkl")

