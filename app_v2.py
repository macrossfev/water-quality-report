"""
水质检测报告系统 V2 - 主应用
支持模板管理、权限系统、多格式导出等功能
"""
from flask import Flask, render_template, request, jsonify, send_file, session
from models_v2 import get_db_connection, init_database, DATABASE_PATH
from auth import (
    login_user, logout_user, get_current_user, login_required, admin_required,
    create_user, change_password, log_operation, get_operation_logs
)
from datetime import datetime, timedelta
import json
import os
import shutil
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # 生产环境需修改
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session有效期7天

# 初始化数据库
init_database()

# ==================== 认证相关 API ====================
@app.route('/api/auth/login', methods=['POST'])
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

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """用户登出"""
    username = session.get('username', '未知用户')
    success, message = logout_user()
    log_operation('用户登出', f'用户 {username} 退出登录', user_id=None)
    return jsonify({'message': message})

@app.route('/api/auth/current-user', methods=['GET'])
def api_current_user():
    """获取当前登录用户"""
    user = get_current_user()
    if user:
        return jsonify({'user': user})
    else:
        return jsonify({'user': None}), 401

@app.route('/api/auth/change-password', methods=['POST'])
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

@app.route('/api/users', methods=['GET', 'POST'])
@admin_required
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
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role, created_at FROM users').fetchall()
    conn.close()

    return jsonify([dict(user) for user in users])

# ==================== 公司管理 API ====================
@app.route('/api/companies', methods=['GET', 'POST'])
@login_required
def api_companies():
    """公司管理"""
    conn = get_db_connection()

    if request.method == 'POST':
        data = request.json
        name = data.get('name')

        if not name:
            return jsonify({'error': '公司名称不能为空'}), 400

        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO companies (name) VALUES (?)', (name,))
            conn.commit()
            company_id = cursor.lastrowid

            log_operation('添加公司', f'添加公司: {name}', conn=conn)
            conn.close()

            return jsonify({'id': company_id, 'message': '公司添加成功'}), 201
        except Exception as e:
            conn.close()
            return jsonify({'error': '公司名称已存在'}), 400

    # GET请求
    companies = conn.execute('SELECT * FROM companies ORDER BY name').fetchall()
    conn.close()

    return jsonify([dict(company) for company in companies])

@app.route('/api/companies/<int:id>', methods=['PUT', 'DELETE'])
@admin_required
def api_company_detail(id):
    """公司详情操作"""
    conn = get_db_connection()

    if request.method == 'DELETE':
        company = conn.execute('SELECT name FROM companies WHERE id = ?', (id,)).fetchone()

        if not company:
            conn.close()
            return jsonify({'error': '公司不存在'}), 404

        conn.execute('DELETE FROM companies WHERE id = ?', (id,))
        conn.commit()

        log_operation('删除公司', f'删除公司: {company["name"]}', conn=conn)
        conn.close()

        return jsonify({'message': '公司删除成功'})

    if request.method == 'PUT':
        data = request.json
        name = data.get('name')

        if not name:
            conn.close()
            return jsonify({'error': '公司名称不能为空'}), 400

        try:
            conn.execute('UPDATE companies SET name = ? WHERE id = ?', (name, id))
            conn.commit()
            conn.close()

            log_operation('更新公司', f'更新公司: {name}')
            return jsonify({'message': '公司更新成功'})
        except Exception as e:
            conn.close()
            return jsonify({'error': '公司名称已存在'}), 400

# ==================== 样品类型管理 API ====================
@app.route('/api/sample-types', methods=['GET', 'POST'])
@login_required
def api_sample_types():
    """样品类型管理"""
    conn = get_db_connection()

    if request.method == 'POST':
        # 仅管理员可创建
        if session.get('role') != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.json
        name = data.get('name')
        code = data.get('code')
        description = data.get('description', '')
        remark = data.get('remark', '')

        if not name or not code:
            return jsonify({'error': '样品类型名称和代码不能为空'}), 400

        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sample_types (name, code, description, remark) VALUES (?, ?, ?, ?)',
                (name, code, description, remark)
            )
            conn.commit()
            sample_type_id = cursor.lastrowid
            conn.close()

            log_operation('添加样品类型', f'添加样品类型: {name} ({code})')
            return jsonify({'id': sample_type_id, 'message': '样品类型添加成功'}), 201
        except Exception as e:
            conn.close()
            return jsonify({'error': '样品类型名称或代码已存在'}), 400

    # GET请求 - 支持搜索
    search = request.args.get('search', '')

    if search:
        sample_types = conn.execute(
            'SELECT * FROM sample_types WHERE name LIKE ? OR remark LIKE ? ORDER BY created_at DESC',
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        sample_types = conn.execute('SELECT * FROM sample_types ORDER BY created_at DESC').fetchall()
    conn.close()

    return jsonify([dict(st) for st in sample_types])

@app.route('/api/sample-types/<int:id>', methods=['PUT', 'DELETE'])
@admin_required
def api_sample_type_detail(id):
    """样品类型详情操作"""
    conn = get_db_connection()

    if request.method == 'DELETE':
        sample_type = conn.execute('SELECT name FROM sample_types WHERE id = ?', (id,)).fetchone()

        if not sample_type:
            conn.close()
            return jsonify({'error': '样品类型不存在'}), 404

        conn.execute('DELETE FROM sample_types WHERE id = ?', (id,))
        conn.commit()

        log_operation('删除样品类型', f'删除样品类型: {sample_type["name"]}', conn=conn)
        conn.close()

        return jsonify({'message': '样品类型删除成功'})

    if request.method == 'PUT':
        data = request.json
        name = data.get('name')
        code = data.get('code')
        description = data.get('description', '')
        remark = data.get('remark', '')

        if not name or not code:
            return jsonify({'error': '样品类型名称和代码不能为空'}), 400

        try:
            conn.execute(
                'UPDATE sample_types SET name = ?, code = ?, description = ?, remark = ? WHERE id = ?',
                (name, code, description, remark, id)
            )
            conn.commit()
            conn.close()

            log_operation('更新样品类型', f'更新样品类型: {name} ({code})')
            return jsonify({'message': '样品类型更新成功'})
        except Exception as e:
            conn.close()
            return jsonify({'error': '样品类型名称或代码已存在'}), 400

# ==================== 检测项目分组管理 API ====================
@app.route('/api/indicator-groups', methods=['GET', 'POST'])
@login_required
def api_indicator_groups():
    """检测项目分组管理"""
    conn = get_db_connection()

    if request.method == 'POST':
        # 仅管理员可创建
        if session.get('role') != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.json
        name = data.get('name')
        sort_order = data.get('sort_order', 0)

        if not name:
            return jsonify({'error': '分组名称不能为空'}), 400

        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO indicator_groups (name, sort_order) VALUES (?, ?)',
                (name, sort_order)
            )
            conn.commit()
            group_id = cursor.lastrowid
            conn.close()

            log_operation('添加检测项目分组', f'添加分组: {name}')
            return jsonify({'id': group_id, 'message': '分组添加成功'}), 201
        except Exception as e:
            conn.close()
            return jsonify({'error': '分组名称已存在'}), 400

    # GET请求
    groups = conn.execute('SELECT * FROM indicator_groups ORDER BY sort_order, name').fetchall()
    conn.close()

    return jsonify([dict(group) for group in groups])

@app.route('/api/indicator-groups/<int:id>', methods=['PUT', 'DELETE'])
@admin_required
def api_indicator_group_detail(id):
    """检测项目分组详情操作"""
    conn = get_db_connection()

    if request.method == 'DELETE':
        group = conn.execute('SELECT name, is_system FROM indicator_groups WHERE id = ?', (id,)).fetchone()

        if not group:
            conn.close()
            return jsonify({'error': '分组不存在'}), 404

        # 检查是否为系统分组
        if group['is_system']:
            conn.close()
            return jsonify({'error': '系统分组不能删除'}), 403

        conn.execute('DELETE FROM indicator_groups WHERE id = ?', (id,))
        conn.commit()

        log_operation('删除检测项目分组', f'删除分组: {group["name"]}', conn=conn)
        conn.close()

        return jsonify({'message': '分组删除成功'})

    if request.method == 'PUT':
        data = request.json
        name = data.get('name')
        sort_order = data.get('sort_order', 0)

        if not name:
            return jsonify({'error': '分组名称不能为空'}), 400

        try:
            conn.execute(
                'UPDATE indicator_groups SET name = ?, sort_order = ? WHERE id = ?',
                (name, sort_order, id)
            )
            conn.commit()
            conn.close()

            log_operation('更新检测项目分组', f'更新分组: {name}')
            return jsonify({'message': '分组更新成功'})
        except Exception as e:
            conn.close()
            return jsonify({'error': '分组名称已存在'}), 400

# ==================== 检测指标管理 API ====================
@app.route('/api/indicators', methods=['GET', 'POST'])
@login_required
def api_indicators():
    """检测指标管理"""
    conn = get_db_connection()

    if request.method == 'POST':
        # 仅管理员可创建
        if session.get('role') != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.json
        group_id = data.get('group_id')
        name = data.get('name')
        unit = data.get('unit', '')
        default_value = data.get('default_value', '')
        limit_value = data.get('limit_value', '')
        detection_method = data.get('detection_method', '')
        description = data.get('description', '')
        remark = data.get('remark', '')
        sort_order = data.get('sort_order', 0)

        if not name:
            return jsonify({'error': '指标名称不能为空'}), 400

        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO indicators (group_id, name, unit, default_value, limit_value, detection_method, description, remark, sort_order) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (group_id, name, unit, default_value, limit_value, detection_method, description, remark, sort_order)
            )
            conn.commit()
            indicator_id = cursor.lastrowid

            log_operation('添加检测指标', f'添加指标: {name}', conn=conn)
            conn.close()

            return jsonify({'id': indicator_id, 'message': '指标添加成功'}), 201
        except Exception as e:
            conn.close()
            return jsonify({'error': '指标名称已存在'}), 400

    # GET请求 - 支持按分组筛选
    group_id = request.args.get('group_id')

    if group_id:
        indicators = conn.execute(
            'SELECT * FROM indicators WHERE group_id = ? ORDER BY sort_order, name',
            (group_id,)
        ).fetchall()
    else:
        indicators = conn.execute(
            'SELECT i.*, g.name as group_name FROM indicators i '
            'LEFT JOIN indicator_groups g ON i.group_id = g.id '
            'ORDER BY i.sort_order, i.name'
        ).fetchall()

    conn.close()

    return jsonify([dict(indicator) for indicator in indicators])

@app.route('/api/indicators/<int:id>', methods=['PUT', 'DELETE'])
@admin_required
def api_indicator_detail(id):
    """检测指标详情操作"""
    conn = get_db_connection()

    if request.method == 'DELETE':
        try:
            indicator = conn.execute('SELECT name FROM indicators WHERE id = ?', (id,)).fetchone()

            if not indicator:
                conn.close()
                return jsonify({'error': '指标不存在'}), 404

            # 检查是否被模板使用
            template_usage = conn.execute(
                'SELECT COUNT(*) as count FROM template_indicators WHERE indicator_id = ?',
                (id,)
            ).fetchone()

            if template_usage['count'] > 0:
                conn.close()
                return jsonify({'error': f'该指标正在被 {template_usage["count"]} 个模板使用，无法删除'}), 400

            # 检查是否被报告数据使用
            report_usage = conn.execute(
                'SELECT COUNT(*) as count FROM report_data WHERE indicator_id = ?',
                (id,)
            ).fetchone()

            if report_usage['count'] > 0:
                conn.close()
                return jsonify({'error': f'该指标已在 {report_usage["count"]} 份报告中使用，无法删除'}), 400

            # 执行删除
            conn.execute('DELETE FROM indicators WHERE id = ?', (id,))

            log_operation('删除检测指标', f'删除指标: {indicator["name"]}', conn=conn)
            conn.close()

            return jsonify({'message': '指标删除成功'})
        except Exception as e:
            conn.close()
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'删除失败: {str(e)}'}), 500

    if request.method == 'PUT':
        data = request.json
        group_id = data.get('group_id')
        name = data.get('name')
        unit = data.get('unit', '')
        default_value = data.get('default_value', '')
        limit_value = data.get('limit_value', '')
        detection_method = data.get('detection_method', '')
        description = data.get('description', '')
        remark = data.get('remark', '')
        sort_order = data.get('sort_order', 0)

        if not name:
            return jsonify({'error': '指标名称不能为空'}), 400

        try:
            conn.execute(
                'UPDATE indicators SET group_id = ?, name = ?, unit = ?, default_value = ?, limit_value = ?, detection_method = ?, '
                'description = ?, remark = ?, sort_order = ? WHERE id = ?',
                (group_id, name, unit, default_value, limit_value, detection_method, description, remark, sort_order, id)
            )
            conn.commit()

            log_operation('更新检测指标', f'更新指标: {name}', conn=conn)
            conn.close()

            return jsonify({'message': '指标更新成功'})
        except Exception as e:
            conn.close()
            return jsonify({'error': '指标名称已存在'}), 400

# ==================== 模板-检测项目关联 API ====================
@app.route('/api/template-indicators', methods=['GET', 'POST'])
@login_required
def api_template_indicators():
    """模板检测项目关联"""
    conn = get_db_connection()

    if request.method == 'POST':
        # 仅管理员可创建
        if session.get('role') != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.json
        sample_type_id = data.get('sample_type_id')
        indicator_id = data.get('indicator_id')
        is_required = data.get('is_required', False)
        sort_order = data.get('sort_order', 0)

        if not sample_type_id or not indicator_id:
            return jsonify({'error': '样品类型和检测指标不能为空'}), 400

        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO template_indicators (sample_type_id, indicator_id, is_required, sort_order) '
                'VALUES (?, ?, ?, ?)',
                (sample_type_id, indicator_id, is_required, sort_order)
            )
            conn.commit()
            ti_id = cursor.lastrowid

            log_operation('添加模板检测项', f'样品类型ID:{sample_type_id}, 指标ID:{indicator_id}', conn=conn)
            conn.close()

            return jsonify({'id': ti_id, 'message': '检测项目添加成功'}), 201
        except Exception as e:
            conn.close()
            return jsonify({'error': '该检测项目已存在于模板中'}), 400

    # GET请求 - 获取指定样品类型的检测项目
    sample_type_id = request.args.get('sample_type_id')

    if sample_type_id:
        template_indicators = conn.execute(
            'SELECT ti.*, i.name as indicator_name, i.unit, i.default_value, i.group_id, '
            'g.name as group_name '
            'FROM template_indicators ti '
            'LEFT JOIN indicators i ON ti.indicator_id = i.id '
            'LEFT JOIN indicator_groups g ON i.group_id = g.id '
            'WHERE ti.sample_type_id = ? '
            'ORDER BY g.sort_order, i.sort_order, ti.sort_order',
            (sample_type_id,)
        ).fetchall()
    else:
        template_indicators = conn.execute(
            'SELECT ti.*, i.name as indicator_name, st.name as sample_type_name '
            'FROM template_indicators ti '
            'LEFT JOIN indicators i ON ti.indicator_id = i.id '
            'LEFT JOIN sample_types st ON ti.sample_type_id = st.id '
            'ORDER BY ti.sample_type_id, ti.sort_order'
        ).fetchall()

    conn.close()

    return jsonify([dict(ti) for ti in template_indicators])

@app.route('/api/template-indicators/<int:id>', methods=['DELETE'])
@admin_required
def api_template_indicator_delete(id):
    """删除模板检测项目"""
    conn = get_db_connection()

    conn.execute('DELETE FROM template_indicators WHERE id = ?', (id,))
    conn.commit()

    log_operation('删除模板检测项', f'模板检测项ID:{id}', conn=conn)
    conn.close()

    return jsonify({'message': '检测项目删除成功'})

# ==================== 报告管理 API ====================
@app.route('/api/reports', methods=['GET', 'POST'])
@login_required
def api_reports():
    """报告管理"""
    conn = get_db_connection()

    if request.method == 'POST':
        data = request.json
        sample_number = data.get('sample_number')
        company_id = data.get('company_id')
        sample_type_id = data.get('sample_type_id')
        detection_person = data.get('detection_person', '')
        review_person = data.get('review_person', '')
        detection_date = data.get('detection_date')
        remark = data.get('remark', '')
        report_data_list = data.get('data', [])
        template_id = data.get('template_id')
        template_fields = data.get('template_fields', [])
        review_status = data.get('review_status', 'draft')  # 默认为草稿，可以是 'draft' 或 'pending'

        if not sample_number or not sample_type_id:
            return jsonify({'error': '样品编号和样品类型不能为空'}), 400

        # 生成报告编号
        sample_type = conn.execute(
            'SELECT code FROM sample_types WHERE id = ?',
            (sample_type_id,)
        ).fetchone()

        if not sample_type:
            conn.close()
            return jsonify({'error': '样品类型不存在'}), 404

        report_number = f"{sample_number}-{sample_type['code']}"

        # 检查报告编号是否已存在
        existing = conn.execute(
            'SELECT id FROM reports WHERE report_number = ?',
            (report_number,)
        ).fetchone()

        if existing:
            conn.close()
            return jsonify({'error': f'报告编号 {report_number} 已存在'}), 400

        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO reports (report_number, sample_number, company_id, sample_type_id, '
                'detection_person, review_person, detection_date, remark, template_id, review_status, created_by) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (report_number, sample_number, company_id, sample_type_id, detection_person,
                 review_person, detection_date, remark, template_id, review_status, session['user_id'])
            )
            conn.commit()
            report_id = cursor.lastrowid

            # 添加报告数据
            for item in report_data_list:
                if item.get('indicator_id'):
                    cursor.execute(
                        'INSERT INTO report_data (report_id, indicator_id, measured_value, remark) '
                        'VALUES (?, ?, ?, ?)',
                        (report_id, item['indicator_id'], item.get('measured_value', ''),
                         item.get('remark', ''))
                    )

            # 添加模板字段值
            for field in template_fields:
                if field.get('field_mapping_id') and field.get('field_value'):
                    cursor.execute(
                        'INSERT INTO report_field_values (report_id, field_mapping_id, field_value) '
                        'VALUES (?, ?, ?)',
                        (report_id, field['field_mapping_id'], field['field_value'])
                    )

            conn.commit()
            conn.close()

            status_text = '草稿' if review_status == 'draft' else '提交审核'
            log_operation('创建报告', f'报告编号:{report_number}, 状态:{status_text}')
            return jsonify({'id': report_id, 'report_number': report_number, 'message': '报告创建成功'}), 201
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 500

    # GET请求 - 支持搜索
    search_sample_number = request.args.get('sample_number', '')
    search_company_id = request.args.get('company_id', '')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))

    query = '''
        SELECT r.*, st.name as sample_type_name, c.name as company_name
        FROM reports r
        LEFT JOIN sample_types st ON r.sample_type_id = st.id
        LEFT JOIN companies c ON r.company_id = c.id
        WHERE 1=1
    '''
    params = []

    if search_sample_number:
        query += ' AND r.sample_number LIKE ?'
        params.append(f'%{search_sample_number}%')

    if search_company_id:
        query += ' AND r.company_id = ?'
        params.append(search_company_id)

    query += ' ORDER BY r.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    reports = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(report) for report in reports])

@app.route('/api/reports/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_report_detail(id):
    """报告详情"""
    conn = get_db_connection()

    if request.method == 'DELETE':
        # 仅创建人或管理员可删除
        report = conn.execute('SELECT created_by, generated_report_path FROM reports WHERE id = ?', (id,)).fetchone()

        if not report:
            conn.close()
            return jsonify({'error': '报告不存在'}), 404

        if session.get('role') != 'admin' and report['created_by'] != session['user_id']:
            conn.close()
            return jsonify({'error': '无权删除此报告'}), 403

        # 删除生成的报告文件（如果存在）
        if report['generated_report_path'] and os.path.exists(report['generated_report_path']):
            try:
                os.remove(report['generated_report_path'])
            except Exception as e:
                print(f"删除报告文件失败: {e}")

        conn.execute('DELETE FROM reports WHERE id = ?', (id,))
        conn.commit()

        log_operation('删除报告', f'报告ID:{id}', conn=conn)
        conn.close()

        return jsonify({'message': '报告删除成功'})

    if request.method == 'PUT':
        # 仅创建人或管理员可修改
        report = conn.execute('SELECT created_by, report_number FROM reports WHERE id = ?', (id,)).fetchone()

        if not report:
            conn.close()
            return jsonify({'error': '报告不存在'}), 404

        if session.get('role') != 'admin' and report['created_by'] != session['user_id']:
            conn.close()
            return jsonify({'error': '无权修改此报告'}), 403

        data = request.json
        company_id = data.get('company_id')
        detection_person = data.get('detection_person', '')
        review_person = data.get('review_person', '')
        detection_date = data.get('detection_date')
        remark = data.get('remark', '')
        report_data_list = data.get('data', [])
        template_fields = data.get('template_fields', [])

        try:
            cursor = conn.cursor()
            # 更新报告基本信息
            cursor.execute(
                'UPDATE reports SET company_id = ?, detection_person = ?, review_person = ?, '
                'detection_date = ?, remark = ? WHERE id = ?',
                (company_id, detection_person, review_person, detection_date, remark, id)
            )

            # 删除旧的报告数据
            cursor.execute('DELETE FROM report_data WHERE report_id = ?', (id,))

            # 插入新的报告数据
            for item in report_data_list:
                if item.get('indicator_id'):
                    cursor.execute(
                        'INSERT INTO report_data (report_id, indicator_id, measured_value, remark) '
                        'VALUES (?, ?, ?, ?)',
                        (id, item['indicator_id'], item.get('measured_value', ''),
                         item.get('remark', ''))
                    )

            # 删除旧的模板字段值
            cursor.execute('DELETE FROM report_field_values WHERE report_id = ?', (id,))

            # 插入新的模板字段值
            for field in template_fields:
                if field.get('field_mapping_id') and field.get('field_value'):
                    cursor.execute(
                        'INSERT INTO report_field_values (report_id, field_mapping_id, field_value) '
                        'VALUES (?, ?, ?)',
                        (id, field['field_mapping_id'], field['field_value'])
                    )

            conn.commit()
            conn.close()

            log_operation('更新报告', f'报告编号:{report["report_number"]}')
            return jsonify({'message': '报告更新成功'})
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 500

    # GET请求 - 获取报告详情
    report = conn.execute(
        'SELECT r.*, st.name as sample_type_name, st.code as sample_type_code, '
        'c.name as company_name, u.username as creator_name '
        'FROM reports r '
        'LEFT JOIN sample_types st ON r.sample_type_id = st.id '
        'LEFT JOIN companies c ON r.company_id = c.id '
        'LEFT JOIN users u ON r.created_by = u.id '
        'WHERE r.id = ?',
        (id,)
    ).fetchone()

    if not report:
        conn.close()
        return jsonify({'error': '报告不存在'}), 404

    # 获取报告数据
    data = conn.execute(
        'SELECT rd.*, i.name as indicator_name, i.unit, i.group_id, g.name as group_name '
        'FROM report_data rd '
        'LEFT JOIN indicators i ON rd.indicator_id = i.id '
        'LEFT JOIN indicator_groups g ON i.group_id = g.id '
        'WHERE rd.report_id = ? '
        'ORDER BY g.sort_order, i.sort_order',
        (id,)
    ).fetchall()

    # 获取模板字段值
    template_fields = []
    if report['template_id']:
        template_fields = conn.execute('''
            SELECT rfv.*, tfm.field_name, tfm.field_display_name
            FROM report_field_values rfv
            LEFT JOIN template_field_mappings tfm ON rfv.field_mapping_id = tfm.id
            WHERE rfv.report_id = ?
        ''', (id,)).fetchall()

    conn.close()

    result = dict(report)
    result['data'] = [dict(row) for row in data]
    result['template_fields'] = [dict(row) for row in template_fields]
    return jsonify(result)

# ==================== 模板导入导出 API ====================
@app.route('/api/templates/export', methods=['POST'])
@admin_required
def api_export_template():
    """导出模板JSON"""
    data = request.json
    sample_type_id = data.get('sample_type_id')

    if not sample_type_id:
        return jsonify({'error': '样品类型ID不能为空'}), 400

    conn = get_db_connection()

    # 获取样品类型信息
    sample_type = conn.execute(
        'SELECT * FROM sample_types WHERE id = ?',
        (sample_type_id,)
    ).fetchone()

    if not sample_type:
        conn.close()
        return jsonify({'error': '样品类型不存在'}), 404

    # 获取关联的检测项目
    template_indicators = conn.execute(
        'SELECT ti.*, i.name as indicator_name, i.unit, i.default_value, i.group_id, '
        'g.name as group_name '
        'FROM template_indicators ti '
        'LEFT JOIN indicators i ON ti.indicator_id = i.id '
        'LEFT JOIN indicator_groups g ON i.group_id = g.id '
        'WHERE ti.sample_type_id = ?',
        (sample_type_id,)
    ).fetchall()

    conn.close()

    # 构建导出数据
    export_data = {
        'sample_type': dict(sample_type),
        'indicators': [dict(ti) for ti in template_indicators],
        'export_date': datetime.now().isoformat(),
        'version': '2.0'
    }

    # 保存JSON文件
    os.makedirs('exports', exist_ok=True)
    filename = f"exports/template_{sample_type['code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    log_operation('导出模板', f'导出模板: {sample_type["name"]}')
    return send_file(filename, as_attachment=True, download_name=f"template_{sample_type['code']}.json")

@app.route('/api/templates/import', methods=['POST'])
@admin_required
def api_import_template():
    """导入模板JSON"""
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    try:
        content = file.read().decode('utf-8')
        data = json.loads(content)

        sample_type_data = data.get('sample_type')
        indicators_data = data.get('indicators', [])

        if not sample_type_data:
            return jsonify({'error': 'JSON格式错误:缺少sample_type'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查样品类型是否已存在
        existing = cursor.execute(
            'SELECT id FROM sample_types WHERE code = ?',
            (sample_type_data['code'],)
        ).fetchone()

        if existing:
            conn.close()
            return jsonify({'error': f'样品类型代码 {sample_type_data["code"]} 已存在'}), 400

        # 创建样品类型
        cursor.execute(
            'INSERT INTO sample_types (name, code, description) VALUES (?, ?, ?)',
            (sample_type_data['name'], sample_type_data['code'], sample_type_data.get('description', ''))
        )
        conn.commit()
        sample_type_id = cursor.lastrowid

        # 导入检测项目(需要匹配现有的indicator)
        imported_count = 0
        for item in indicators_data:
            # 查找匹配的indicator
            indicator = cursor.execute(
                'SELECT id FROM indicators WHERE name = ?',
                (item['indicator_name'],)
            ).fetchone()

            if indicator:
                try:
                    cursor.execute(
                        'INSERT INTO template_indicators (sample_type_id, indicator_id, is_required, sort_order) '
                        'VALUES (?, ?, ?, ?)',
                        (sample_type_id, indicator['id'], item.get('is_required', False), item.get('sort_order', 0))
                    )
                    imported_count += 1
                except:
                    pass  # 忽略重复项

        conn.commit()
        conn.close()

        log_operation('导入模板', f'导入模板: {sample_type_data["name"]}, 检测项:{imported_count}')
        return jsonify({
            'message': f'模板导入成功,共导入 {imported_count} 个检测项目',
            'sample_type_id': sample_type_id
        })

    except json.JSONDecodeError:
        return jsonify({'error': 'JSON格式错误'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 报告导出 API ====================
@app.route('/api/reports/<int:id>/export/excel', methods=['GET'])
@login_required
def api_export_excel(id):
    """导出Excel报告"""
    conn = get_db_connection()

    report = conn.execute(
        'SELECT r.*, st.name as sample_type_name, c.name as company_name '
        'FROM reports r '
        'LEFT JOIN sample_types st ON r.sample_type_id = st.id '
        'LEFT JOIN companies c ON r.company_id = c.id '
        'WHERE r.id = ?',
        (id,)
    ).fetchone()

    if not report:
        conn.close()
        return jsonify({'error': '报告不存在'}), 404

    data = conn.execute(
        'SELECT rd.*, i.name as indicator_name, i.unit, g.name as group_name '
        'FROM report_data rd '
        'LEFT JOIN indicators i ON rd.indicator_id = i.id '
        'LEFT JOIN indicator_groups g ON i.group_id = g.id '
        'WHERE rd.report_id = ? '
        'ORDER BY g.sort_order, i.sort_order',
        (id,)
    ).fetchall()

    conn.close()

    # 创建Excel工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "水质检测报告"

    # 设置样式
    title_font = Font(name='宋体', size=16, bold=True)
    header_font = Font(name='宋体', size=11, bold=True)
    normal_font = Font(name='宋体', size=10)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 标题
    ws.merge_cells('A1:G1')
    title_cell = ws['A1']
    title_cell.value = '水质检测报告'
    title_cell.font = title_font
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30

    # 报告信息
    row = 3
    info_items = [
        ('报告编号', report['report_number']),
        ('样品编号', report['sample_number']),
        ('样品类型', report['sample_type_name']),
        ('委托单位', report['company_name']),
        ('检测日期', report['detection_date']),
        ('检测人员', report['detection_person']),
        ('审核人员', report['review_person'])
    ]

    for label, value in info_items:
        if value:
            ws[f'A{row}'] = label + '：'
            ws[f'B{row}'] = value
            ws[f'A{row}'].font = header_font
            ws.merge_cells(f'B{row}:G{row}')
            row += 1

    row += 1

    # 表头
    headers = ['序号', '检测项目', '单位', '检测结果', '所属分组', '备注']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # 数据行
    for idx, item in enumerate(data, start=1):
        row += 1
        row_data = [
            idx,
            item['indicator_name'],
            item['unit'] or '',
            item['measured_value'] or '',
            item['group_name'] or '',
            item['remark'] or ''
        ]

        for col, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row, column=col)
            cell.value = value
            cell.font = normal_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

    # 调整列宽
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 20

    # 保存文件
    os.makedirs('exports', exist_ok=True)
    filename = f"exports/report_{report['report_number']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    wb.save(filename)

    log_operation('导出Excel报告', f'报告编号:{report["report_number"]}')
    return send_file(filename, as_attachment=True, download_name=f"{report['report_number']}.xlsx")

@app.route('/api/reports/<int:id>/export-simple', methods=['GET'])
@login_required
def api_export_simple_report(id):
    """使用简化模式导出报告"""
    from report_generator import generate_simple_report

    try:
        output_path = generate_simple_report(id)
        log_operation('导出简化报告', f'报告ID: {id}')
        return send_file(output_path, as_attachment=True, download_name=os.path.basename(output_path))
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500

@app.route('/api/reports/<int:id>/export/word', methods=['GET'])
@login_required
def api_export_word(id):
    """导出Word报告"""
    conn = get_db_connection()

    report = conn.execute(
        'SELECT r.*, st.name as sample_type_name, c.name as company_name '
        'FROM reports r '
        'LEFT JOIN sample_types st ON r.sample_type_id = st.id '
        'LEFT JOIN companies c ON r.company_id = c.id '
        'WHERE r.id = ?',
        (id,)
    ).fetchone()

    if not report:
        conn.close()
        return jsonify({'error': '报告不存在'}), 404

    data = conn.execute(
        'SELECT rd.*, i.name as indicator_name, i.unit, g.name as group_name '
        'FROM report_data rd '
        'LEFT JOIN indicators i ON rd.indicator_id = i.id '
        'LEFT JOIN indicator_groups g ON i.group_id = g.id '
        'WHERE rd.report_id = ? '
        'ORDER BY g.sort_order, i.sort_order',
        (id,)
    ).fetchall()

    conn.close()

    # 创建Word文档
    doc = Document()

    # 标题
    title = doc.add_heading('水质检测报告', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 报告信息
    info_items = [
        ('报告编号', report['report_number']),
        ('样品编号', report['sample_number']),
        ('样品类型', report['sample_type_name']),
        ('委托单位', report['company_name'] or ''),
        ('检测日期', report['detection_date'] or ''),
        ('检测人员', report['detection_person'] or ''),
        ('审核人员', report['review_person'] or '')
    ]

    for label, value in info_items:
        if value:
            p = doc.add_paragraph()
            p.add_run(f'{label}：').bold = True
            p.add_run(value)

    doc.add_paragraph()

    # 创建表格
    table = doc.add_table(rows=1, cols=6)
    table.style = 'Light Grid Accent 1'

    # 表头
    headers = ['序号', '检测项目', '单位', '检测结果', '所属分组', '备注']
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        cell.text = header
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 数据行
    for idx, item in enumerate(data, start=1):
        row = table.add_row()
        row.cells[0].text = str(idx)
        row.cells[1].text = item['indicator_name']
        row.cells[2].text = item['unit'] or ''
        row.cells[3].text = item['measured_value'] or ''
        row.cells[4].text = item['group_name'] or ''
        row.cells[5].text = item['remark'] or ''

        for cell in row.cells:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 保存文件
    os.makedirs('exports', exist_ok=True)
    filename = f"exports/report_{report['report_number']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    doc.save(filename)

    log_operation('导出Word报告', f'报告编号:{report["report_number"]}')
    return send_file(filename, as_attachment=True, download_name=f"{report['report_number']}.docx")

# ==================== 检测指标导入导出 API ====================
@app.route('/api/indicators/export/excel', methods=['GET'])
@admin_required
def api_export_indicators_excel():
    """导出检测指标到Excel"""
    conn = get_db_connection()

    indicators = conn.execute(
        'SELECT i.*, g.name as group_name '
        'FROM indicators i '
        'LEFT JOIN indicator_groups g ON i.group_id = g.id '
        'ORDER BY i.sort_order, i.name'
    ).fetchall()

    # 关闭连接释放锁
    conn.close()

    # 创建Excel工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "检测指标"

    # 设置样式
    header_font = Font(name='宋体', size=11, bold=True)
    normal_font = Font(name='宋体', size=10)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 表头
    headers = ['指标名称', '单位', '默认值', '限值', '检测方法', '所属分组', '排序', '备注']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # 数据行
    for row_idx, indicator in enumerate(indicators, start=2):
        row_data = [
            indicator['name'],
            indicator['unit'] or '',
            indicator['default_value'] or '',
            indicator['limit_value'] or '',
            indicator['detection_method'] or '',
            indicator['group_name'] or '',
            indicator['sort_order'],
            indicator['remark'] or ''
        ]

        for col, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col)
            cell.value = value
            cell.font = normal_font
            cell.border = border

    # 调整列宽
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 25
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 10
    ws.column_dimensions['H'].width = 30

    # 保存文件
    os.makedirs('exports', exist_ok=True)
    filename = f"exports/indicators_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    wb.save(filename)

    log_operation('导出检测指标', f'导出 {len(indicators)} 个检测指标')

    return send_file(filename, as_attachment=True, download_name='检测指标.xlsx')

@app.route('/api/indicators/import/excel', methods=['POST'])
@admin_required
def api_import_indicators_excel():
    """从Excel导入检测指标"""
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': '请上传Excel文件(.xlsx 或 .xls)'}), 400

    try:
        # 读取Excel文件
        wb = openpyxl.load_workbook(file)
        ws = wb.active

        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取所有分组，建立名称到ID的映射
        groups = cursor.execute('SELECT id, name FROM indicator_groups').fetchall()
        group_map = {g['name']: g['id'] for g in groups}

        imported_count = 0
        updated_count = 0
        error_rows = []

        # 从第2行开始读取（第1行是表头）
        # 新格式：指标名称、单位、默认值、限值、检测方法、所属分组、排序、备注
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[0]:  # 跳过空行
                continue

            name = row[0]
            unit = row[1] or ''
            default_value = row[2] or ''
            limit_value = row[3] or '' if len(row) > 3 else ''
            detection_method = row[4] or '' if len(row) > 4 else ''
            group_name = row[5] or '' if len(row) > 5 else ''
            sort_order = row[6] if len(row) > 6 and row[6] is not None else 0
            remark = row[7] or '' if len(row) > 7 else ''

            # 查找分组ID
            group_id = group_map.get(group_name) if group_name else None

            try:
                # 检查指标是否已存在
                existing = cursor.execute('SELECT id FROM indicators WHERE name = ?', (name,)).fetchone()

                if existing:
                    # 更新现有指标
                    cursor.execute(
                        'UPDATE indicators SET group_id = ?, unit = ?, default_value = ?, limit_value = ?, '
                        'detection_method = ?, remark = ?, sort_order = ? WHERE name = ?',
                        (group_id, unit, default_value, limit_value, detection_method, remark, sort_order, name)
                    )
                    updated_count += 1
                else:
                    # 插入新指标
                    cursor.execute(
                        'INSERT INTO indicators (group_id, name, unit, default_value, limit_value, detection_method, remark, sort_order) '
                        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (group_id, name, unit, default_value, limit_value, detection_method, remark, sort_order)
                    )
                    imported_count += 1
            except Exception as e:
                error_rows.append(f'第{row_idx}行: {str(e)}')

        conn.commit()
        conn.close()

        log_operation('导入检测指标', f'新增 {imported_count} 个，更新 {updated_count} 个')

        result = {
            'message': f'导入成功！新增 {imported_count} 个指标，更新 {updated_count} 个指标',
            'imported': imported_count,
            'updated': updated_count
        }

        if error_rows:
            result['errors'] = error_rows

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

# ==================== 样品类型导入导出 API ====================
@app.route('/api/sample-types/export/excel', methods=['GET'])
@admin_required
def api_export_sample_types_excel():
    """导出样品类型到Excel"""
    conn = get_db_connection()

    sample_types = conn.execute('SELECT * FROM sample_types ORDER BY created_at DESC').fetchall()

    conn.close()

    # 创建Excel工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "样品类型"

    # 设置样式
    header_font = Font(name='宋体', size=11, bold=True)
    normal_font = Font(name='宋体', size=10)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 表头
    headers = ['样品类型名称', '样品代码', '说明']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # 数据行
    for row_idx, sample_type in enumerate(sample_types, start=2):
        row_data = [
            sample_type['name'],
            sample_type['code'],
            sample_type['description'] or ''
        ]

        for col, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col)
            cell.value = value
            cell.font = normal_font
            cell.border = border

    # 调整列宽
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 40

    # 保存文件
    os.makedirs('exports', exist_ok=True)
    filename = f"exports/sample_types_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    wb.save(filename)

    log_operation('导出样品类型', f'导出 {len(sample_types)} 个样品类型')
    return send_file(filename, as_attachment=True, download_name='样品类型.xlsx')

@app.route('/api/sample-types/import/excel', methods=['POST'])
@admin_required
def api_import_sample_types_excel():
    """从Excel导入样品类型"""
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': '请上传Excel文件(.xlsx 或 .xls)'}), 400

    try:
        # 读取Excel文件
        wb = openpyxl.load_workbook(file)
        ws = wb.active

        conn = get_db_connection()
        cursor = conn.cursor()

        imported_count = 0
        updated_count = 0
        error_rows = []

        # 从第2行开始读取（第1行是表头）
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[0]:  # 跳过空行
                continue

            name = row[0]
            code = row[1]
            description = row[2] or ''

            if not code:
                error_rows.append(f'第{row_idx}行: 样品代码不能为空')
                continue

            try:
                # 检查样品类型是否已存在（通过代码）
                existing = cursor.execute('SELECT id FROM sample_types WHERE code = ?', (code,)).fetchone()

                if existing:
                    # 更新现有样品类型
                    cursor.execute(
                        'UPDATE sample_types SET name = ?, description = ? WHERE code = ?',
                        (name, description, code)
                    )
                    updated_count += 1
                else:
                    # 插入新样品类型
                    cursor.execute(
                        'INSERT INTO sample_types (name, code, description) VALUES (?, ?, ?)',
                        (name, code, description)
                    )
                    imported_count += 1
            except Exception as e:
                error_rows.append(f'第{row_idx}行: {str(e)}')

        conn.commit()
        conn.close()

        log_operation('导入样品类型', f'新增 {imported_count} 个，更新 {updated_count} 个')

        result = {
            'message': f'导入成功！新增 {imported_count} 个样品类型，更新 {updated_count} 个样品类型',
            'imported': imported_count,
            'updated': updated_count
        }

        if error_rows:
            result['errors'] = error_rows

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

# ==================== 报告批量导入 API ====================
@app.route('/api/reports/import/excel', methods=['POST'])
@login_required
def api_import_reports_excel():
    """从Excel批量导入报告"""
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': '请上传Excel文件(.xlsx 或 .xls)'}), 400

    try:
        # 读取Excel文件
        wb = openpyxl.load_workbook(file)
        ws = wb.active

        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取样品类型映射
        sample_types = cursor.execute('SELECT id, name, code FROM sample_types').fetchall()
        sample_type_name_map = {st['name']: st for st in sample_types}
        sample_type_code_map = {st['code']: st for st in sample_types}

        # 获取公司映射
        companies = cursor.execute('SELECT id, name FROM companies').fetchall()
        company_map = {c['name']: c['id'] for c in companies}

        # 获取检测指标映射
        indicators = cursor.execute('SELECT id, name FROM indicators').fetchall()
        indicator_map = {i['name']: i['id'] for i in indicators}

        imported_count = 0
        error_rows = []

        # 读取表头（第1行）
        headers = [cell.value for cell in ws[1]]

        # 查找固定列的索引
        try:
            sample_number_idx = headers.index('样品编号')
            sample_type_idx = headers.index('样品类型')
        except ValueError:
            return jsonify({'error': 'Excel格式错误：必须包含"样品编号"和"样品类型"列'}), 400

        # 可选列
        company_idx = headers.index('委托单位') if '委托单位' in headers else None
        detection_date_idx = headers.index('检测日期') if '检测日期' in headers else None
        detection_person_idx = headers.index('检测人员') if '检测人员' in headers else None
        review_person_idx = headers.index('审核人员') if '审核人员' in headers else None
        remark_idx = headers.index('备注') if '备注' in headers else None

        # 检测指标列（除了固定列之外的列都视为检测指标）
        fixed_cols = {'样品编号', '样品类型', '委托单位', '检测日期', '检测人员', '审核人员', '备注'}
        indicator_cols = [(idx, col) for idx, col in enumerate(headers) if col and col not in fixed_cols]

        # 从第2行开始读取数据
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[sample_number_idx]:  # 跳过空行
                continue

            try:
                sample_number = str(row[sample_number_idx]).strip()
                sample_type_value = str(row[sample_type_idx]).strip()

                # 查找样品类型（支持名称或代码）
                sample_type = sample_type_name_map.get(sample_type_value) or sample_type_code_map.get(sample_type_value)

                if not sample_type:
                    error_rows.append(f'第{row_idx}行: 样品类型"{sample_type_value}"不存在')
                    continue

                sample_type_id = sample_type['id']

                # 获取其他字段
                company_id = None
                if company_idx is not None and row[company_idx]:
                    company_name = str(row[company_idx]).strip()
                    company_id = company_map.get(company_name)
                    if not company_id and company_name:
                        # 自动创建公司
                        cursor.execute('INSERT INTO companies (name) VALUES (?)', (company_name,))
                        conn.commit()
                        company_id = cursor.lastrowid
                        company_map[company_name] = company_id

                detection_person = str(row[detection_person_idx]).strip() if detection_person_idx is not None and row[detection_person_idx] else ''
                review_person = str(row[review_person_idx]).strip() if review_person_idx is not None and row[review_person_idx] else ''
                detection_date = str(row[detection_date_idx]) if detection_date_idx is not None and row[detection_date_idx] else None
                remark = str(row[remark_idx]).strip() if remark_idx is not None and row[remark_idx] else ''

                # 生成报告编号
                report_number = f"{sample_number}-{sample_type['code']}"

                # 检查报告编号是否已存在
                existing = cursor.execute('SELECT id FROM reports WHERE report_number = ?', (report_number,)).fetchone()

                if existing:
                    error_rows.append(f'第{row_idx}行: 报告编号"{report_number}"已存在')
                    continue

                # 创建报告
                cursor.execute(
                    'INSERT INTO reports (report_number, sample_number, company_id, sample_type_id, '
                    'detection_person, review_person, detection_date, remark, created_by) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (report_number, sample_number, company_id, sample_type_id, detection_person,
                     review_person, detection_date, remark, session['user_id'])
                )
                conn.commit()
                report_id = cursor.lastrowid

                # 添加检测数据
                for col_idx, col_name in indicator_cols:
                    if col_name in indicator_map and row[col_idx]:
                        measured_value = str(row[col_idx]).strip()
                        if measured_value:
                            cursor.execute(
                                'INSERT INTO report_data (report_id, indicator_id, measured_value, remark) '
                                'VALUES (?, ?, ?, ?)',
                                (report_id, indicator_map[col_name], measured_value, '')
                            )

                conn.commit()
                imported_count += 1

            except Exception as e:
                error_rows.append(f'第{row_idx}行: {str(e)}')
                continue

        conn.close()

        log_operation('批量导入报告', f'成功导入 {imported_count} 份报告')

        result = {
            'message': f'导入成功！共导入 {imported_count} 份报告',
            'imported': imported_count
        }

        if error_rows:
            result['errors'] = error_rows

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

@app.route('/api/reports/export/template', methods=['GET'])
@login_required
def api_export_reports_template():
    """导出报告导入模板Excel"""
    sample_type_id = request.args.get('sample_type_id')

    if not sample_type_id:
        return jsonify({'error': '请指定样品类型'}), 400

    conn = get_db_connection()

    # 获取样品类型信息
    sample_type = conn.execute('SELECT * FROM sample_types WHERE id = ?', (sample_type_id,)).fetchone()

    if not sample_type:
        conn.close()
        return jsonify({'error': '样品类型不存在'}), 404

    # 获取该样品类型的检测指标
    indicators = conn.execute(
        'SELECT i.name, i.unit '
        'FROM template_indicators ti '
        'LEFT JOIN indicators i ON ti.indicator_id = i.id '
        'WHERE ti.sample_type_id = ? '
        'ORDER BY ti.sort_order',
        (sample_type_id,)
    ).fetchall()

    conn.close()

    # 创建Excel工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "报告导入模板"

    # 设置样式
    header_font = Font(name='宋体', size=11, bold=True)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 表头
    headers = ['样品编号', '样品类型', '委托单位', '检测日期', '检测人员', '审核人员', '备注']

    # 添加检测指标列
    for indicator in indicators:
        unit = f"({indicator['unit']})" if indicator['unit'] else ''
        headers.append(f"{indicator['name']}{unit}")

    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # 添加示例数据行
    example_row = ['SMP001', sample_type['name'], '示例公司', '2026-01-01', '张三', '李四', '']
    for indicator in indicators:
        example_row.append('')  # 空白检测值

    for col, value in enumerate(example_row, start=1):
        cell = ws.cell(row=2, column=col)
        cell.value = value
        cell.border = border

    # 调整列宽
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15

    # 保存文件
    os.makedirs('exports', exist_ok=True)
    filename = f"exports/report_template_{sample_type['code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    wb.save(filename)

    log_operation('导出报告模板', f'导出样品类型:{sample_type["name"]}')
    return send_file(filename, as_attachment=True, download_name=f'报告导入模板_{sample_type["code"]}.xlsx')

# ==================== 数据备份与恢复 API ====================
@app.route('/api/backup/create', methods=['POST'])
@admin_required
def api_create_backup():
    """创建数据备份"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'backups/backup_{timestamp}'
        os.makedirs(backup_dir, exist_ok=True)

        # 备份数据库文件
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, f'{backup_dir}/water_quality_v2.db')

        # 创建备份信息文件
        backup_info = {
            'backup_time': datetime.now().isoformat(),
            'backup_by': session.get('username', 'unknown'),
            'version': '2.0'
        }

        with open(f'{backup_dir}/backup_info.json', 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)

        log_operation('创建数据备份', f'备份目录:{backup_dir}')
        return jsonify({'message': '备份创建成功', 'backup_dir': backup_dir})

    except Exception as e:
        return jsonify({'error': f'备份失败: {str(e)}'}), 500

@app.route('/api/backup/list', methods=['GET'])
@admin_required
def api_list_backups():
    """获取备份列表"""
    try:
        backups = []
        backup_base = 'backups'

        if os.path.exists(backup_base):
            for backup_name in os.listdir(backup_base):
                backup_path = os.path.join(backup_base, backup_name)
                if os.path.isdir(backup_path):
                    info_file = os.path.join(backup_path, 'backup_info.json')
                    if os.path.exists(info_file):
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                            info['name'] = backup_name
                            info['path'] = backup_path
                            backups.append(info)

        backups.sort(key=lambda x: x['backup_time'], reverse=True)
        return jsonify(backups)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/restore', methods=['POST'])
@admin_required
def api_restore_backup():
    """恢复数据备份"""
    data = request.json
    backup_name = data.get('backup_name')

    if not backup_name:
        return jsonify({'error': '备份名称不能为空'}), 400

    backup_path = os.path.join('backups', backup_name)

    if not os.path.exists(backup_path):
        return jsonify({'error': '备份不存在'}), 404

    try:
        # 备份当前数据库(防止恢复失败)
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, f'{DATABASE_PATH}.before_restore')

        # 恢复数据库文件
        backup_db = os.path.join(backup_path, 'water_quality_v2.db')
        if os.path.exists(backup_db):
            shutil.copy2(backup_db, DATABASE_PATH)

        log_operation('恢复数据备份', f'恢复备份:{backup_name}')
        return jsonify({'message': '数据恢复成功'})

    except Exception as e:
        # 恢复失败,回滚
        if os.path.exists(f'{DATABASE_PATH}.before_restore'):
            shutil.copy2(f'{DATABASE_PATH}.before_restore', DATABASE_PATH)
        return jsonify({'error': f'恢复失败: {str(e)}'}), 500

# ==================== 操作日志 API ====================
@app.route('/api/logs', methods=['GET'])
@login_required
def api_logs():
    """获取操作日志"""
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    user_id = request.args.get('user_id')
    operation_type = request.args.get('operation_type')

    logs = get_operation_logs(limit, offset, user_id, operation_type)

    return jsonify(logs)

# ==================== 报告模版管理 API ====================
@app.route('/api/report-templates', methods=['GET'])
@login_required
def api_report_templates():
    """获取报告模版列表"""
    conn = get_db_connection()

    templates = conn.execute(
        'SELECT t.*, st.name as sample_type_name '
        'FROM excel_report_templates t '
        'LEFT JOIN sample_types st ON t.sample_type_id = st.id '
        'WHERE t.is_active = 1 '
        'ORDER BY t.created_at DESC'
    ).fetchall()

    conn.close()

    return jsonify([dict(t) for t in templates])

@app.route('/api/report-templates/import', methods=['POST'])
@admin_required
def api_import_report_template():
    """导入报告模版"""
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': '只支持Excel文件'}), 400

    # 获取表单数据
    template_name = request.form.get('name')
    sample_type_id = request.form.get('sample_type_id')
    description = request.form.get('description', '')

    if not template_name:
        return jsonify({'error': '模版名称不能为空'}), 400

    try:
        # 保存上传的文件
        os.makedirs('templates/excel_reports', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{template_name}_{timestamp}.xlsx"
        file_path = os.path.join('templates/excel_reports', filename)
        file.save(file_path)

        # 读取Excel文件
        wb = openpyxl.load_workbook(file_path)

        # 保存到数据库
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查模板名称是否已存在，如果存在则自动添加序号
        final_template_name = template_name
        existing = conn.execute(
            'SELECT COUNT(*) as count FROM excel_report_templates WHERE name = ?',
            (template_name,)
        ).fetchone()

        if existing['count'] > 0:
            # 查找所有相似名称的模板
            similar = conn.execute(
                'SELECT name FROM excel_report_templates WHERE name LIKE ?',
                (f'{template_name}%',)
            ).fetchall()

            # 找出最大的序号
            max_num = 0
            for row in similar:
                name = row['name']
                # 尝试提取末尾的数字
                import re
                match = re.search(r'_(\d+)$', name)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num

            # 使用下一个序号
            final_template_name = f"{template_name}_{max_num + 1}"

        cursor.execute(
            'INSERT INTO excel_report_templates (name, sample_type_id, description, template_file_path) '
            'VALUES (?, ?, ?, ?)',
            (final_template_name, sample_type_id if sample_type_id else None, description, file_path)
        )

        template_id = cursor.lastrowid

        # 分析工作表结构
        for index, sheet_name in enumerate(wb.sheetnames):
            sheet_type = identify_sheet_type(sheet_name)
            page_number = extract_page_number(sheet_name)

            cursor.execute(
                'INSERT INTO template_sheet_configs '
                '(template_id, sheet_name, sheet_index, sheet_type, page_number) '
                'VALUES (?, ?, ?, ?, ?)',
                (template_id, sheet_name, index, sheet_type, page_number)
            )

        # 解析模板字段（带有[]、()、;标记的单元格）
        from template_field_parser import TemplateFieldParser

        field_count = 0
        try:
            fields = TemplateFieldParser.extract_template_fields(file_path)

            for field in fields:
                # 插入字段映射
                cursor.execute(
                    '''INSERT INTO template_field_mappings
                       (template_id, field_name, field_display_name, field_type,
                        sheet_name, cell_address, placeholder, default_value, is_required)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (template_id,
                     field['field_name'],
                     field['display_name'],
                     'text',  # 默认文本类型
                     field['sheet_name'],
                     field['cell_address'],
                     field.get('placeholder', ''),
                     field.get('default_value', ''),
                     1 if field.get('is_required', True) else 0)
                )
                field_count += 1
        except Exception as e:
            print(f"字段解析警告: {e}")
            # 字段解析失败不影响模板导入

        conn.commit()
        conn.close()

        log_operation('导入报告模版', f'导入模版: {template_name}, 解析字段: {field_count}个')

        return jsonify({
            'id': template_id,
            'message': '模版导入成功',
            'sheet_count': len(wb.sheetnames),
            'field_count': field_count
        }), 201

    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

@app.route('/api/report-templates/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_report_template_detail(id):
    """获取、修改或删除报告模版"""
    conn = get_db_connection()

    if request.method == 'PUT':
        # 仅管理员可修改
        if session.get('role') != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.json
        name = data.get('name')
        description = data.get('description', '')

        if not name:
            return jsonify({'error': '模版名称不能为空'}), 400

        # 检查是否存在同名的其他模版（包括已删除的模版，因为UNIQUE约束对所有行生效）
        existing = conn.execute(
            'SELECT id, is_active, name FROM excel_report_templates WHERE name = ? AND id != ?',
            (name, id)
        ).fetchone()

        if existing:
            if existing['is_active']:
                conn.close()
                return jsonify({'error': '模版名称已存在，请使用其他名称'}), 400
            else:
                # 如果是已删除的模版，自动重命名它以释放该名称
                import datetime
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                new_name_for_deleted = f"{existing['name']}_已删除_{timestamp}"
                conn.execute(
                    'UPDATE excel_report_templates SET name = ? WHERE id = ?',
                    (new_name_for_deleted, existing['id'])
                )
                conn.commit()

        try:
            conn.execute(
                'UPDATE excel_report_templates SET name = ?, description = ? WHERE id = ?',
                (name, description, id)
            )
            conn.commit()

            log_operation('修改报告模版', f'修改模版: {name}', conn=conn)
            conn.close()

            return jsonify({'message': '模版更新成功'})
        except Exception as e:
            conn.close()
            return jsonify({'error': f'更新失败: {str(e)}'}), 500

    if request.method == 'DELETE':
        # 仅管理员可删除
        if session.get('role') != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403

        # 获取模版信息
        template = conn.execute(
            'SELECT * FROM excel_report_templates WHERE id = ?',
            (id,)
        ).fetchone()

        if not template:
            conn.close()
            return jsonify({'error': '模版不存在'}), 404

        # 删除文件
        if template['template_file_path'] and os.path.exists(template['template_file_path']):
            try:
                os.remove(template['template_file_path'])
            except Exception as e:
                print(f"删除模版文件失败: {e}")

        # 软删除（设置is_active=0）
        conn.execute('UPDATE excel_report_templates SET is_active = 0 WHERE id = ?', (id,))
        conn.commit()
        conn.close()

        log_operation('删除报告模版', f'删除模版: {template["name"]}')

        return jsonify({'message': '模版删除成功'})

    # GET请求 - 获取模版详情
    template = conn.execute(
        'SELECT * FROM excel_report_templates WHERE id = ?',
        (id,)
    ).fetchone()

    if not template:
        conn.close()
        return jsonify({'error': '模版不存在'}), 404

    # 获取工作表配置
    sheets = conn.execute(
        'SELECT * FROM template_sheet_configs WHERE template_id = ? ORDER BY sheet_index',
        (id,)
    ).fetchall()

    # 获取字段映射
    fields = conn.execute(
        'SELECT * FROM template_field_mappings WHERE template_id = ?',
        (id,)
    ).fetchall()

    conn.close()

    return jsonify({
        'template': dict(template),
        'sheets': [dict(s) for s in sheets],
        'fields': [dict(f) for f in fields]
    })

@app.route('/api/report-templates/<int:id>/fields', methods=['GET', 'POST'])
@admin_required
def api_template_fields(id):
    """获取或添加模版字段映射"""
    conn = get_db_connection()

    if request.method == 'POST':
        data = request.json
        field_name = data.get('field_name')
        field_type = data.get('field_type')
        sheet_name = data.get('sheet_name')
        cell_address = data.get('cell_address')
        start_row = data.get('start_row')
        start_col = data.get('start_col')
        description = data.get('description', '')
        is_required = data.get('is_required', False)
        default_value = data.get('default_value', '')

        if not all([field_name, field_type, sheet_name]):
            conn.close()
            return jsonify({'error': '缺少必填字段'}), 400

        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO template_field_mappings '
            '(template_id, field_name, field_type, sheet_name, cell_address, '
            'start_row, start_col, description, is_required, default_value) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (id, field_name, field_type, sheet_name, cell_address,
             start_row, start_col, description, is_required, default_value)
        )

        field_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log_operation('添加模版字段映射', f'模版ID: {id}, 字段: {field_name}')

        return jsonify({'id': field_id, 'message': '字段映射添加成功'}), 201

    # GET请求
    fields = conn.execute(
        'SELECT * FROM template_field_mappings WHERE template_id = ? ORDER BY id',
        (id,)
    ).fetchall()

    conn.close()

    return jsonify([dict(f) for f in fields])

def identify_sheet_type(sheet_name):
    """识别工作表类型"""
    sheet_name_lower = sheet_name.lower()

    if '1' in sheet_name or 'cover' in sheet_name_lower or '封面' in sheet_name:
        return 'cover'
    elif '2' in sheet_name or 'info' in sheet_name_lower or '信息' in sheet_name:
        return 'info'
    elif any(x in sheet_name for x in ['3', '4']) or 'data' in sheet_name_lower or '数据' in sheet_name:
        return 'data'
    elif '5' in sheet_name or 'note' in sheet_name_lower or '说明' in sheet_name:
        return 'conclusion'
    else:
        return 'other'

def extract_page_number(sheet_name):
    """从工作表名称提取页码"""
    import re
    match = re.search(r'\d+', sheet_name)
    return int(match.group()) if match else 0

# ==================== 页面路由 ====================
@app.route('/login')
def login_page():
    """登录页面"""
    return render_template('login.html')

@app.route('/')
def index():
    """主页面 - 需要登录"""
    # 检查是否已登录
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('index_v2.html')

@app.route('/sample-types-manager')
def sample_types_manager():
    """样品类型管理专项页面"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('sample_types_manager.html')

@app.route('/indicators-manager')
def indicators_manager():
    """检测指标管理专项页面"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('indicators_manager.html')

@app.route('/report-template-manager')
def report_template_manager():
    """报告模版管理专项页面"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('report_template_manager.html')

# ==================== 新增API接口 ====================

@app.route('/api/download-import-template', methods=['GET'])
@login_required
def api_download_import_template():
    """下载导入模板"""
    from import_template_generator import generate_import_template

    template_id = request.args.get('template_id')
    template_id = int(template_id) if template_id else None

    try:
        output_path = generate_import_template(template_id)
        log_operation('下载导入模板', f'模板ID: {template_id or "通用"}')
        return send_file(output_path, as_attachment=True, download_name=os.path.basename(output_path))
    except Exception as e:
        return jsonify({'error': f'生成导入模板失败: {str(e)}'}), 500

@app.route('/api/import-reports', methods=['POST'])
@login_required
def api_import_reports():
    """批量导入报告"""
    from import_processor import import_reports_from_excel

    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': '仅支持Excel文件(.xlsx, .xls)'}), 400

    # 保存上传的文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"import_{timestamp}_{file.filename}"
    upload_path = os.path.join('uploads', filename)
    os.makedirs('uploads', exist_ok=True)
    file.save(upload_path)

    # 获取参数
    template_id = request.form.get('template_id')
    template_id = int(template_id) if template_id else None
    created_by = session.get('username', 'system')

    try:
        # 处理导入
        results = import_reports_from_excel(upload_path, template_id, created_by)

        log_operation('批量导入报告',
                     f'成功:{len(results["success"])} 失败:{len(results["errors"])} 警告:{len(results["warnings"])}')

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500
    finally:
        # 清理临时文件
        if os.path.exists(upload_path):
            os.remove(upload_path)

@app.route('/api/reports/pending-submit', methods=['GET'])
@login_required
def api_reports_pending_submit():
    """获取待提交报告列表（草稿和被拒绝的报告）"""
    conn = get_db_connection()

    # 获取筛选条件
    sample_number = request.args.get('sample_number', '')
    company_id = request.args.get('company_id', '')

    # 构建SQL - 查询当前用户创建的draft和rejected状态的报告
    sql = '''
        SELECT r.*,
               st.name as sample_type_name,
               c.name as company_name,
               t.name as template_name
        FROM reports r
        LEFT JOIN sample_types st ON r.sample_type_id = st.id
        LEFT JOIN companies c ON r.company_id = c.id
        LEFT JOIN excel_report_templates t ON r.template_id = t.id
        WHERE r.created_by = ? AND (r.review_status = 'draft' OR r.review_status = 'rejected' OR r.review_status IS NULL)
    '''
    params = [session['user_id']]

    if sample_number:
        sql += ' AND r.sample_number LIKE ?'
        params.append(f'%{sample_number}%')

    if company_id:
        sql += ' AND r.company_id = ?'
        params.append(company_id)

    sql += ' ORDER BY r.created_at DESC'

    reports = conn.execute(sql, params).fetchall()
    conn.close()

    return jsonify([dict(r) for r in reports])

@app.route('/api/reports/submitted', methods=['GET'])
@login_required
def api_reports_submitted():
    """获取已提交报告列表（pending、approved、rejected状态的报告）"""
    conn = get_db_connection()

    # 获取筛选条件
    sample_number = request.args.get('sample_number', '')
    status = request.args.get('status', '')
    company_id = request.args.get('company_id', '')
    date = request.args.get('date', '')

    # 构建SQL - 查询当前用户创建的已提交报告
    sql = '''
        SELECT r.*,
               st.name as sample_type_name,
               c.name as company_name,
               t.name as template_name
        FROM reports r
        LEFT JOIN sample_types st ON r.sample_type_id = st.id
        LEFT JOIN companies c ON r.company_id = c.id
        LEFT JOIN excel_report_templates t ON r.template_id = t.id
        WHERE r.created_by = ? AND r.review_status IN ('pending', 'approved', 'rejected')
    '''
    params = [session['user_id']]

    if sample_number:
        sql += ' AND r.sample_number LIKE ?'
        params.append(f'%{sample_number}%')

    if status:
        sql += ' AND r.review_status = ?'
        params.append(status)

    if company_id:
        sql += ' AND r.company_id = ?'
        params.append(company_id)

    if date:
        sql += ' AND DATE(r.created_at) = ?'
        params.append(date)

    sql += ' ORDER BY r.created_at DESC'

    reports = conn.execute(sql, params).fetchall()
    conn.close()

    return jsonify([dict(r) for r in reports])

@app.route('/api/reports/review', methods=['GET'])
@login_required
def api_reports_review():
    """获取报告列表（用于审核）"""
    conn = get_db_connection()

    # 获取筛选条件
    status = request.args.get('status', '')
    sample_number = request.args.get('sample_number', '')
    company_id = request.args.get('company_id', '')

    # 构建SQL
    sql = '''
        SELECT r.*,
               st.name as sample_type_name,
               c.name as company_name
        FROM reports r
        LEFT JOIN sample_types st ON r.sample_type_id = st.id
        LEFT JOIN companies c ON r.company_id = c.id
        WHERE 1=1
    '''
    params = []

    if status:
        sql += ' AND r.review_status = ?'
        params.append(status)

    if sample_number:
        sql += ' AND r.sample_number LIKE ?'
        params.append(f'%{sample_number}%')

    if company_id:
        sql += ' AND r.company_id = ?'
        params.append(company_id)

    sql += ' ORDER BY r.created_at DESC'

    reports = conn.execute(sql, params).fetchall()
    conn.close()

    return jsonify([dict(r) for r in reports])

@app.route('/api/reports/<int:id>/review-detail', methods=['GET'])
@login_required
def api_report_review_detail(id):
    """获取报告审核详情"""
    conn = get_db_connection()

    # 获取报告基本信息
    report = conn.execute('''
        SELECT r.*,
               st.name as sample_type_name,
               c.name as company_name,
               t.name as template_name
        FROM reports r
        LEFT JOIN sample_types st ON r.sample_type_id = st.id
        LEFT JOIN companies c ON r.company_id = c.id
        LEFT JOIN excel_report_templates t ON r.template_id = t.id
        WHERE r.id = ?
    ''', (id,)).fetchone()

    if not report:
        conn.close()
        return jsonify({'error': '报告不存在'}), 404

    # 获取检测数据
    detection_data = conn.execute('''
        SELECT rd.*,
               i.name as indicator_name,
               i.unit,
               i.limit_value,
               i.detection_method,
               ig.name as group_name
        FROM report_data rd
        LEFT JOIN indicators i ON rd.indicator_id = i.id
        LEFT JOIN indicator_groups ig ON i.group_id = ig.id
        WHERE rd.report_id = ?
        ORDER BY ig.sort_order, i.sort_order, i.name
    ''', (id,)).fetchall()

    # 获取模板字段值
    template_fields = []
    if report['template_id']:
        template_fields = conn.execute('''
            SELECT rfv.*,
                   tfm.field_name,
                   tfm.field_display_name,
                   tfm.sheet_name,
                   tfm.cell_address
            FROM report_field_values rfv
            LEFT JOIN template_field_mappings tfm ON rfv.field_mapping_id = tfm.id
            WHERE rfv.report_id = ?
        ''', (id,)).fetchall()

    conn.close()

    return jsonify({
        'report': dict(report),
        'detection_data': [dict(d) for d in detection_data],
        'template_fields': [dict(f) for f in template_fields]
    })

@app.route('/api/reports/<int:id>/approve', methods=['POST'])
@login_required
def api_approve_report(id):
    """审核通过报告"""
    data = request.json
    comment = data.get('comment', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 检查报告是否存在
        report = conn.execute('SELECT id, review_status FROM reports WHERE id = ?', (id,)).fetchone()
        if not report:
            return jsonify({'error': '报告不存在'}), 404

        # 更新审核状态
        cursor.execute('''
            UPDATE reports
            SET review_status = 'approved',
                review_person = ?,
                review_time = ?,
                review_comment = ?
            WHERE id = ?
        ''', (session.get('username', 'unknown'), datetime.now(), comment, id))

        conn.commit()
        log_operation('审核报告', f'报告ID: {id}, 结果: 通过')

        return jsonify({'message': '审核通过'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/reports/<int:id>/reject', methods=['POST'])
@login_required
def api_reject_report(id):
    """拒绝报告"""
    data = request.json
    comment = data.get('comment', '')

    if not comment:
        return jsonify({'error': '请填写拒绝原因'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 检查报告是否存在
        report = conn.execute('SELECT id, review_status FROM reports WHERE id = ?', (id,)).fetchone()
        if not report:
            return jsonify({'error': '报告不存在'}), 404

        # 更新审核状态
        cursor.execute('''
            UPDATE reports
            SET review_status = 'rejected',
                review_person = ?,
                review_time = ?,
                review_comment = ?
            WHERE id = ?
        ''', (session.get('username', 'unknown'), datetime.now(), comment, id))

        conn.commit()
        log_operation('审核报告', f'报告ID: {id}, 结果: 拒绝')

        return jsonify({'message': '已拒绝'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/reports/<int:id>/submit', methods=['POST'])
@login_required
def api_submit_report(id):
    """提交报告到审核（将draft或rejected状态改为pending）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 检查报告是否存在
        report = conn.execute('SELECT id, review_status, created_by FROM reports WHERE id = ?', (id,)).fetchone()
        if not report:
            return jsonify({'error': '报告不存在'}), 404

        # 检查权限（仅创建人或管理员可提交）
        if session.get('role') != 'admin' and report['created_by'] != session['user_id']:
            return jsonify({'error': '无权提交此报告'}), 403

        # 检查当前状态是否允许提交
        if report['review_status'] not in ['draft', 'rejected', None]:
            return jsonify({'error': f'当前状态 ({report["review_status"]}) 不允许提交'}), 400

        # 更新状态为pending
        cursor.execute('''
            UPDATE reports
            SET review_status = 'pending'
            WHERE id = ?
        ''', (id,))

        conn.commit()
        log_operation('提交报告', f'报告ID: {id}')

        return jsonify({'message': '报告已提交审核'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/reports/<int:id>/generate', methods=['POST'])
@login_required
def api_generate_report(id):
    """生成最终报告"""
    from report_generator import ReportGenerator

    data = request.json
    template_id = data.get('template_id')

    if not template_id:
        return jsonify({'error': '请选择报告模板'}), 400

    conn = get_db_connection()

    try:
        # 检查报告是否已审核
        report = conn.execute('SELECT * FROM reports WHERE id = ?', (id,)).fetchone()
        if not report:
            return jsonify({'error': '报告不存在'}), 404

        if report['review_status'] != 'approved':
            return jsonify({'error': '只有已审核通过的报告才能生成'}), 400

        # 获取报告数据
        detection_items = conn.execute('''
            SELECT rd.*, i.name, i.unit, i.limit_value, i.detection_method
            FROM report_data rd
            LEFT JOIN indicators i ON rd.indicator_id = i.id
            WHERE rd.report_id = ?
        ''', (id,)).fetchall()

        # 构建报告数据
        report_data = {
            'report_number': report['report_number'],
            'sample_number': report['sample_number'],
            'detection_date': report['detection_date'],
            'detection_person': report['detection_person'],
            'review_person': report['review_person'],
            'detection_items': [
                {
                    'name': item['name'],
                    'unit': item['unit'],
                    'result': item['measured_value'],
                    'limit': item['limit_value'],
                    'method': item['detection_method']
                }
                for item in detection_items
            ]
        }

        # 生成报告
        generator = ReportGenerator(template_id, report_data)
        output_path = generator.generate()

        # 更新报告记录
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE reports SET generated_report_path = ? WHERE id = ?',
            (output_path, id)
        )
        conn.commit()

        log_operation('生成报告', f'报告ID: {id}')

        return jsonify({
            'message': '生成成功',
            'file_path': output_path
        })
    except Exception as e:
        return jsonify({'error': f'生成失败: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/reports/<int:id>/download', methods=['GET'])
@login_required
def api_download_report(id):
    """下载生成的报告"""
    conn = get_db_connection()

    report = conn.execute(
        'SELECT generated_report_path FROM reports WHERE id = ?',
        (id,)
    ).fetchone()

    conn.close()

    if not report or not report['generated_report_path']:
        return jsonify({'error': '报告文件不存在'}), 404

    file_path = report['generated_report_path']
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404

    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

@app.route('/api/template-fields/batch-update-defaults', methods=['POST'])
@admin_required
def api_batch_update_field_defaults():
    """批量更新字段默认值"""
    data = request.json
    updates = data.get('updates', [])

    if not updates:
        return jsonify({'error': '没有要更新的数据'}), 400

    conn = get_db_connection()

    try:
        for update in updates:
            field_id = update.get('id')
            default_value = update.get('default_value', '')

            conn.execute(
                'UPDATE template_field_mappings SET default_value = ? WHERE id = ?',
                (default_value, field_id)
            )

        conn.commit()
        log_operation('更新字段默认值', f'批量更新 {len(updates)} 个字段', conn=conn)
        conn.close()

        return jsonify({'message': f'成功更新 {len(updates)} 个字段的默认值'})
    except Exception as e:
        conn.close()
        return jsonify({'error': f'更新失败: {str(e)}'}), 500

@app.route('/api/template-fields/<int:template_id>', methods=['GET'])
@login_required
def api_get_template_fields_list(template_id):
    """获取模板字段配置（用于报告填写）"""
    conn = get_db_connection()

    fields = conn.execute('''
        SELECT * FROM template_field_mappings
        WHERE template_id = ?
        ORDER BY id
    ''', (template_id,)).fetchall()

    conn.close()

    return jsonify([dict(f) for f in fields])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
