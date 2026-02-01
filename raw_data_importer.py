"""
原始数据导入模块
支持Excel数据导入、列名固化、数据校验等功能
"""
import pandas as pd
import re
from datetime import datetime
from models_v2 import get_db_connection
import os


class RawDataImporter:
    """原始数据导入器"""

    # 基础字段名称（系统预定义）
    BASE_FIELDS = ['样品编号', '所属公司', '所属水厂', '水样类型', '采样时间']

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
        """获取当前的列名配置"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT column_name, column_order, data_type, is_base_field
            FROM raw_data_column_schema
            ORDER BY column_order
        ''')
        return cursor.fetchall()

    def save_column_schema(self, columns):
        """
        保存列名配置（首次导入时）
        columns: 列名列表
        """
        cursor = self.conn.cursor()

        for idx, col_name in enumerate(columns):
            # 判断是否为基础字段
            is_base = 1 if col_name in self.BASE_FIELDS else 0

            # 判断数据类型
            if col_name == '采样时间':
                data_type = 'date'
            elif col_name in self.BASE_FIELDS:
                data_type = 'text'
            else:
                # 检测指标默认为数值型（部分可能是文本型，导入时会保留原样）
                data_type = 'numeric'

            cursor.execute('''
                INSERT INTO raw_data_column_schema
                (column_name, column_order, data_type, is_base_field)
                VALUES (?, ?, ?, ?)
            ''', (col_name, idx, data_type, is_base))

        self.conn.commit()

    def validate_columns(self, excel_columns):
        """
        验证Excel列名与系统列名是否一致
        返回: (是否通过, 错误信息)
        """
        schema = self.get_column_schema()

        if not schema:
            # 首次导入，检查必需的基础字段是否存在
            missing_fields = [field for field in self.BASE_FIELDS if field not in excel_columns]
            if missing_fields:
                return False, f"Excel缺少必需字段: {', '.join(missing_fields)}"
            return True, None

        # 非首次导入，列名必须完全一致
        system_columns = [row[0] for row in schema]

        if len(excel_columns) != len(system_columns):
            return False, f"列数量不匹配: Excel有{len(excel_columns)}列，系统要求{len(system_columns)}列"

        for i, (excel_col, system_col) in enumerate(zip(excel_columns, system_columns)):
            if excel_col != system_col:
                return False, f"第{i+1}列不匹配: Excel为'{excel_col}'，系统要求'{system_col}'"

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
        导入Excel文件

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

            df = pd.read_excel(file_path)

            if df.empty:
                return {
                    'success': False,
                    'message': 'Excel文件为空',
                    'errors': ['Excel文件为空']
                }

            # 获取列名
            excel_columns = df.columns.tolist()

            # 建立数据库连接
            self.conn = get_db_connection()

            # 验证列名
            valid, error_msg = self.validate_columns(excel_columns)
            if not valid:
                self.conn.close()
                return {
                    'success': False,
                    'message': error_msg,
                    'errors': [error_msg]
                }

            # 首次导入时保存列名配置
            schema = self.get_column_schema()
            if not schema:
                self.save_column_schema(excel_columns)
                self.warnings.append('首次导入，已保存列名配置')

            # 逐行处理数据
            total_rows = len(df)

            for idx, row in df.iterrows():
                row_num = idx + 2  # Excel行号（从2开始，1是表头）

                try:
                    # 提取基础字段
                    sample_number = str(row['样品编号']).strip() if pd.notna(row['样品编号']) else ''
                    company_name = str(row['所属公司']).strip() if pd.notna(row['所属公司']) else ''
                    plant_name = str(row['所属水厂']).strip() if pd.notna(row['所属水厂']) else ''
                    sample_type = str(row['水样类型']).strip() if pd.notna(row['水样类型']) else ''
                    sampling_date_raw = row['采样时间']

                    # 验证样品编号
                    if not sample_number:
                        self.errors.append(f"第{row_num}行: 样品编号为空，跳过该行")
                        self.skip_count += 1
                        continue

                    # 验证采样时间格式
                    valid_date, sampling_date = self.validate_date_format(sampling_date_raw)
                    if not valid_date:
                        self.errors.append(
                            f"第{row_num}行: 采样时间'{sampling_date_raw}'格式错误，必须为YYYY-MM-DD格式，跳过该行"
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
                                'message': f'第{row_num}行: 样品编号"{sample_number}"重复，已终止导入',
                                'total_rows': total_rows,
                                'success_count': self.success_count,
                                'skip_count': self.skip_count,
                                'errors': self.errors,
                                'warnings': self.warnings
                            }
                        elif on_duplicate == 'skip':
                            self.warnings.append(f"第{row_num}行: 样品编号'{sample_number}'已存在，已跳过")
                            self.skip_count += 1
                            continue
                        elif on_duplicate == 'overwrite':
                            # 删除旧记录（级联删除会自动删除关联的检测值）
                            cursor = self.conn.cursor()
                            cursor.execute('DELETE FROM raw_data_records WHERE id = ?', (existing_id,))
                            self.warnings.append(f"第{row_num}行: 样品编号'{sample_number}'已存在，已覆盖")

                    # 插入主记录
                    cursor = self.conn.cursor()
                    cursor.execute('''
                        INSERT INTO raw_data_records
                        (sample_number, company_name, plant_name, sample_type, sampling_date)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (sample_number, company_name, plant_name, sample_type, sampling_date))

                    record_id = cursor.lastrowid

                    # 插入检测指标数据
                    for col_name in excel_columns:
                        if col_name not in self.BASE_FIELDS:
                            value = row[col_name]
                            # 保留原始值（包括空值、数值的原始小数位数）
                            if pd.notna(value):
                                value_str = str(value)
                            else:
                                value_str = None

                            cursor.execute('''
                                INSERT INTO raw_data_values (record_id, column_name, value)
                                VALUES (?, ?, ?)
                            ''', (record_id, col_name, value_str))

                    self.success_count += 1

                except Exception as e:
                    self.errors.append(f"第{row_num}行处理失败: {str(e)}")
                    self.skip_count += 1
                    continue

            self.conn.commit()
            self.conn.close()

            return {
                'success': True,
                'message': f'导入完成: 成功{self.success_count}条，跳过{self.skip_count}条',
                'total_rows': total_rows,
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
        获取当前系统的列名列表
        返回: 列名列表，如果未初始化则返回None
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
    print("列名列表:", importer.get_column_list())
