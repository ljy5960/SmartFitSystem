from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # 用户当前的身体数据缓存
    height = db.Column(db.Float, nullable=True)
    waist = db.Column(db.Float, nullable=True)
    hips = db.Column(db.Float, nullable=True)
    bra_size = db.Column(db.Float, nullable=True)
    cup_size = db.Column(db.String(5), nullable=True)

    history = db.relationship('History', backref='user', lazy=True)


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # 商品信息
    category = db.Column(db.String(50), nullable=False)
    size_input = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)

    # 预测结果
    result = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.String(10), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # --- 新增：记录当时的身体数据 (快照) ---
    height = db.Column(db.Float, nullable=True)
    waist = db.Column(db.Float, nullable=True)
    hips = db.Column(db.Float, nullable=True)
    bra_size = db.Column(db.Float, nullable=True)
    cup_size = db.Column(db.String(5), nullable=True)