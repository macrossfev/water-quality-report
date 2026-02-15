"""
用户认证与授权模块
"""
from functools import wraps
from flask import session, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from models_v2 import get_db_connection
from datetime import datetime

def login_user(username, password):
    """
    用户登录
    :param username: 用户名
    :param password: 密码
    :return: (success: bool, message: str, user: dict or None)
    """
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?',
        (username,)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        # 登录成功,保存到session
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session.permanent = True  # 使session持久化

        return True, '登录成功', {
            'id': user['id'],
            'username': user['username'],
            'role': user['role']
        }
    else:
        return False, '用户名或密码错误', None

def logout_user():
    """用户登出"""
    session.clear()
    return True, '已退出登录'

def get_current_user():
    """
    获取当前登录用户
    :return: dict or None
    """
    if 'user_id' in session:
        return {
            'id': session['user_id'],
            'username': session['username'],
            'role': session['role']
        }
    return None

def login_required(f):
    """装饰器:要求用户登录"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """装饰器:要求管理员权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        if session.get('role') not in ['admin', 'super_admin']:
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        if session.get('role') != 'super_admin':
            return jsonify({'error': '需要超级管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function

def admin_or_above(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        if session.get('role') not in ['admin', 'super_admin']:
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function

def reviewer_or_above(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        if session.get('role') not in ['reviewer', 'super_admin']:
            return jsonify({'error': '需要审核权限'}), 403
        return f(*args, **kwargs)
    return decorated_function

def create_user(username, password, role='reporter'):
    """
    创建新用户(仅管理员可调用)
    :param username: 用户名
    :param password: 密码
    :param role: 角色 (admin/reporter)
    :return: (success: bool, message: str, user_id: int or None)
    """
    if role not in ['super_admin', 'admin', 'reviewer', 'reporter']:
        return False, '角色参数错误', None

    conn = get_db_connection()

    # 检查用户名是否已存在
    existing_user = conn.execute(
        'SELECT id FROM users WHERE username = ?',
        (username,)
    ).fetchone()

    if existing_user:
        conn.close()
        return False, '用户名已存在', None

    # 创建用户
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
        (username, generate_password_hash(password), role)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return True, '用户创建成功', user_id

def change_password(user_id, old_password, new_password):
    """
    修改密码
    :param user_id: 用户ID
    :param old_password: 旧密码
    :param new_password: 新密码
    :return: (success: bool, message: str)
    """
    conn = get_db_connection()

    user = conn.execute(
        'SELECT password_hash FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return False, '用户不存在'

    # 验证旧密码
    if not check_password_hash(user['password_hash'], old_password):
        conn.close()
        return False, '原密码错误'

    # 更新密码
    conn.execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (generate_password_hash(new_password), user_id)
    )
    conn.commit()
    conn.close()

    return True, '密码修改成功'

def log_operation(operation_type, operation_detail='', user_id=None, ip_address=None, conn=None):
    """
    记录操作日志
    :param operation_type: 操作类型
    :param operation_detail: 操作详情
    :param user_id: 用户ID(如果为None则从session获取)
    :param ip_address: IP地址(如果为None则从request获取)
    :param conn: 数据库连接(如果为None则创建新连接)
    """
    if user_id is None and 'user_id' in session:
        user_id = session['user_id']

    if ip_address is None:
        ip_address = request.remote_addr

    # 如果没有传入连接，则创建新连接
    own_conn = conn is None
    if own_conn:
        conn = get_db_connection()

    conn.execute(
        'INSERT INTO operation_logs (user_id, operation_type, operation_detail, ip_address, created_at) '
        'VALUES (?, ?, ?, ?, ?)',
        (user_id, operation_type, operation_detail, ip_address, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )

    # 只有我们自己创建的连接才需要commit和close
    if own_conn:
        conn.commit()
        conn.close()

def get_operation_logs(limit=100, offset=0, user_id=None, operation_type=None):
    """
    获取操作日志
    :param limit: 返回数量限制
    :param offset: 偏移量
    :param user_id: 筛选用户ID
    :param operation_type: 筛选操作类型
    :return: list of logs
    """
    conn = get_db_connection()

    query = '''
        SELECT ol.*, u.username
        FROM operation_logs ol
        LEFT JOIN users u ON ol.user_id = u.id
        WHERE 1=1
    '''
    params = []

    if user_id:
        query += ' AND ol.user_id = ?'
        params.append(user_id)

    if operation_type:
        query += ' AND ol.operation_type = ?'
        params.append(operation_type)

    query += ' ORDER BY ol.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    logs = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(log) for log in logs]
