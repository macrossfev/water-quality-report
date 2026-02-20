from flask import Blueprint, request, jsonify, session
from auth import login_required, admin_required, log_operation
from models_v2 import get_db

sample_indicator_bp = Blueprint('sample_indicator_bp', __name__)

# ==================== 样品类型管理 API ====================
@sample_indicator_bp.route('/api/sample-types', methods=['GET', 'POST'])
@login_required
def api_sample_types():
    """样品类型管理"""
    with get_db() as conn:

        if request.method == 'POST':
            # 仅管理员可创建
            if session.get('role') not in ('admin', 'super_admin'):
                return jsonify({'error': '需要管理员权限'}), 403

            data = request.json
            name = data.get('name')
            code = data.get('code')
            description = data.get('description', '')
            remark = data.get('remark', '')
            indicator_ids = data.get('indicator_ids', [])  # 检测项目ID列表
            default_sample_status = data.get('default_sample_status', '')
            default_sampling_basis = data.get('default_sampling_basis', '')
            default_product_standard = data.get('default_product_standard', '')
            default_detection_items = data.get('default_detection_items', '')
            default_test_conclusion = data.get('default_test_conclusion', '')

            if not name or not code:
                return jsonify({'error': '样品类型名称和代码不能为空'}), 400

            try:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO sample_types (name, code, description, remark, '
                    'default_sample_status, default_sampling_basis, default_product_standard, '
                    'default_detection_items, default_test_conclusion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (name, code, description, remark,
                     default_sample_status, default_sampling_basis, default_product_standard,
                     default_detection_items, default_test_conclusion)
                )
                sample_type_id = cursor.lastrowid

                # 添加检测项目关联（使用间隔序号）
                if indicator_ids:
                    for idx, indicator_id in enumerate(indicator_ids):
                        cursor.execute(
                            'INSERT INTO template_indicators (sample_type_id, indicator_id, sort_order) VALUES (?, ?, ?)',
                            (sample_type_id, indicator_id, idx * 10)  # 使用间隔序号 0, 10, 20, 30...
                        )


                log_operation('添加样品类型', f'添加样品类型: {name} ({code})，关联{len(indicator_ids)}个检测项目', conn=conn)
                return jsonify({'id': sample_type_id, 'message': '样品类型添加成功'}), 201
            except Exception as e:
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

        return jsonify([dict(st) for st in sample_types])

@sample_indicator_bp.route('/api/sample-types/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_sample_type_detail(id):
    """样品类型详情操作"""
    with get_db() as conn:

        if request.method == 'GET':
            # 获取样品类型基本信息
            sample_type = conn.execute('SELECT * FROM sample_types WHERE id = ?', (id,)).fetchone()

            if not sample_type:
                return jsonify({'error': '样品类型不存在'}), 404

            # 获取已关联的检测项目ID列表
            indicator_ids = conn.execute(
                'SELECT indicator_id FROM template_indicators WHERE sample_type_id = ? ORDER BY sort_order',
                (id,)
            ).fetchall()

            result = dict(sample_type)
            result['indicator_ids'] = [row['indicator_id'] for row in indicator_ids]

            return jsonify(result)

        if request.method == 'DELETE':
            # 仅管理员可删除
            if session.get('role') not in ('admin', 'super_admin'):
                return jsonify({'error': '需要管理员权限'}), 403
            sample_type = conn.execute('SELECT name FROM sample_types WHERE id = ?', (id,)).fetchone()

            if not sample_type:
                return jsonify({'error': '样品类型不存在'}), 404

            conn.execute('DELETE FROM sample_types WHERE id = ?', (id,))

            log_operation('删除样品类型', f'删除样品类型: {sample_type["name"]}', conn=conn)

            return jsonify({'message': '样品类型删除成功'})

        if request.method == 'PUT':
            # 仅管理员可更新
            if session.get('role') not in ('admin', 'super_admin'):
                return jsonify({'error': '需要管理员权限'}), 403

            data = request.json
            name = data.get('name')
            code = data.get('code')
            description = data.get('description', '')
            remark = data.get('remark', '')
            indicator_ids = data.get('indicator_ids', [])  # 检测项目ID列表
            client_version = data.get('version')  # 客户端的版本号
            default_sample_status = data.get('default_sample_status', '')
            default_sampling_basis = data.get('default_sampling_basis', '')
            default_product_standard = data.get('default_product_standard', '')
            default_detection_items = data.get('default_detection_items', '')
            default_test_conclusion = data.get('default_test_conclusion', '')

            if not name or not code:
                return jsonify({'error': '样品类型名称和代码不能为空'}), 400

            try:
                cursor = conn.cursor()

                # 获取当前版本号进行乐观锁检查
                current = cursor.execute(
                    'SELECT version FROM sample_types WHERE id = ?', (id,)
                ).fetchone()

                if not current:
                    return jsonify({'error': '样品类型不存在'}), 404

                current_version = current['version'] if current['version'] else 1

                # 版本号检查：如果客户端提供了版本号，检查是否匹配
                if client_version is not None and current_version != client_version:
                    return jsonify({
                        'error': '数据已被其他用户修改，请刷新页面后重试',
                        'conflict': True,
                        'current_version': current_version
                    }), 409  # 409 Conflict

                # 更新样品类型，版本号+1
                new_version = current_version + 1
                cursor.execute(
                    'UPDATE sample_types SET name = ?, code = ?, description = ?, remark = ?, version = ?, '
                    'default_sample_status = ?, default_sampling_basis = ?, default_product_standard = ?, '
                    'default_detection_items = ?, default_test_conclusion = ?, '
                    'updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (name, code, description, remark, new_version,
                     default_sample_status, default_sampling_basis, default_product_standard,
                     default_detection_items, default_test_conclusion, id)
                )

                # 更新检测项目关联：保留已有limit_value，先备份再删除重建（使用间隔序号）
                existing_limits = {
                    row['indicator_id']: row['limit_value']
                    for row in cursor.execute(
                        'SELECT indicator_id, limit_value FROM template_indicators WHERE sample_type_id = ?', (id,)
                    ).fetchall()
                }
                cursor.execute('DELETE FROM template_indicators WHERE sample_type_id = ?', (id,))

                if indicator_ids:
                    for idx, indicator_id in enumerate(indicator_ids):
                        saved_limit = existing_limits.get(indicator_id)
                        cursor.execute(
                            'INSERT INTO template_indicators (sample_type_id, indicator_id, sort_order, limit_value) VALUES (?, ?, ?, ?)',
                            (id, indicator_id, idx * 10, saved_limit)
                        )


                log_operation('更新样品类型', f'更新样品类型: {name} ({code})，关联{len(indicator_ids)}个检测项目 (v{current_version}->v{new_version})', conn=conn)
                return jsonify({
                    'message': '样品类型更新成功',
                    'version': new_version
                })
            except Exception as e:
                if 'UNIQUE constraint failed' in str(e):
                    return jsonify({'error': '样品类型名称或代码已存在'}), 400
                return jsonify({'error': f'更新失败: {str(e)}'}), 400

# ==================== 检测项目分组管理 API ====================
@sample_indicator_bp.route('/api/indicator-groups', methods=['GET', 'POST'])
@login_required
def api_indicator_groups():
    """检测项目分组管理"""
    with get_db() as conn:

        if request.method == 'POST':
            # 仅管理员可创建
            if session.get('role') not in ('admin', 'super_admin'):
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
                group_id = cursor.lastrowid

                log_operation('添加检测项目分组', f'添加分组: {name}', conn=conn)
                return jsonify({'id': group_id, 'message': '分组添加成功'}), 201
            except Exception as e:
                return jsonify({'error': '分组名称已存在'}), 400

        # GET请求
        groups = conn.execute('SELECT * FROM indicator_groups ORDER BY sort_order, name').fetchall()

        return jsonify([dict(group) for group in groups])

@sample_indicator_bp.route('/api/indicator-groups/<int:id>', methods=['PUT', 'DELETE'])
@admin_required
def api_indicator_group_detail(id):
    """检测项目分组详情操作"""
    with get_db() as conn:

        if request.method == 'DELETE':
            group = conn.execute('SELECT name, is_system FROM indicator_groups WHERE id = ?', (id,)).fetchone()

            if not group:
                return jsonify({'error': '分组不存在'}), 404

            # 检查是否为系统分组
            if group['is_system']:
                return jsonify({'error': '系统分组不能删除'}), 403

            conn.execute('DELETE FROM indicator_groups WHERE id = ?', (id,))

            log_operation('删除检测项目分组', f'删除分组: {group["name"]}', conn=conn)

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

                log_operation('更新检测项目分组', f'更新分组: {name}', conn=conn)
                return jsonify({'message': '分组更新成功'})
            except Exception as e:
                return jsonify({'error': '分组名称已存在'}), 400

# ==================== 检测指标管理 API ====================
@sample_indicator_bp.route('/api/indicators', methods=['GET', 'POST'])
@login_required
def api_indicators():
    """检测指标管理"""
    with get_db() as conn:

        if request.method == 'POST':
            # 仅管理员可创建
            if session.get('role') not in ('admin', 'super_admin'):
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
                indicator_id = cursor.lastrowid

                log_operation('添加检测指标', f'添加指标: {name}', conn=conn)

                return jsonify({'id': indicator_id, 'message': '指标添加成功'}), 201
            except Exception as e:
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


        return jsonify([dict(indicator) for indicator in indicators])

@sample_indicator_bp.route('/api/indicators/<int:id>', methods=['PUT', 'DELETE'])
@admin_required
def api_indicator_detail(id):
    """检测指标详情操作"""
    with get_db() as conn:

        if request.method == 'DELETE':
            try:
                indicator = conn.execute('SELECT name FROM indicators WHERE id = ?', (id,)).fetchone()

                if not indicator:
                    return jsonify({'error': '指标不存在'}), 404

                # 检查是否被模板使用
                template_usage = conn.execute(
                    'SELECT COUNT(*) as count FROM template_indicators WHERE indicator_id = ?',
                    (id,)
                ).fetchone()

                if template_usage['count'] > 0:
                    return jsonify({'error': f'该指标正在被 {template_usage["count"]} 个模板使用，无法删除'}), 400

                # 检查是否被报告数据使用
                report_usage = conn.execute(
                    'SELECT COUNT(*) as count FROM report_data WHERE indicator_id = ?',
                    (id,)
                ).fetchone()

                if report_usage['count'] > 0:
                    return jsonify({'error': f'该指标已在 {report_usage["count"]} 份报告中使用，无法删除'}), 400

                # 执行删除
                conn.execute('DELETE FROM indicators WHERE id = ?', (id,))

                log_operation('删除检测指标', f'删除指标: {indicator["name"]}', conn=conn)

                return jsonify({'message': '指标删除成功'})
            except Exception as e:
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

                log_operation('更新检测指标', f'更新指标: {name}', conn=conn)

                return jsonify({'message': '指标更新成功'})
            except Exception as e:
                return jsonify({'error': '指标名称已存在'}), 400

# ==================== 模板-检测项目关联 API ====================
@sample_indicator_bp.route('/api/template-indicators', methods=['GET', 'POST'])
@login_required
def api_template_indicators():
    """模板检测项目关联"""
    with get_db() as conn:

        if request.method == 'POST':
            # 仅管理员可创建
            if session.get('role') not in ('admin', 'super_admin'):
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
                ti_id = cursor.lastrowid

                log_operation('添加模板检测项', f'样品类型ID:{sample_type_id}, 指标ID:{indicator_id}', conn=conn)

                return jsonify({'id': ti_id, 'message': '检测项目添加成功'}), 201
            except Exception as e:
                return jsonify({'error': '该检测项目已存在于模板中'}), 400

        # GET请求 - 获取指定样品类型的检测项目
        sample_type_id = request.args.get('sample_type_id')

        if sample_type_id:
            template_indicators = conn.execute(
                'SELECT ti.id, ti.sample_type_id, ti.indicator_id, ti.is_required, ti.sort_order, ti.created_at, '
                'i.name as indicator_name, i.unit, i.default_value, '
                'COALESCE(ti.limit_value, i.limit_value) as limit_value, '
                'i.detection_method, i.group_id, g.name as group_name '
                'FROM template_indicators ti '
                'LEFT JOIN indicators i ON ti.indicator_id = i.id '
                'LEFT JOIN indicator_groups g ON i.group_id = g.id '
                'WHERE ti.sample_type_id = ? '
                'ORDER BY ti.sort_order, g.sort_order, i.sort_order',
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


        return jsonify([dict(ti) for ti in template_indicators])

@sample_indicator_bp.route('/api/template-indicators/<int:id>', methods=['DELETE'])
@admin_required
def api_template_indicator_delete(id):
    """删除模板检测项目"""
    with get_db() as conn:

        conn.execute('DELETE FROM template_indicators WHERE id = ?', (id,))

        log_operation('删除模板检测项', f'模板检测项ID:{id}', conn=conn)

        return jsonify({'message': '检测项目删除成功'})

# ==================== 样品类型检测指标 API ====================
@sample_indicator_bp.route('/api/sample-types/<int:sample_type_id>/indicators', methods=['GET'])
@login_required
def api_sample_type_indicators(sample_type_id):
    """获取指定样品类型的所有检测指标"""
    with get_db() as conn:
        try:
            cursor = conn.cursor()

            # 获取该样品类型关联的检测指标
            cursor.execute('''
                SELECT i.id, i.name, i.unit, ti.is_required, ti.sort_order,
                       COALESCE(ti.limit_value, i.limit_value) as limit_value,
                       i.detection_method
                FROM template_indicators ti
                JOIN indicators i ON ti.indicator_id = i.id
                WHERE ti.sample_type_id = ?
                ORDER BY ti.sort_order, i.name
            ''', (sample_type_id,))

            indicators = []
            for row in cursor.fetchall():
                indicators.append({
                    'id': row[0],
                    'name': row[1],
                    'unit': row[2],
                    'is_required': bool(row[3]),
                    'sort_order': row[4],
                    'limit_value': row[5] or '',
                    'detection_method': row[6] or ''
                })

            return jsonify({'indicators': indicators})

        except Exception as e:
            return jsonify({'error': f'获取指标失败: {str(e)}'}), 500
