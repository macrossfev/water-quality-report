"""
报告生成器
按照Excel模版生成水质检测报告
"""
import os
import openpyxl
from openpyxl.styles import Font, Alignment
from datetime import datetime
from models_v2 import get_db_connection
import shutil

class ReportGenerator:
    """按模版生成Excel报告"""

    def __init__(self, template_id, report_data):
        """
        初始化报告生成器

        Args:
            template_id: 报告模版ID
            report_data: 报告数据字典，包含：
                - report_number: 报告编号
                - sample_number: 样品编号
                - sample_name: 样品名称
                - sample_type: 样品类型
                - company_name: 委托单位
                - detection_date: 检测日期
                - detection_person: 检测人
                - review_person: 审核人
                - detection_items: 检测项目列表 [{name, unit, result, limit, method}, ...]
                - etc.
        """
        self.template_id = template_id
        self.report_data = report_data
        self.template_info = None
        self.workbook = None

    def generate(self, output_path=None):
        """
        生成报告

        Args:
            output_path: 输出文件路径，如果为None则自动生成

        Returns:
            str: 生成的文件路径
        """
        # 1. 加载模版信息
        self._load_template_info()

        # 2. 复制模版文件
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_number = self.report_data.get('report_number', 'report')
            output_path = f"exports/report_{report_number}_{timestamp}.xlsx"

        os.makedirs('exports', exist_ok=True)
        shutil.copy2(self.template_info['template_file_path'], output_path)

        # 3. 打开工作簿
        self.workbook = openpyxl.load_workbook(output_path)

        # 4. 填充数据
        self._fill_data()

        # 5. 保存文件
        self.workbook.save(output_path)
        self.workbook.close()

        return output_path

    def _load_template_info(self):
        """加载模版信息"""
        conn = get_db_connection()

        template = conn.execute(
            'SELECT * FROM excel_report_templates WHERE id = ?',
            (self.template_id,)
        ).fetchone()

        if not template:
            conn.close()
            raise ValueError(f"模版不存在: ID={self.template_id}")

        # 获取字段映射
        fields = conn.execute(
            'SELECT * FROM template_field_mappings WHERE template_id = ?',
            (self.template_id,)
        ).fetchall()

        conn.close()

        self.template_info = dict(template)
        self.template_info['fields'] = [dict(f) for f in fields]

    def _fill_data(self):
        """填充报告数据"""
        fields = self.template_info.get('fields', [])

        for field in fields:
            field_name = field['field_name']
            field_type = field['field_type']
            sheet_name = field['sheet_name']
            cell_address = field['cell_address']

            # 如果没有字段映射配置，跳过
            if not cell_address or sheet_name not in self.workbook.sheetnames:
                continue

            # 获取工作表
            ws = self.workbook[sheet_name]

            # 根据字段类型填充数据
            if field_type == 'table_data':
                # 表格数据特殊处理
                self._fill_table_data(ws, field)
            else:
                # 简单字段直接填充
                value = self.report_data.get(field_name, field.get('default_value', ''))
                if value and cell_address:
                    try:
                        ws[cell_address] = value
                    except Exception as e:
                        print(f"填充字段失败 {field_name}: {e}")

    def _fill_table_data(self, worksheet, field):
        """
        填充表格数据（检测结果）

        Args:
            worksheet: 工作表对象
            field: 字段配置
        """
        detection_items = self.report_data.get('detection_items', [])

        if not detection_items:
            return

        start_row = field.get('start_row', 8)  # 默认从第8行开始
        start_col = field.get('start_col', 1)  # 默认从第1列开始

        # 填充每一行数据
        for idx, item in enumerate(detection_items):
            row = start_row + idx

            # 序号
            worksheet.cell(row, start_col).value = idx + 1

            # 项目名称
            worksheet.cell(row, start_col + 1).value = item.get('name', '')

            # 单位
            worksheet.cell(row, start_col + 2).value = item.get('unit', '')

            # 检测结果
            worksheet.cell(row, start_col + 3).value = item.get('result', '')

            # 标准限值
            worksheet.cell(row, start_col + 4).value = item.get('limit', '')

            # 检测方法
            worksheet.cell(row, start_col + 5).value = item.get('method', '')

def generate_simple_report(report_id):
    """
    简化版报告生成（不依赖模版）
    直接从数据库读取报告数据并生成Excel

    Args:
        report_id: 报告ID

    Returns:
        str: 生成的文件路径
    """
    conn = get_db_connection()

    # 获取报告基本信息
    report = conn.execute(
        'SELECT r.*, st.name as sample_type_name, c.name as company_name '
        'FROM reports r '
        'LEFT JOIN sample_types st ON r.sample_type_id = st.id '
        'LEFT JOIN companies c ON r.company_id = c.id '
        'WHERE r.id = ?',
        (report_id,)
    ).fetchone()

    if not report:
        conn.close()
        raise ValueError(f"报告不存在: ID={report_id}")

    # 获取检测数据
    data_items = conn.execute(
        'SELECT rd.*, i.name as indicator_name, i.unit, i.limit_value, i.detection_method '
        'FROM report_data rd '
        'JOIN indicators i ON rd.indicator_id = i.id '
        'WHERE rd.report_id = ? '
        'ORDER BY i.sort_order, i.name',
        (report_id,)
    ).fetchall()

    conn.close()

    # 创建Excel文件
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "检测报告"

    # 设置标题
    ws['A1'] = "水质检测报告"
    ws['A1'].font = Font(size=18, bold=True)
    ws['A1'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A1:F1')

    # 基本信息
    row = 3
    ws[f'A{row}'] = "报告编号："
    ws[f'B{row}'] = report['report_number']
    ws[f'D{row}'] = "样品编号："
    ws[f'E{row}'] = report['sample_number']

    row += 1
    ws[f'A{row}'] = "样品类型："
    ws[f'B{row}'] = report['sample_type_name']
    ws[f'D{row}'] = "委托单位："
    ws[f'E{row}'] = report['company_name'] or '-'

    row += 1
    ws[f'A{row}'] = "检测日期："
    ws[f'B{row}'] = report['detection_date'] or '-'
    ws[f'D{row}'] = "检测人员："
    ws[f'E{row}'] = report['detection_person'] or '-'

    # 检测数据表格
    row += 2
    headers = ['序号', '检测项目', '单位', '检测结果', '标准限值', '检测方法']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row, col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # 填充检测数据
    for idx, item in enumerate(data_items, start=1):
        row += 1
        ws.cell(row, 1).value = idx
        ws.cell(row, 2).value = item['indicator_name']
        ws.cell(row, 3).value = item['unit'] or '-'
        ws.cell(row, 4).value = item['measured_value'] or '-'
        ws.cell(row, 5).value = item['limit_value'] or '-'
        ws.cell(row, 6).value = item['detection_method'] or '-'

    # 调整列宽
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 40

    # 保存文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"exports/report_{report['report_number']}_{timestamp}.xlsx"
    os.makedirs('exports', exist_ok=True)
    wb.save(output_path)

    return output_path

if __name__ == '__main__':
    # 测试简化版报告生成
    print("报告生成器已就绪")
    print("使用方法：")
    print("1. 按模版生成：ReportGenerator(template_id, report_data).generate()")
    print("2. 简化版生成：generate_simple_report(report_id)")
