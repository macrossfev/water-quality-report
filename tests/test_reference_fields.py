"""
测试引用字段功能
验证 [*字段名] 格式的字段解析和数据引用
"""
from template_field_parser import TemplateFieldParser

def test_parse_reference_field():
    """测试解析引用字段"""
    print("=" * 60)
    print("测试引用字段解析")
    print("=" * 60)

    test_cases = [
        "[*被检单位]",
        "[*采样日期]",
        "[*被检水厂]",
        "[*委托单位]",
        "[报告编号];(请输入报告编号)",  # 普通字段对照
        "[检测人]张三;()",  # 有默认值的普通字段对照
    ]

    for test_text in test_cases:
        print(f"\n输入: {test_text}")
        result = TemplateFieldParser.parse_field(test_text)
        print(f"结果:")
        print(f"  字段名: {result['field_name']}")
        print(f"  显示名: {result['display_name']}")
        print(f"  是否引用字段: {result['is_reference']}")
        print(f"  是否可编辑: {result['is_editable']}")
        print(f"  是否必填: {result['is_required']}")
        print(f"  占位符: {result['placeholder']}")
        print(f"  默认值: {result['default_value']}")

        # 验证引用字段的特性
        if test_text.startswith('[*'):
            assert result['is_reference'] == True, "引用字段应该标记为 is_reference=True"
            assert result['is_editable'] == False, "引用字段应该标记为不可编辑"
            assert result['field_name'] != '', "引用字段应该提取出字段名（不含*号）"
            print("  ✓ 引用字段验证通过")
        else:
            assert result['is_reference'] == False, "普通字段应该标记为 is_reference=False"
            print("  ✓ 普通字段验证通过")

def test_field_mapping():
    """测试字段名映射"""
    print("\n" + "=" * 60)
    print("测试字段名映射")
    print("=" * 60)

    # 从 report_generator.py 中复制的映射表
    field_mapping = {
        '报告编号': 'report_number',
        '样品编号': 'sample_number',
        '样品类型': 'sample_type_name',
        '被检单位': 'customer_unit',
        '被检水厂': 'customer_plant',
        '单位地址': 'unit_address',
        '委托单位': 'company_name',
        '采样人': 'sampler',
        '采样日期': 'sampling_date',
        '采样地点': 'sampling_location',
        '采样依据': 'sampling_basis',
        '样品来源': 'sample_source',
        '样品状态': 'sample_status',
        '收样日期': 'sample_received_date',
        '检测日期': 'detection_date',
        '检测人': 'detection_person',
        '检测人员': 'detection_person',
        '审核人': 'review_person',
        '审核人员': 'review_person',
        '报告编制日期': 'report_date',
        '产品标准': 'product_standard',
        '检测结论': 'test_conclusion',
        '附加信息': 'additional_info',
        '备注': 'remark'
    }

    print(f"\n支持的引用字段数量: {len(field_mapping)}")
    print("\n支持的引用字段列表:")
    for field_name, db_field in field_mapping.items():
        print(f"  [*{field_name}] -> {db_field}")

def main():
    """主测试函数"""
    try:
        test_parse_reference_field()
        test_field_mapping()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

        print("\n功能说明:")
        print("1. 在 Excel 模板中使用 [*字段名] 格式标记引用字段")
        print("2. 引用字段会从最近的已审核报告中自动获取数据")
        print("3. 优先查找相同样品编号的报告，其次查找最近的报告")
        print("4. 引用字段不可编辑，由系统自动填充")

        print("\n使用示例:")
        print("  Excel单元格内容: [*被检单位]")
        print("  系统行为: 从已审核报告中查询被检单位信息并自动填充")

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        raise

if __name__ == '__main__':
    main()
