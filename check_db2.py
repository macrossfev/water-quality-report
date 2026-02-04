#!/usr/bin/env python3
import sqlite3
import os

db_path = 'reports.db'
print(f"数据库路径: {os.path.abspath(db_path)}")
print(f"文件大小: {os.path.getsize(db_path)} bytes")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

if tables:
    print(f"\n找到 {len(tables)} 个表:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count} 行")
else:
    print("\n数据库中没有表！")

conn.close()
