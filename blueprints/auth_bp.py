from flask import Blueprint, request, jsonify, session
from auth import (
    login_user, logout_user, get_current_user, login_required,
    super_admin_required, change_password, log_operation, create_user
)
from models_v2 import get_db
from werkzeug.security import generate_password_hash
from datetime import datetime
import json

auth_bp = Blueprint('auth_bp', __name__)

# ==================== 认证相关 API ====================
@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """用户登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    success, message, user = login_user(username, password)

    if success:
        log_operation('用户登录', f'用户 {username} 登录成功')
        return jsonify({'message': message, 'user': user})
    else:
        return jsonify({'error': message}), 401

@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """用户登出"""
    username = session.get('username', '未知用户')
    success, message = logout_user()
    log_operation('用户登出', f'用户 {username} 退出登录', user_id=None)
    return jsonify({'message': message})

@auth_bp.route('/api/auth/current-user', methods=['GET'])
def api_current_user():
    """获取当前登录用户"""
    user = get_current_user()
    if user:
        return jsonify({'user': user})
    else:
        return jsonify({'user': None}), 401

@auth_bp.route('/api/auth/change-password', methods=['POST'])
@login_required
def api_change_password():
    """修改密码"""
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({'error': '旧密码和新密码不能为空'}), 400

    user_id = session['user_id']
    success, message = change_password(user_id, old_password, new_password)

    if success:
        log_operation('修改密码', '用户修改密码成功')
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

@auth_bp.route('/api/users', methods=['GET', 'POST'])
@super_admin_required
def api_users():
    """用户管理(仅管理员)"""
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'reporter')

        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400

        success, message, user_id = create_user(username, password, role)

        if success:
            log_operation('创建用户', f'创建用户 {username}, 角色:{role}')
            return jsonify({'message': message, 'user_id': user_id}), 201
        else:
            return jsonify({'error': message}), 400

    # GET请求 - 获取所有用户
    with get_db() as conn:
        users = conn.execute('SELECT id, username, role, created_at FROM users').fetchall()

        return jsonify([dict(user) for user in users])

@auth_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    """管理员修改用户角色或重置密码"""
    current_role = session.get('role')
    if current_role not in ['super_admin', 'admin']:
        return jsonify({'error': '权限不足'}), 403
    data = request.json
    with get_db() as conn:
        try:
            user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'error': '用户不存在'}), 404

            new_role = data.get('role')
            new_password = data.get('new_password')
            changes = []

            if new_role:
                if current_role != 'super_admin':
                    return jsonify({'error': '只有超级管理员可以修改角色'}), 403
                if new_role not in ['super_admin', 'admin', 'reviewer', 'reporter']:
                    return jsonify({'error': '角色参数错误'}), 400
                conn.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
                changes.append(f'角色改为{new_role}')

            if new_password:
                from werkzeug.security import generate_password_hash
                conn.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                            (generate_password_hash(new_password), user_id))
                changes.append('密码已重置')

            if changes:
                log_operation('修改用户', f'用户{user["username"]}: {", ".join(changes)}', conn=conn)

            return jsonify({'message': '、'.join(changes) if changes else '无修改'})
        except Exception as e:
            return jsonify({'error': f'操作失败: {str(e)}'}), 500
