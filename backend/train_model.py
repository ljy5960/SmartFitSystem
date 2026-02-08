import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline


def train_engine():
    print("🚀 [1/4] 开始训练... (V10: 全矩阵网格训练版)")

    # ---------------------------------------------------------
    # 1. 构建全逻辑网格 (Grid Matrix)
    # ---------------------------------------------------------
    # 我们遍历所有可能的 腰围(60-100) 和 尺码(0-14) 组合
    # 彻底消除模型的“盲区”

    grid_data = []

    # 遍历尺码 0 到 14
    for s in range(15):
        # 遍历腰围 55 到 105 (步长 1cm)
        for w in range(55, 106):

            # --- 核心标准公式 (V9逻辑) ---
            # Size 0=60, Size 3=78 (每码差6cm)
            std_waist = 60 + (s * 6.0)

            diff = w - std_waist

            # 判定逻辑
            target = 1  # 默认 Fit

            if diff > 4:
                # 人比衣服大 4cm 以上 -> 衣服小了
                target = 0  # Small
            elif diff < -4:
                # 人比衣服小 4cm 以上 -> 衣服大了
                target = 2  # Large

            # --- 特殊物理锁 ---
            # Size 0 和 1 很难“偏大”(Large)，除非腰围极细(<55)
            # 如果判定为 Large 但 Size <= 1，强制纠正为 Fit (防止误判)
            if target == 2 and s <= 1:
                target = 1

            # 生成一批样本 (增加一点点随机扰动，防止过拟合)
            n_repeat = 50  # 每个点生成 50 条数据

            batch = pd.DataFrame({
                'size': [s] * n_repeat,
                'height_cm': [165] * n_repeat,  # 标准身高
                'waist': np.random.normal(w, 0.5, n_repeat),  # 紧贴网格点
                'hips': np.random.normal(w * 1.4, 1.0, n_repeat),  # 严格关联臀围
                'bra_num': [34] * n_repeat,
                'cup_size': 'b',
                'category': 'dresses',
                'target': target
            })
            grid_data.append(batch)

    print("🧩 网格构建完成，正在合并...")
    df_grid = pd.concat(grid_data)

    # ---------------------------------------------------------
    # 2. 加入背景噪音数据 (Background Noise)
    # ---------------------------------------------------------
    # 只有网格数据可能会太死板，加入一些随机数据增加泛化能力
    n_noise = 10000
    sizes_noise = np.random.randint(0, 15, n_noise)
    waist_noise = np.random.uniform(55, 105, n_noise)

    # 同样的逻辑打标
    std_waist_noise = 60 + (sizes_noise * 6.0)
    diff_noise = waist_noise - std_waist_noise
    targets_noise = np.where(diff_noise > 4, 0, np.where(diff_noise < -4, 2, 1))

    # 物理锁
    targets_noise = np.where((targets_noise == 2) & (sizes_noise <= 1), 1, targets_noise)

    df_noise = pd.DataFrame({
        'size': sizes_noise,
        'height_cm': np.random.normal(165, 5, n_noise),
        'waist': waist_noise,
        'hips': waist_noise * 1.4,  # 保持 hips 逻辑一致
        'bra_num': 34, 'cup_size': 'b', 'category': 'dresses',
        'target': targets_noise
    })

    # ---------------------------------------------------------
    # 3. 合并与训练
    # ---------------------------------------------------------
    df_final = pd.concat([df_grid, df_noise], ignore_index=True)

    # 计算 BMI
    df_final['bmi_proxy'] = df_final['waist'] / df_final['height_cm']
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"✅ 训练集准备完毕: {len(df_final)} 条 (覆盖所有逻辑组合)")

    features = ['cup_size', 'bra_num', 'hips', 'waist', 'category', 'size', 'height_cm', 'bmi_proxy']
    X = df_final[features]
    y = df_final['target']

    preprocessor = ColumnTransformer(transformers=[
        ('num', StandardScaler(), ['bra_num', 'hips', 'waist', 'size', 'height_cm', 'bmi_proxy']),
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['cup_size', 'category'])
    ])

    pipeline = Pipeline(steps=[
        ('pre', preprocessor),
        # 增加深度到 10，让决策树能完美拟合我们的网格逻辑
        ('clf', XGBClassifier(n_estimators=500, learning_rate=0.05, max_depth=10))
    ])

    print("🏋️ [3/4] 训练 V10 全矩阵模型...")
    pipeline.fit(X, y)

    print("💾 [4/4] 保存模型...")
    if not os.path.exists('models'): os.makedirs('models')
    joblib.dump(pipeline, 'models/fit_model.pkl')
    print("🎉 V10 模型已保存！")

    # --- 自测代码 ---
    print("\n🔍 --- 模型自测 (Self Check) ---")
    test_cases = [
        {'w': 60, 's': 0, 'exp': 'Fit'},
        {'w': 78, 's': 0, 'exp': 'Small'},  # 之前错在这里
        {'w': 78, 's': 1, 'exp': 'Small'},  # 之前错在这里
        {'w': 78, 's': 3, 'exp': 'Fit'},
        {'w': 78, 's': 4, 'exp': 'Large'},
    ]

    for case in test_cases:
        # 模拟 app.py 的输入构建
        input_row = pd.DataFrame({
            'cup_size': ['b'], 'bra_num': [34],
            'hips': [case['w'] * 1.4], 'waist': [case['w']],
            'category': ['dresses'], 'size': [case['s']],
            'height_cm': [165], 'bmi_proxy': [case['w'] / 165]
        })
        pred = pipeline.predict(input_row)[0]
        labels = {0: 'Small', 1: 'Fit', 2: 'Large'}
        res = labels[pred]
        status = "✅" if res == case['exp'] else "❌"
        print(f"Waist {case['w']} | Size {case['s']} -> Pred: {res} (Exp: {case['exp']}) {status}")


if __name__ == "__main__":
    train_engine()