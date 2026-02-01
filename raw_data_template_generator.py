"""
原始数据导入模板生成器
根据已固化的列名配置生成Excel导入模板
"""
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from models_v2 import get_db_connection
import os
from datetime import datetime


class RawDataTemplateGenerator:
    """原始数据导入模板生成器"""

    # 基础字段名称（系统预定义）
    BASE_FIELDS = ['样品编号', '所属公司', '所属水厂', '水样类型', '采样时间']

    def __init__(self):
        """初始化生成器"""
        self.columns = []
        self.has_schema = False

    def generate(self, output_path=None):
        """
        生成导入模板

        Args:
            output_path: 输出文件路径（可选）

        Returns:
            str: 生成的文件路径
        """
        # 加载列名配置
        self._load_columns()

        # 创建工作簿
        wb = openpyxl.Workbook()

        # 移除默认的Sheet
        wb.remove(wb.active)

        # 1. 创建说明sheet（放在第一个）
        self._create_instruction_sheet(wb)

        # 2. 创建数据导入sheet
        self._create_data_sheet(wb)

        # 3. 保存文件
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"exports/raw_data_import_template_{timestamp}.xlsx"

        os.makedirs('exports', exist_ok=True)
        wb.save(output_path)
        wb.close()

        return output_path

    def _load_columns(self):
        """加载列名配置"""
        conn = get_db_connection()
        cursor = conn.cursor()

        # 尝试获取已固化的列名配置
        cursor.execute('''
            SELECT column_name, column_order, data_type, is_base_field
            FROM raw_data_column_schema
            ORDER BY column_order
        ''')

        rows = cursor.fetchall()
        conn.close()

        if rows:
            # 使用已固化的列名
            self.columns = [row[0] for row in rows]
            self.has_schema = True
        else:
            # 使用默认列名（仅包含基础字段 + 示例检测指标）
            self.columns = self.BASE_FIELDS + [
                'pH', '浊度', '余氯', '色度', '臭和味',
                '肉眼可见物', '耗氧量', '总大肠菌群', '菌落总数'
            ]
            self.has_schema = False

    def _create_data_sheet(self, wb):
        """
        创建数据导入sheet
        格式：每列一个字段，第一行是表头
        """
        ws = wb.create_sheet("数据导入")

        # 设置样式
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=11)
        required_fill = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
        required_font = Font(bold=True, size=10, color="C00000")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # 第一行：表头
        for col_idx, col_name in enumerate(self.columns, start=1):
            cell = ws.cell(1, col_idx)
            cell.value = col_name

            # 基础字段（必填）用特殊样式标记
            if col_name in self.BASE_FIELDS:
                cell.fill = required_fill
                cell.font = required_font
            else:
                cell.fill = header_fill
                cell.font = header_font

            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = border

        # 第二行：添加示例数据
        example_data = {
            '样品编号': 'W260129C001',
            '所属公司': '某某水务公司',
            '所属水厂': '第一水厂',
            '水样类型': '出厂水',
            '采样时间': '2026-01-29',
            'pH': '7.2',
            '浊度': '0.5',
            '余氯': '0.3',
            '色度': '<5',
            '臭和味': '无',
            '肉眼可见物': '无',
            '耗氧量': '1.2',
            '总大肠菌群': '未检出',
            '菌落总数': '<1'
        }

        for col_idx, col_name in enumerate(self.columns, start=1):
            cell = ws.cell(2, col_idx)
            cell.value = example_data.get(col_name, '')
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        # 添加更多空行供填写
        for row_idx in range(3, 12):
            for col_idx in range(1, len(self.columns) + 1):
                cell = ws.cell(row_idx, col_idx)
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center')

        # 调整列宽
        for col_idx, col_name in enumerate(self.columns, start=1):
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            if col_name in self.BASE_FIELDS:
                ws.column_dimensions[col_letter].width = 18
            else:
                ws.column_dimensions[col_letter].width = 12

        # 冻结首行
        ws.freeze_panes = 'A2'

    def _create_instruction_sheet(self, wb):
        """创建填写说明sheet"""
        ws = wb.create_sheet("填写说明", 0)  # 插入到第一个位置

        # 标题
        ws['A1'] = "原始数据导入模板填写说明"
        ws['A1'].font = Font(size=16, bold=True, color="4472C4")

        row = 3

        # 基本说明
        status_text = "已固化" if self.has_schema else "默认示例"
        column_count = len(self.columns)

        instructions = [
            ("一、模板信息", ""),
            ("", f"列名配置状态: {status_text}"),
            ("", f"列数量: {column_count} 列"),
            ("", f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
            ("", ""),
            ("二、列名说明", ""),
            ("", f"当前模板包含以下列（按顺序）："),
        ]

        # 添加列名列表
        for idx, col_name in enumerate(self.columns, start=1):
            is_required = "【必填】" if col_name in self.BASE_FIELDS else "【选填】"
            instructions.append(("", f"  {idx}. {col_name} {is_required}"))

        instructions.extend([
            ("", ""),
            ("三、填写说明", ""),
            ("", "1. 必填字段说明："),
            ("", "   • 样品编号：唯一标识，不能重复（如：W260129C001）"),
            ("", "   • 所属公司：样品所属的公司名称"),
            ("", "   • 所属水厂：样品所属的水厂名称"),
            ("", "   • 水样类型：如出厂水、管网水、原水等"),
            ("", "   • 采样时间：必须为YYYY-MM-DD格式（如：2026-01-29）"),
            ("", ""),
            ("", "2. 检测指标字段："),
            ("", "   • 直接填写检测结果（数值或文本）"),
            ("", "   • 可以是数字（如：7.2、0.5）"),
            ("", "   • 可以是文本（如：未检出、无、<5）"),
            ("", "   • 留空表示未检测该指标"),
            ("", ""),
            ("", "3. 格式要求："),
            ("", "   • 采样时间严格按照YYYY-MM-DD格式"),
            ("", "   • 不要修改表头（第一行）的列名"),
            ("", "   • 不要修改列的顺序"),
            ("", "   • 不要删除或增加列"),
        ])

        if self.has_schema:
            instructions.extend([
                ("", "   • 系统已固化列名，必须与此模板完全一致"),
            ])
        else:
            instructions.extend([
                ("", "   • 首次导入将固化列名配置"),
                ("", "   • 后续导入必须与首次导入的列名一致"),
            ])

        instructions.extend([
            ("", ""),
            ("", "4. 示例数据："),
            ("", "   • 第2行提供了示例数据，可以参考填写"),
            ("", "   • 导入前可以删除示例数据行"),
            ("", ""),
            ("四、重复数据处理", ""),
            ("", "导入时可以选择重复样品编号的处理方式："),
            ("", "• 跳过重复记录（推荐）：重复的样品编号会被跳过，不影响其他数据导入"),
            ("", "• 覆盖已有记录：重复的样品编号会覆盖数据库中的旧数据"),
            ("", "• 终止导入：遇到重复样品编号立即停止导入"),
            ("", ""),
            ("五、导入步骤", ""),
            ("", "1. 下载本模板"),
            ("", "2. 按照说明填写数据（在\"数据导入\"sheet中）"),
            ("", "3. 保存文件"),
            ("", "4. 在系统中点击\"选择Excel文件\"上传"),
            ("", "5. 选择重复处理方式"),
            ("", "6. 点击\"开始导入\"按钮"),
            ("", "7. 查看导入结果报告"),
            ("", ""),
            ("六、常见问题", ""),
            ("", "Q: 为什么导入失败提示\"列名不匹配\"？"),
            ("", "A: 系统已固化列名，必须使用系统生成的最新模板，不能修改列名或列顺序。"),
            ("", ""),
            ("", "Q: 采样时间应该如何填写？"),
            ("", "A: 必须严格按照YYYY-MM-DD格式，如2026-01-29，不能是其他格式。"),
            ("", ""),
            ("", "Q: 检测指标可以留空吗？"),
            ("", "A: 可以，留空表示该样品未检测此指标。"),
            ("", ""),
            ("", "Q: 可以添加自己的检测指标吗？"),
        ])

        if self.has_schema:
            instructions.extend([
                ("", "A: 不可以，系统已固化列名，不能增加或删除列。如需修改，请联系管理员。"),
            ])
        else:
            instructions.extend([
                ("", "A: 可以，首次导入时可以添加任意检测指标列，导入后列名将被固化。"),
            ])

        # 写入说明内容
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


def generate_raw_data_template(output_path=None):
    """
    生成原始数据导入模板的便捷函数

    Args:
        output_path: 输出路径（可选）

    Returns:
        str: 生成的文件路径
    """
    generator = RawDataTemplateGenerator()
    return generator.generate(output_path)


if __name__ == '__main__':
    print("="*60)
    print("原始数据导入模板生成器测试")
    print("="*60)

    # 生成模板
    print("\n生成原始数据导入模板...")
    path = generate_raw_data_template()
    print(f"✓ 生成成功: {path}")
