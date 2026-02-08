import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline


def train_engine():
    print("🚀 [1/4] 开始训练... (V7: 物理规律锁定版)")

    # ---------------------------------------------------------
    # 1. 通用背景数据
    # ---------------------------------------------------------
    n_samples = 25000
    np.random.seed(42)

    sizes = np.random.randint(0, 26, n_samples)
    heights = np.random.normal(165, 5, n_samples)

    # 基础公式：标准腰围 = 60 + (尺码 * 3)
    base_waist = 60 + (sizes * 3.0)

    # === A. 合身 (Fit) ===
    waist_fit = base_waist + np.random.uniform(-5, 5, n_samples)
    df_fit = pd.DataFrame(
        {'size': sizes, 'height_cm': heights, 'waist': waist_fit, 'hips': waist_fit * 1.4, 'bra_num': 34,
         'cup_size': 'b', 'category': 'dresses', 'target': 1})

    # === B. 偏小 (Small) ===
    waist_small = base_waist + np.random.randint(8, 40, n_samples)
    df_small = pd.DataFrame(
        {'size': sizes, 'height_cm': heights, 'waist': waist_small, 'hips': waist_small * 1.4, 'bra_num': 34,
         'cup_size': 'b', 'category': 'dresses', 'target': 0})

    # === C. 偏大 (Large) - 关键修改 ===
    # 逻辑锁：禁止生成 Size 0 和 Size 1 的偏大样本
    # 只有当 Size >= 2 时，才允许出现“衣服太大”的情况
    waist_large = base_waist - np.random.randint(8, 30, n_samples)
    waist_large = np.maximum(waist_large, 45)

    df_large = pd.DataFrame({
        'size': sizes, 'height_cm': heights, 'waist': waist_large,
        'hips': waist_large * 1.4, 'bra_num': 34, 'cup_size': 'b',
        'category': 'dresses', 'target': 2
    })

    # 过滤掉 Size 0 和 Size 1 的 Large 样本
    df_large = df_large[df_large['size'] >= 2]

    # ---------------------------------------------------------
    # 2. ⭐️ 修复 1: 针对腰围 60cm (Size 0-1) 的特调
    # ---------------------------------------------------------
    print("💉 注入小尺码修正数据 (Waist 60cm)...")
    fix_data_small = []

    # 场景: 60cm腰围 穿 0码 (标准60) -> 必须是 Fit (1)
    # 增加权重到 5000 条，确保覆盖
    fix_data_small.append(pd.DataFrame({
        'size': [0] * 5000,
        'height_cm': [160] * 5000,  # 配合身高 160
        'waist': np.random.normal(60, 0.5, 5000),
        'hips': [85] * 5000, 'bra_num': [32] * 5000, 'cup_size': 'a', 'category': 'dresses',
        'target': 1  # Fit
    }))

    # 场景: 60cm腰围 穿 1码 (标准63) -> 60 vs 63 -> 也是 Fit (1)
    fix_data_small.append(pd.DataFrame({
        'size': [1] * 5000,
        'height_cm': [160] * 5000,
        'waist': np.random.normal(60, 0.5, 5000),
        'hips': [85] * 5000, 'bra_num': [32] * 5000, 'cup_size': 'a', 'category': 'dresses',
        'target': 1  # Fit
    }))

    # 场景: 60cm腰围 穿 3码 (标准69) -> 60 vs 69 -> 衣服大了 -> Large (2)
    fix_data_small.append(pd.DataFrame({
        'size': [3] * 3000,
        'height_cm': [160] * 3000,
        'waist': np.random.normal(60, 0.5, 3000),
        'hips': [85] * 3000, 'bra_num': [32] * 3000, 'cup_size': 'a', 'category': 'dresses',
        'target': 2  # Large
    }))

    # ---------------------------------------------------------
    # 3. ⭐️ 修复 2: 保留针对腰围 78cm (Size 6) 的扫描
    # ---------------------------------------------------------
    print("💉 注入中尺码修正数据 (Waist 78cm)...")
    fix_data_mid = []

    # Size 4, 5 -> Small
    for s in [4, 5]:
        fix_data_mid.append(pd.DataFrame({
            'size': [s] * 2000,
            'height_cm': [165] * 2000,
            'waist': np.random.normal(78, 0.5, 2000),
            'hips': [100] * 2000, 'bra_num': [34] * 2000, 'cup_size': 'b', 'category': 'dresses',
            'target': 0
        }))
    # Size 6 -> Fit
    fix_data_mid.append(pd.DataFrame({
        'size': [6] * 4000,
        'height_cm': [165] * 4000,
        'waist': np.random.normal(78, 0.5, 4000),
        'hips': [100] * 4000, 'bra_num': [34] * 4000, 'cup_size': 'b', 'category': 'dresses',
        'target': 1
    }))
    # Size 8 -> Large
    fix_data_mid.append(pd.DataFrame({
        'size': [8] * 2000,
        'height_cm': [165] * 2000,
        'waist': np.random.normal(78, 0.5, 2000),
        'hips': [100] * 2000, 'bra_num': [34] * 2000, 'cup_size': 'b', 'category': 'dresses',
        'target': 2
    }))

    # ---------------------------------------------------------
    # 4. 合并与训练
    # ---------------------------------------------------------
    df_fix = pd.concat(fix_data_small + fix_data_mid)
    df_final = pd.concat([df_fit, df_small, df_large, df_fix], ignore_index=True)

    df_final['bmi_proxy'] = df_final['waist'] / df_final['height_cm']
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"✅ 训练集准备完毕: {len(df_final)} 条")

    features = ['cup_size', 'bra_num', 'hips', 'waist', 'category', 'size', 'height_cm', 'bmi_proxy']
    X = df_final[features]
    y = df_final['target']

    preprocessor = ColumnTransformer(transformers=[
        ('num', StandardScaler(), ['bra_num', 'hips', 'waist', 'size', 'height_cm', 'bmi_proxy']),
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['cup_size', 'category'])
    ])

    pipeline = Pipeline(steps=[
        ('pre', preprocessor),
        # 深度适中，避免过拟合
        ('clf', XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=7))
    ])

    print("🏋️ [3/4] 训练模型...")
    pipeline.fit(X, y)

    print("💾 [4/4] 保存模型...")
    if not os.path.exists('models'): os.makedirs('models')
    joblib.dump(pipeline, 'models/fit_model.pkl')
    print("🎉 V7模型已保存！")


if __name__ == "__main__":
    train_engine()