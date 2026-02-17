from flask import Blueprint, request, jsonify, session
from auth import login_required, admin_required, log_operation
from models_v2 import get_db

company_bp = Blueprint('company_bp', __name__)

# ==================== 公司管理 API ====================
@company_bp.route('/api/companies', methods=['GET', 'POST'])
@login_required
def api_companies():
    """公司管理"""
    with get_db() as conn:

        if request.method == 'POST':
            data = request.json
            name = data.get('name')

            if not name:
                return jsonify({'error': '公司名称不能为空'}), 400

            try:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO companies (name) VALUES (?)', (name,))
                company_id = cursor.lastrowid

                log_operation('添加公司', f'添加公司: {name}', conn=conn)

                return jsonify({'id': company_id, 'message': '公司添加成功'}), 201
            except Exception as e:
                return jsonify({'error': '公司名称已存在'}), 400

        # GET请求
        companies = conn.execute('SELECT * FROM companies ORDER BY name').fetchall()

        return jsonify([dict(company) for company in companies])

@company_bp.route('/api/companies/<int:id>', methods=['PUT', 'DELETE'])
@admin_required
def api_company_detail(id):
    """公司详情操作"""
    with get_db() as conn:

        if request.method == 'DELETE':
            company = conn.execute('SELECT name FROM companies WHERE id = ?', (id,)).fetchone()

            if not company:
                return jsonify({'error': '公司不存在'}), 404

            conn.execute('DELETE FROM companies WHERE id = ?', (id,))

            log_operation('删除公司', f'删除公司: {company["name"]}', conn=conn)

            return jsonify({'message': '公司删除成功'})

        if request.method == 'PUT':
            data = request.json
            name = data.get('name')

            if not name:
                return jsonify({'error': '公司名称不能为空'}), 400

            try:
                conn.execute('UPDATE companies SET name = ? WHERE id = ?', (name, id))

                log_operation('更新公司', f'更新公司: {name}', conn=conn)
                return jsonify({'message': '公司更新成功'})
            except Exception as e:
                return jsonify({'error': '公司名称已存在'}), 400
