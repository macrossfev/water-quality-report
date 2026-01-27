"""
模板字段解析器
解析[]、()、;格式，生成填写表单配置

字段格式规则:
1. [字段名];(占位符说明) - 必填字段，无默认值
2. [字段名]默认值;(占位符说明) - 有默认值，可编辑
3. [字段名](占位符说明) - 必填字段（简化格式）
4. [字段名] - 必填字段（最简格式）

示例:
- [报告编号];(请输入报告编号) - 必填
- [检测日期]2025-01-15;(检测日期) - 默认值为2025-01-15，可编辑
- [检测人]张三;() - 默认值为张三，可编辑
"""
import re
from typing import Dict, List, Optional, Tuple

class TemplateFieldParser:
    """模板字段解析器"""

    @staticmethod
    def parse_field(field_text: str) -> Dict:
        """
        解析单个字段文本

        Args:
            field_text: 字段文本，如 "[报告编号];(请输入报告编号)"

        Returns:
            dict: {
                'field_name': '报告编号',
                'display_name': '报告编号',
                'default_value': None,
                'placeholder': '请输入报告编号',
                'is_required': True,
                'is_editable': True
            }
        """
        result = {
            'field_name': '',
            'display_name': '',
            'default_value': None,
            'placeholder': '',
            'is_required': True,
            'is_editable': True
        }

        if not field_text:
            return result

        # 1. 提取字段名（方括号内容）
        field_name_match = re.search(r'\[(.*?)\]', field_text)
        if field_name_match:
            result['field_name'] = field_name_match.group(1).strip()
            result['display_name'] = result['field_name']
        else:
            # 没有方括号，使用整个文本作为字段名
            result['field_name'] = field_text.strip()
            result['display_name'] = field_text.strip()
            return result

        # 2. 检查是否有分号
        if ';' in field_text:
            # 有分号，需要解析默认值和占位符
            # 分号前的内容（除去[字段名]部分）
            before_semicolon = field_text.split(';')[0]
            after_semicolon = field_text.split(';')[1] if len(field_text.split(';')) > 1 else ''

            # 提取默认值（方括号后、分号前的内容）
            default_value_match = re.search(r'\](.+)', before_semicolon)
            if default_value_match:
                default_val = default_value_match.group(1).strip()
                if default_val:
                    result['default_value'] = default_val
                    result['is_required'] = False  # 有默认值，非必填
            else:
                # 分号前为空（只有[字段名];），表示必填
                result['is_required'] = True

            # 提取占位符（圆括号内容）
            placeholder_match = re.search(r'\((.*?)\)', after_semicolon)
            if placeholder_match:
                result['placeholder'] = placeholder_match.group(1).strip()

        else:
            # 没有分号，检查是否有圆括号
            placeholder_match = re.search(r'\((.*?)\)', field_text)
            if placeholder_match:
                result['placeholder'] = placeholder_match.group(1).strip()

            # 检查方括号后是否有内容作为默认值
            after_bracket = field_text.split(']')[1] if ']' in field_text else ''
            # 移除圆括号部分
            after_bracket = re.sub(r'\(.*?\)', '', after_bracket).strip()
            if after_bracket:
                result['default_value'] = after_bracket
                result['is_required'] = False

        return result

    @staticmethod
    def parse_cell_value(cell_value: str) -> List[Dict]:
        """
        解析单元格值中的所有字段

        Args:
            cell_value: 单元格值，可能包含多个字段

        Returns:
            list: 字段列表
        """
        if not cell_value:
            return []

        fields = []

        # 查找所有方括号标记的字段
        field_matches = re.finditer(r'\[([^\]]+)\]', cell_value)

        for match in field_matches:
            # 获取字段及其周围的上下文
            start = match.start()
            end = match.end()

            # 向后查找直到遇到下一个[或字符串结束
            context_end = cell_value.find('[', end)
            if context_end == -1:
                context_end = len(cell_value)

            field_text = cell_value[start:context_end].strip()
            field_info = TemplateFieldParser.parse_field(field_text)

            if field_info['field_name']:
                fields.append(field_info)

        return fields

    @staticmethod
    def extract_template_fields(template_path: str) -> List[Dict]:
        """
        从模板文件中提取所有字段配置

        Args:
            template_path: 模板文件路径

        Returns:
            list: 字段配置列表
        """
        import openpyxl
        from openpyxl.utils import get_column_letter

        wb = openpyxl.load_workbook(template_path)
        all_fields = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            for row in range(1, ws.max_row + 1):
                for col in range(1, ws.max_column + 1):
                    cell = ws.cell(row, col)
                    cell_value = str(cell.value) if cell.value else ""

                    # 检查是否包含字段标记
                    if '[' in cell_value and ']' in cell_value:
                        fields = TemplateFieldParser.parse_cell_value(cell_value)

                        for field in fields:
                            field['sheet_name'] = sheet_name
                            field['cell_address'] = f"{get_column_letter(col)}{row}"
                            field['row'] = row
                            field['col'] = col
                            field['original_value'] = cell_value
                            all_fields.append(field)

        wb.close()
        return all_fields

    @staticmethod
    def generate_form_config(template_id: int, fields: List[Dict]) -> List[Dict]:
        """
        生成表单配置

        Args:
            template_id: 模板ID
            fields: 字段列表

        Returns:
            list: 表单配置
        """
        form_config = []

        for field in fields:
            config = {
                'template_id': template_id,
                'field_name': field['field_name'],
                'field_display_name': field['display_name'],
                'field_type': 'text',  # 默认为文本类型
                'sheet_name': field['sheet_name'],
                'cell_address': field['cell_address'],
                'placeholder': field['placeholder'],
                'default_value': field['default_value'],
                'is_required': field['is_required'],
                'description': f"工作表:{field['sheet_name']}, 位置:{field['cell_address']}"
            }

            # 根据字段名判断类型
            field_name_lower = field['field_name'].lower()
            if '日期' in field['field_name'] or 'date' in field_name_lower:
                config['field_type'] = 'date'
            elif '时间' in field['field_name'] or 'time' in field_name_lower:
                config['field_type'] = 'datetime'
            elif '数量' in field['field_name'] or '编号' in field['field_name']:
                config['field_type'] = 'number'
            elif '备注' in field['field_name'] or '说明' in field['field_name']:
                config['field_type'] = 'textarea'

            form_config.append(config)

        return form_config


def test_parser():
    """测试解析器"""
    test_cases = [
        "[报告编号];(请输入报告编号)",
        "[检测日期]2025-01-15;(检测日期)",
        "[检测人]张三;()",
        "[样品编号](样品编号)",
        "[委托单位]",
        "检测项目: [总大肠菌群]0;(CFU/100mL)",
    ]

    print("="*60)
    print("模板字段解析器测试")
    print("="*60)

    for test_text in test_cases:
        print(f"\n输入: {test_text}")
        result = TemplateFieldParser.parse_field(test_text)
        print(f"结果:")
        print(f"  字段名: {result['field_name']}")
        print(f"  显示名: {result['display_name']}")
        print(f"  默认值: {result['default_value']}")
        print(f"  占位符: {result['placeholder']}")
        print(f"  必填: {result['is_required']}")
        print(f"  可编辑: {result['is_editable']}")


if __name__ == '__main__':
    test_parser()
