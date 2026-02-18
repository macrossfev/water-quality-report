"""
水质检测报告系统 - 数据库模型 V2
重构版本,支持模板管理、权限系统、分组等新功能
"""
from contextlib import contextmanager
from datetime import datetime
import sqlite3
import os
import re
from werkzeug.security import generate_password_hash

DATABASE_PATH = 'database/water_quality_v2.db'

def get_db_connection():
    """获取数据库连接（旧接口，保持向后兼容，需手动 close()）
    注意：使用 autocommit 模式，rollback() 无效。新代码请使用 get_db()"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA busy_timeout = 30000')
    return conn

@contextmanager
def get_db():
    """数据库连接上下文管理器（推荐），自动处理 commit/rollback/close
    使用事务模式，支持正确的 rollback"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA busy_timeout = 30000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_database():
    """初始化数据库表结构"""
    os.makedirs('database', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    os.makedirs('backups', exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()

    # 启用WAL模式以支持更好的并发
    cursor.execute('PRAGMA journal_mode = WAL')
    # 启用外键约束
    cursor.execute('PRAGMA foreign_keys = ON')
    # 设置繁忙超时
    cursor.execute('PRAGMA busy_timeout = 30000')

    # ==================== 用户表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('super_admin', 'admin', 'reviewer', 'reporter')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 迁移：修复旧的角色 CHECK 约束（仅允许 admin/reporter -> 支持全部角色）
    user_sql = cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    if user_sql and "'admin', 'reporter')" in user_sql[0] and "'super_admin'" not in user_sql[0]:
        print("正在修复users表角色约束...")
        cursor.execute('PRAGMA writable_schema = ON')
        fixed_sql = user_sql[0].replace(
            "role IN ('admin', 'reporter')",
            "role IN ('super_admin', 'admin', 'reviewer', 'reporter')"
        )
        cursor.execute(
            "UPDATE sqlite_master SET sql = ? WHERE type = 'table' AND name = 'users'",
            (fixed_sql,)
        )
        cursor.execute('PRAGMA writable_schema = OFF')
        print("users表角色约束已更新，支持 super_admin/admin/reviewer/reporter")

    # ==================== 公司表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 客户管理表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspected_unit TEXT NOT NULL,
            water_plant TEXT,
            unit_address TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            email TEXT,
            remark TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 样品类型表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sample_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            description TEXT,
            remark TEXT,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 检测项目分组表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicator_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            is_system BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 检测指标表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            name TEXT NOT NULL,
            unit TEXT,
            default_value TEXT,
            limit_value TEXT,
            detection_method TEXT,
            description TEXT,
            remark TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES indicator_groups (id) ON DELETE SET NULL,
            UNIQUE(name, group_id)
        )
    ''')

    # ==================== 模板-检测项目关联表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_type_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL,
            is_required BOOLEAN DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sample_type_id) REFERENCES sample_types (id) ON DELETE CASCADE,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id) ON DELETE CASCADE,
            UNIQUE(sample_type_id, indicator_id)
        )
    ''')

    # ==================== 报告模板配置表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT DEFAULT '水质检测中心',
            report_title TEXT DEFAULT '水质检测报告',
            footer_text TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 报告表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_number TEXT NOT NULL UNIQUE,
            sample_number TEXT NOT NULL,
            company_id INTEGER,
            sample_type_id INTEGER NOT NULL,
            detection_person TEXT,
            review_person TEXT,
            detection_date DATE,
            remark TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE SET NULL,
            FOREIGN KEY (sample_type_id) REFERENCES sample_types (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # ==================== 报告数据表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL,
            measured_value TEXT,
            remark TEXT,
            FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id)
        )
    ''')

    # ==================== 操作日志表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            operation_type TEXT NOT NULL,
            operation_detail TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # ==================== 原始数据列名配置表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data_column_schema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            column_name TEXT NOT NULL UNIQUE,
            column_order INTEGER NOT NULL,
            data_type TEXT NOT NULL CHECK(data_type IN ('text', 'numeric', 'date')),
            is_base_field BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 原始数据记录表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_number TEXT NOT NULL UNIQUE,
            report_number TEXT,
            company_name TEXT,
            plant_name TEXT,
            sample_type TEXT,
            sampling_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 原始数据检测值表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            value TEXT,
            FOREIGN KEY (record_id) REFERENCES raw_data_records (id) ON DELETE CASCADE,
            UNIQUE(record_id, column_name)
        )
    ''')

    # ==================== 原始数据字段映射表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data_field_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_field_name TEXT NOT NULL UNIQUE,
            indicator_id INTEGER NOT NULL,
            indicator_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (indicator_id) REFERENCES indicators (id) ON DELETE CASCADE
        )
    ''')

    # ==================== 导出模板分类表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS export_template_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==================== 导出模板表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS export_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            sample_type_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES export_template_categories (id) ON DELETE SET NULL,
            FOREIGN KEY (sample_type_id) REFERENCES sample_types (id) ON DELETE SET NULL,
            UNIQUE(category_id, name)
        )
    ''')

    # ==================== 导出模板-列关联表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS export_template_columns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            column_order INTEGER DEFAULT 0,
            FOREIGN KEY (template_id) REFERENCES export_templates (id) ON DELETE CASCADE,
            UNIQUE(template_id, column_name)
        )
    ''')

    conn.commit()

    # ==================== 初始化默认数据 ====================
    init_default_data(cursor, conn)

    conn.close()
    print("数据库初始化成功！")

def init_default_data(cursor, conn):
    """初始化默认数据"""

    # 检查是否已有管理员用户
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    admin_count = cursor.fetchone()[0]

    if admin_count == 0:
        # 创建默认管理员账号: admin/admin123
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', generate_password_hash('admin123'), 'admin')
        )
        print("默认管理员账号已创建: admin/admin123")

    # 检查是否已有报告模板配置
    cursor.execute('SELECT COUNT(*) FROM report_templates')
    template_count = cursor.fetchone()[0]

    if template_count == 0:
        cursor.execute(
            'INSERT INTO report_templates (company_name, report_title, footer_text) VALUES (?, ?, ?)',
            ('水质检测中心', '水质检测报告', '检测人:______  审核人:______')
        )
        print("默认报告模板已创建")

    # 创建默认分组
    cursor.execute('SELECT COUNT(*) FROM indicator_groups')
    if cursor.fetchone()[0] == 0:
        default_groups = [
            ('理化指标', 1, 1),
            ('微生物指标', 2, 1),
            ('重金属指标', 3, 1)
        ]
        cursor.executemany(
            'INSERT INTO indicator_groups (name, sort_order, is_system) VALUES (?, ?, ?)',
            default_groups
        )
        print("默认检测项目分组已创建")

    conn.commit()

def run_migrations():
    """独立的数据库迁移函数，仅在需要时手动调用（python3 -c "from models_v2 import run_migrations; run_migrations()"）"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode = WAL')
    cursor.execute('PRAGMA foreign_keys = ON')
    cursor.execute('PRAGMA busy_timeout = 30000')

    migrated = False

    try:
        # ==================== export_templates 添加 sample_type_id ====================
        cursor.execute("PRAGMA table_info(export_templates)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'sample_type_id' not in columns:
            print("正在迁移export_templates表，添加sample_type_id列...")
            cursor.execute('ALTER TABLE export_templates ADD COLUMN sample_type_id INTEGER')
            migrated = True
            print("export_templates表迁移完成！")

        # ==================== reports 添加新列 ====================
        cursor.execute("PRAGMA table_info(reports)")
        report_columns = [row[1] for row in cursor.fetchall()]
        if 'detection_items_description' not in report_columns:
            print("正在迁移reports表，添加detection_items_description列...")
            cursor.execute('ALTER TABLE reports ADD COLUMN detection_items_description TEXT')
            migrated = True
            print("reports表迁移完成（detection_items_description）！")
        if 'attachment_info' not in report_columns:
            print("正在迁移reports表，添加attachment_info列...")
            cursor.execute('ALTER TABLE reports ADD COLUMN attachment_info TEXT')
            migrated = True
            print("reports表迁移完成（attachment_info）！")

        # ==================== sample_types 去掉 UNIQUE(name) ====================
        st_indexes = cursor.execute("PRAGMA index_list(sample_types)").fetchall()
        for idx in st_indexes:
            idx_cols = cursor.execute(f"PRAGMA index_info('{idx[1]}')").fetchall()
            if idx[2] == 1 and len(idx_cols) == 1:
                table_info = cursor.execute("PRAGMA table_info(sample_types)").fetchall()
                col_map = {row[0]: row[1] for row in table_info}
                if col_map.get(idx_cols[0][1]) == 'name':
                    existing_tables = [r[0] for r in cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sample_types_old')"
                    ).fetchall()]
                    if 'sample_types_old' in existing_tables:
                        print("sample_types迁移：检测到sample_types_old已存在，跳过")
                        break
                    print("正在迁移sample_types表：去掉UNIQUE(name)约束...")
                    cursor.execute('PRAGMA foreign_keys = OFF')
                    cursor.execute('ALTER TABLE sample_types RENAME TO sample_types_old')
                    cursor.execute('''
                        CREATE TABLE sample_types (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            code TEXT NOT NULL UNIQUE,
                            description TEXT,
                            remark TEXT,
                            version INTEGER DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    old_cols = [r[1] for r in cursor.execute("PRAGMA table_info(sample_types_old)").fetchall()]
                    new_cols = [r[1] for r in cursor.execute("PRAGMA table_info(sample_types)").fetchall()]
                    common = [c for c in old_cols if c in new_cols]
                    cols_str = ', '.join(common)
                    cursor.execute(f'INSERT INTO sample_types ({cols_str}) SELECT {cols_str} FROM sample_types_old')
                    cursor.execute('DROP TABLE sample_types_old')
                    cursor.execute('PRAGMA foreign_keys = ON')
                    migrated = True
                    print("sample_types表迁移完成：允许同名样品类型！")
                    break

        # ==================== template_indicators 添加 limit_value ====================
        cursor.execute("PRAGMA table_info(template_indicators)")
        ti_columns = [row[1] for row in cursor.fetchall()]
        if 'limit_value' not in ti_columns:
            print("正在迁移template_indicators表，添加limit_value列...")
            cursor.execute('ALTER TABLE template_indicators ADD COLUMN limit_value TEXT')
            cursor.execute('''
                UPDATE template_indicators SET limit_value = (
                    SELECT i.limit_value FROM indicators i
                    WHERE i.id = template_indicators.indicator_id
                )
            ''')
            migrated = True
            print("template_indicators表迁移完成（limit_value）！")

        # ==================== sample_types 添加新列 ====================
        cursor.execute("PRAGMA table_info(sample_types)")
        sample_type_columns = [row[1] for row in cursor.fetchall()]
        if 'version' not in sample_type_columns:
            cursor.execute('ALTER TABLE sample_types ADD COLUMN version INTEGER DEFAULT 1')
            migrated = True
        if 'updated_at' not in sample_type_columns:
            cursor.execute('ALTER TABLE sample_types ADD COLUMN updated_at TIMESTAMP')
            cursor.execute("UPDATE sample_types SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
            migrated = True

        default_fields = [
            ('default_sample_status', 'TEXT'),
            ('default_sampling_basis', 'TEXT'),
            ('default_product_standard', 'TEXT'),
            ('default_detection_items', 'TEXT'),
            ('default_test_conclusion', 'TEXT'),
        ]
        cursor.execute("PRAGMA table_info(sample_types)")
        sample_type_columns = [row[1] for row in cursor.fetchall()]
        for field_name, field_type in default_fields:
            if field_name not in sample_type_columns:
                cursor.execute(f'ALTER TABLE sample_types ADD COLUMN {field_name} {field_type}')
                migrated = True

        # ==================== indicators 迁移 UNIQUE(name) → UNIQUE(name, group_id) ====================
        old_indexes = cursor.execute("PRAGMA index_list(indicators)").fetchall()
        has_old_unique = False
        for idx in old_indexes:
            idx_info = cursor.execute(f"PRAGMA index_info('{idx[1]}')").fetchall()
            if idx[2] == 1 and len(idx_info) == 1:
                col_name_in_idx = cursor.execute(f"PRAGMA index_info('{idx[1]}')").fetchone()
                col_id = col_name_in_idx[1]
                table_info = cursor.execute("PRAGMA table_info(indicators)").fetchall()
                col_map = {row[0]: row[1] for row in table_info}
                if col_map.get(col_id) == 'name':
                    has_old_unique = True
                    break

        if has_old_unique:
            existing_tables = [r[0] for r in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('indicators_old')"
            ).fetchall()]
            if 'indicators_old' not in existing_tables:
                print("正在迁移indicators表：UNIQUE(name) → UNIQUE(name, group_id)...")
                cursor.execute('PRAGMA foreign_keys = OFF')
                cursor.execute('ALTER TABLE indicators RENAME TO indicators_old')
                cursor.execute('''
                    CREATE TABLE indicators (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id INTEGER,
                        name TEXT NOT NULL,
                        unit TEXT,
                        default_value TEXT,
                        limit_value TEXT,
                        detection_method TEXT,
                        description TEXT,
                        remark TEXT,
                        sort_order INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (group_id) REFERENCES indicator_groups (id) ON DELETE SET NULL,
                        UNIQUE(name, group_id)
                    )
                ''')
                cursor.execute('''
                    INSERT INTO indicators (id, group_id, name, unit, default_value, limit_value,
                        detection_method, description, remark, sort_order, created_at)
                    SELECT id, group_id, name, unit, default_value, limit_value,
                        detection_method, description, remark, sort_order, created_at
                    FROM indicators_old
                ''')
                cursor.execute('DROP TABLE indicators_old')
                cursor.execute('PRAGMA foreign_keys = ON')
                migrated = True
                print("  约束已更新为 UNIQUE(name, group_id)")

            # 拆分共享指标
            shared = cursor.execute('''
                SELECT ti.id, ti.sample_type_id, ti.indicator_id, ti.limit_value,
                       i.name, i.unit, i.default_value, i.detection_method, i.description,
                       i.remark, i.sort_order, i.group_id,
                       st.name
                FROM template_indicators ti
                JOIN indicators i ON ti.indicator_id = i.id
                JOIN sample_types st ON ti.sample_type_id = st.id
                JOIN indicator_groups g ON g.name = st.name
                WHERE i.group_id != g.id
            ''').fetchall()

            for row in shared:
                ti_id, st_id, ind_id, ti_limit = row[0], row[1], row[2], row[3]
                ind_name, ind_unit, ind_default = row[4], row[5], row[6]
                ind_method, ind_desc, ind_remark, ind_sort = row[7], row[8], row[9], row[10]
                st_name = row[12]

                target_group = cursor.execute(
                    'SELECT id FROM indicator_groups WHERE name = ?', (st_name,)
                ).fetchone()
                if not target_group:
                    continue
                target_group_id = target_group[0]

                existing = cursor.execute(
                    'SELECT id FROM indicators WHERE name = ? AND group_id = ?',
                    (ind_name, target_group_id)
                ).fetchone()

                if existing:
                    new_id = existing[0]
                else:
                    cursor.execute(
                        'INSERT INTO indicators (group_id, name, unit, default_value, limit_value, '
                        'detection_method, description, remark, sort_order) '
                        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (target_group_id, ind_name, ind_unit, ind_default,
                         ti_limit or '', ind_method, ind_desc, ind_remark, ind_sort)
                    )
                    new_id = cursor.lastrowid

                cursor.execute(
                    'UPDATE template_indicators SET indicator_id = ? WHERE id = ?',
                    (new_id, ti_id)
                )
                cursor.execute('''
                    UPDATE report_data SET indicator_id = ?
                    WHERE indicator_id = ? AND report_id IN (
                        SELECT id FROM reports WHERE sample_type_id = ?
                    )
                ''', (new_id, ind_id, st_id))
                print(f"  拆分: {ind_name} -> 独立记录(group={st_name}, ID={new_id})")

        # ==================== 修复外键引用 ====================
        stale_fk_rows = cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' "
            "AND sql IS NOT NULL "
            "AND (sql LIKE '%indicators_old%' OR sql LIKE '%sample_types_old%' "
            "     OR sql LIKE '%_fixfk%')"
        ).fetchall()

        if stale_fk_rows:
            stale_names = [r[0] for r in stale_fk_rows]
            print(f"检测到外键引用旧表的表: {stale_names}，修复中...")
            cursor.execute('PRAGMA writable_schema = ON')
            for tbl_name, tbl_sql in stale_fk_rows:
                fixed_sql = tbl_sql
                fixed_sql = re.sub(r'"indicators_old[^"]*"', 'indicators', fixed_sql)
                fixed_sql = re.sub(r'"sample_types_old[^"]*"', 'sample_types', fixed_sql)
                fixed_sql = re.sub(r'"reports_fixfk[^"]*"', 'reports', fixed_sql)
                fixed_sql = re.sub(r'"excel_report_templates_fixfk[^"]*"', 'excel_report_templates', fixed_sql)
                fixed_sql = re.sub(r'"template_field_mappings_fixfk[^"]*"', 'template_field_mappings', fixed_sql)
                if fixed_sql != tbl_sql:
                    cursor.execute(
                        "UPDATE sqlite_master SET sql = ? WHERE type = 'table' AND name = ?",
                        (fixed_sql, tbl_name)
                    )
                    print(f"  已修复 {tbl_name} 的外键引用")
            cursor.execute('PRAGMA writable_schema = OFF')
            integrity = cursor.execute('PRAGMA integrity_check').fetchone()
            if integrity and integrity[0] == 'ok':
                print("外键引用修复完成，完整性检查通过！")
            else:
                print(f"警告：完整性检查结果: {integrity}")
            migrated = True

        conn.commit()
        if migrated:
            print("数据库迁移完成！")
        else:
            print("数据库无需迁移。")

    except Exception as e:
        conn.rollback()
        print(f"数据库迁移失败，已回滚: {e}")
        raise
    finally:
        conn.close()


def create_indexes():
    """创建索引优化查询性能"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 为常用查询字段创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_sample_number ON reports(sample_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_report_number ON reports(report_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_operation_logs_created_at ON operation_logs(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicators_group_id ON indicators(group_id)')

    # 原始数据相关索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_sample_number ON raw_data_records(sample_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_sampling_date ON raw_data_records(sampling_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_company_name ON raw_data_records(company_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_plant_name ON raw_data_records(plant_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_records_sample_type ON raw_data_records(sample_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_data_values_record_id ON raw_data_values(record_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_export_template_columns_template_id ON export_template_columns(template_id)')

    conn.commit()
    conn.close()
    print("数据库索引创建成功！")

if __name__ == '__main__':
    import sys
    init_database()
    if '--migrate' in sys.argv:
        run_migrations()
    create_indexes()
