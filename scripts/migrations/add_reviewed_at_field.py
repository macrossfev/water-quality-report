#!/usr/bin/env python3
"""
添加reviewed_at字段到reports表
"""
import sqlite3
from models_v2 import DATABASE_PATH

def add_reviewed_at_field():
    """添加审核时间字段"""
    print("=" * 60)
    print("添加reviewed_at字段到reports表")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()

    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(reports)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'reviewed_at' not in columns:
            print("\n添加字段: reviewed_at...")
            cursor.execute("ALTER TABLE reports ADD COLUMN reviewed_at TIMESTAMP")
            conn.commit()
            print("  ✓ 成功添加字段: reviewed_at")
        else:
            print("\n字段已存在: reviewed_at")

    except Exception as e:
        print(f"  ✗ 添加字段失败: {e}")
        conn.rollback()

    # 验证字段
    print("\n验证reports表结构:")
    cursor.execute("PRAGMA table_info(reports)")
    columns = cursor.fetchall()

    print(f"\n共 {len(columns)} 个字段")
    for col in columns:
        if col[1] == 'reviewed_at':
            print(f"  ✓ {col[1]:25} {col[2]:10}")

    conn.close()

    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)

if __name__ == "__main__":
    add_reviewed_at_field()
