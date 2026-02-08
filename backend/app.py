from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from db_models import db, User, History
import joblib
import pandas as pd
import numpy as np
import os
import traceback

app = Flask(__name__)

# --- 1. 配置项 ---
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'this-is-a-very-long-and-secure-secret-key-that-should-be-kept-hidden-and-safe'

db.init_app(app)
jwt = JWTManager(app)

# --- 2. 加载模型 ---
model_path = 'models/fit_model.pkl'
if os.path.exists(model_path):
    model = joblib.load(model_path)
    print(f"✅ 模型加载成功: {model_path}")
else:
    model = None
    print(f"❌ 警告: 模型未找到 ({model_path})，请先运行 train_model.py")


# --- 3. JWT 回调 ---
@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    return jsonify({'msg': f'无效的 Token: {error_string}'}), 422


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'msg': 'Token 已过期，请重新登录'}), 401


@jwt.unauthorized_loader
def missing_token_callback(error_string):
    return jsonify({'msg': '缺少 Token'}), 401


# --- 4. 辅助函数 ---
def get_category_image(category):
    if category == 'dresses':
        return "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop"
    elif category == 'tops':
        return "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=400&h=500&fit=crop"
    elif category == 'bottoms':
        return "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400&h=500&fit=crop"
    return "https://placehold.co/300x400?text=No+Image"


# --- 5. 路由接口 ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'msg': '用户名或密码不能为空'}), 400

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
        user_info = {
            'height': user.height,
            'waist': user.waist,
            'hips': user.hips,
            'bra_num': user.bra_size,
            'cup_size': user.cup_size
        }
        return jsonify({'token': token, 'user': user_info}), 200

    return jsonify({'msg': '用户名或密码错误'}), 401


# ... (保留前面的引用和配置)

@app.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    if not model:
        return jsonify({'msg': '后端模型未加载'}), 500

    try:
        current_user_id = int(get_jwt_identity())
        data = request.json

        # --- 数据提取 ---
        raw_h = data.get('height')
        h_val = float(raw_h) if raw_h is not None else 0.0

        raw_w = data.get('waist')
        w_val = float(raw_w) if raw_w is not None else 0.0

        # 🛠️ 核心修复：强制接管臀围逻辑 🛠️
        # 不管前端传没传 hips (通常是默认值 90)，我们都强制用腰围反推
        # 只有这样才能匹配 V11 模型的训练分布
        if w_val > 0:
            hips_val = w_val * 1.4
            print(f"✅ 强制修正臀围: {hips_val:.1f} (基于腰围 {w_val}, 忽略前端输入)")
        else:
            hips_val = float(data.get('hips') or 0)  # 只有腰围是0时才看前端

        raw_bra = data.get('bra_num')
        bra_val = float(raw_bra) if raw_bra is not None else 0.0

        raw_size = data.get('size')
        # 0值修复逻辑保留
        size_val = float(raw_size) if raw_size is not None else 6.0

        cup_val = data.get('cup_size', 'b')
        cat_val = data.get('category', 'dresses')

        # ... (后续代码保持不变，存入数据库等)
        # 1. 更新用户表 ...
        user = db.session.get(User, current_user_id)
        if user:
            user.height = h_val
            user.waist = w_val
            user.hips = hips_val
            user.bra_size = bra_val
            user.cup_size = cup_val
            db.session.commit()

        # 2. 计算 BMI ...
        bmi_val = w_val / h_val if h_val > 0 else 0

        # 3. 构建预测数据 ...
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

        # 4. 预测 ...
        probs = model.predict_proba(input_df)[0]
        pred_idx = int(np.argmax(probs))

        labels = ['偏小 (Small)', '合身 (Fit)', '偏大 (Large)']
        result_str = labels[pred_idx]

        prob_small = float(probs[0])
        prob_fit = float(probs[1])
        prob_large = float(probs[2])

        confidence_str = f"{prob_fit * 100:.1f}%"
        img_url = get_category_image(cat_val)

        # 5. 存入历史 ...
        new_history = History(
            user_id=current_user_id,
            category=cat_val,
            size_input=size_val,
            image_url=img_url,
            result=result_str,
            confidence=confidence_str,
            height=h_val,
            waist=w_val,
            hips=hips_val,  # 这里存的将是计算后的正确值 (如 126)
            bra_size=bra_val,
            cup_size=cup_val
        )
        db.session.add(new_history)
        db.session.commit()

        return jsonify({
            'result': result_str,
            'image_url': img_url,
            'probs': {
                'small': round(prob_small * 100, 1),
                'fit': round(prob_fit * 100, 1),
                'large': round(prob_large * 100, 1)
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'msg': f"预测服务出错: {str(e)}"}), 500


# ... (其余代码不变)


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