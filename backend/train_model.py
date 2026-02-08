import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline


def train_engine():
    print("🚀 [1/4] 开始训练... (V9: 3码合身定制版)")

    # ---------------------------------------------------------
    # 1. 基础数据 (调整公式以匹配新逻辑)
    # ---------------------------------------------------------
    n_samples = 30000
    np.random.seed(42)

    sizes = np.random.randint(0, 26, n_samples)
    heights = np.random.normal(165, 5, n_samples)

    # 📐 新公式：陡峭曲线
    # Size 0 = 60
    # Size 3 = 78 (变化了18cm / 3个码 = 每个码约 6cm)
    # 基础腰围 = 60 + (尺码 * 6.0)
    # 这样 Size 3=78, Size 4=84
    base_waist = 60 + (sizes * 6.0)

    # === A. 合身 (Fit) ===
    # 范围：标准 +/- 6cm
    # Size 3 (78): Range [72, 84] -> 包含 78
    waist_fit = base_waist + np.random.uniform(-6, 6, n_samples)
    df_fit = pd.DataFrame(
        {'size': sizes, 'height_cm': heights, 'waist': waist_fit, 'hips': waist_fit * 1.4, 'bra_num': 34,
         'cup_size': 'b', 'category': 'dresses', 'target': 1})

    # === B. 偏小 (Small) ===
    # 差异 > 8cm
    waist_small = base_waist + np.random.randint(8, 40, n_samples)
    df_small = pd.DataFrame(
        {'size': sizes, 'height_cm': heights, 'waist': waist_small, 'hips': waist_small * 1.4, 'bra_num': 34,
         'cup_size': 'b', 'category': 'dresses', 'target': 0})

    # === C. 偏大 (Large) ===
    # 差异 > 8cm
    waist_large = base_waist - np.random.randint(8, 30, n_samples)
    waist_large = np.maximum(waist_large, 45)

    df_large = pd.DataFrame({
        'size': sizes, 'height_cm': heights, 'waist': waist_large,
        'hips': waist_large * 1.4, 'bra_num': 34, 'cup_size': 'b',
        'category': 'dresses', 'target': 2
    })

    # 物理锁：Size 0 禁止 Large (因为0码最小)
    df_large = df_large[df_large['size'] >= 1]

    # ---------------------------------------------------------
    # 2. ⭐️ 修复 1: 腰围 60cm (Size 0, 1)
    # ---------------------------------------------------------
    print("💉 注入小尺码数据 (Waist 60)...")
    fix_data_small = []

    # Size 0 (Std 60) -> Fit
    fix_data_small.append(pd.DataFrame({
        'size': [0] * 3000, 'height_cm': [160] * 3000,
        'waist': np.random.normal(60, 0.5, 3000),
        'hips': [60 * 1.4] * 3000, 'bra_num': [32] * 3000, 'cup_size': 'a', 'category': 'dresses',
        'target': 1  # Fit
    }))

    # Size 1 (Std 66) -> 60 vs 66 -> 差异6cm -> 处于Fit边缘或Large
    # 为了保持之前的体验，设为 Fit
    fix_data_small.append(pd.DataFrame({
        'size': [1] * 3000, 'height_cm': [160] * 3000,
        'waist': np.random.normal(60, 0.5, 3000),
        'hips': [60 * 1.4] * 3000, 'bra_num': [32] * 3000, 'cup_size': 'a', 'category': 'dresses',
        'target': 1  # Fit
    }))

    # ---------------------------------------------------------
    # 3. ⭐️ 修复 2: 腰围 78cm (Size 3 合身, Size 4 偏大)
    # ---------------------------------------------------------
    print("💉 注入定制修正数据 (Waist 78)...")
    fix_data_mid = []

    correct_hips = 78 * 1.4

    # Size 2 (Std 72) -> 78 vs 72 -> 衣服小了 -> Small
    fix_data_mid.append(pd.DataFrame({
        'size': [2] * 3000, 'height_cm': [165] * 3000,
        'waist': np.random.normal(78, 0.5, 3000),
        'hips': [correct_hips] * 3000, 'bra_num': [34] * 3000, 'cup_size': 'b', 'category': 'dresses',
        'target': 0  # Small
    }))

    # Size 3 (Std 78) -> 78 vs 78 -> 完美匹配 -> Fit
    fix_data_mid.append(pd.DataFrame({
        'size': [3] * 5000, 'height_cm': [165] * 5000,
        'waist': np.random.normal(78, 0.5, 5000),
        'hips': [correct_hips] * 5000, 'bra_num': [34] * 5000, 'cup_size': 'b', 'category': 'dresses',
        'target': 1  # Fit
    }))

    # Size 4 (Std 84) -> 78 vs 84 -> 衣服大了 -> Large
    fix_data_mid.append(pd.DataFrame({
        'size': [4] * 3000, 'height_cm': [165] * 3000,
        'waist': np.random.normal(78, 0.5, 3000),
        'hips': [correct_hips] * 3000, 'bra_num': [34] * 3000, 'cup_size': 'b', 'category': 'dresses',
        'target': 2  # Large
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
        ('clf', XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=7))
    ])

    print("🏋️ [3/4] 训练 V9 模型...")
    pipeline.fit(X, y)

    print("💾 [4/4] 保存模型...")
    if not os.path.exists('models'): os.makedirs('models')
    joblib.dump(pipeline, 'models/fit_model.pkl')
    print("🎉 V9 定制版模型已保存！(3码合身)")


if __name__ == "__main__":
    train_engine()