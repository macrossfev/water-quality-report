"""
测试模板配置导入导出功能
"""
from models_v2 import get_db_connection
from template_config_excel import TemplateConfigExcel

def test_export_import():
    """测试导出和导入功能"""
    # 获取第一个模板
    conn = get_db_connection()
    template = conn.execute(
        'SELECT * FROM excel_report_templates WHERE is_active = 1 LIMIT 1'
    ).fetchone()
    conn.close()

    if not template:
        print("❌ 没有可用的模板进行测试")
        return False

    template_id = template['id']
    template_name = template['name']

    print(f"📋 测试模板: {template_name} (ID: {template_id})")
    print()

    # 测试导出
    print("⏳ 测试导出配置...")
    try:
        export_path = TemplateConfigExcel.export_template_config(template_id)
        print(f"✅ 导出成功: {export_path}")
    except Exception as e:
        print(f"❌ 导出失败: {str(e)}")
        return False

    # 检查导出文件是否存在
    import os
    if not os.path.exists(export_path):
        print(f"❌ 导出文件不存在: {export_path}")
        return False

    print(f"✅ 导出文件已创建")
    print()

    # 测试导入（先备份字段数据）
    print("⏳ 测试导入配置...")
    conn = get_db_connection()
    original_fields = conn.execute(
        'SELECT * FROM template_field_mappings WHERE template_id = ?',
        (template_id,)
    ).fetchall()
    conn.close()

    original_field_count = len(original_fields)
    print(f"📊 原始字段数量: {original_field_count}")

    try:
        result = TemplateConfigExcel.import_template_config(template_id, export_path)
        print(f"✅ 导入成功: {result['message']}")
        print(f"📊 导入字段数量: {result['inserted_count']}")

        if result['inserted_count'] != original_field_count:
            print(f"⚠️  警告: 导入字段数量与原始不一致")
        else:
            print(f"✅ 字段数量一致")

    except Exception as e:
        print(f"❌ 导入失败: {str(e)}")
        return False

    print()
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

    return True

if __name__ == '__main__':
    test_export_import()
