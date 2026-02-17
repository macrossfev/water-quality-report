"""
水质检测报告系统 V2 - 主应用
支持模板管理、权限系统、多格式导出等功能
"""
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from models_v2 import init_database
from datetime import timedelta
import os
import secrets
import glob
import time
import threading

app = Flask(__name__)

# 安全配置：从文件加载持久化密钥，避免重启后session失效
_secret_key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secret_key')
if os.path.exists(_secret_key_path):
    with open(_secret_key_path, 'r') as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(_secret_key_path, 'w') as f:
        f.write(app.secret_key)
    os.chmod(_secret_key_path, 0o600)

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session有效期7天
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 文件上传限制50MB
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# CSRF保护
csrf = CSRFProtect(app)

# 初始化数据库
init_database()

# ==================== 注册蓝图 ====================
from blueprints.auth_bp import auth_bp
from blueprints.company_bp import company_bp
from blueprints.customer_bp import customer_bp
from blueprints.sample_indicator_bp import sample_indicator_bp
from blueprints.report_bp import report_bp
from blueprints.report_template_bp import report_template_bp
from blueprints.report_workflow_bp import report_workflow_bp
from blueprints.import_bp import import_bp
from blueprints.raw_data_bp import raw_data_bp
from blueprints.backup_bp import backup_bp
from blueprints.export_template_bp import export_template_bp
from blueprints.pages_bp import pages_bp

app.register_blueprint(auth_bp)
app.register_blueprint(company_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(sample_indicator_bp)
app.register_blueprint(report_bp)
app.register_blueprint(report_template_bp)
app.register_blueprint(report_workflow_bp)
app.register_blueprint(import_bp)
app.register_blueprint(raw_data_bp)
app.register_blueprint(backup_bp)
app.register_blueprint(export_template_bp)
app.register_blueprint(pages_bp)

# ==================== 临时文件清理 ====================

def cleanup_temp_files(max_age_hours=24):
    """清理超过指定时间的临时文件"""
    now = time.time()
    max_age_sec = max_age_hours * 3600
    cleaned = 0
    for pattern in ['temp/**/*', 'exports/*.xlsx', 'exports/*.docx']:
        for f in glob.glob(pattern, recursive=True):
            if os.path.isfile(f):
                try:
                    if now - os.path.getmtime(f) > max_age_sec:
                        os.remove(f)
                        cleaned += 1
                except OSError:
                    pass
    if cleaned:
        print(f"已清理 {cleaned} 个过期临时文件")

def periodic_cleanup(interval_hours=6):
    """后台定期清理临时文件"""
    while True:
        time.sleep(interval_hours * 3600)
        try:
            cleanup_temp_files()
        except Exception:
            pass

# 启动时清理一次
cleanup_temp_files()
# 启动后台清理线程
_cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
_cleanup_thread.start()


if __name__ == '__main__':
    import sys
    debug_mode = '--debug' in sys.argv
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
