"""
原始数据导入模块
支持Excel数据导入、字段固化、数据校验等功能

导入格式（转置布局）：
  - 第一行：A1为空或标签，B1起为样品编号
  - 第一列：A2起为字段名（报告编号、被检单位、被检水厂、样品类型、采样日期、检测指标...）
  - 数据区：各样品对应字段的值
"""
import pandas as pd
import re
from datetime import datetime
from models_v2 import get_db_connection
import os


class RawDataImporter:
    """原始数据导入器"""

    # 基础行字段名称（系统预定义，不含样品编号，样品编号在第一行表头中）
    BASE_ROW_FIELDS = ['报告编号', '被检单位', '被检水厂', '样品类型', '采样日期']

    def __init__(self):
        self.conn = None
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.skip_count = 0

    def validate_date_format(self, date_str):
        """
        验证日期格式，只接受YYYY-MM-DD格式
        返回: (是否有效, 标准化后的日期字符串)
        """
        if pd.isna(date_str) or date_str is None or str(date_str).strip() == '':
            return False, None

        date_str = str(date_str).strip()

        # 严格匹配YYYY-MM-DD格式
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False, None

        # 验证日期是否真实有效
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True, date_str
        except ValueError:
            return False, None

    def get_column_schema(self):
        """获取当前的字段配置"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT column_name, column_order, data_type, is_base_field
            FROM raw_data_column_schema
            ORDER BY column_order
        ''')
        return cursor.fetchall()

    def save_column_schema(self, row_fields):
        """
        保存字段配置（首次导入时）
        row_fields: 字段名列表（Excel第一列中的行标签，不含样品编号）
        """
        cursor = self.conn.cursor()

        # 过滤掉样品编号（它在表头行，不属于行字段）
        fields_to_save = [f for f in row_fields if f != '样品编号']

        for idx, field_name in enumerate(fields_to_save):
            # 判断是否为基础字段
            is_base = 1 if field_name in self.BASE_ROW_FIELDS else 0

            # 判断数据类型
            if field_name == '采样日期':
                data_type = 'date'
            elif field_name in self.BASE_ROW_FIELDS:
                data_type = 'text'
            else:
                # 检测指标默认为数值型（部分可能是文本型，导入时会保留原样）
                data_type = 'numeric'

            cursor.execute('''
                INSERT INTO raw_data_column_schema
                (column_name, column_order, data_type, is_base_field)
                VALUES (?, ?, ?, ?)
            ''', (field_name, idx, data_type, is_base))

        self.conn.commit()

    def validate_columns(self, row_fields):
        """
        验证Excel行字段名与系统配置是否一致
        row_fields: 从Excel第一列提取的字段名列表
        返回: (是否通过, 错误信息)
        """
        schema = self.get_column_schema()

        # 过滤掉样品编号（兼容旧schema或Excel中包含样品编号行的情况）
        excel_fields = [f for f in row_fields if f != '样品编号']

        if not schema:
            # 首次导入，检查必需的基础字段是否存在
            missing_fields = [field for field in self.BASE_ROW_FIELDS if field not in excel_fields]
            if missing_fields:
                return False, f"Excel缺少必需字段行: {', '.join(missing_fields)}"
            return True, None

        # 非首次导入，字段名必须完全一致
        # 兼容旧schema：过滤掉可能存在的样品编号
        system_fields = [row[0] for row in schema if row[0] != '样品编号']

        if len(excel_fields) != len(system_fields):
            return False, f"字段行数量不匹配: Excel有{len(excel_fields)}行字段，系统要求{len(system_fields)}行"

        for i, (excel_field, system_field) in enumerate(zip(excel_fields, system_fields)):
            if excel_field != system_field:
                return False, f"第{i+2}行字段不匹配: Excel为'{excel_field}'，系统要求'{system_field}'"

        return True, None

    def check_duplicate_sample_number(self, sample_number):
        """
        检查样品编号是否已存在
        返回: (是否存在, 记录ID)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id FROM raw_data_records WHERE sample_number = ?',
            (sample_number,)
        )
        result = cursor.fetchone()
        if result:
            return True, result[0]
        return False, None

    def import_excel(self, file_path, on_duplicate='skip'):
        """
        导入Excel文件（转置布局）

        Excel格式：
            - 第一行：A1为空或标签，B1起为样品编号
            - 第一列：A2起为字段名（报告编号、被检单位、...、检测指标...）
            - 数据区：各样品对应字段的值

        参数:
            file_path: Excel文件路径
            on_duplicate: 遇到重复样品编号时的处理方式
                - 'skip': 跳过重复记录
                - 'overwrite': 覆盖已有记录
                - 'abort': 终止导入

        返回:
            {
                'success': bool,
                'message': str,
                'total_rows': int,
                'success_count': int,
                'skip_count': int,
                'errors': list,
                'warnings': list
            }
        """
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.skip_count = 0

        try:
            # 读取Excel文件
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'message': f'文件不存在: {file_path}',
                    'errors': [f'文件不存在: {file_path}']
                }

            # 尝试读取"数据导入"sheet，如果不存在则读取第一个sheet
            try:
                df = pd.read_excel(file_path, sheet_name='数据导入', header=None)
            except Exception:
                df = pd.read_excel(file_path, header=None)

            if df.empty:
                return {
                    'success': False,
                    'message': 'Excel文件为空',
                    'errors': ['Excel文件为空']
                }

            # === 解析转置布局 ===

            # 第一行（从B列开始）：样品编号
            sample_columns = []
            for col_idx in range(1, len(df.columns)):
                val = df.iloc[0, col_idx]
                if pd.notna(val) and str(val).strip():
                    sample_columns.append((col_idx, str(val).strip()))
                else:
                    break  # 遇到空列停止

            if not sample_columns:
                return {
                    'success': False,
                    'message': '第一行未找到样品编号（应从B1单元格开始填写样品编号）',
                    'errors': ['第一行未找到样品编号']
                }

            # 第一列（从第2行开始）：字段名
            row_fields = []
            row_field_indices = {}
            for row_idx in range(1, len(df)):
                val = df.iloc[row_idx, 0]
                if pd.notna(val) and str(val).strip():
                    field_name = str(val).strip()
                    row_fields.append(field_name)
                    row_field_indices[field_name] = row_idx

            if not row_fields:
                return {
                    'success': False,
                    'message': '第一列未找到字段名（应从A2单元格开始填写字段名）',
                    'errors': ['第一列未找到字段名']
                }

            # 建立数据库连接
            self.conn = get_db_connection()

            # 验证字段名
            valid, error_msg = self.validate_columns(row_fields)
            if not valid:
                self.conn.close()
                return {
                    'success': False,
                    'message': error_msg,
                    'errors': [error_msg]
                }

            # 首次导入时保存字段配置
            schema = self.get_column_schema()
            if not schema:
                self.save_column_schema(row_fields)
                self.warnings.append('首次导入，已保存字段配置')

            # 用于提取某样品某字段值的辅助函数
            def get_cell_value(field_name, col_idx):
                ri = row_field_indices.get(field_name)
                if ri is None:
                    return ''
                val = df.iloc[ri, col_idx]
                if pd.notna(val):
                    return str(val).strip()
                return ''

            # 过滤出非基础字段的检测指标（排除样品编号）
            indicator_fields = [
                f for f in row_fields
                if f not in self.BASE_ROW_FIELDS and f != '样品编号'
            ]

            total_samples = len(sample_columns)

            # 逐列处理每个样品
            for col_idx, sample_number in sample_columns:
                try:
                    # 验证样品编号
                    if not sample_number:
                        self.errors.append(f"样品编号为空（第{col_idx+1}列），跳过")
                        self.skip_count += 1
                        continue

                    # 提取基础字段
                    report_number = get_cell_value('报告编号', col_idx)
                    company_name = get_cell_value('被检单位', col_idx)
                    plant_name = get_cell_value('被检水厂', col_idx)
                    sample_type = get_cell_value('样品类型', col_idx)
                    sampling_date_raw = get_cell_value('采样日期', col_idx)

                    # 验证采样日期格式
                    valid_date, sampling_date = self.validate_date_format(sampling_date_raw)
                    if not valid_date:
                        self.errors.append(
                            f"样品'{sample_number}': 采样日期'{sampling_date_raw}'格式错误，"
                            f"必须为YYYY-MM-DD格式，跳过"
                        )
                        self.skip_count += 1
                        continue

                    # 检查样品编号是否重复
                    is_duplicate, existing_id = self.check_duplicate_sample_number(sample_number)

                    if is_duplicate:
                        if on_duplicate == 'abort':
                            self.conn.close()
                            return {
                                'success': False,
                                'message': f'样品编号"{sample_number}"重复，已终止导入',
                                'total_rows': total_samples,
                                'success_count': self.success_count,
                                'skip_count': self.skip_count,
                                'errors': self.errors,
                                'warnings': self.warnings
                            }
                        elif on_duplicate == 'skip':
                            self.warnings.append(f"样品'{sample_number}'已存在，已跳过")
                            self.skip_count += 1
                            continue
                        elif on_duplicate == 'overwrite':
                            # 删除旧记录（级联删除会自动删除关联的检测值）
                            cursor = self.conn.cursor()
                            cursor.execute('DELETE FROM raw_data_records WHERE id = ?', (existing_id,))
                            self.warnings.append(f"样品'{sample_number}'已存在，已覆盖")

                    # 插入主记录
                    cursor = self.conn.cursor()
                    cursor.execute('''
                        INSERT INTO raw_data_records
                        (sample_number, report_number, company_name, plant_name, sample_type, sampling_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (sample_number, report_number, company_name, plant_name, sample_type, sampling_date))

                    record_id = cursor.lastrowid

                    # 插入检测指标数据
                    for field_name in indicator_fields:
                        value = get_cell_value(field_name, col_idx)
                        value_str = value if value else None

                        cursor.execute('''
                            INSERT INTO raw_data_values (record_id, column_name, value)
                            VALUES (?, ?, ?)
                        ''', (record_id, field_name, value_str))

                    self.success_count += 1

                except Exception as e:
                    self.errors.append(f"样品'{sample_number}'处理失败: {str(e)}")
                    self.skip_count += 1
                    continue

            self.conn.commit()
            self.conn.close()

            return {
                'success': True,
                'message': f'导入完成: 成功{self.success_count}条，跳过{self.skip_count}条',
                'total_rows': total_samples,
                'success_count': self.success_count,
                'skip_count': self.skip_count,
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            if self.conn:
                self.conn.close()
            return {
                'success': False,
                'message': f'导入失败: {str(e)}',
                'errors': [str(e)]
            }

    def get_column_list(self):
        """
        获取当前系统的字段列表
        返回: 字段列表，如果未初始化则返回None
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT column_name
                FROM raw_data_column_schema
                ORDER BY column_order
            ''')
            columns = [row[0] for row in cursor.fetchall()]
            conn.close()
            return columns if columns else None
        except Exception:
            return None


if __name__ == '__main__':
    # 测试代码
    importer = RawDataImporter()
    print("字段列表:", importer.get_column_list())
