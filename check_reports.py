#!/usr/bin/env python3
"""检查所有报告的template_id"""
import sqlite3

DATABASE_PATH = 'database/water_quality_v2.db'

conn = sqlite3.connect(DATABASE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查询所有报告
cursor.execute("""
    SELECT id, report_number, sample_number, template_id, created_at
    FROM reports
    ORDER BY id DESC
    LIMIT 20
""")

reports = cursor.fetchall()

print(f"数据库中的报告 (最近20个):\n")
print(f"{'ID':<5} {'报告编号':<20} {'样品编号':<15} {'模板ID':<8} {'创建时间'}")
print("-" * 80)

for r in reports:
    template_id = r['template_id'] if r['template_id'] else '(无)'
    print(f"{r['id']:<5} {r['report_number']:<20} {r['sample_number']:<15} {template_id:<8} {r['created_at']}")

# 统计
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN template_id IS NULL THEN 1 ELSE 0 END) as no_template,
        SUM(CASE WHEN template_id IS NOT NULL THEN 1 ELSE 0 END) as has_template
    FROM reports
""")

stats = cursor.fetchone()
print(f"\n统计:")
print(f"  总报告数: {stats['total']}")
print(f"  有模板: {stats['has_template']}")
print(f"  无模板: {stats['no_template']}")

# 查看可用模板
cursor.execute("SELECT id, name FROM excel_report_templates WHERE is_active = 1")
templates = cursor.fetchall()

print(f"\n可用的Excel报告模板 ({len(templates)} 个):")
for t in templates:
    print(f"  ID {t['id']}: {t['name']}")

conn.close()
