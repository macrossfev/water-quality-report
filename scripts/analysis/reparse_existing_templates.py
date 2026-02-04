"""
为已导入的模板重新解析字段
适用于在添加字段解析功能之前导入的模板
"""
from models_v2 import get_db_connection
from template_field_parser import TemplateFieldParser
import os

def reparse_all_templates():
    """重新解析所有模板的字段"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取所有活跃的模板
    templates = conn.execute(
        'SELECT id, name, template_file_path FROM excel_report_templates WHERE is_active = 1'
    ).fetchall()

    if not templates:
        print("没有找到需要解析的模板")
        conn.close()
        return

    print(f"找到 {len(templates)} 个模板，开始重新解析...\n")

    for template in templates:
        template_id = template['id']
        template_name = template['name']
        file_path = template['template_file_path']

        print(f"处理模板: {template_name} (ID: {template_id})")

        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"  ✗ 文件不存在: {file_path}")
            continue

        # 检查是否已有字段映射
        existing_fields = conn.execute(
            'SELECT COUNT(*) as count FROM template_field_mappings WHERE template_id = ?',
            (template_id,)
        ).fetchone()

        if existing_fields['count'] > 0:
            print(f"  ⚠ 已有 {existing_fields['count']} 个字段映射，删除旧数据...")
            cursor.execute('DELETE FROM template_field_mappings WHERE template_id = ?', (template_id,))

        # 解析字段
        try:
            fields = TemplateFieldParser.extract_template_fields(file_path)

            if not fields:
                print(f"  ⚠ 未找到任何字段标记（[]、()、;）")
                continue

            # 插入字段映射
            for field in fields:
                cursor.execute(
                    '''INSERT INTO template_field_mappings
                       (template_id, field_name, field_display_name, field_type,
                        sheet_name, cell_address, placeholder, default_value, is_required)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (template_id,
                     field['field_name'],
                     field['display_name'],
                     'text',
                     field['sheet_name'],
                     field['cell_address'],
                     field.get('placeholder', ''),
                     field.get('default_value', ''),
                     1 if field.get('is_required', True) else 0)
                )

            conn.commit()
            print(f"  ✓ 成功解析 {len(fields)} 个字段")

            # 显示字段详情
            if len(fields) <= 10:
                for field in fields:
                    req_mark = '*' if field.get('is_required') else ''
                    default_text = f" (默认: {field.get('default_value')})" if field.get('default_value') else ''
                    print(f"    - [{field['field_name']}]{req_mark} @ {field['sheet_name']}:{field['cell_address']}{default_text}")
            else:
                print(f"    (字段较多，仅显示前3个)")
                for field in fields[:3]:
                    req_mark = '*' if field.get('is_required') else ''
                    print(f"    - [{field['field_name']}]{req_mark} @ {field['sheet_name']}:{field['cell_address']}")
                print(f"    ... 还有 {len(fields) - 3} 个字段")

        except Exception as e:
            print(f"  ✗ 解析失败: {e}")
            import traceback
            traceback.print_exc()

        print()

    conn.close()
    print("="*60)
    print("重新解析完成！")

if __name__ == '__main__':
    print("="*60)
    print("为已导入的模板重新解析字段")
    print("="*60)
    print()

    reparse_all_templates()
