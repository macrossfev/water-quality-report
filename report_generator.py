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

    def __init__(self, template_id, report_data, report_id=None):
        """
        初始化报告生成器

        Args:
            template_id: 报告模版ID
            report_data: 报告数据字典，包含基本信息和检测数据
            report_id: 报告ID（用于从数据库加载完整数据）
        """
        self.template_id = template_id
        self.report_data = report_data
        self.report_id = report_id
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

        # 2. 从数据库加载完整数据（包括report_field_values）
        self._load_complete_data()

        # 3. 复制模版文件
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_number = self.report_data.get('report_number', 'report')
            output_path = f"exports/report_{report_number}_{timestamp}.xlsx"

        os.makedirs('exports', exist_ok=True)
        shutil.copy2(self.template_info['template_file_path'], output_path)

        # 4. 打开工作簿
        self.workbook = openpyxl.load_workbook(output_path)

        # 5. 填充数据
        self._fill_data()

        # 6. 保存文件
        self.workbook.save(output_path)
        self.workbook.close()

        return output_path

    def _load_complete_data(self):
        """从数据库加载完整的报告数据（包括report_field_values）"""
        if not self.report_id:
            return

        conn = get_db_connection()

        # 1. 加载报告基本信息
        report = conn.execute('''
            SELECT r.*, st.name as sample_type_name, st.code as sample_type_code,
                   c.name as company_name
            FROM reports r
            LEFT JOIN sample_types st ON r.sample_type_id = st.id
            LEFT JOIN companies c ON r.company_id = c.id
            WHERE r.id = ?
        ''', (self.report_id,)).fetchone()

        if report:
            # 合并所有基本信息到report_data
            self.report_data['report_number'] = report['report_number'] or ''
            self.report_data['sample_number'] = report['sample_number'] or ''
            self.report_data['sample_type'] = report['sample_type_name'] or ''
            self.report_data['sample_type_name'] = report['sample_type_name'] or ''
            self.report_data['company_name'] = report['company_name'] or ''
            self.report_data['detection_date'] = report['detection_date'] or ''
            self.report_data['detection_person'] = report['detection_person'] or ''
            self.report_data['review_person'] = report['review_person'] or ''
            self.report_data['remark'] = report['remark'] or ''

            # 添加更多字段
            self.report_data['sampling_date'] = report['sampling_date'] or ''
            self.report_data['sampler'] = report['sampler'] or ''
            self.report_data['sampling_location'] = report['sampling_location'] or ''
            self.report_data['sampling_basis'] = report['sampling_basis'] or ''
            self.report_data['sample_source'] = report['sample_source'] or ''
            self.report_data['sample_status'] = report['sample_status'] or ''
            self.report_data['sample_received_date'] = report['sample_received_date'] or ''
            self.report_data['report_date'] = report['report_date'] or ''
            self.report_data['product_standard'] = report['product_standard'] or ''
            self.report_data['test_conclusion'] = report['test_conclusion'] or ''
            self.report_data['additional_info'] = report['additional_info'] or ''

            # 从remark中提取客户信息
            if report['remark']:
                try:
                    import json
                    remark_data = json.loads(report['remark'])
                    self.report_data['customer_unit'] = remark_data.get('customer_unit', '')
                    self.report_data['customer_plant'] = remark_data.get('customer_plant', '')
                    self.report_data['unit_address'] = remark_data.get('unit_address', '')
                except:
                    pass

            print(f"已加载报告数据，字段数量: {len(self.report_data)}")
            print(f"报告数据键: {list(self.report_data.keys())}")

        # 2. 加载模板字段值（关键！之前缺失的部分）
        field_values = conn.execute('''
            SELECT rfv.field_value, tfm.field_name, tfm.field_display_name
            FROM report_field_values rfv
            JOIN template_field_mappings tfm ON rfv.field_mapping_id = tfm.id
            WHERE rfv.report_id = ?
        ''', (self.report_id,)).fetchall()

        for fv in field_values:
            # 使用field_name作为键
            field_key = fv['field_name']
            self.report_data[field_key] = fv['field_value']
            # 同时使用display_name作为备用键
            if fv['field_display_name']:
                self.report_data[fv['field_display_name']] = fv['field_value']

        # 3. 加载检测数据
        if 'detection_items' not in self.report_data or not self.report_data['detection_items']:
            detection_items = conn.execute('''
                SELECT rd.measured_value, i.name, i.unit, i.limit_value, i.detection_method
                FROM report_data rd
                JOIN indicators i ON rd.indicator_id = i.id
                LEFT JOIN indicator_groups g ON i.group_id = g.id
                WHERE rd.report_id = ?
                ORDER BY g.sort_order, i.sort_order, i.name
            ''', (self.report_id,)).fetchall()

            self.report_data['detection_items'] = [
                {
                    'name': item['name'],
                    'unit': item['unit'] or '',
                    'result': item['measured_value'] or '',
                    'limit': item['limit_value'] or '',
                    'method': item['detection_method'] or ''
                }
                for item in detection_items
            ]

        conn.close()

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

        print(f"\n=== 开始填充数据 ===")
        print(f"模板字段数量: {len(fields)}")
        print(f"报告数据键: {list(self.report_data.keys())}")

        for field in fields:
            field_name = field['field_name']
            field_type = field['field_type']
            sheet_name = field['sheet_name']
            cell_address = field['cell_address']
            is_reference = field.get('is_reference', False)

            # 如果没有字段映射配置，跳过
            if not cell_address or sheet_name not in self.workbook.sheetnames:
                print(f"跳过字段 {field_name}: cell_address={cell_address}, sheet存在={sheet_name in self.workbook.sheetnames if self.workbook else False}")
                continue

            # 获取工作表
            ws = self.workbook[sheet_name]

            # 根据字段类型填充数据
            if field_type == 'table_data':
                # 表格数据特殊处理
                print(f"填充表格数据: {field_name}")
                self._fill_table_data(ws, field)
            else:
                # 获取字段值
                if is_reference:
                    # 引用字段：从已审核报告中查询数据
                    value = self._get_reference_value(field_name)
                    print(f"引用字段 [{field_name}] = {value} (来自已审核报告)")
                else:
                    # 普通字段：从当前报告数据中获取
                    value = self.report_data.get(field_name, field.get('default_value', ''))
                    print(f"普通字段 [{field_name}] = {value}")

                # 修改条件：即使value为空字符串也要填充（除非是None）
                if value is not None and cell_address:
                    try:
                        ws[cell_address] = value
                        print(f"  ✓ 已填充到 {sheet_name}!{cell_address}")
                    except Exception as e:
                        print(f"  ✗ 填充失败: {e}")
                else:
                    print(f"  - 跳过（值为None）")

        print(f"=== 数据填充完成 ===\n")

    def _get_reference_value(self, field_name):
        """
        从已审核报告中获取引用字段的值

        Args:
            field_name: 字段名（如：被检单位、采样日期等）

        Returns:
            str: 字段值，如果找不到返回空字符串
        """
        conn = get_db_connection()

        # 字段名到数据库字段的映射
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

        db_field = field_mapping.get(field_name)

        if not db_field:
            print(f"警告: 未知的引用字段 '{field_name}'")
            conn.close()
            return ''

        try:
            # 从最近的已审核报告中查询数据
            # 优先查找相同样品编号的已审核报告
            sample_number = self.report_data.get('sample_number', '')

            if sample_number:
                # 先尝试查找相同样品编号的已审核报告
                query = f'''
                    SELECT r.{db_field}, r.remark
                    FROM reports r
                    LEFT JOIN sample_types st ON r.sample_type_id = st.id
                    WHERE r.review_status = 'approved'
                    AND r.sample_number = ?
                    ORDER BY r.created_at DESC
                    LIMIT 1
                '''
                result = conn.execute(query, (sample_number,)).fetchone()

                if result and result[db_field]:
                    value = result[db_field]

                    # 如果字段为空但在remark的JSON中，尝试从remark中提取
                    if not value and result['remark']:
                        try:
                            import json
                            remark_data = json.loads(result['remark'])
                            # 检查是否有customer_unit和customer_plant
                            if field_name == '被检单位' and 'customer_unit' in remark_data:
                                value = remark_data['customer_unit']
                            elif field_name == '被检水厂' and 'customer_plant' in remark_data:
                                value = remark_data['customer_plant']
                            elif field_name == '单位地址' and 'unit_address' in remark_data:
                                value = remark_data['unit_address']
                        except:
                            pass

                    conn.close()
                    return value or ''

            # 如果找不到相同样品编号的，查找最近的已审核报告
            query = f'''
                SELECT r.{db_field}, r.remark
                FROM reports r
                WHERE r.review_status = 'approved'
                ORDER BY r.created_at DESC
                LIMIT 1
            '''
            result = conn.execute(query).fetchone()

            if result:
                value = result[db_field] or ''

                # 如果字段为空但在remark的JSON中，尝试从remark中提取
                if not value and result['remark']:
                    try:
                        import json
                        remark_data = json.loads(result['remark'])
                        if field_name == '被检单位' and 'customer_unit' in remark_data:
                            value = remark_data['customer_unit']
                        elif field_name == '被检水厂' and 'customer_plant' in remark_data:
                            value = remark_data['customer_plant']
                        elif field_name == '单位地址' and 'unit_address' in remark_data:
                            value = remark_data['unit_address']
                    except:
                        pass

                conn.close()
                return value

            conn.close()
            return ''

        except Exception as e:
            print(f"查询引用字段失败 {field_name}: {e}")
            conn.close()
            return ''

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
