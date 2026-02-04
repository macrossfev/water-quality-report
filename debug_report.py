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
        WHERE template_id = 1 AND sheet_name = '02第二页'
        ORDER BY cell_address
        LIMIT 10
    """)

    fields = cursor.fetchall()
    print(f"\n找到 {len(fields)} 个字段映射：\n")

    for field in fields:
        print(f"字段名: {field['field_name']}")
        print(f"  字段代号: {field['field_code']}")
        print(f"  单元格: {field['sheet_name']}!{field['cell_address']}")
        print(f"  原始文本: {field['original_cell_text']}")
        print()

    conn.close()

def debug_report_data():
    """调试报告20260203编4的数据"""
    print("=" * 60)
    print("2. 检查报告 20260203编4 的数据")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查找报告
    cursor.execute("""
        SELECT id, report_number, sample_name, template_id
        FROM reports
        WHERE report_number LIKE '%20260203编4%'
    """)

    report = cursor.fetchone()

    if not report:
        print("\n❌ 未找到报告 20260203编4")
        conn.close()
        return

    report_id = report['id']
    print(f"\n✓ 找到报告:")
    print(f"  ID: {report_id}")
    print(f"  报告编号: {report['report_number']}")
    print(f"  样品名称: {report['sample_name']}")
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
    for col in columns:
        print(f"  {col['sheet_name']}!{col['cell_address']}: {col['column_mapping']} [{col['field_name']}]")

    # 检查数据区结束标记
    cursor.execute("""
        SELECT field_name, field_type, sheet_name, cell_address, control_type
        FROM template_field_mappings
        WHERE template_id = ? AND field_type = 'control_mark'
    """, (template_id,))

    marks = cursor.fetchall()

    if marks:
        print(f"\n控制标记 ({len(marks)} 个):")
        for mark in marks:
            print(f"  {mark['sheet_name']}!{mark['cell_address']}: {mark.get('control_type', 'N/A')}")
    else:
        print("\n⚠ 未找到控制标记（数据区结束标记）")

    conn.close()

def check_template_field_parser():
    """检查模板解析是否正确保存了original_cell_text"""
    print("=" * 60)
    print("3. 检查所有模板的 original_cell_text 字段")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN original_cell_text IS NOT NULL AND original_cell_text != '' THEN 1 ELSE 0 END) as has_text
        FROM template_field_mappings
    """)

    stats = cursor.fetchone()
    print(f"\n字段映射统计:")
    print(f"  总字段数: {stats['total']}")
    print(f"  有 original_cell_text: {stats['has_text']}")
    print(f"  缺失率: {(stats['total'] - stats['has_text']) / stats['total'] * 100:.1f}%")

    # 查看几个典型字段
    cursor.execute("""
        SELECT template_id, field_name, field_code, original_cell_text
        FROM template_field_mappings
        WHERE field_code IS NOT NULL
        LIMIT 10
    """)

    fields = cursor.fetchall()
    print(f"\n典型字段示例 (有 field_code 的):")
    for field in fields:
        print(f"  模板{field['template_id']}: {field['field_name']} [{field['field_code']}]")
        print(f"    原始文本: {field['original_cell_text'][:80] if field['original_cell_text'] else '(空)'}")

    conn.close()

if __name__ == '__main__':
    debug_string_replacement()
    print("\n")
    debug_report_data()
    print("\n")
    check_template_field_parser()
