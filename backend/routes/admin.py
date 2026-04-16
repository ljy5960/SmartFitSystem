from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db_models import db, User, History
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    # 1. 获取当前用户并校验管理员权限
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user or not user.is_admin:
        return jsonify({"code": 403, "msg": "权限不足，仅限管理员访问"}), 403

    # 2. 统计系统总用户数
    total_users = User.query.count()

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
            "total_users": total_users,
            "prediction_distribution": chart_data
        }
    })