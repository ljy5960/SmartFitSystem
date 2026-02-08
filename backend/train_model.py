import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline


def train_engine():
    print("🚀 [1/4] 开始训练... (V14: 品类差异化容忍度版)")

    # ---------------------------------------------------------
    # 1. 定义核心逻辑生成器 (带容忍度参数)
    # ---------------------------------------------------------
    def generate_batch(category, n_per_combo=20):
        # --- 设定品类容忍度 ---
        if category == 'tops':
            tolerance = 7.0  # 上衣最宽容 (允许+7cm)
        elif category == 'dresses':
            tolerance = 6.0  # 连衣裙中等
        else:
            tolerance = 4.0  # 下装最严格 (只允许+4cm)

        data_list = []

        # 遍历尺码 0 到 18
        for s in range(19):
            # 遍历腰围 50 到 120
            for w in range(50, 121):

                # 标准公式: Size 0=60, Size 3=78
                std_waist = 60 + (s * 6.0)
                diff = w - std_waist

                # --- 差异化判定逻辑 ---
                target = 1  # 默认 Fit

                if diff > tolerance:
                    target = 0  # Small (人 > 衣服)
                elif diff < -tolerance:
                    target = 2  # Large (人 < 衣服)

                # 🛡️ 物理锁：0码和1码几乎不可能 "偏大"
                if target == 2 and s <= 1:
                    target = 1

                # --- 特征生成 ---
                # 上衣的臀围影响较小
                if category == 'tops':
                    hips_factor = np.random.uniform(1.2, 1.6)
                else:
                    hips_factor = 1.4

                base_bra = 32 + (s // 2) * 2

                batch = pd.DataFrame({
                    'size': [s] * n_per_combo,
                    'height_cm': np.random.uniform(155, 175, n_per_combo),
                    'waist': np.random.normal(w, 0.5, n_per_combo),
                    'hips': np.random.normal(w * hips_factor, 1.0, n_per_combo),
                    'bra_num': np.random.randint(base_bra, base_bra + 4, n_per_combo),
                    'cup_size': np.random.choice(['a', 'b', 'c', 'd'], n_per_combo),
                    'category': [category] * n_per_combo,
                    'target': target
                })
                data_list.append(batch)

        return pd.concat(data_list)

    # ---------------------------------------------------------
    # 2. 生成数据
    # ---------------------------------------------------------
    print("🧩 生成 Dresses (Tol=6)...")
    df_dresses = generate_batch('dresses')

    print("🧩 生成 Tops (Tol=7)...")
    df_tops = generate_batch('tops')

    print("🧩 生成 Bottoms (Tol=4)...")
    df_bottoms = generate_batch('bottoms')

    # ---------------------------------------------------------
    # 3. 💉 注入用户特例 (关键锚点)
    # ---------------------------------------------------------
    print("💉 注入特例锚点 (包含 Waist 66/Size 0 的差异化)...")

    anchors = []

    # 特例 1: Waist 66, Size 0 -> Tops=Fit, Bottoms=Small
    # Tops (Fit)
    anchors.append(pd.DataFrame({
        'size': [0] * 3000, 'waist': [66] * 3000, 'height_cm': [160] * 3000,
        'hips': [66 * 1.4] * 3000, 'bra_num': [32] * 3000, 'cup_size': 'b', 'category': 'tops', 'target': 1
    }))
    # Bottoms (Small)
    anchors.append(pd.DataFrame({
        'size': [0] * 3000, 'waist': [66] * 3000, 'height_cm': [160] * 3000,
        'hips': [66 * 1.4] * 3000, 'bra_num': [32] * 3000, 'cup_size': 'b', 'category': 'bottoms', 'target': 0
    }))

    # 特例 2: Waist 78, Size 3 -> All Fit (您的黄金标准)
    for cat in ['dresses', 'tops', 'bottoms']:
        anchors.append(pd.DataFrame({
            'size': [3] * 2000, 'waist': [78] * 2000, 'height_cm': [165] * 2000,
            'hips': [78 * 1.4] * 2000, 'bra_num': [34] * 2000, 'cup_size': 'b', 'category': cat, 'target': 1
        }))

    df_anchors = pd.concat(anchors)

    # ---------------------------------------------------------
    # 4. 合并与训练
    # ---------------------------------------------------------
    df_final = pd.concat([df_dresses, df_tops, df_bottoms, df_anchors], ignore_index=True)
    df_final['bmi_proxy'] = df_final['waist'] / df_final['height_cm']
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    features = ['cup_size', 'bra_num', 'hips', 'waist', 'category', 'size', 'height_cm', 'bmi_proxy']
    X = df_final[features]
    y = df_final['target']

    preprocessor = ColumnTransformer(transformers=[
        ('num', StandardScaler(), ['bra_num', 'hips', 'waist', 'size', 'height_cm', 'bmi_proxy']),
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['cup_size', 'category'])
    ])

    pipeline = Pipeline(steps=[
        ('pre', preprocessor),
        ('clf', XGBClassifier(n_estimators=500, learning_rate=0.05, max_depth=10))
    ])

    print("🏋️ [3/4] 训练 V14 模型...")
    pipeline.fit(X, y)

    print("💾 [4/4] 保存模型...")
    if not os.path.exists('models'): os.makedirs('models')
    joblib.dump(pipeline, 'models/fit_model.pkl')
    print("🎉 V14 模型已保存！(已启用差异化容忍度)")

    # --- 自测 ---
    print("\n🔍 --- 最终自测 (Waist 66, Size 0) ---")
    test_inputs = [
        {'cat': 'tops', 'exp': 'Fit'},  # 应该合身
        {'cat': 'bottoms', 'exp': 'Small'}  # 应该偏小
    ]
    labels = {0: 'Small', 1: 'Fit', 2: 'Large'}

    for t in test_inputs:
        row = pd.DataFrame({
            'cup_size': ['b'], 'bra_num': [32], 'hips': [66 * 1.4], 'waist': [66],
            'category': [t['cat']], 'size': [0], 'height_cm': [160], 'bmi_proxy': [66 / 160]
        })
        pred = pipeline.predict(row)[0]
        res = labels[pred]
        print(f"Category: {t['cat']:<8} -> {res} (Exp: {t['exp']})")


if __name__ == "__main__":
    train_engine()