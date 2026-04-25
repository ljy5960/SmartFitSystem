from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db_models import db, User, History, Feedback
from sqlalchemy import func
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def _get_admin_user():
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    return current_user_id, user


@admin_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    current_user_id, user = _get_admin_user()

    if not user or not user.is_admin:
        return jsonify({"code": 403, "msg": "权限不足，仅限管理员访问"}), 403

        # 仅统计普通注册用户（不含管理员账号）
    total_registered_users = User.query.filter_by(is_admin=False).count()

    # 3. 分组统计全站推荐结果分布 (Fit, Small, Large)
    results_stats = db.session.query(
        History.result,
        func.count(History.id)
    ).group_by(History.result).all()

    # 将查询结果转换为前端 ECharts 所需的字典格式
    chart_data = [{"name": row[0], "value": row[1]} for row in results_stats]

    return jsonify({
        "code": 200,
        "data": {
            "total_users": total_registered_users,
            "prediction_distribution": chart_data,
            "admin_id": current_user_id
        }
    })
@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    _, user = _get_admin_user()

    if not user or not user.is_admin:
        return jsonify({"code": 403, "msg": "权限不足，仅限管理员访问"}), 403

    history_count_subquery = db.session.query(
        History.user_id,
        func.count(History.id).label('history_count')
    ).group_by(History.user_id).subquery()

    users = db.session.query(
        User.id,
        User.username,
        User.is_admin,
        func.coalesce(history_count_subquery.c.history_count, 0).label('history_count')
    ).outerjoin(
        history_count_subquery, User.id == history_count_subquery.c.user_id
    ).order_by(User.id.asc()).all()

    user_list = [
        {
            "id": u.id,
            "username": u.username,
            "is_admin": u.is_admin,
            "history_count": int(u.history_count)
        }
        for u in users
    ]

    return jsonify({"code": 200, "data": {"users": user_list}}), 200


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user_id, admin_user = _get_admin_user()

    if not admin_user or not admin_user.is_admin:
        return jsonify({"code": 403, "msg": "权限不足，仅限管理员访问"}), 403

    if current_user_id == user_id:
        return jsonify({"code": 400, "msg": "不能删除当前登录的管理员账号"}), 400

    user_to_delete = db.session.get(User, user_id)
    if not user_to_delete:
        return jsonify({"code": 404, "msg": "用户不存在"}), 404

    try:
        history_ids_subquery = db.session.query(History.id).filter(History.user_id == user_id).subquery()

        db.session.query(Feedback).filter(
            (Feedback.user_id == user_id) | (Feedback.history_id.in_(history_ids_subquery))
        ).delete(synchronize_session=False)

        db.session.query(History).filter(History.user_id == user_id).delete(synchronize_session=False)
        db.session.delete(user_to_delete)
        db.session.commit()

        return jsonify({"code": 200, "msg": "用户及相关数据删除成功"}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"code": 500, "msg": "删除用户失败"}), 500