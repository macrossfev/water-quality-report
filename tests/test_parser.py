#!/usr/bin/env python3
"""测试模板字段解析器"""
from template_field_parser import TemplateFieldParser
from field_code_mapping import FieldCodeMapping

# 测试代号解析
print("=" * 60)
print("测试 FieldCodeMapping")
print("=" * 60)

test_codes = ['[#dt_index]', '[#dt_name]', '[#dt_unit]', '[#dt_result]', '[#dt_limit]', '[#dt_method]', '[#dt_end]']

for code in test_codes:
    info = FieldCodeMapping.get_field_info(code)
    print(f"\n{code}:")
    if info:
        print(f"  类型: {info['type']}")
        print(f"  显示名: {info['display_name']}")
        if 'column_mapping' in info:
            print(f"  列映射: {info['column_mapping']}")
    else:
        print(f"  ❌ 未识别")

# 测试字段解析
print("\n" + "=" * 60)
print("测试 TemplateFieldParser")
print("=" * 60)

for code in test_codes:
    result = TemplateFieldParser.parse_field(code)
    print(f"\n{code}:")
    print(f"  field_name: {result['field_name']}")
    print(f"  field_type: {result['field_type']}")
    print(f"  display_name: {result['display_name']}")
    if result.get('column_mapping'):
        print(f"  column_mapping: {result['column_mapping']}")
    if result.get('control_type'):
        print(f"  control_type: {result['control_type']}")

# 测试从Excel文件解析
print("\n" + "=" * 60)
print("测试从Excel文件解析")
print("=" * 60)

template_path = 'templates/excel_reports/出厂水_20260203_002830.xlsx'
fields = TemplateFieldParser.extract_template_fields(template_path)

print(f"\n总共解析到 {len(fields)} 个字段")

# 查找 detection_column 类型的字段
detection_cols = [f for f in fields if f.get('field_type') == 'detection_column']
print(f"\ndetection_column 类型: {len(detection_cols)} 个")
for field in detection_cols:
    print(f"  {field['sheet_name']}!{field['cell_address']}: {field['field_name']} -> {field.get('column_mapping')}")

# 查找 control_mark 类型的字段
control_marks = [f for f in fields if f.get('field_type') == 'control_mark']
print(f"\ncontrol_mark 类型: {len(control_marks)} 个")
for field in control_marks:
    print(f"  {field['sheet_name']}!{field['cell_address']}: {field['field_name']}")
