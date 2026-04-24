from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from db_models import db, User, History, Feedback
from routes.admin import admin_bp
import joblib
import pandas as pd
import numpy as np
import os
import traceback
import json
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": ["http://localhost:8080", "http://127.0.0.1:8080"]}})
app.register_blueprint(admin_bp)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'smart-fit-super-secure-secret-key-2026-very-long'

db.init_app(app)
jwt = JWTManager(app)

model_path = 'models/fit_model.pkl'
if os.path.exists(model_path):
    model = joblib.load(model_path)
else:
    model = None

meta_path = 'models/fit_model_meta.json'
if os.path.exists(meta_path):
    with open(meta_path, 'r', encoding='utf-8') as f:
        model_meta = json.load(f)
else:
    model_meta = None


# --- 辅助功能 ---
def get_category_image(category):
    images = {
        'dresses': "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop",
        'tops': "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=400&h=500&fit=crop",
        'bottoms': "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400&h=500&fit=crop",
        'outerwear': "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400&h=500&fit=crop"
    }
    return images.get(category, "https://placehold.co/300x400?text=No+Image")


def get_size_recommendations(size_val):
    return {
        'slim': max(size_val - 1, 0),
        'regular': size_val,
        'relaxed': min(size_val + 1, 26)
    }


def _probs_to_percent(prob_arr):
    return {
        'small': round(float(prob_arr[0]) * 100, 1),
        'fit': round(float(prob_arr[1]) * 100, 1),
        'large': round(float(prob_arr[2]) * 100, 1)
    }


def _build_override_probs(pred_idx):
    # 规则覆盖时，返回与最终标签一致的概率分布，避免“标签与概率看起来冲突”
    epsilon = 0.005
    probs = [epsilon, epsilon, epsilon]
    probs[pred_idx] = 1.0 - 2 * epsilon
    return probs


def check_size_monotonicity(input_df, model_obj):
    # 只做轻量检查：size+1 后 small 概率不应显著上升
    cur_size = float(input_df['size'].iloc[0])
    if cur_size >= 26:
        return None

    next_df = input_df.copy()
    next_df.loc[0, 'size'] = min(cur_size + 1, 26)

    base_small = float(model_obj.predict_proba(input_df)[0][0])
    next_small = float(model_obj.predict_proba(next_df)[0][0])
    diff = round((next_small - base_small) * 100, 1)
    if diff > 8:
        return f"检测到 size+1 后偏小概率上升 {diff}%，建议结合推荐尺码阶梯再判断。"
    return None


def build_explainability(waist, size_val, category, confidence_level):
    std_waist_for_size = size_val * 1.5 + 60.0
    waist_delta = round(waist - std_waist_for_size, 1)

    if waist_delta >= 6:
        reason = f"你的腰围比该尺码经验腰围高 {waist_delta}cm，当前尺码可能偏紧。"
    elif waist_delta <= -6:
        reason = f"你的腰围比该尺码经验腰围低 {abs(waist_delta)}cm，当前尺码可能偏松。"
    else:
        reason = f"你的腰围与该尺码经验腰围差值约 {abs(waist_delta)}cm，整体匹配度较高。"

    guidance = "建议补充臀围/胸围信息以提高准确性。" if confidence_level == 'low' else "当前结果可信度较高，可直接参考推荐。"

    return {
        'top_factors': [
            {'factor': 'waist_delta_cm', 'value': waist_delta},
            {'factor': 'category', 'value': category},
            {'factor': 'size_input', 'value': size_val}
        ],
        'reason': reason,
        'guidance': guidance
    }


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


@app.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    if not model:
        return jsonify({'msg': '后端推理引擎未就绪'}), 500

    try:
        current_user_id = int(get_jwt_identity())
        data = request.json

        h_val = float(data.get('height', 0.0))
        w_val = float(data.get('waist', 0.0))
        bra_val = float(data.get('bra_num', 0.0))
        size_val = float(data.get('size', 6.0))
        cup_val = data.get('cup_size', 'b')
        cat_val = data.get('category', 'dresses')

        if h_val < 120 or h_val > 240:
            return jsonify({'msg': '身高范围异常，请输入 120~240cm'}), 400
        if w_val <= 0 or w_val > 180:
            return jsonify({'msg': '腰围范围异常，请输入 1~180cm'}), 400
        if size_val < 0 or size_val > 26:
            return jsonify({'msg': '尺码范围异常，请输入 0~26'}), 400

        raw_hips = data.get('hips')
        if raw_hips is not None and float(raw_hips) > 0:
            hips_val = float(raw_hips)
        elif w_val > 0:
            hips_val = w_val * 1.4
        else:
            hips_val = 0.0

        body_ratio_val = w_val / h_val if h_val > 0 else 0

        input_df = pd.DataFrame({
            'cup_size': [cup_val],
            'bra_num': [bra_val],
            'hips': [hips_val],
            'waist': [w_val],
            'category': [cat_val],
            'size': [size_val],
            'height_cm': [h_val],
            'body_ratio_proxy': [body_ratio_val]
        })

        probs = model.predict_proba(input_df)[0]
        consistency_warning = check_size_monotonicity(input_df, model)
        # 在 app.py 的 probs = model.predict_proba(input_df)[0] 下方添加：

        # 物理常识强制校验：
        std_waist_for_size = size_val * 1.5 + 60.0
        if w_val > std_waist_for_size + 10:
            # 用户腰围比当前尺码的标准腰围大 10cm 以上，衣服绝对是偏小的！
            pred_idx = 0
            max_prob = 0.99
            decision_source = 'physics_rule'
        elif w_val < std_waist_for_size - 10:
            # 用户腰围比当前尺码小 10cm 以上，衣服绝对是偏大的！
            pred_idx = 2  # 强行纠正为 偏大 (Large)
            max_prob = 0.99
            decision_source = 'physics_rule'
        else:
            # 正常范围内，听从 XGBoost 模型的判断
            pred_idx = int(np.argmax(probs))
            max_prob = float(probs[pred_idx])
            decision_source = 'ml_model'


        # labels = ['偏小 (Small)', '合身 (Fit)', '偏大 (Large)']
        # result_str = labels[pred_idx]
            # [架构升级] 字典硬绑定，防止模型类别索引漂移
        label_map = {
                0: '偏小 (Small)',
                1: '合身 (Fit)',
                2: '偏大 (Large)'
            }

            # 使用 .get() 方法，即使遇到未知的索引，不会让服务器崩溃报错
        result_str = label_map.get(pred_idx, '未知的合身度 (Unknown)')
        img_url = get_category_image(cat_val)

        new_history = History(
            user_id=current_user_id,
            category=cat_val,
            size_input=size_val,
            image_url=img_url,
            result=result_str,
            confidence=max_prob,
            height=h_val,
            waist=w_val,
            hips=hips_val,
            bra_size=bra_val,
            cup_size=cup_val
        )
        db.session.add(new_history)

        user = db.session.get(User, current_user_id)
        if user:
            user.height, user.waist, user.hips = h_val, w_val, hips_val
            user.bra_size, user.cup_size = bra_val, cup_val

        db.session.commit()

        confidence_level = 'low' if max_prob < 0.6 else 'high'
        explainability = build_explainability(w_val, size_val, cat_val, confidence_level)
        if consistency_warning:
            explainability['size_consistency_warning'] = consistency_warning
        size_recommendations = get_size_recommendations(size_val)
        final_probs = probs if decision_source == 'ml_model' else _build_override_probs(pred_idx)

        return jsonify({
            'result': result_str,
            'image_url': img_url,
            'probs': _probs_to_percent(final_probs),
            'raw_probs': _probs_to_percent(probs),
            'confidence_level': confidence_level,
            'decision_source': decision_source,
            'explainability': explainability,
            'size_recommendations': size_recommendations
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'msg': "预测服务内部异常"}), 500


@app.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    try:
        current_user_id = int(get_jwt_identity())
        histories = History.query.filter_by(user_id=current_user_id) \
            .order_by(History.timestamp.desc()).limit(50).all()

        result = []
        for h in histories:
            latest_feedback = Feedback.query.filter_by(history_id=h.id, user_id=current_user_id) \
                .order_by(Feedback.created_at.desc()).first()
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
                },
                'feedback': latest_feedback.fit_feedback if latest_feedback else None,
                'feedback_note': latest_feedback.note if latest_feedback else None
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
        db.session.query(Feedback).filter(Feedback.user_id == current_user_id).delete()
        db.session.commit()
        return jsonify({'msg': '已清空'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': '清除失败'}), 500


@app.route('/history/<int:history_id>/feedback', methods=['POST'])
@jwt_required()
def submit_feedback(history_id):
    try:
        current_user_id = int(get_jwt_identity())
        data = request.json or {}
        fit_feedback = data.get('fit_feedback')
        note = data.get('note')

        if fit_feedback not in {'tight', 'fit', 'loose'}:
            return jsonify({'msg': '反馈值非法，必须是 tight/fit/loose'}), 400

        history_item = History.query.filter_by(id=history_id, user_id=current_user_id).first()
        if not history_item:
            return jsonify({'msg': '未找到对应历史记录'}), 404

        feedback = Feedback(
            history_id=history_id,
            user_id=current_user_id,
            fit_feedback=fit_feedback,
            note=note
        )
        db.session.add(feedback)
        db.session.commit()
        return jsonify({'msg': '反馈已保存'}), 201
    except Exception:
        db.session.rollback()
        return jsonify({'msg': '保存反馈失败'}), 500


@app.route('/model/meta', methods=['GET'])
def get_model_meta():
    if not model_meta:
        return jsonify({'msg': '模型指标文件不存在，请先重新训练模型'}), 404
    return jsonify(model_meta), 200
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    is_debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=is_debug, port=5000)
