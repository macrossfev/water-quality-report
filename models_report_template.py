"""
报告模版数据模型扩展
支持Excel报告模版的存储和管理
"""
import sqlite3
import os
from models_v2 import DATABASE_PATH, get_db_connection

def create_report_template_tables():
    """创建报告模版相关的数据表"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 启用外键约束
    cursor.execute('PRAGMA foreign_keys = ON')

    # ==================== Excel报告模版表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS excel_report_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sample_type_id INTEGER,
            description TEXT,
            template_file_path TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sample_type_id) REFERENCES sample_types (id) ON DELETE SET NULL
        )
    ''')

    # ==================== 模版字段映射表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_field_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            field_display_name TEXT,
            field_type TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            cell_address TEXT,
            start_row INTEGER,
            start_col INTEGER,
            placeholder TEXT,
            description TEXT,
            is_required BOOLEAN DEFAULT 0,
            is_reference BOOLEAN DEFAULT 0,
            default_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (template_id) REFERENCES excel_report_templates (id) ON DELETE CASCADE
        )
    ''')

    # ==================== 模版页面配置表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_sheet_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            sheet_name TEXT NOT NULL,
            sheet_index INTEGER NOT NULL,
            sheet_type TEXT,
            page_number INTEGER,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (template_id) REFERENCES excel_report_templates (id) ON DELETE CASCADE
        )
    ''')

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_template_field_mappings_template_id ON template_field_mappings(template_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_template_sheet_configs_template_id ON template_sheet_configs(template_id)')

    conn.commit()
    conn.close()

    print("报告模版数据表创建成功！")

    # 执行数据库迁移
    migrate_template_tables()

def migrate_template_tables():
    """迁移模板表，添加新字段"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # 检查 template_field_mappings 表是否需要添加新字段
        cursor.execute("PRAGMA table_info(template_field_mappings)")
        columns = [row[1] for row in cursor.fetchall()]

        migrations_needed = []

        if 'field_display_name' not in columns:
            migrations_needed.append('field_display_name')
        if 'placeholder' not in columns:
            migrations_needed.append('placeholder')
        if 'is_reference' not in columns:
            migrations_needed.append('is_reference')

        if migrations_needed:
            print(f"正在迁移 template_field_mappings 表，添加字段: {', '.join(migrations_needed)}")

            if 'field_display_name' in migrations_needed:
                cursor.execute('ALTER TABLE template_field_mappings ADD COLUMN field_display_name TEXT')
                print("  ✓ 添加字段 field_display_name")

            if 'placeholder' in migrations_needed:
                cursor.execute('ALTER TABLE template_field_mappings ADD COLUMN placeholder TEXT')
                print("  ✓ 添加字段 placeholder")

            if 'is_reference' in migrations_needed:
                cursor.execute('ALTER TABLE template_field_mappings ADD COLUMN is_reference BOOLEAN DEFAULT 0')
                print("  ✓ 添加字段 is_reference")

            conn.commit()
            print("模板表迁移完成！")

    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

def init_template_field_types():
    """
    初始化支持的字段类型

    字段类型说明：
    - text: 文本字段（报告编号、样品编号等）
    - date: 日期字段（检测日期、报告日期等）
    - selection: 下拉选择字段（样品类型、委托单位等）
    - table_data: 表格数据（检测数据列表）
    - signature: 签名字段（检测人员、审核人员等）
    - constant: 常量字段（单位名称、联系方式等）
    - formula: 公式字段（自动计算）
    """
    return {
        'text': '文本字段',
        'date': '日期字段',
        'selection': '选择字段',
        'table_data': '表格数据',
        'signature': '签名字段',
        'constant': '常量字段',
        'formula': '公式字段'
    }

def get_standard_field_definitions():
    """
    获取标准字段定义
    这些是从报告模版.xlsx中识别出的常用字段
    """
    return {
        # 基本信息
        'report_number': {
            'name': '报告编号',
            'type': 'text',
            'description': '报告编号，格式如：( 06 )字( 2025 )第( 220 )号'
        },
        'page_info': {
            'name': '页码信息',
            'type': 'formula',
            'description': '页码信息，格式如：第 1 页 共 5 页'
        },
        'company_name': {
            'name': '单位名称',
            'type': 'constant',
            'description': '检测单位名称'
        },
        'report_title': {
            'name': '报告标题',
            'type': 'constant',
            'description': '报告标题，如：检验检测报告'
        },

        # 样品信息
        'sample_name': {
            'name': '样品名称',
            'type': 'text',
            'description': '样品名称，如：出厂水【朱家岩水厂】'
        },
        'sample_number': {
            'name': '样品编号',
            'type': 'text',
            'description': '样品编号'
        },
        'sample_type': {
            'name': '样品类型',
            'type': 'selection',
            'description': '样品类型，如：出厂水、原水等'
        },
        'client_name': {
            'name': '委托单位',
            'type': 'selection',
            'description': '委托单位名称'
        },
        'client_address': {
            'name': '委托单位地址',
            'type': 'text',
            'description': '委托单位地址'
        },

        # 日期信息
        'report_date': {
            'name': '报告编制日期',
            'type': 'date',
            'description': '报告编制日期，格式如：2025 年 3 月 31 日'
        },
        'sampling_date': {
            'name': '采样日期',
            'type': 'date',
            'description': '采样日期'
        },
        'detection_date': {
            'name': '检测日期',
            'type': 'date',
            'description': '检测日期'
        },

        # 采样信息
        'sampling_person': {
            'name': '采样人',
            'type': 'text',
            'description': '采样人员姓名'
        },
        'sampling_location': {
            'name': '采样地点',
            'type': 'text',
            'description': '采样地点'
        },
        'sampling_method': {
            'name': '采样依据',
            'type': 'text',
            'description': '采样依据标准'
        },
        'sample_status': {
            'name': '样品状态',
            'type': 'text',
            'description': '样品状态描述'
        },

        # 检测标准
        'product_standard': {
            'name': '产品标准',
            'type': 'text',
            'description': '检测依据的产品标准'
        },
        'detection_items': {
            'name': '检测项目',
            'type': 'text',
            'description': '检测项目列表描述'
        },

        # 检测数据表格
        'detection_data_table': {
            'name': '检测数据表',
            'type': 'table_data',
            'description': '检测结果数据表，包含序号、项目、单位、检测结果、标准限值、检测方法'
        },

        # 结论和说明
        'detection_conclusion': {
            'name': '检测结论',
            'type': 'text',
            'description': '检测结论'
        },
        'additional_info': {
            'name': '附加信息',
            'type': 'text',
            'description': '附加信息或说明'
        },

        # 人员签名
        'prepared_by': {
            'name': '编制人',
            'type': 'signature',
            'description': '报告编制人员'
        },
        'reviewed_by': {
            'name': '审核人',
            'type': 'signature',
            'description': '报告审核人员'
        },
        'approved_by': {
            'name': '签发人',
            'type': 'signature',
            'description': '报告签发人员'
        },
        'approved_date': {
            'name': '签发日期',
            'type': 'date',
            'description': '报告签发日期'
        },

        # 联系信息
        'contact_address': {
            'name': '联系地址',
            'type': 'constant',
            'description': '检测单位联系地址'
        },
        'contact_phone': {
            'name': '联系电话',
            'type': 'constant',
            'description': '检测单位联系电话'
        },
        'postal_code': {
            'name': '邮编',
            'type': 'constant',
            'description': '检测单位邮编'
        }
    }

if __name__ == '__main__':
    create_report_template_tables()
    print("\n支持的字段类型：")
    for key, value in init_template_field_types().items():
        print(f"  - {key}: {value}")

    print("\n标准字段定义数量：", len(get_standard_field_definitions()))
