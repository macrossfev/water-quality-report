#!/usr/bin/env python3
"""
添加审核历史表
"""
import sqlite3
from models_v2 import DATABASE_PATH

def create_review_history_table():
    """创建审核历史表"""
    print("=" * 60)
    print("创建审核历史表")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()

    # 创建审核历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS review_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            review_status TEXT NOT NULL,
            review_comment TEXT,
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
            FOREIGN KEY (reviewer_id) REFERENCES users(id)
        )
    ''')

    # 创建索引以提高查询性能
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_review_history_report_id
        ON review_history(report_id)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_review_history_reviewed_at
        ON review_history(reviewed_at)
    ''')

    conn.commit()

    # 验证表结构
    print("\n审核历史表结构:")
    cursor.execute("PRAGMA table_info(review_history)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]:20} {col[2]:10}")

    # 检查索引
    print("\n索引:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='review_history'")
    indexes = cursor.fetchall()
    for idx in indexes:
        print(f"  {idx[0]}")

    conn.close()

    print("\n" + "=" * 60)
    print("审核历史表创建完成！")
    print("=" * 60)

if __name__ == "__main__":
    create_review_history_table()
