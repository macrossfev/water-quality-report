#!/usr/bin/env python3
"""调试脚本：排查报告20260203编4的问题"""
import sqlite3
import json

DATABASE_PATH = 'database/water_quality_v2.db'

def debug_string_replacement():
    """调试字符串替换功能"""
    print("=" * 60)
    print("1. 检查模板字段映射中的 original_cell_text")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查询模板1的第二页字段映射
    cursor.execute("""
        SELECT field_name, field_code, cell_address, original_cell_text, sheet_name
        FROM template_field_mappings
        WHERE template_id = 1 AND sheet_name LIKE '%第二页%'
        ORDER BY cell_address
        LIMIT 15
    """)

    fields = cursor.fetchall()
    print(f"\n找到 {len(fields)} 个字段映射（第二页）：\n")

    for field in fields:
        print(f"字段名: {field['field_name']}")
        print(f"  字段代号: {field['field_code']}")
        print(f"  单元格: {field['sheet_name']}!{field['cell_address']}")
        print(f"  原始文本: {repr(field['original_cell_text'])}")
        print()

    # 统计original_cell_text的填充情况
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN original_cell_text IS NOT NULL AND original_cell_text != '' THEN 1 ELSE 0 END) as has_text,
            SUM(CASE WHEN field_code IS NOT NULL AND field_code != '' THEN 1 ELSE 0 END) as has_code
        FROM template_field_mappings
        WHERE template_id = 1
    """)

    stats = cursor.fetchone()
    print(f"\n模板1字段统计:")
    print(f"  总字段数: {stats['total']}")
    print(f"  有 original_cell_text: {stats['has_text']}")
    print(f"  有 field_code: {stats['has_code']}")

    conn.close()

def debug_report_data():
    """调试报告20260203编4的数据"""
    print("\n" + "=" * 60)
    print("2. 检查报告 20260203编4 的数据")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查找报告
    cursor.execute("""
        SELECT id, report_number, sample_number, template_id
        FROM reports
        WHERE report_number LIKE '%20260203编4%' OR report_number LIKE '%20260203%4%'
    """)

    report = cursor.fetchone()

    if not report:
        # 如果找不到，列出所有报告
        cursor.execute("SELECT id, report_number FROM reports ORDER BY id DESC LIMIT 10")
        all_reports = cursor.fetchall()
        print(f"\n❌ 未找到报告 20260203编4")
        print(f"\n数据库中的报告:")
        for r in all_reports:
            print(f"  - ID: {r['id']}, 编号: {r['report_number']}")
        conn.close()
        return

    report_id = report['id']
    print(f"\n✓ 找到报告:")
    print(f"  ID: {report_id}")
    print(f"  报告编号: {report['report_number']}")
    print(f"  样品编号: {report['sample_number']}")
    print(f"  模板ID: {report['template_id']}")

    # 查询检测数据
    cursor.execute("""
        SELECT rd.id, rd.measured_value, i.name, i.unit, i.limit_value, i.detection_method
        FROM report_data rd
        JOIN indicators i ON rd.indicator_id = i.id
        WHERE rd.report_id = ?
        ORDER BY i.name
    """, (report_id,))

    detection_items = cursor.fetchall()

    print(f"\n检测数据 ({len(detection_items)} 项):")
    for item in detection_items:
        print(f"  - {item['name']}: {item['measured_value']} {item['unit'] or ''}")
        print(f"    标准限值: {item['limit_value']}")
        print(f"    检测方法: {item['detection_method']}")

    # 检查模板的检测数据列映射
    template_id = report['template_id']
    cursor.execute("""
        SELECT field_name, field_type, sheet_name, cell_address, column_mapping
        FROM template_field_mappings
        WHERE template_id = ? AND field_type = 'detection_column'
        ORDER BY sheet_name, cell_address
    """, (template_id,))

    columns = cursor.fetchall()

    print(f"\n模板 {template_id} 的检测数据列映射 ({len(columns)} 个):")

    # 按sheet分组显示
    from collections import defaultdict
    by_sheet = defaultdict(list)
    for col in columns:
        by_sheet[col['sheet_name']].append(col)

    for sheet_name, cols in sorted(by_sheet.items()):
        print(f"\n  {sheet_name}:")
        for col in cols:
            print(f"    {col['cell_address']}: {col['column_mapping']} [{col['field_name']}]")

    # 检查数据区结束标记
    cursor.execute("""
        SELECT field_name, field_type, sheet_name, cell_address
        FROM template_field_mappings
        WHERE template_id = ? AND field_type = 'control_mark'
    """, (template_id,))

    marks = cursor.fetchall()

    if marks:
        print(f"\n控制标记 ({len(marks)} 个):")
        for mark in marks:
            print(f"  {mark['sheet_name']}!{mark['cell_address']}: {mark['field_name']}")
    else:
        print("\n⚠ 未找到控制标记（数据区结束标记）")

    conn.close()

def check_template_examples():
    """检查模板中的字段示例"""
    print("\n" + "=" * 60)
    print("3. 检查有 field_code 的字段示例")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT template_id, field_name, field_code, cell_address, sheet_name, original_cell_text
        FROM template_field_mappings
        WHERE field_code IS NOT NULL AND field_code != ''
        ORDER BY template_id, sheet_name, cell_address
        LIMIT 20
    """)

    fields = cursor.fetchall()
    print(f"\n找到 {len(fields)} 个有 field_code 的字段:\n")

    for field in fields:
        print(f"模板{field['template_id']} - {field['sheet_name']}!{field['cell_address']}")
        print(f"  字段名: {field['field_name']}")
        print(f"  字段代号: {field['field_code']}")
        print(f"  原始文本: {repr(field['original_cell_text'][:100] if field['original_cell_text'] else None)}")
        print()

    conn.close()

if __name__ == '__main__':
    debug_string_replacement()
    debug_report_data()
    check_template_examples()
