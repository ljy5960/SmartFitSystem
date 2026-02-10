import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline


def train_engine():
    print("🚀 [1/4] 开始训练... (V15: 含外套 Outerwear 全品类版)")

    # ---------------------------------------------------------
    # 1. 定义核心逻辑生成器 (带容忍度参数)
    # ---------------------------------------------------------
    def generate_batch(category, n_per_combo=20):
        # --- 设定品类容忍度 ---
        if category == 'outerwear':
            tolerance = 8.0  # 🧥 外套：最宽容 (允许 ±8cm)
        elif category == 'tops':
            tolerance = 7.0  # 👚 上衣：宽容 (允许 ±7cm)
        elif category == 'dresses':
            tolerance = 6.0  # 👗 连衣裙：中等
        else:
            tolerance = 4.0  # 👖 下装：严格 (只允许 ±4cm)

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
                # 上衣和外套的臀围影响较小
                if category in ['tops', 'outerwear']:
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
    # 2. 生成数据 (四大品类)
    # ---------------------------------------------------------
    print("🧩 生成 Dresses (Tol=6)...")
    df_dresses = generate_batch('dresses')

    print("🧩 生成 Tops (Tol=7)...")
    df_tops = generate_batch('tops')

    print("🧩 生成 Bottoms (Tol=4)...")
    df_bottoms = generate_batch('bottoms')

    print("🧩 生成 Outerwear (Tol=8)...")  # ✅ 新增外套
    df_outerwear = generate_batch('outerwear')

    # ---------------------------------------------------------
    # 3. 💉 注入用户特例 (关键锚点)
    # ---------------------------------------------------------
    print("💉 注入特例锚点...")

    anchors = []

    # 特例: Waist 66, Size 0
    # Tops/Outerwear -> Fit (宽松)
    for cat in ['tops', 'outerwear']:
        anchors.append(pd.DataFrame({
            'size': [0] * 3000, 'waist': [66] * 3000, 'height_cm': [160] * 3000,
            'hips': [66 * 1.4] * 3000, 'bra_num': [32] * 3000, 'cup_size': 'b', 'category': cat, 'target': 1
        }))
    # Bottoms -> Small (严格)
    anchors.append(pd.DataFrame({
        'size': [0] * 3000, 'waist': [66] * 3000, 'height_cm': [160] * 3000,
        'hips': [66 * 1.4] * 3000, 'bra_num': [32] * 3000, 'cup_size': 'b', 'category': 'bottoms', 'target': 0
    }))

    # 特例: Waist 78, Size 3 -> All Fit
    for cat in ['dresses', 'tops', 'bottoms', 'outerwear']:
        anchors.append(pd.DataFrame({
            'size': [3] * 2000, 'waist': [78] * 2000, 'height_cm': [165] * 2000,
            'hips': [78 * 1.4] * 2000, 'bra_num': [34] * 2000, 'cup_size': 'b', 'category': cat, 'target': 1
        }))

    df_anchors = pd.concat(anchors)

    # ---------------------------------------------------------
    # 4. 合并与训练
    # ---------------------------------------------------------
    # ✅ 1. 先合并所有数据
    df_final = pd.concat([df_dresses, df_tops, df_bottoms, df_outerwear, df_anchors], ignore_index=True)

    # ✅ 2. 必须在合并后计算 BMI，否则新加入的 outerwear 会缺失这个列，导致报错！
    df_final['bmi_proxy'] = df_final['waist'] / df_final['height_cm']

    # 打乱数据
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
        ('clf', XGBClassifier(n_estimators=500, learning_rate=0.05, max_depth=10))
    ])

    print("🏋️ [3/4] 训练 V15 模型...")
    pipeline.fit(X, y)

    print("💾 [4/4] 保存模型...")
    if not os.path.exists('models'): os.makedirs('models')
    joblib.dump(pipeline, 'models/fit_model.pkl')
    print("🎉 V15 模型已保存！(含外套 Outerwear)")

    # --- 自测 ---
    print("\n🔍 --- 最终自测 (Waist 70, Size 0) ---")
    # 70cm 比 0码(60cm) 大 10cm
    # Bottoms/Dresses 应该 Small
    # Outerwear (Tol=8) 10>8 应该也是 Small，但如果是 Waist 68 (Diff=8) 就会是 Fit

    test_inputs = [
        {'cat': 'bottoms', 'w': 70, 'exp': 'Small'},
        {'cat': 'outerwear', 'w': 67, 'exp': 'Fit'},  # 67-60=7 < 8 (Fit)
    ]
    labels = {0: 'Small', 1: 'Fit', 2: 'Large'}

    for t in test_inputs:
        row = pd.DataFrame({
            'cup_size': ['b'], 'bra_num': [32], 'hips': [t['w'] * 1.4], 'waist': [t['w']],
            'category': [t['cat']], 'size': [0], 'height_cm': [160], 'bmi_proxy': [t['w'] / 160]
        })
        pred = pipeline.predict(row)[0]
        res = labels[pred]
        print(f"Category: {t['cat']:<9} | Waist: {t['w']} -> {res} (Exp: {t['exp']})")


if __name__ == "__main__":
    train_engine()