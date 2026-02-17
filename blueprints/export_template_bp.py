from flask import Blueprint, request, jsonify, session
from auth import login_required, log_operation
from models_v2 import get_db

export_template_bp = Blueprint('export_template_bp', __name__)

# ==================== 导出模板管理 API ====================

@export_template_bp.route('/api/export-templates/categories', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_export_template_categories():
    """导出模板分类管理"""
    with get_db() as conn:

        try:
            if request.method == 'GET':
                # 获取所有分类
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, sort_order, created_at
                    FROM export_template_categories
                    ORDER BY sort_order, id
                ''')
                categories = []
                for row in cursor.fetchall():
                    categories.append({
                        'id': row[0],
                        'name': row[1],
                        'sort_order': row[2],
                        'created_at': row[3]
                    })
                return jsonify({'categories': categories})

            elif request.method == 'POST':
                # 创建新分类
                data = request.json
                name = data.get('name', '').strip()

                if not name:
                    return jsonify({'error': '分类名称不能为空'}), 400

                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO export_template_categories (name, sort_order)
                    VALUES (?, ?)
                ''', (name, data.get('sort_order', 0)))

                category_id = cursor.lastrowid

                log_operation('创建导出模板分类', f'分类名称: {name}', conn=conn)

                return jsonify({'message': '分类创建成功', 'category_id': category_id})

            elif request.method == 'DELETE':
                # 删除分类
                data = request.json
                category_id = data.get('category_id')

                if not category_id:
                    return jsonify({'error': '分类ID不能为空'}), 400

                cursor = conn.cursor()
                cursor.execute('DELETE FROM export_template_categories WHERE id = ?', (category_id,))

                log_operation('删除导出模板分类', f'分类ID: {category_id}', conn=conn)

                return jsonify({'message': '分类删除成功'})

        except Exception as e:
            return jsonify({'error': f'操作失败: {str(e)}'}), 500

@export_template_bp.route('/api/export-templates', methods=['GET', 'POST'])
@login_required
def api_export_templates_list():
    """获取或创建导出模板"""
    with get_db() as conn:

        try:
            if request.method == 'GET':
                # 获取所有模板
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT et.id, et.category_id, etc.name as category_name,
                           et.sample_type_id, st.name as sample_type_name,
                           et.name, et.description, et.created_at, et.updated_at
                    FROM export_templates et
                    LEFT JOIN export_template_categories etc ON et.category_id = etc.id
                    LEFT JOIN sample_types st ON et.sample_type_id = st.id
                    ORDER BY etc.sort_order, et.id
                ''')

                templates = []
                for row in cursor.fetchall():
                    template_id = row[0]

                    # 获取模板包含的列
                    cursor.execute('''
                        SELECT column_name, column_order
                        FROM export_template_columns
                        WHERE template_id = ?
                        ORDER BY column_order
                    ''', (template_id,))

                    columns = [col[0] for col in cursor.fetchall()]

                    templates.append({
                        'id': row[0],
                        'category_id': row[1],
                        'category_name': row[2],
                        'sample_type_id': row[3],
                        'sample_type_name': row[4],
                        'name': row[5],
                        'description': row[6],
                        'columns': columns,
                        'created_at': row[7],
                        'updated_at': row[8]
                    })

                return jsonify({'templates': templates})

            elif request.method == 'POST':
                # 创建新模板
                data = request.json
                category_id = data.get('category_id')
                sample_type_id = data.get('sample_type_id')
                name = data.get('name', '').strip()
                description = data.get('description', '').strip()
                columns = data.get('columns', [])

                if not name:
                    return jsonify({'error': '模板名称不能为空'}), 400

                if not sample_type_id:
                    return jsonify({'error': '请选择样品类型'}), 400

                if not columns:
                    return jsonify({'error': '至少选择一个检测指标'}), 400

                cursor = conn.cursor()

                # 插入模板
                cursor.execute('''
                    INSERT INTO export_templates (category_id, sample_type_id, name, description)
                    VALUES (?, ?, ?, ?)
                ''', (category_id, sample_type_id, name, description))

                template_id = cursor.lastrowid

                # 插入模板列
                for idx, col_name in enumerate(columns):
                    cursor.execute('''
                        INSERT INTO export_template_columns (template_id, column_name, column_order)
                        VALUES (?, ?, ?)
                    ''', (template_id, col_name, idx))


                log_operation('创建导出模板', f'模板名称: {name}，样品类型ID: {sample_type_id}，包含{len(columns)}个指标', conn=conn)

                return jsonify({'message': '模板创建成功', 'template_id': template_id})

        except Exception as e:
            return jsonify({'error': f'操作失败: {str(e)}'}), 500

@export_template_bp.route('/api/export-templates/<int:template_id>', methods=['PUT', 'DELETE'])
@login_required
def api_export_template_detail(template_id):
    """修改或删除导出模板"""
    with get_db() as conn:

        try:
            if request.method == 'PUT':
                # 修改模板
                data = request.json
                sample_type_id = data.get('sample_type_id')
                name = data.get('name', '').strip()
                description = data.get('description', '').strip()
                columns = data.get('columns', [])

                if not name:
                    return jsonify({'error': '模板名称不能为空'}), 400

                if not sample_type_id:
                    return jsonify({'error': '请选择样品类型'}), 400

                cursor = conn.cursor()

                # 更新模板基本信息
                cursor.execute('''
                    UPDATE export_templates
                    SET sample_type_id = ?, name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (sample_type_id, name, description, template_id))

                # 删除旧的列配置
                cursor.execute('DELETE FROM export_template_columns WHERE template_id = ?', (template_id,))

                # 插入新的列配置
                for idx, col_name in enumerate(columns):
                    cursor.execute('''
                        INSERT INTO export_template_columns (template_id, column_name, column_order)
                        VALUES (?, ?, ?)
                    ''', (template_id, col_name, idx))


                log_operation('修改导出模板', f'模板ID: {template_id}', conn=conn)

                return jsonify({'message': '模板修改成功'})

            elif request.method == 'DELETE':
                # 删除模板
                cursor = conn.cursor()
                cursor.execute('DELETE FROM export_templates WHERE id = ?', (template_id,))

                log_operation('删除导出模板', f'模板ID: {template_id}', conn=conn)

                return jsonify({'message': '模板删除成功'})

        except Exception as e:
            return jsonify({'error': f'操作失败: {str(e)}'}), 500
