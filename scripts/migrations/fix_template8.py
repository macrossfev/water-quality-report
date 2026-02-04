#!/usr/bin/env python3
"""修复模板8的字段映射"""
import sqlite3
from template_field_parser import TemplateFieldParser

DATABASE_PATH = 'database/water_quality_v2.db'
TEMPLATE_ID = 8

def fix_template_fields():
    """重新解析并更新模板8的字段映射"""

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取模板信息
    cursor.execute("SELECT * FROM excel_report_templates WHERE id = ?", (TEMPLATE_ID,))
    template = cursor.fetchone()

    if not template:
        print(f"❌ 模板ID {TEMPLATE_ID} 不存在")
        conn.close()
        return

    print(f"模板信息:")
    print(f"  ID: {template['id']}")
    print(f"  名称: {template['name']}")
    print(f"  文件路径: {template['template_file_path']}")

    # 重新解析模板文件
    template_path = template['template_file_path']
    print(f"\n正在重新解析模板文件...")

    try:
        fields = TemplateFieldParser.extract_template_fields(template_path)
        print(f"✓ 解析完成，找到 {len(fields)} 个字段")
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        conn.close()
        return

    # 统计字段类型
    from collections import Counter
    type_counts = Counter(f.get('field_type', 'text') for f in fields)
    print(f"\n字段类型统计:")
    for ftype, count in type_counts.items():
        print(f"  {ftype}: {count} 个")

    # 删除旧的字段映射
    print(f"\n删除旧的字段映射...")
    cursor.execute("DELETE FROM template_field_mappings WHERE template_id = ?", (TEMPLATE_ID,))
    print(f"✓ 已删除")

    # 插入新的字段映射
    print(f"\n插入新的字段映射...")
    inserted = 0

    for field in fields:
        try:
            cursor.execute(
                '''INSERT INTO template_field_mappings
                   (template_id, field_name, field_display_name, field_type,
                    sheet_name, cell_address, placeholder, default_value, is_required,
                    original_cell_text, field_code, is_reference, column_mapping)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (TEMPLATE_ID,
                 field['field_name'],
                 field['display_name'],
                 field.get('field_type', 'text'),
                 field['sheet_name'],
                 field['cell_address'],
                 field.get('placeholder', ''),
                 field.get('default_value', ''),
                 1 if field.get('is_required', True) else 0,
                 field.get('original_value', ''),
                 field.get('field_code'),
                 1 if field.get('is_reference', False) else 0,
                 field.get('column_mapping', ''))
            )
            inserted += 1
        except Exception as e:
            print(f"  ⚠ 插入字段失败: {field['field_name']} - {e}")

    print(f"✓ 已插入 {inserted} 个字段映射")

    # 提交更改
    conn.commit()

    # 验证更新结果
    print(f"\n验证更新结果...")
    cursor.execute("""
        SELECT field_type, COUNT(*) as count
        FROM template_field_mappings
        WHERE template_id = ?
        GROUP BY field_type
    """, (TEMPLATE_ID,))

    results = cursor.fetchall()
    print(f"数据库中的字段类型:")
    for row in results:
        print(f"  {row['field_type']}: {row['count']} 个")

    # 特别检查 detection_column
    cursor.execute("""
        SELECT sheet_name, cell_address, field_name, column_mapping
        FROM template_field_mappings
        WHERE template_id = ? AND field_type = 'detection_column'
        ORDER BY sheet_name, cell_address
    """, (TEMPLATE_ID,))

    dt_cols = cursor.fetchall()
    print(f"\n检测数据列 (detection_column): {len(dt_cols)} 个")
    for col in dt_cols:
        print(f"  {col['sheet_name']}!{col['cell_address']}: {col['field_name']} -> {col['column_mapping']}")

    # 检查控制标记
    cursor.execute("""
        SELECT sheet_name, cell_address, field_name
        FROM template_field_mappings
        WHERE template_id = ? AND field_type = 'control_mark'
        ORDER BY sheet_name, cell_address
    """, (TEMPLATE_ID,))

    marks = cursor.fetchall()
    print(f"\n控制标记 (control_mark): {len(marks)} 个")
    for mark in marks:
        print(f"  {mark['sheet_name']}!{mark['cell_address']}: {mark['field_name']}")

    conn.close()

    print(f"\n" + "=" * 80)
    print(f"✅ 模板8字段映射更新完成！")
    print(f"现在可以正确填充检测数据了。")
    print(f"=" * 80)

if __name__ == '__main__':
    fix_template8()
