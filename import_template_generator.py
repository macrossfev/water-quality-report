"""
Excel导入模板生成器
根据报告模板生成统一的导入模板
"""
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from models_v2 import get_db_connection
import os
from datetime import datetime

class ImportTemplateGenerator:
    """导入模板生成器"""

    def __init__(self, template_id=None):
        """
        初始化生成器

        Args:
            template_id: 报告模板ID（可选），如果不指定则生成通用模板
        """
        self.template_id = template_id
        self.template_info = None

    def generate(self, output_path=None):
        """
        生成导入模板

        Args:
            output_path: 输出文件路径

        Returns:
            str: 生成的文件路径
        """
        # 创建工作簿
        wb = openpyxl.Workbook()

        # 移除默认的Sheet
        wb.remove(wb.active)

        # 1. 创建基本信息sheet
        self._create_basic_info_sheet(wb)

        # 2. 创建检测数据sheet
        self._create_detection_data_sheet(wb)

        # 3. 如果指定了模板，创建模板字段sheet
        if self.template_id:
            self._load_template_info()
            if self.template_info and self.template_info.get('fields'):
                self._create_template_fields_sheet(wb)

        # 4. 创建说明sheet
        self._create_instruction_sheet(wb)

        # 5. 保存文件
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            template_name = self.template_info['name'] if self.template_info else '通用'
            output_path = f"exports/import_template_{template_name}_{timestamp}.xlsx"

        os.makedirs('exports', exist_ok=True)
        wb.save(output_path)
        wb.close()

        return output_path

    def _load_template_info(self):
        """加载模板信息"""
        conn = get_db_connection()

        template = conn.execute(
            'SELECT * FROM excel_report_templates WHERE id = ?',
            (self.template_id,)
        ).fetchone()

        if template:
            self.template_info = dict(template)

            # 获取字段映射
            fields = conn.execute(
                'SELECT * FROM template_field_mappings WHERE template_id = ?',
                (self.template_id,)
            ).fetchall()
            self.template_info['fields'] = [dict(f) for f in fields]

        conn.close()

    def _create_basic_info_sheet(self, wb):
        """创建基本信息sheet"""
        ws = wb.create_sheet("基本信息")

        # 设置标题行样式
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        # 标题行
        headers = [
            '样品编号*', '样品类型*', '委托单位', '检测日期',
            '检测人员', '审核人员', '备注'
        ]

        for col, header in enumerate(headers, start=1):
            cell = ws.cell(1, col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 示例数据行
        example_data = [
            'S20250115001', '出厂水', '某水厂', '2025-01-15',
            '张三', '李四', '正常检测'
        ]

        for col, value in enumerate(example_data, start=1):
            cell = ws.cell(2, col)
            cell.value = value
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 调整列宽
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 25

    def _create_detection_data_sheet(self, wb):
        """创建检测数据sheet（横向格式：首行样品编号，首列检测项目）"""
        ws = wb.create_sheet("检测数据")

        # 设置标题行样式
        header_fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        # A1单元格：说明
        cell = ws.cell(1, 1)
        cell.value = "检测项目 \\ 样品编号"
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

        # 首行：样品编号（示例3个样品）
        sample_numbers = ['S20250115001', 'S20250115002', 'S20250115003']
        for col_idx, sample_number in enumerate(sample_numbers, start=2):
            cell = ws.cell(1, col_idx)
            cell.value = sample_number
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 首列：检测项目
        indicators = [
            'pH',
            '浊度',
            '余氯',
            '色度',
            '臭和味',
            '肉眼可见物',
            '耗氧量',
            '总大肠菌群',
            '菌落总数'
        ]

        # 左侧列头样式
        left_header_fill = PatternFill(start_color="A9D08E", end_color="A9D08E", fill_type="solid")
        left_header_font = Font(bold=True)

        for row_idx, indicator in enumerate(indicators, start=2):
            cell = ws.cell(row_idx, 1)
            cell.value = indicator
            cell.fill = left_header_fill
            cell.font = left_header_font
            cell.alignment = Alignment(horizontal='left', vertical='center')

        # 填写示例数据（第一个样品）
        example_values = ['7.2', '0.5', '0.3', '<5', '无', '无', '1.2', '未检出', '<1']
        for row_idx, value in enumerate(example_values, start=2):
            cell = ws.cell(row_idx, 2)
            cell.value = value
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 调整列宽
        ws.column_dimensions['A'].width = 25  # 检测项目列
        for col_letter in ['B', 'C', 'D', 'E', 'F']:
            ws.column_dimensions[col_letter].width = 18  # 样品数据列

        # 冻结首行首列
        ws.freeze_panes = 'B2'

    def _create_template_fields_sheet(self, wb):
        """创建模板字段sheet"""
        ws = wb.create_sheet("模板字段")

        # 设置标题行样式
        header_fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
        header_font = Font(color="000000", bold=True)

        # 标题行
        headers = ['样品编号*']

        # 添加模板字段
        for field in self.template_info.get('fields', []):
            field_name = field.get('field_display_name') or field.get('field_name')
            is_required = field.get('is_required', 0)
            if is_required:
                field_name += '*'
            headers.append(field_name)

        for col, header in enumerate(headers, start=1):
            cell = ws.cell(1, col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 示例数据行
        example_row = ['S20250115001']
        for field in self.template_info.get('fields', []):
            default_value = field.get('default_value', '')
            placeholder = field.get('placeholder', '')
            example_value = default_value if default_value else placeholder
            example_row.append(example_value)

        for col, value in enumerate(example_row, start=1):
            cell = ws.cell(2, col)
            cell.value = value
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 调整列宽
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    def _create_instruction_sheet(self, wb):
        """创建说明sheet"""
        ws = wb.create_sheet("填写说明", 0)  # 插入到第一个位置

        # 标题
        ws['A1'] = "导入模板填写说明"
        ws['A1'].font = Font(size=16, bold=True, color="4472C4")

        row = 3

        # 基本说明
        instructions = [
            ("一、基本说明", ""),
            ("", "1. 本模板用于批量导入检测报告数据"),
            ("", "2. 标记 * 的字段为必填项"),
            ("", "3. 请勿修改表头名称"),
            ("", "4. 样品编号必须保持一致（作为关联标识）"),
            ("", ""),
            ("二、各sheet说明", ""),
            ("", "【基本信息】：填写报告的基本信息，每个报告一行"),
            ("", "  - 样品编号：唯一标识，建议格式：S+日期+序号，如 S20250115001"),
            ("", "  - 样品类型：必须是系统中已存在的样品类型名称"),
            ("", "  - 委托单位：可选，填写委托单位名称"),
            ("", "  - 检测日期：格式：YYYY-MM-DD"),
            ("", "  - 检测人员、审核人员：可选"),
            ("", ""),
            ("", "【检测数据】：横向格式，首行为样品编号，首列为检测项目"),
            ("", "  - 格式说明：第1行填写样品编号，第1列填写检测项目名称"),
            ("", "  - 数据填写：在对应的交叉单元格中填写检测值"),
            ("", "  - 例如：pH项目、S001样品的值填在B2单元格"),
            ("", "  - 优点：可同时查看多个样品的同一指标，便于横向对比"),
            ("", "  - 支持冻结首行首列，方便浏览大量数据"),
            ("", ""),
        ]

        if self.template_info:
            instructions.append(("", "【模板字段】：填写报告模板的自定义字段"))
            instructions.append(("", "  - 样品编号：与基本信息中的样品编号对应"))
            instructions.append(("", "  - 其他字段：根据模板定义填写"))
            instructions.append(("", ""))

        instructions.extend([
            ("三、注意事项", ""),
            ("", "1. 同一个样品的所有数据（基本信息、检测数据、模板字段）的样品编号必须一致"),
            ("", "2. 样品类型和指标名称必须事先在系统中创建"),
            ("", "3. 日期格式统一使用 YYYY-MM-DD，如 2025-01-15"),
            ("", "4. 删除示例数据行，填入实际数据"),
            ("", "5. 可以填写多个样品的数据"),
            ("", ""),
            ("四、导入步骤", ""),
            ("", "1. 在系统中选择对应的报告模板"),
            ("", "2. 点击\"下载导入模板\"按钮获取本模板"),
            ("", "3. 按照说明填写数据"),
            ("", "4. 点击\"批量导入\"按钮上传填写好的文件"),
            ("", "5. 系统将自动创建报告并填充数据"),
        ])

        for title, content in instructions:
            if title:
                cell = ws.cell(row, 1)
                cell.value = title
                cell.font = Font(size=12, bold=True, color="4472C4")
            else:
                cell = ws.cell(row, 1)
                cell.value = content
                cell.alignment = Alignment(wrap_text=True)

            row += 1

        # 调整列宽
        ws.column_dimensions['A'].width = 100


def generate_import_template(template_id=None, output_path=None):
    """
    生成导入模板的便捷函数

    Args:
        template_id: 报告模板ID（可选）
        output_path: 输出路径（可选）

    Returns:
        str: 生成的文件路径
    """
    generator = ImportTemplateGenerator(template_id)
    return generator.generate(output_path)


if __name__ == '__main__':
    print("="*60)
    print("Excel导入模板生成器测试")
    print("="*60)

    # 生成通用模板
    print("\n生成通用导入模板...")
    path = generate_import_template()
    print(f"✓ 生成成功: {path}")

    # 如果有模板ID，生成特定模板
    conn = get_db_connection()
    templates = conn.execute('SELECT id, name FROM excel_report_templates WHERE is_active = 1 LIMIT 1').fetchone()
    conn.close()

    if templates:
        template_id = templates['id']
        template_name = templates['name']
        print(f"\n生成模板 [{template_name}] 的导入模板...")
        path = generate_import_template(template_id)
        print(f"✓ 生成成功: {path}")
