from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db_models import db, User, History, Feedback
from sqlalchemy import func, and_, or_
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

    feedback_total = Feedback.query.count()
    matched_feedback = db.session.query(func.count(Feedback.id)).join(
        History, Feedback.history_id == History.id
    ).filter(
        or_(
            and_(Feedback.fit_feedback == 'tight', History.result.like('%Small%')),
            and_(Feedback.fit_feedback == 'fit', History.result.like('%Fit%')),
            and_(Feedback.fit_feedback == 'loose', History.result.like('%Large%'))
        )
    ).scalar() or 0
    accuracy = round((matched_feedback / feedback_total) * 100, 2) if feedback_total > 0 else None

    # 将查询结果转换为前端 ECharts 所需的字典格式
    chart_data = [{"name": row[0], "value": row[1]} for row in results_stats]

    return jsonify({
        "code": 200,
        "data": {
            "total_users": total_registered_users,
            "prediction_distribution": chart_data,
            "feedback_accuracy": accuracy,
            "feedback_total": feedback_total,
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


@admin_bp.route('/users/<int:user_id>/details', methods=['GET'])
@jwt_required()
def get_user_detail(user_id):
    _, user = _get_admin_user()
    if not user or not user.is_admin:
        return jsonify({"code": 403, "msg": "权限不足，仅限管理员访问"}), 403

    target_user = db.session.get(User, user_id)
    if not target_user:
        return jsonify({"code": 404, "msg": "用户不存在"}), 404

    feedback_rows = db.session.query(Feedback, History).join(
        History, Feedback.history_id == History.id
    ).filter(
        Feedback.user_id == user_id
    ).order_by(Feedback.created_at.desc()).all()

    mismatch_list = []
    matched_count = 0
    for feedback, history in feedback_rows:
        predicted_key = 'unknown'
        if 'Small' in history.result:
            predicted_key = 'tight'
        elif 'Fit' in history.result:
            predicted_key = 'fit'
        elif 'Large' in history.result:
            predicted_key = 'loose'

        is_match = feedback.fit_feedback == predicted_key
        if is_match:
            matched_count += 1

        if not is_match:
            mismatch_list.append({
                "history_id": history.id,
                "prediction_result": history.result,
                "feedback_result": feedback.fit_feedback,
                "note": feedback.note,
                "category": history.category,
                "size_input": history.size_input,
                "created_at": feedback.created_at.strftime('%Y-%m-%d %H:%M')
            })

    feedback_total = len(feedback_rows)
    accuracy = round((matched_count / feedback_total) * 100, 2) if feedback_total > 0 else None

    return jsonify({
        "code": 200,
        "data": {
            "user_id": target_user.id,
            "username": target_user.username,
            "feedback_total": feedback_total,
            "feedback_accuracy": accuracy,
            "mismatch_feedbacks": mismatch_list
        }
    }), 200



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