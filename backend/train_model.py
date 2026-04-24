import json
import os
import re
from datetime import datetime, timezone
from collections import Counter

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

RANDOM_STATE = 42


def parse_height_to_cm(height_text):
    if pd.isna(height_text) or not isinstance(height_text, str):
        return np.nan
    match = re.match(r"\s*(\d+)\s*ft\s*(\d+)\s*in\s*", height_text.lower())
    if not match:
        return np.nan
    ft, inches = float(match.group(1)), float(match.group(2))
    return ft * 30.48 + inches * 2.54


def load_raw_data(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"训练数据不存在: {file_path}")
    return pd.read_json(file_path, lines=True)


def build_features(df):
    work_df = df.copy()

    # 标签映射
    work_df['fit'] = work_df['fit'].astype(str).str.lower().str.strip()
    fit_map = {'small': 0, 'fit': 1, 'large': 2}
    work_df['target'] = work_df['fit'].map(fit_map)
    work_df = work_df.dropna(subset=['target'])

    # 类目标准化与过滤
    work_df['category'] = work_df['category'].astype(str).str.lower().str.strip()
    category_map = {'new': 'dresses'}
    work_df['category'] = work_df['category'].replace(category_map)
    work_df = work_df[work_df['category'].isin(['dresses', 'tops', 'bottoms', 'outerwear'])].copy()

    # 身高解析
    work_df['height_cm'] = work_df['height'].apply(parse_height_to_cm)

    # 腰围与臀围：统一转 cm
    work_df['waist'] = pd.to_numeric(work_df['waist'], errors='coerce') * 2.54
    work_df['hips'] = pd.to_numeric(work_df['hips'], errors='coerce') * 2.54

    # --- 关键修复：避免 label leakage ---
    # 以前按 target 构造 waist，会把标签信息泄漏到特征中；
    # 现在改为按 (category, size) 的统计值进行无监督填补。
    work_df['size'] = pd.to_numeric(work_df['size'], errors='coerce')
    group_waist_median = work_df.groupby(['category', 'size'])['waist'].transform('median')
    work_df['waist'] = work_df['waist'].fillna(group_waist_median)
    work_df['waist'] = work_df['waist'].fillna(work_df['size'] * 1.5 + 60.0)

    # 臀围按组中位数，再兜底腰围比例
    group_hips_median = work_df.groupby(['category', 'size'])['hips'].transform('median')
    work_df['hips'] = work_df['hips'].fillna(group_hips_median)
    work_df['hips'] = work_df['hips'].fillna(work_df['waist'] * 1.35)

    # Bra / cup
    work_df['bra_num'] = pd.to_numeric(work_df['bra size'], errors='coerce')
    work_df['bra_num'] = work_df['bra_num'].fillna(34)

    work_df['cup_size'] = work_df['cup size'].astype(str).str.lower().str.strip()
    work_df['cup_size'] = work_df['cup_size'].replace({'nan': 'b', '': 'b'}).fillna('b')

    # 代理体型比
    work_df['height_cm'] = work_df['height_cm'].fillna(work_df['height_cm'].median())
    work_df['body_ratio_proxy'] = work_df['waist'] / work_df['height_cm']

    features = ['cup_size', 'bra_num', 'hips', 'waist', 'category', 'size', 'height_cm', 'body_ratio_proxy']
    X = work_df[features]
    y = work_df['target'].astype(int)
    return X, y


def train_from_json():
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, 'data', 'modcloth_final_data.json')
    model_dir = os.path.join(base_dir, 'models')
    model_path = os.path.join(model_dir, 'fit_model.pkl')
    meta_path = os.path.join(model_dir, 'fit_model_meta.json')

    df = load_raw_data(data_path)
    X, y = build_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y
    )

    numeric_features = ['bra_num', 'hips', 'waist', 'size', 'height_cm', 'body_ratio_proxy']
    categorical_features = ['cup_size', 'category']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), numeric_features),
            ('cat', Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('onehot', OneHotEncoder(handle_unknown='ignore'))
            ]), categorical_features),
        ]
    )

    model = XGBClassifier(
        n_estimators=350,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.9,
        colsample_bytree=0.9,
        objective='multi:softprob',
        eval_metric='mlogloss',
        random_state=RANDOM_STATE
    )

    pipeline = Pipeline(steps=[
        ('pre', preprocessor),
        ('clf', model)
    ])

    class_counts = Counter(y_train.tolist())
    total = float(len(y_train))
    class_weight_map = {cls: total / (len(class_counts) * count) for cls, count in class_counts.items()}
    sample_weight = y_train.map(class_weight_map)

    pipeline.fit(X_train, y_train, clf__sample_weight=sample_weight)
    y_pred = pipeline.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    report = classification_report(y_test, y_pred, output_dict=True)
    conf = confusion_matrix(y_test, y_pred).tolist()

    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(pipeline, model_path)

    meta = {
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'data_rows': int(len(X)),
        'train_rows': int(len(X_train)),
        'test_rows': int(len(X_test)),
        'target_distribution': {
            'small': int((y == 0).sum()),
            'fit': int((y == 1).sum()),
            'large': int((y == 2).sum())
        },
        'metrics': {
            'accuracy': round(acc, 4),
            'macro_f1': round(float(report['macro avg']['f1-score']), 4),
            'weighted_f1': round(float(report['weighted avg']['f1-score']), 4),
            'confusion_matrix': conf,
        },
        'class_weight_map': {str(k): round(float(v), 4) for k, v in class_weight_map.items()},
        'notes': [
            'Removed target-dependent waist imputation to avoid label leakage.',
            'Switched to stratified train/test split and stored evaluation metrics.',
            'Applied class-balanced sample weights to reduce majority-class bias.'
        ]
    }

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print('训练完成')
    print(json.dumps(meta['metrics'], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    train_from_json()
