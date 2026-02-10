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

    # ==================== 客户管理表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspected_unit TEXT NOT NULL,
            water_plant TEXT,
            unit_address TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            email TEXT,
            remark TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # ==================== 原始数据列名配置表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data_column_schema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            column_name TEXT NOT NULL UNIQUE,
            column_order INTEGER NOT NULL,
            data_type TEXT NOT NULL CHECK(data_type IN ('text', 'numeric', 'date')),
            is_base_field BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 原始数据记录表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_number TEXT NOT NULL UNIQUE,
            report_number TEXT,
            company_name TEXT,
            plant_name TEXT,
            sample_type TEXT,
            sampling_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 原始数据检测值表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            value TEXT,
            FOREIGN KEY (record_id) REFERENCES raw_data_records (id) ON DELETE CASCADE,
            UNIQUE(record_id, column_name)
        )
    ''')

    # ==================== 原始数据字段映射表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data_field_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_field_name TEXT NOT NULL UNIQUE,
            indicator_id INTEGER NOT NULL,
            indicator_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id) ON DELETE CASCADE
        )
    ''')

    # ==================== 导出模板分类表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS export_template_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 导出模板表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS export_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            sample_type_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES export_template_categories (id) ON DELETE SET NULL,
            FOREIGN KEY (sample_type_id) REFERENCES sample_types (id) ON DELETE SET NULL,
            UNIQUE(category_id, name)
        )
    ''')

    # ==================== 导出模板-列关联表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS export_template_columns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            column_order INTEGER DEFAULT 0,
            FOREIGN KEY (template_id) REFERENCES export_templates (id) ON DELETE CASCADE,
            UNIQUE(template_id, column_name)
        )
    ''')

    # ==================== 数据库迁移 ====================
    # 检查export_templates表是否有sample_type_id列
    cursor.execute("PRAGMA table_info(export_templates)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'sample_type_id' not in columns:
        print("正在迁移export_templates表，添加sample_type_id列...")
        cursor.execute('ALTER TABLE export_templates ADD COLUMN sample_type_id INTEGER')
        print("export_templates表迁移完成！")

    # 检查reports表是否有detection_items_description和attachment_info列
    cursor.execute("PRAGMA table_info(reports)")
    report_columns = [row[1] for row in cursor.fetchall()]

    if 'detection_items_description' not in report_columns:
        print("正在迁移reports表，添加detection_items_description列...")
        cursor.execute('ALTER TABLE reports ADD COLUMN detection_items_description TEXT')
        print("reports表迁移完成（detection_items_description）！")

    if 'attachment_info' not in report_columns:
        print("正在迁移reports表，添加attachment_info列...")
        cursor.execute('ALTER TABLE reports ADD COLUMN attachment_info TEXT')
        print("reports表迁移完成（attachment_info）！")

    # 检查sample_types表是否有version和updated_at列
    cursor.execute("PRAGMA table_info(sample_types)")
    sample_type_columns = [row[1] for row in cursor.fetchall()]

    if 'version' not in sample_type_columns:
        print("正在迁移sample_types表，添加version列...")
        cursor.execute('ALTER TABLE sample_types ADD COLUMN version INTEGER DEFAULT 1')
        print("sample_types表迁移完成（version）！")

    if 'updated_at' not in sample_type_columns:
        print("正在迁移sample_types表，添加updated_at列...")
        # SQLite不支持ALTER TABLE时使用CURRENT_TIMESTAMP，需要分两步
        cursor.execute('ALTER TABLE sample_types ADD COLUMN updated_at TIMESTAMP')
        # 为现有记录设置默认值
        cursor.execute("UPDATE sample_types SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        print("sample_types表迁移完成（updated_at）！")

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

    # 原始数据相关索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_sample_number ON raw_data_records(sample_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_sampling_date ON raw_data_records(sampling_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_company_name ON raw_data_records(company_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_plant_name ON raw_data_records(plant_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_sample_type ON raw_data_records(sample_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_values_record_id ON raw_data_values(record_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_export_template_columns_template_id ON export_template_columns(template_id)')

    conn.commit()
    conn.close()
    print("数据库索引创建成功！")

if __name__ == '__main__':
    init_database()
    create_indexes()
