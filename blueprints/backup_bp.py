from flask import Blueprint, request, jsonify, session, send_file
from auth import login_required, admin_required, log_operation, get_operation_logs
from models_v2 import get_db, DATABASE_PATH
from datetime import datetime
import json
import os
import shutil

backup_bp = Blueprint('backup_bp', __name__)

# ==================== 数据备份与恢复 API ====================
@backup_bp.route('/api/backup/create', methods=['POST'])
@admin_required
def api_create_backup():
    """创建数据备份"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'backups/backup_{timestamp}'
        os.makedirs(backup_dir, exist_ok=True)

        # 统计当前数据概况
        description_parts = []
        with get_db() as conn:
            try:
                counts = {
                    '检测报告': conn.execute('SELECT COUNT(*) FROM reports').fetchone()[0],
                    '客户': conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0],
                    '样品类型': conn.execute('SELECT COUNT(*) FROM sample_types').fetchone()[0],
                    '检测指标': conn.execute('SELECT COUNT(*) FROM indicators').fetchone()[0],
                    '报告模板': conn.execute('SELECT COUNT(*) FROM report_templates').fetchone()[0],
                    '原始数据': conn.execute('SELECT COUNT(*) FROM raw_data_records').fetchone()[0],
                }
                for name, count in counts.items():
                    if count > 0:
                        description_parts.append(f'{name} {count} 条')
            except Exception:
                description_parts.append('数据库完整备份')

            description = '包含：' + '、'.join(description_parts) if description_parts else '数据库完整备份'

            # 备份数据库文件
            if os.path.exists(DATABASE_PATH):
                shutil.copy2(DATABASE_PATH, f'{backup_dir}/water_quality_v2.db')

            # 创建备份信息文件
            backup_info = {
                'backup_time': datetime.now().isoformat(),
                'backup_by': session.get('username', 'unknown'),
                'version': '2.0',
                'description': description
            }

            with open(f'{backup_dir}/backup_info.json', 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)

            log_operation('创建数据备份', f'备份目录:{backup_dir}')
            return jsonify({'message': '备份创建成功', 'backup_dir': backup_dir})

    except Exception as e:
        return jsonify({'error': f'备份失败: {str(e)}'}), 500

@backup_bp.route('/api/backup/import', methods=['POST'])
@admin_required
def api_import_backup():
    """导入外部备份文件"""
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '未选择文件'}), 400

    if not file.filename.endswith('.db'):
        return jsonify({'error': '仅支持 .db 格式的SQLite数据库文件'}), 400

    # 保存到临时位置进行校验
    import tempfile
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db')
    os.close(tmp_fd)
    try:
        file.save(tmp_path)

        # 校验是否为合法SQLite数据库
        import sqlite3
        try:
            conn = sqlite3.connect(tmp_path)
            conn.execute('SELECT 1')
        except sqlite3.DatabaseError:
            return jsonify({'error': '文件不是有效的SQLite数据库'}), 400

        # 校验核心表是否存在
        required_tables = ['reports', 'customers', 'sample_types', 'indicators', 'report_templates', 'users']
        existing_tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        missing = [t for t in required_tables if t not in existing_tables]
        if missing:
            conn.close()
            return jsonify({'error': f'数据库缺少核心表: {", ".join(missing)}，不兼容当前系统'}), 400

        # 统计导入数据概况
        description_parts = []
        count_tables = {
            '检测报告': 'reports', '客户': 'customers', '样品类型': 'sample_types',
            '检测指标': 'indicators', '报告模板': 'report_templates'
        }
        for label, table in count_tables.items():
            try:
                cnt = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                if cnt > 0:
                    description_parts.append(f'{label} {cnt} 条')
            except Exception:
                pass
        conn.close()

        description = '导入备份，包含：' + '、'.join(description_parts) if description_parts else '导入备份（空数据库）'

        # 校验通过，保存为备份
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'backups/import_{timestamp}'
        os.makedirs(backup_dir, exist_ok=True)
        shutil.copy2(tmp_path, os.path.join(backup_dir, 'water_quality_v2.db'))

        backup_info = {
            'backup_time': datetime.now().isoformat(),
            'backup_by': session.get('username', 'unknown'),
            'version': '2.0',
            'description': description,
            'source': file.filename
        }
        with open(os.path.join(backup_dir, 'backup_info.json'), 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)

        log_operation('导入数据备份', f'来源文件:{file.filename}, 备份目录:{backup_dir}')
        return jsonify({'message': f'导入成功，已保存为备份。{description}'})

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@backup_bp.route('/api/backup/download/<backup_name>', methods=['GET'])
@admin_required
def api_download_backup(backup_name):
    """下载备份文件"""
    backup_db = os.path.join('backups', backup_name, 'water_quality_v2.db')
    # 安全校验：确保路径在 backups 目录内
    real_path = os.path.realpath(backup_db)
    real_base = os.path.realpath('backups')
    if not real_path.startswith(real_base + os.sep):
        return jsonify({'error': '非法路径'}), 403
    if not os.path.exists(backup_db):
        return jsonify({'error': '备份文件不存在'}), 404
    return send_file(backup_db, as_attachment=True, download_name=f'{backup_name}.db')

@backup_bp.route('/api/backup/delete/<backup_name>', methods=['DELETE'])
@admin_required
def api_delete_backup(backup_name):
    """删除备份"""
    backup_path = os.path.join('backups', backup_name)
    # 安全校验：确保路径在 backups 目录内
    real_path = os.path.realpath(backup_path)
    real_base = os.path.realpath('backups')
    if not real_path.startswith(real_base + os.sep):
        return jsonify({'error': '非法路径'}), 400
    if not os.path.exists(backup_path):
        return jsonify({'error': '备份不存在'}), 404
    try:
        shutil.rmtree(backup_path)
        log_operation('删除数据备份', f'删除备份:{backup_name}')
        return jsonify({'message': '备份已删除'})
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

@backup_bp.route('/api/backup/list', methods=['GET'])
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

@backup_bp.route('/api/backup/restore', methods=['POST'])
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
@backup_bp.route('/api/logs', methods=['GET'])
@login_required
def api_logs():
    """获取操作日志"""
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    user_id = request.args.get('user_id')
    operation_type = request.args.get('operation_type')

    logs = get_operation_logs(limit, offset, user_id, operation_type)

    return jsonify(logs)
