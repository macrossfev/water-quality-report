#!/usr/bin/env python3
"""
添加报告表的新字段
"""
import sqlite3
from models_v2 import DATABASE_PATH

def add_report_fields():
    """添加新的报告字段"""
    print("=" * 60)
    print("添加报告表新字段")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()

    # 要添加的字段列表
    new_fields = [
        ("report_date", "DATE", "报告编制日期"),
        ("sample_source", "TEXT", "样品来源"),
        ("sampler", "TEXT", "采样人"),
        ("sampling_date", "DATE", "采样日期"),
        ("sampling_basis", "TEXT", "采样依据"),
        ("sample_received_date", "DATE", "收样日期"),
        ("sampling_location", "TEXT", "采样地点"),
        ("sample_status", "TEXT", "样品状态"),
        ("product_standard", "TEXT", "产品标准"),
        ("test_conclusion", "TEXT", "检测结论"),
        ("additional_info", "TEXT", "附加信息")
    ]

    # 检查并添加字段
    for field_name, field_type, description in new_fields:
        try:
            # 检查字段是否已存在
            cursor.execute(f"PRAGMA table_info(reports)")
            columns = [col[1] for col in cursor.fetchall()]

            if field_name not in columns:
                print(f"\n添加字段: {field_name} ({description})...")
                cursor.execute(f"ALTER TABLE reports ADD COLUMN {field_name} {field_type}")
                print(f"  ✓ 成功添加字段: {field_name}")
            else:
                print(f"\n字段已存在: {field_name} ({description})")
        except Exception as e:
            print(f"  ✗ 添加字段 {field_name} 失败: {e}")

    conn.commit()

    # 验证字段
    print("\n" + "=" * 60)
    print("验证reports表结构:")
    print("=" * 60)
    cursor.execute("PRAGMA table_info(reports)")
    columns = cursor.fetchall()

    print(f"\n共 {len(columns)} 个字段:\n")
    for col in columns:
        print(f"  {col[1]:25} {col[2]:10}")

    conn.close()

    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)

if __name__ == "__main__":
    add_report_fields()
