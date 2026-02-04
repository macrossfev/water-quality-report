#!/usr/bin/env python3
import sqlite3

DATABASE_PATH = 'database/water_quality_v2.db'

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

# 检查所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print(f"数据库中的表 ({len(tables)} 个):")
for table in tables:
    table_name = table[0]

    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    # 获取记录数
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]

    print(f"\n{table_name} ({count} 行):")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

conn.close()
