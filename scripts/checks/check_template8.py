#!/usr/bin/env python3
"""检查模板8的字段映射"""
import sqlite3

DATABASE_PATH = 'database/water_quality_v2.db'

conn = sqlite3.connect(DATABASE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查询模板8的信息
cursor.execute("SELECT * FROM excel_report_templates WHERE id = 8")
template = cursor.fetchone()

print(f"模板信息:")
print(f"  ID: {template['id']}")
print(f"  名称: {template['name']}")
print(f"  模板文件: {template['template_file_path']}")

# 查询字段映射
cursor.execute("""
    SELECT id, field_name, field_type, sheet_name, cell_address, column_mapping, original_cell_text, field_code
    FROM template_field_mappings
    WHERE template_id = 8
    ORDER BY sheet_name, cell_address
""")

fields = cursor.fetchall()

print(f"\n字段映射总数: {len(fields)}")

# 按类型分组
from collections import defaultdict
by_type = defaultdict(list)
for field in fields:
    by_type[field['field_type']].append(field)

print(f"\n字段类型统计:")
for field_type, items in sorted(by_type.items()):
    print(f"  {field_type}: {len(items)} 个")

# 特别关注 detection_column 类型
print(f"\n检测数据列映射 (detection_column):")
detection_cols = by_type.get('detection_column', [])

if detection_cols:
    by_sheet = defaultdict(list)
    for col in detection_cols:
        by_sheet[col['sheet_name']].append(col)

    for sheet_name, cols in sorted(by_sheet.items()):
        print(f"\n  工作表: {sheet_name}")
        for col in cols:
            print(f"    {col['cell_address']}: {col['column_mapping']} [{col['field_name']}]")
else:
    print("  ❌ 没有找到任何 detection_column 类型的字段！")
    print("\n  这就是为什么检测数据没有被填充的原因！")

# 查找包含 #dt_ 的字段
print(f"\n查找包含 #dt_ 的字段标记:")
cursor.execute("""
    SELECT field_name, field_type, sheet_name, cell_address, field_code, original_cell_text
    FROM template_field_mappings
    WHERE template_id = 8 AND (field_code LIKE '%dt_%' OR original_cell_text LIKE '%#dt_%')
""")

dt_fields = cursor.fetchall()

if dt_fields:
    print(f"  找到 {len(dt_fields)} 个:")
    for field in dt_fields:
        print(f"    {field['sheet_name']}!{field['cell_address']}: {field['field_name']}")
        print(f"      类型: {field['field_type']}")
        print(f"      field_code: {field['field_code']}")
        print(f"      original_cell_text: {repr(field['original_cell_text'][:50] if field['original_cell_text'] else None)}")
else:
    print("  ❌ 没有找到任何包含 #dt_ 的字段！")

conn.close()
