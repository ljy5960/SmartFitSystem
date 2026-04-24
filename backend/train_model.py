import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline


def train_from_json():
    file_path = 'data/modcloth_final_data.json'

    # 路径校验，防止运行目录错误
    if not os.path.exists(file_path):
        return

    try:
        df = pd.read_json(file_path, lines=True)
    except Exception as e:
        return


    # 1. 复杂字符串解析：身高 (5ft 6in -> 167.6 cm)
    def parse_height(h):
        if pd.isna(h) or not isinstance(h, str): return np.nan
        try:
            parts = h.split('ft')
            ft = float(parts[0].strip())
            inches = float(parts[1].replace('in', '').strip())
            return (ft * 30.48) + (inches * 2.54)
        except:
            return np.nan

    df['height_cm'] = df['height'].apply(parse_height)
    df['height_cm'] = df['height_cm'].fillna(df['height_cm'].mean())  # 填补极少量缺失的身高

    # 2. 目标变量映射 (Target)
    df['fit'] = df['fit'].astype(str).str.lower().str.strip()

    fit_map = {'small': 0, 'fit': 1, 'large': 2}
    df['target'] = df['fit'].map(fit_map)

    df = df.dropna(subset=['target'])
    # fit_map = {'small': 0, 'fit': 1, 'large': 2}
    # df['target'] = df['fit'].map(fit_map)

    # 3. 96% 缺失的腰围数据
    np.random.seed(42)

    # def impute_waist(row):
    #     if pd.notna(row['waist']):
    #         return float(row['waist']) * 2.54
    #     std_waist = row['size'] * 1.5 + 60.0
    #     if row['target'] == 1:
    #         return std_waist + np.random.normal(0, 2.0)
    #     elif row['target'] == 0:
    #         return std_waist + np.random.normal(5.0, 2.0)
    #     else:
    #         return std_waist - np.random.normal(5.0, 2.0)
    def impute_waist(row):
        if pd.notna(row['waist']):
            return float(row['waist']) * 2.54
        std_waist = row['size'] * 1.5 + 60.0
        # 将原来的 2.0 放大到 4.0 或 5.0
        if row['target'] == 1:
            return std_waist + np.random.normal(0, 4.0)
        elif row['target'] == 0:
            return std_waist + np.random.normal(6.0, 4.0)
        else:
            return std_waist - np.random.normal(6.0, 4.0)

    df['waist_cm'] = df.apply(impute_waist, axis=1)

    # 4. 解决臀围缺失 (后端的 1.4 比例硬性填补)
    def impute_hips(row):
        if pd.notna(row['hips']):
            return float(row['hips']) * 2.54
        return row['waist_cm'] * 1.4

    df['hips_cm'] = df.apply(impute_hips, axis=1)

    df['bra_num'] = df['bra size'].fillna((32 + (df['size'] // 2) * 2)).astype(int)

    df['cup_size'] = df['cup size'].fillna('b')

    df['bmi_proxy'] = df['waist_cm'] / df['height_cm']

    df['category'] = df['category'].str.lower()
    df = df[df['category'].isin(['dresses', 'tops', 'bottoms', 'outerwear'])].copy()

    df = df.drop(columns=['waist', 'hips'], errors='ignore')

    df = df.rename(columns={'waist_cm': 'waist', 'hips_cm': 'hips'})

    features = ['cup_size', 'bra_num', 'hips', 'waist', 'category', 'size', 'height_cm', 'bmi_proxy']
    X = df[features]
    y = df['target'].astype(int)


    # 构建预处理管道与模型拟合

    preprocessor = ColumnTransformer(transformers=[
        ('num', StandardScaler(), ['bra_num', 'hips', 'waist', 'size', 'height_cm', 'bmi_proxy']),
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['cup_size', 'category'])
    ])

    pipeline = Pipeline(steps=[
        ('pre', preprocessor),
        ('clf', XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=8, random_state=42))
    ])


    pipeline.fit(X, y)

    # 保存模型
    if not os.path.exists('models'):
        os.makedirs('models')

    output_path = 'models/fit_model.pkl'
    joblib.dump(pipeline, output_path)


if __name__ == "__main__":
    train_from_json()