#!/usr/bin/env python3
"""
添加样品类型默认字段
为sample_types表添加默认样品状态、采样依据、产品标准、检测项目、检测结论字段
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from models_v2 import DATABASE_PATH


def add_sample_type_defaults():
    """添加样品类型默认字段"""
    print("=" * 60)
    print("添加样品类型默认字段")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()

    new_fields = [
        ("default_sample_status", "TEXT", "默认样品状态"),
        ("default_sampling_basis", "TEXT", "默认采样依据"),
        ("default_product_standard", "TEXT", "默认产品标准"),
        ("default_detection_items", "TEXT", "默认检测项目"),
        ("default_test_conclusion", "TEXT", "默认检测结论"),
    ]

    cursor.execute("PRAGMA table_info(sample_types)")
    columns = [col[1] for col in cursor.fetchall()]

    for field_name, field_type, description in new_fields:
        try:
            if field_name not in columns:
                print(f"\n添加字段: {field_name} ({description})...")
                cursor.execute(f"ALTER TABLE sample_types ADD COLUMN {field_name} {field_type}")
                print(f"  ✓ 成功添加字段: {field_name}")
            else:
                print(f"\n字段已存在: {field_name} ({description})")
        except Exception as e:
            print(f"  ✗ 添加字段 {field_name} 失败: {e}")

    conn.commit()

    # 验证字段
    print("\n" + "=" * 60)
    print("验证sample_types表结构:")
    print("=" * 60)
    cursor.execute("PRAGMA table_info(sample_types)")
    columns = cursor.fetchall()

    print(f"\n共 {len(columns)} 个字段:\n")
    for col in columns:
        print(f"  {col[1]:30} {col[2]:10}")

    conn.close()

    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)


if __name__ == "__main__":
    add_sample_type_defaults()
