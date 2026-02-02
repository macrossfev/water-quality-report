#!/usr/bin/env python3
"""
数据库迁移脚本：为 raw_data_records 表添加 report_number 字段
"""
import sqlite3
import os

def migrate():
    db_path = 'water_quality.db'

    if not os.path.exists(db_path):
        print(f"数据库文件 {db_path} 不存在")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_data_records'")
        if not cursor.fetchone():
            print("✓ raw_data_records 表不存在，将在应用启动时自动创建")
            return

        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(raw_data_records)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'report_number' in columns:
            print("✓ report_number 字段已存在，无需迁移")
            return

        # 添加 report_number 字段
        print("开始添加 report_number 字段...")
        cursor.execute('''
            ALTER TABLE raw_data_records
            ADD COLUMN report_number TEXT
        ''')

        conn.commit()
        print("✓ 成功添加 report_number 字段到 raw_data_records 表")

    except Exception as e:
        print(f"✗ 迁移失败: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
