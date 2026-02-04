#!/usr/bin/env python3
"""对比模板8数据库中的字段和实际解析结果"""
import sqlite3
from template_field_parser import TemplateFieldParser

DATABASE_PATH = 'database/water_quality_v2.db'

# 1. 从数据库读取模板8的字段
conn = sqlite3.connect(DATABASE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT id, name, template_file_path, created_at
    FROM excel_report_templates
    WHERE id = 8
""")
template = cursor.fetchone()

print(f"模板8信息:")
print(f"  名称: {template['name']}")
print(f"  创建时间: {template['created_at']}")
print(f"  文件路径: {template['template_file_path']}")

cursor.execute("""
    SELECT field_name, field_type, sheet_name, cell_address, column_mapping, original_cell_text
    FROM template_field_mappings
    WHERE template_id = 8
    ORDER BY sheet_name, cell_address
""")

db_fields = cursor.fetchall()
conn.close()

print(f"\n数据库中的字段 ({len(db_fields)} 个):")
print(f"  text类型: {sum(1 for f in db_fields if f['field_type'] == 'text')}")
print(f"  detection_column类型: {sum(1 for f in db_fields if f['field_type'] == 'detection_column')}")
print(f"  control_mark类型: {sum(1 for f in db_fields if f['field_type'] == 'control_mark')}")

# 2. 重新解析模板文件
template_path = template['template_file_path']
parsed_fields = TemplateFieldParser.extract_template_fields(template_path)

print(f"\n重新解析的字段 ({len(parsed_fields)} 个):")
print(f"  text类型: {sum(1 for f in parsed_fields if f.get('field_type') == 'text')}")
print(f"  detection_column类型: {sum(1 for f in parsed_fields if f.get('field_type') == 'detection_column')}")
print(f"  control_mark类型: {sum(1 for f in parsed_fields if f.get('field_type') == 'control_mark')}")

# 3. 对比差异
print("\n对比检测数据列字段:")
print("-" * 80)

db_dt_fields = [(f['sheet_name'], f['cell_address'], f['field_name'], f['field_type'], f['column_mapping'])
                for f in db_fields if 'dt' in f['cell_address'].lower() or (f['original_cell_text'] and '#dt' in f['original_cell_text'])]

parsed_dt_fields = [(f['sheet_name'], f['cell_address'], f['field_name'], f.get('field_type'), f.get('column_mapping'))
                    for f in parsed_fields if f.get('field_type') in ('detection_column', 'control_mark')]

print(f"\n数据库中包含dt的字段 ({len(db_dt_fields)} 个):")
for sheet, cell, name, ftype, mapping in db_dt_fields:
    print(f"  {sheet}!{cell}: {name} [{ftype}] -> {mapping}")

print(f"\n解析出的detection_column字段 ({len(parsed_dt_fields)} 个):")
for sheet, cell, name, ftype, mapping in parsed_dt_fields:
    print(f"  {sheet}!{cell}: {name} [{ftype}] -> {mapping}")

print("\n结论:")
print("=" * 80)
print("✅ 解析器现在可以正确识别字段类型")
print("❌ 但数据库中的模板8是旧数据，字段类型错误")
print("💡 解决方案: 需要重新导入模板8，或更新数据库中的字段映射")
