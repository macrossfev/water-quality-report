"""
水质检测报告系统 - 数据库模型 V2
重构版本,支持模板管理、权限系统、分组等新功能
"""
from datetime import datetime
import sqlite3
import os
from werkzeug.security import generate_password_hash

DATABASE_PATH = 'database/water_quality_v2.db'

def get_db_connection():
    """获取数据库连接"""
    # 设置30秒超时时间，避免数据库锁定错误
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    # 启用外键约束
    conn.execute('PRAGMA foreign_keys = ON')
    # 启用WAL模式以支持更好的并发
    conn.execute('PRAGMA journal_mode = WAL')
    # 设置繁忙超时
    conn.execute('PRAGMA busy_timeout = 30000')
    return conn

def init_database():
    """初始化数据库表结构"""
    os.makedirs('database', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    os.makedirs('backups', exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()

    # 启用WAL模式以支持更好的并发
    cursor.execute('PRAGMA journal_mode = WAL')
    # 启用外键约束
    cursor.execute('PRAGMA foreign_keys = ON')
    # 设置繁忙超时
    cursor.execute('PRAGMA busy_timeout = 30000')

    # ==================== 用户表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'reporter')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 公司表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 样品类型表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sample_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            description TEXT,
            remark TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 检测项目分组表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicator_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            is_system BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 检测指标表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            name TEXT NOT NULL UNIQUE,
            unit TEXT,
            default_value TEXT,
            limit_value TEXT,
            detection_method TEXT,
            description TEXT,
            remark TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES indicator_groups (id) ON DELETE SET NULL
        )
    ''')

    # ==================== 模板-检测项目关联表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_type_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL,
            is_required BOOLEAN DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sample_type_id) REFERENCES sample_types (id) ON DELETE CASCADE,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id) ON DELETE CASCADE,
            UNIQUE(sample_type_id, indicator_id)
        )
    ''')

    # ==================== 报告模板配置表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT DEFAULT '水质检测中心',
            report_title TEXT DEFAULT '水质检测报告',
            footer_text TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 报告表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_number TEXT NOT NULL UNIQUE,
            sample_number TEXT NOT NULL,
            company_id INTEGER,
            sample_type_id INTEGER NOT NULL,
            detection_person TEXT,
            review_person TEXT,
            detection_date DATE,
            remark TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE SET NULL,
            FOREIGN KEY (sample_type_id) REFERENCES sample_types (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # ==================== 报告数据表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL,
            measured_value TEXT,
            remark TEXT,
            FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id)
        )
    ''')

    # ==================== 操作日志表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            operation_type TEXT NOT NULL,
            operation_detail TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()

    # ==================== 初始化默认数据 ====================
    init_default_data(cursor, conn)

    conn.close()
    print("数据库初始化成功！")

def init_default_data(cursor, conn):
    """初始化默认数据"""

    # 检查是否已有管理员用户
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    admin_count = cursor.fetchone()[0]

    if admin_count == 0:
        # 创建默认管理员账号: admin/admin123
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', generate_password_hash('admin123'), 'admin')
        )
        print("默认管理员账号已创建: admin/admin123")

    # 检查是否已有报告模板配置
    cursor.execute('SELECT COUNT(*) FROM report_templates')
    template_count = cursor.fetchone()[0]

    if template_count == 0:
        cursor.execute(
            'INSERT INTO report_templates (company_name, report_title, footer_text) VALUES (?, ?, ?)',
            ('水质检测中心', '水质检测报告', '检测人:______  审核人:______')
        )
        print("默认报告模板已创建")

    # 创建默认分组
    cursor.execute('SELECT COUNT(*) FROM indicator_groups')
    if cursor.fetchone()[0] == 0:
        default_groups = [
            ('理化指标', 1, 1),
            ('微生物指标', 2, 1),
            ('重金属指标', 3, 1)
        ]
        cursor.executemany(
            'INSERT INTO indicator_groups (name, sort_order, is_system) VALUES (?, ?, ?)',
            default_groups
        )
        print("默认检测项目分组已创建")

    conn.commit()

def create_indexes():
    """创建索引优化查询性能"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 为常用查询字段创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_sample_number ON reports(sample_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_report_number ON reports(report_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_operation_logs_created_at ON operation_logs(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicators_group_id ON indicators(group_id)')

    conn.commit()
    conn.close()
    print("数据库索引创建成功！")

if __name__ == '__main__':
    init_database()
    create_indexes()
