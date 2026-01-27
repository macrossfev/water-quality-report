"""
水质检测报告系统 - 数据库迁移脚本
用于更新现有数据库结构以支持新功能
"""
import sqlite3
import os

DATABASE_PATH = 'database/water_quality_v2.db'

def get_column_names(cursor, table_name):
    """获取表的所有列名"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

def migrate_database():
    """执行数据库迁移"""
    if not os.path.exists(DATABASE_PATH):
        print(f"数据库文件不存在: {DATABASE_PATH}")
        print("请先运行 models_v2.py 初始化数据库")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("开始数据库迁移...")

    # 1. 迁移 sample_types 表
    print("\n检查 sample_types 表...")
    sample_types_columns = get_column_names(cursor, 'sample_types')
    if 'remark' not in sample_types_columns:
        print("  添加 remark 字段...")
        cursor.execute('ALTER TABLE sample_types ADD COLUMN remark TEXT')
        print("  ✓ 已添加 remark 字段")
    else:
        print("  - remark 字段已存在")

    # 2. 迁移 indicator_groups 表
    print("\n检查 indicator_groups 表...")
    indicator_groups_columns = get_column_names(cursor, 'indicator_groups')
    if 'is_system' not in indicator_groups_columns:
        print("  添加 is_system 字段...")
        cursor.execute('ALTER TABLE indicator_groups ADD COLUMN is_system BOOLEAN DEFAULT 0')
        print("  ✓ 已添加 is_system 字段")

        # 将现有的默认分组标记为系统分组
        print("  更新现有默认分组为系统分组...")
        cursor.execute('''
            UPDATE indicator_groups
            SET is_system = 1
            WHERE name IN ('理化指标', '微生物指标', '重金属指标')
        ''')
        print("  ✓ 已更新默认分组")
    else:
        print("  - is_system 字段已存在")

    # 3. 迁移 indicators 表
    print("\n检查 indicators 表...")
    indicators_columns = get_column_names(cursor, 'indicators')

    if 'limit_value' not in indicators_columns:
        print("  添加 limit_value 字段...")
        cursor.execute('ALTER TABLE indicators ADD COLUMN limit_value TEXT')
        print("  ✓ 已添加 limit_value 字段")
    else:
        print("  - limit_value 字段已存在")

    if 'detection_method' not in indicators_columns:
        print("  添加 detection_method 字段...")
        cursor.execute('ALTER TABLE indicators ADD COLUMN detection_method TEXT')
        print("  ✓ 已添加 detection_method 字段")
    else:
        print("  - detection_method 字段已存在")

    if 'remark' not in indicators_columns:
        print("  添加 remark 字段...")
        cursor.execute('ALTER TABLE indicators ADD COLUMN remark TEXT')
        print("  ✓ 已添加 remark 字段")
    else:
        print("  - remark 字段已存在")

    # 提交更改
    conn.commit()
    conn.close()

    print("\n数据库迁移完成！")
    print("\n迁移总结:")
    print("  - sample_types 表: 添加 remark 字段")
    print("  - indicator_groups 表: 添加 is_system 字段")
    print("  - indicators 表: 添加 limit_value, detection_method, remark 字段")

if __name__ == '__main__':
    migrate_database()
