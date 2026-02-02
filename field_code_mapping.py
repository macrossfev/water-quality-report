"""
字段代号映射系统
定义Excel模板中使用的字段代号与数据库字段的映射关系
"""

class FieldCodeMapping:
    """字段代号映射表"""

    # 报告基本信息字段代号映射
    BASIC_FIELDS = {
        # 报告基本信息
        '#report_no': {
            'db_field': 'report_number',
            'display_name': '报告编号',
            'description': '报告编号'
        },
        '#sample_no': {
            'db_field': 'sample_number',
            'display_name': '样品编号',
            'description': '样品编号'
        },
        '#sample_type': {
            'db_field': 'sample_type_name',
            'display_name': '样品类型',
            'description': '样品类型'
        },
        '#company': {
            'db_field': 'company_name',
            'display_name': '委托单位',
            'description': '委托单位名称'
        },
        '#customer_unit': {
            'db_field': 'customer_unit',
            'display_name': '被检单位',
            'description': '被检单位'
        },
        '#customer_plant': {
            'db_field': 'customer_plant',
            'display_name': '被检水厂',
            'description': '被检水厂'
        },
        '#unit_address': {
            'db_field': 'unit_address',
            'display_name': '单位地址',
            'description': '单位地址'
        },

        # 采样信息
        '#sampling_date': {
            'db_field': 'sampling_date',
            'display_name': '采样日期',
            'description': '采样日期'
        },
        '#sampler': {
            'db_field': 'sampler',
            'display_name': '采样人',
            'description': '采样人员'
        },
        '#sampling_location': {
            'db_field': 'sampling_location',
            'display_name': '采样地点',
            'description': '采样地点'
        },
        '#sampling_basis': {
            'db_field': 'sampling_basis',
            'display_name': '采样依据',
            'description': '采样依据标准'
        },
        '#sample_source': {
            'db_field': 'sample_source',
            'display_name': '样品来源',
            'description': '样品来源'
        },
        '#sample_status': {
            'db_field': 'sample_status',
            'display_name': '样品状态',
            'description': '样品状态描述'
        },
        '#sample_received': {
            'db_field': 'sample_received_date',
            'display_name': '收样日期',
            'description': '收样日期'
        },

        # 检测信息
        '#detection_date': {
            'db_field': 'detection_date',
            'display_name': '检测日期',
            'description': '检测日期'
        },
        '#detection_person': {
            'db_field': 'detection_person',
            'display_name': '检测人',
            'description': '检测人员'
        },
        '#review_person': {
            'db_field': 'review_person',
            'display_name': '审核人',
            'description': '审核人员'
        },
        '#report_date': {
            'db_field': 'report_date',
            'display_name': '报告编制日期',
            'description': '报告编制日期'
        },

        # 其他信息
        '#product_standard': {
            'db_field': 'product_standard',
            'display_name': '产品标准',
            'description': '产品标准/检测依据'
        },
        '#detection_items': {
            'db_field': 'detection_items_description',
            'display_name': '检测项目',
            'description': '检测项目列表描述'
        },
        '#test_conclusion': {
            'db_field': 'test_conclusion',
            'display_name': '检测结论',
            'description': '检测结论'
        },
        '#additional_info': {
            'db_field': 'additional_info',
            'display_name': '附加信息',
            'description': '附加信息或说明'
        },
        '#attachment_info': {
            'db_field': 'attachment_info',
            'display_name': '附件信息',
            'description': '附件说明'
        },
        '#remark': {
            'db_field': 'remark',
            'display_name': '备注',
            'description': '备注信息'
        }
    }

    # 检测数据列代号映射
    DETECTION_COLUMNS = {
        '#dt_index': {
            'column_mapping': 'index',
            'display_name': '序号',
            'description': '检测项目序号（自动编号）'
        },
        '#dt_name': {
            'column_mapping': 'name',
            'display_name': '检测项目',
            'description': '检测项目名称'
        },
        '#dt_unit': {
            'column_mapping': 'unit',
            'display_name': '单位',
            'description': '检测项目单位'
        },
        '#dt_result': {
            'column_mapping': 'result',
            'display_name': '检测结果',
            'description': '检测结果值'
        },
        '#dt_limit': {
            'column_mapping': 'limit',
            'display_name': '标准限值',
            'description': '标准限值'
        },
        '#dt_method': {
            'column_mapping': 'method',
            'display_name': '检测方法',
            'description': '检测方法/依据'
        },
        '#dt_judgment': {
            'column_mapping': 'judgment',
            'display_name': '单项判定',
            'description': '单项判定结果'
        }
    }

    # 特殊控制标记
    CONTROL_MARKS = {
        '#dt_end': {
            'type': 'data_region_end',
            'display_name': '数据区结束',
            'description': '标记数据区域的结束位置（用于多页数据表）'
        },
        '#page_break': {
            'type': 'page_break',
            'display_name': '分页符',
            'description': '分页符标记'
        }
    }

    @classmethod
    def get_field_info(cls, field_code):
        """
        根据字段代号获取字段信息

        Args:
            field_code: 字段代号，如 '#report_no', '#dt_name'

        Returns:
            dict: 字段信息，包含 db_field/column_mapping, display_name, description
            None: 如果代号不存在
        """
        # 去掉方括号
        code = field_code.strip('[]')

        # 检查是否为基本字段
        if code in cls.BASIC_FIELDS:
            return {
                'type': 'basic_field',
                'code': code,
                **cls.BASIC_FIELDS[code]
            }

        # 检查是否为检测数据列
        if code in cls.DETECTION_COLUMNS:
            return {
                'type': 'detection_column',
                'code': code,
                **cls.DETECTION_COLUMNS[code]
            }

        # 检查是否为控制标记
        if code in cls.CONTROL_MARKS:
            return {
                'code': code,
                **cls.CONTROL_MARKS[code]
            }

        return None

    @classmethod
    def is_field_code(cls, text):
        """
        判断文本是否为字段代号

        Args:
            text: 文本内容

        Returns:
            bool: 是否为字段代号（[#xxx]格式）
        """
        if not text:
            return False

        text = str(text).strip()
        return text.startswith('[#') and text.endswith(']')

    @classmethod
    def get_all_basic_field_codes(cls):
        """获取所有基本字段代号列表"""
        return list(cls.BASIC_FIELDS.keys())

    @classmethod
    def get_all_detection_column_codes(cls):
        """获取所有检测数据列代号列表"""
        return list(cls.DETECTION_COLUMNS.keys())

    @classmethod
    def get_all_control_marks(cls):
        """获取所有控制标记列表"""
        return list(cls.CONTROL_MARKS.keys())

    @classmethod
    def generate_documentation(cls):
        """生成标记代号使用文档"""
        doc = []
        doc.append("=" * 80)
        doc.append("Excel模板字段代号使用说明")
        doc.append("=" * 80)
        doc.append("")

        doc.append("一、报告基本信息字段代号")
        doc.append("-" * 80)
        for code, info in cls.BASIC_FIELDS.items():
            doc.append(f"[{code:25}] - {info['display_name']:15} ({info['description']})")
        doc.append("")

        doc.append("二、检测数据列代号")
        doc.append("-" * 80)
        for code, info in cls.DETECTION_COLUMNS.items():
            doc.append(f"[{code:25}] - {info['display_name']:15} ({info['description']})")
        doc.append("")

        doc.append("三、特殊控制标记")
        doc.append("-" * 80)
        for code, info in cls.CONTROL_MARKS.items():
            doc.append(f"[{code:25}] - {info['display_name']:15} ({info['description']})")
        doc.append("")

        doc.append("四、引用字段（从已审核报告引用）")
        doc.append("-" * 80)
        doc.append("[*字段名]                   - 从已审核报告中引用对应字段的值")
        doc.append("示例: [*被检单位], [*采样日期]")
        doc.append("")

        doc.append("五、使用示例")
        doc.append("-" * 80)
        doc.append("报告信息页：")
        doc.append("  B2: [#report_no]         - 报告编号")
        doc.append("  B3: [#sample_no]         - 样品编号")
        doc.append("  B4: [*被检单位]          - 从已审核报告引用被检单位")
        doc.append("")
        doc.append("检测数据页（第三页）：")
        doc.append("  A8: [#dt_index]          - 序号列")
        doc.append("  B8: [#dt_name]           - 项目名称列")
        doc.append("  C8: [#dt_unit]           - 单位列")
        doc.append("  D8: [#dt_result]         - 检测结果列")
        doc.append("  E8: [#dt_limit]          - 限值列")
        doc.append("  F8: [#dt_method]         - 方法列")
        doc.append("  A30: [#dt_end]           - 数据区结束标记（该页最多22行数据）")
        doc.append("")
        doc.append("=" * 80)

        return "\n".join(doc)


if __name__ == '__main__':
    # 打印使用文档
    print(FieldCodeMapping.generate_documentation())

    # 测试代号解析
    print("\n测试代号解析：")
    test_codes = ['[#report_no]', '[#dt_name]', '[#dt_end]', '[*被检单位]']
    for code in test_codes:
        info = FieldCodeMapping.get_field_info(code)
        if info:
            print(f"{code:20} -> {info}")
        else:
            print(f"{code:20} -> 未知代号")
