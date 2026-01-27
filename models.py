from datetime import datetime
import sqlite3
import os

DATABASE_PATH = 'database/water_quality.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """初始化数据库表结构"""
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 水质指标表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            unit TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 检测方法表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detection_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_id INTEGER NOT NULL,
            method_name TEXT NOT NULL,
            standard_code TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id) ON DELETE CASCADE
        )
    ''')

    # 限值标准表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS limit_standards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_id INTEGER NOT NULL,
            standard_name TEXT NOT NULL,
            min_value REAL,
            max_value REAL,
            exact_value REAL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id) ON DELETE CASCADE
        )
    ''')

    # 报告表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_name TEXT NOT NULL,
            sample_location TEXT,
            sample_date DATE,
            sampler TEXT,
            weather TEXT,
            temperature TEXT,
            remark TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 报告数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL,
            detection_method_id INTEGER,
            measured_value TEXT,
            limit_standard_id INTEGER,
            is_qualified BOOLEAN,
            remark TEXT,
            FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id),
            FOREIGN KEY (detection_method_id) REFERENCES detection_methods (id),
            FOREIGN KEY (limit_standard_id) REFERENCES limit_standards (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("数据库初始化成功！")

if __name__ == '__main__':
    init_database()
