from flask import Blueprint, request, jsonify, send_file, session
from models_v2 import get_db
from auth import login_required, admin_required, log_operation
from datetime import datetime
import json
import os
import traceback

report_workflow_bp = Blueprint('report_workflow_bp', __name__)

@report_workflow_bp.route('/api/reports/pending-submit', methods=['GET'])
@login_required
def api_reports_pending_submit():
    """获取待提交报告列表（草稿和被拒绝的报告）"""
    with get_db() as conn:

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

        return jsonify([dict(r) for r in reports])

@report_workflow_bp.route('/api/reports/submitted', methods=['GET'])
@login_required
def api_reports_submitted():
    """获取已提交报告列表（pending、approved、rejected状态的报告）"""
    with get_db() as conn:

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

        return jsonify([dict(r) for r in reports])

@report_workflow_bp.route('/api/reports/review', methods=['GET'])
@login_required
def api_reports_review():
    """获取报告列表（用于审核）"""
    with get_db() as conn:

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

        return jsonify([dict(r) for r in reports])

@report_workflow_bp.route('/api/reports/<int:id>/review-detail', methods=['GET'])
@login_required
def api_report_review_detail(id):
    """获取报告审核详情"""
    with get_db() as conn:

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
            return jsonify({'error': '报告不存在'}), 404

        # 获取检测数据
        detection_data = conn.execute('''
            SELECT rd.*,
                   i.name as indicator_name,
                   i.unit,
                   COALESCE(ti.limit_value, i.limit_value) as limit_value,
                   i.detection_method,
                   ig.name as group_name
            FROM report_data rd
            LEFT JOIN indicators i ON rd.indicator_id = i.id
            LEFT JOIN indicator_groups ig ON i.group_id = ig.id
            LEFT JOIN template_indicators ti
                ON ti.indicator_id = rd.indicator_id AND ti.sample_type_id = ?
            WHERE rd.report_id = ?
            ORDER BY ti.sort_order, ig.sort_order, i.sort_order, i.name
        ''', (report['sample_type_id'], id,)).fetchall()

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

        # 获取审核历史记录
        review_history = conn.execute('''
            SELECT rh.*,
                   u.username as reviewer_name
            FROM review_history rh
            LEFT JOIN users u ON rh.reviewer_id = u.id
            WHERE rh.report_id = ?
            ORDER BY rh.reviewed_at DESC
        ''', (id,)).fetchall()


        return jsonify({
            'report': dict(report),
            'detection_data': [dict(d) for d in detection_data],
            'template_fields': [dict(f) for f in template_fields],
            'review_history': [dict(h) for h in review_history]
        })

@report_workflow_bp.route('/api/reports/<int:id>/approve', methods=['POST'])
@login_required
def api_approve_report(id):
    """审核通过报告"""
    data = request.json
    comment = data.get('comment', '')

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # 获取完整报告信息
            report = conn.execute('''
                SELECT r.*, st.name as sample_type_name
                FROM reports r
                LEFT JOIN sample_types st ON r.sample_type_id = st.id
                WHERE r.id = ?
            ''', (id,)).fetchone()

            if not report:
                return jsonify({'error': '报告不存在'}), 404

            review_time = datetime.now()
            username = session.get('username', 'unknown')

            # 更新审核状态
            cursor.execute('''
                UPDATE reports
                SET review_status = 'approved',
                    review_person = ?,
                    review_time = ?,
                    review_comment = ?,
                    reviewed_at = ?
                WHERE id = ?
            ''', (username, review_time, comment, review_time, id))

            # 记录审核历史
            cursor.execute('''
                INSERT INTO review_history (report_id, reviewer_id, review_status, review_comment, reviewed_at)
                VALUES (?, ?, 'approved', ?, ?)
            ''', (id, session.get('user_id'), comment, review_time))

            log_operation('审核报告', f'报告ID: {id}, 结果: 通过', conn=conn)

            return jsonify({'message': '审核通过'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@report_workflow_bp.route('/api/reports/<int:id>/reject', methods=['POST'])
@login_required
def api_reject_report(id):
    """拒绝报告"""
    data = request.json
    comment = data.get('comment', '')

    if not comment:
        return jsonify({'error': '请填写拒绝原因'}), 400

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # 检查报告是否存在
            report = conn.execute('SELECT id, review_status FROM reports WHERE id = ?', (id,)).fetchone()
            if not report:
                return jsonify({'error': '报告不存在'}), 404

            review_time = datetime.now()
            username = session.get('username', 'unknown')

            # 更新审核状态
            cursor.execute('''
                UPDATE reports
                SET review_status = 'rejected',
                    review_person = ?,
                    review_time = ?,
                    review_comment = ?,
                    reviewed_at = ?
                WHERE id = ?
            ''', (username, review_time, comment, review_time, id))

            # 记录审核历史
            cursor.execute('''
                INSERT INTO review_history (report_id, reviewer_id, review_status, review_comment, reviewed_at)
                VALUES (?, ?, 'rejected', ?, ?)
            ''', (id, session.get('user_id'), comment, review_time))

            log_operation('审核报告', f'报告ID: {id}, 结果: 拒绝', conn=conn)

            return jsonify({'message': '已拒绝'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@report_workflow_bp.route('/api/reports/<int:id>/submit', methods=['POST'])
@login_required
def api_submit_report(id):
    """提交报告到审核（将draft或rejected状态改为pending）"""
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # 检查报告是否存在
            report = conn.execute('SELECT id, review_status, created_by FROM reports WHERE id = ?', (id,)).fetchone()
            if not report:
                return jsonify({'error': '报告不存在'}), 404

            # 检查权限（仅创建人或管理员可提交）
            if session.get('role') not in ('admin', 'super_admin') and report['created_by'] != session['user_id']:
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

            log_operation('提交报告', f'报告ID: {id}', conn=conn)

            return jsonify({'message': '报告已提交审核'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@report_workflow_bp.route('/api/reports/<int:id>/return', methods=['POST'])
@login_required
def api_return_report(id):
    """退回报告到审核状态"""
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # 检查报告是否存在
            report = conn.execute('SELECT id, review_status, created_by, review_person FROM reports WHERE id = ?', (id,)).fetchone()
            if not report:
                return jsonify({'error': '报告不存在'}), 404

            # 检查权限（仅管理员或报告创建人可退回）
            if session.get('role') not in ('admin', 'super_admin') and report['created_by'] != session['user_id']:
                return jsonify({'error': '无权退回此报告'}), 403

            # 检查当前状态是否为已审核
            if report['review_status'] != 'approved':
                return jsonify({'error': f'只有已审核通过的报告才能退回（当前状态: {report["review_status"]}）'}), 400

            # 获取退回原因
            data = request.json or {}
            return_reason = data.get('reason', '').strip()

            # 更新状态为pending，清除生成的报告路径
            cursor.execute('''
                UPDATE reports
                SET review_status = 'pending',
                    generated_report_path = NULL,
                    review_comment = ?
                WHERE id = ?
            ''', (f'[已退回] {return_reason}' if return_reason else '[已退回] 需要重新审核', id))

            # 记录退回历史
            cursor.execute('''
                INSERT INTO review_history (report_id, reviewer_id, review_status, review_comment, reviewed_at)
                VALUES (?, ?, 'returned', ?, ?)
            ''', (id, session.get('user_id'), return_reason or '退回重新审核', datetime.now()))

            log_operation('退回报告', f'报告ID: {id}, 原因: {return_reason}', conn=conn)

            return jsonify({'message': '报告已退回到审核状态'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@report_workflow_bp.route('/api/reports/<int:id>/generate', methods=['POST'])
@login_required
def api_generate_report(id):
    """生成最终报告"""
    from report_generator import ReportGenerator

    data = request.json
    template_id = data.get('template_id')
    export_format = data.get('export_format', 'xlsx')  # 导出格式：xlsx 或 pdf
    filename_template = data.get('filename_template')  # 文件名模板（可选）

    if not template_id:
        return jsonify({'error': '请选择报告模板'}), 400

    # 验证导出格式
    if export_format not in ['xlsx', 'pdf']:
        return jsonify({'error': '导出格式必须是 xlsx 或 pdf'}), 400

    with get_db() as conn:
        try:
            # 检查报告是否已审核
            report = conn.execute('SELECT * FROM reports WHERE id = ?', (id,)).fetchone()
            if not report:
                return jsonify({'error': '报告不存在'}), 404

            if report['review_status'] != 'approved':
                return jsonify({'error': '只有已审核通过的报告才能生成'}), 400

            # 获取报告数据
            detection_items = conn.execute('''
                SELECT rd.*, i.name, i.unit,
                    COALESCE(ti.limit_value, i.limit_value) as limit_value,
                    i.detection_method
                FROM report_data rd
                LEFT JOIN indicators i ON rd.indicator_id = i.id
                LEFT JOIN reports r ON rd.report_id = r.id
                LEFT JOIN template_indicators ti
                    ON ti.indicator_id = rd.indicator_id AND ti.sample_type_id = r.sample_type_id
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

            # 生成报告（传递report_id以从数据库加载完整数据）
            generator = ReportGenerator(template_id, report_data, report_id=id)
            output_path = generator.generate(
                filename_template=filename_template,
                export_format=export_format
            )

            # 更新报告记录
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE reports SET generated_report_path = ? WHERE id = ?',
                (output_path, id)
            )

            log_operation('生成报告', f'报告ID: {id}', conn=conn)

            return jsonify({
                'message': '生成成功',
                'file_path': output_path
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'生成失败: {str(e)}'}), 500

@report_workflow_bp.route('/api/reports/<int:id>/download', methods=['GET'])
@login_required
def api_download_report(id):
    """下载生成的报告"""
    with get_db() as conn:
        report = conn.execute(
            'SELECT generated_report_path FROM reports WHERE id = ?',
            (id,)
        ).fetchone()

    if not report or not report['generated_report_path']:
        return jsonify({'error': '报告文件不存在'}), 404

    file_path = report['generated_report_path']
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404

    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

@report_workflow_bp.route('/api/template-fields/batch-update-defaults', methods=['POST'])
@admin_required
def api_batch_update_field_defaults():
    """批量更新字段默认值"""
    data = request.json
    updates = data.get('updates', [])

    if not updates:
        return jsonify({'error': '没有要更新的数据'}), 400

    with get_db() as conn:
        try:
            for update in updates:
                field_id = update.get('id')
                default_value = update.get('default_value', '')

                conn.execute(
                    'UPDATE template_field_mappings SET default_value = ? WHERE id = ?',
                    (default_value, field_id)
                )

            log_operation('更新字段默认值', f'批量更新 {len(updates)} 个字段', conn=conn)

            return jsonify({'message': f'成功更新 {len(updates)} 个字段的默认值'})
        except Exception as e:
            return jsonify({'error': f'更新失败: {str(e)}'}), 500
