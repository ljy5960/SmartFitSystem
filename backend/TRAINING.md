# 模型训练说明

## 训练命令
```bash
cd backend
python train_model.py
```

训练后会产出：
- `models/fit_model.pkl`：推理模型
- `models/fit_model_meta.json`：训练时间、数据量、准确率、F1、混淆矩阵

## 本次修复点
1. 去除了按 `target` 反向构造 `waist` 的逻辑（避免 label leakage）。
2. 使用 `train_test_split(..., stratify=y)` 做分层切分。
3. 保存评估指标，便于线上排查与回归对比。

## 线上查看
启动后端后可调用：
- `GET /model/meta`
