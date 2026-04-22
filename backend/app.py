from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from db_models import db, User, History
from routes.admin import admin_bp
import joblib
import pandas as pd
import numpy as np
import os
import traceback

app = Flask(__name__)

# --- 配置项 ---
CORS(app, resources={r"/*": {"origins": "*"}})
app.register_blueprint(admin_bp)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'smart-fit-super-secure-secret-key-2026-very-long'

db.init_app(app)
jwt = JWTManager(app)

# --- 加载模型 (单例驻留模式) ---
model_path = 'models/fit_model.pkl'
if os.path.exists(model_path):
    model = joblib.load(model_path)
    print(f"✅ 算法引擎加载成功: {model_path}")
else:
    model = None
    print(f"❌ 警告: 未找到训练好的模型，预测功能将受限")


# --- 辅助功能 ---
def get_category_image(category):
    images = {
        'dresses': "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop",
        'tops': "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=400&h=500&fit=crop",
        'bottoms': "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400&h=500&fit=crop",
        'outerwear': "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400&h=500&fit=crop"
    }
    return images.get(category, "https://placehold.co/300x400?text=No+Image")


# --- 注册登录逻辑 (省略，保持原样) ---
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'msg': '用户已存在'}), 400
    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'msg': '注册成功'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = create_access_token(identity=str(user.id))
        return jsonify({
            'token': token,
            'user': {'height': user.height, 'waist': user.waist},
            'is_admin': user.is_admin
        }), 200
    return jsonify({'msg': '用户名或密码错误'}), 401


# --- [核心] 智能推断接口 ---
@app.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    if not model:
        return jsonify({'msg': '后端推理引擎未就绪'}), 500

    try:
        current_user_id = int(get_jwt_identity())
        data = request.json

        # 数据预处理
        h_val = float(data.get('height', 0.0))
        w_val = float(data.get('waist', 0.0))
        bra_val = float(data.get('bra_num', 0.0))
        size_val = float(data.get('size', 6.0))
        cup_val = data.get('cup_size', 'b')
        cat_val = data.get('category', 'dresses')

        # [论文架构落地] 柔性业务兜底机制
        raw_hips = data.get('hips')
        if raw_hips is not None and float(raw_hips) > 0:
            hips_val = float(raw_hips)
        elif w_val > 0:
            # 前端未填时，通过人体工程学经验比例补全特征
            hips_val = w_val * 1.4
        else:
            hips_val = 0.0

        # 计算 BMI 代理因子
        bmi_val = w_val / h_val if h_val > 0 else 0

        # 构造推理 DataFrame
        input_df = pd.DataFrame({
            'cup_size': [cup_val],
            'bra_num': [bra_val],
            'hips': [hips_val],
            'waist': [w_val],
            'category': [cat_val],
            'size': [size_val],
            'height_cm': [h_val],
            'bmi_proxy': [bmi_val]
        })

        # 启动模型前向传播推理
        probs = model.predict_proba(input_df)[0]
        pred_idx = int(np.argmax(probs))
        max_prob = float(probs[pred_idx])  # 提取最大概率

        labels = ['偏小 (Small)', '合身 (Fit)', '偏大 (Large)']
        result_str = labels[pred_idx]
        img_url = get_category_image(cat_val)

        # [数据飞轮设计] 持久化推理快照
        new_history = History(
            user_id=current_user_id,
            category=cat_val,
            size_input=size_val,
            image_url=img_url,
            result=result_str,
            confidence=max_prob,  # 修正为 Float 存入数据库
            height=h_val,
            waist=w_val,
            hips=hips_val,
            bra_size=bra_val,
            cup_size=cup_val
        )
        db.session.add(new_history)

        # 同步更新用户信息缓存
        user = db.session.get(User, current_user_id)
        if user:
            user.height, user.waist, user.hips = h_val, w_val, hips_val
            user.bra_size, user.cup_size = bra_val, cup_val

        db.session.commit()

        return jsonify({
            'result': result_str,
            'image_url': img_url,
            'probs': {
                'small': round(float(probs[0]) * 100, 1),
                'fit': round(float(probs[1]) * 100, 1),
                'large': round(float(probs[2]) * 100, 1)
            },
            'confidence_level': 'low' if max_prob < 0.6 else 'high'
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'msg': "预测服务内部异常"}), 500


# 其他路由 (history/clear) 保持原样
@app.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    try:
        current_user_id = int(get_jwt_identity())
        histories = History.query.filter_by(user_id=current_user_id) \
            .order_by(History.timestamp.desc()).limit(50).all()

        result = []
        for h in histories:
            result.append({
                'id': h.id,
                'category': h.category,
                'size': h.size_input,
                'result': h.result,
                'confidence': h.confidence,
                'image_url': h.image_url,
                'date': h.timestamp.strftime('%Y-%m-%d %H:%M'),
                'body_data': {
                    'height': h.height,
                    'waist': h.waist,
                    'hips': h.hips,
                    'bra': h.bra_size,
                    'cup': h.cup_size
                }
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'msg': str(e)}), 500

@app.route('/history', methods=['DELETE'])
@jwt_required()
def clear_history():
    try:
        current_user_id = int(get_jwt_identity())
        db.session.query(History).filter(History.user_id == current_user_id).delete()
        db.session.commit()
        return jsonify({'msg': '已清空'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': '清除失败'}), 500
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)