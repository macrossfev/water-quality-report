"""
数据库迁移脚本 V3
添加报告审核功能相关字段
"""
import sqlite3
import os
from datetime import datetime

def migrate_database():
    """执行数据库迁移"""
    db_path = 'database/water_quality_v2.db'

    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("="*60)
        print("开始数据库迁移 V3")
        print("="*60)

        # 1. 检查reports表的现有列
        cursor.execute("PRAGMA table_info(reports)")
        reports_columns = [col[1] for col in cursor.fetchall()]
        print(f"\n当前reports表字段: {reports_columns}")

        # 2. 添加template_id字段（关联报告模板）
        if 'template_id' not in reports_columns:
            print("\n添加 template_id 字段...")
            cursor.execute('ALTER TABLE reports ADD COLUMN template_id INTEGER')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_reports_template_id ON reports(template_id)
            ''')
            print("✓ template_id 字段添加成功")
        else:
            print("\n✓ template_id 字段已存在")

        # 3. 添加review_status字段（审核状态）
        # draft: 草稿, pending: 待审核, approved: 已审核, rejected: 已拒绝
        if 'review_status' not in reports_columns:
            print("\n添加 review_status 字段...")
            cursor.execute("ALTER TABLE reports ADD COLUMN review_status TEXT DEFAULT 'draft'")
            # 更新现有记录为待审核状态
            cursor.execute("UPDATE reports SET review_status = 'pending' WHERE review_status IS NULL")
            print("✓ review_status 字段添加成功")
        else:
            print("\n✓ review_status 字段已存在")

        # 4. 添加review_person字段（审核人）
        if 'review_person' not in reports_columns:
            print("\n添加 review_person 字段...")
            cursor.execute('ALTER TABLE reports ADD COLUMN review_person TEXT')
            print("✓ review_person 字段添加成功")
        else:
            print("\n✓ review_person 字段已存在")

        # 5. 添加review_time字段（审核时间）
        if 'review_time' not in reports_columns:
            print("\n添加 review_time 字段...")
            cursor.execute('ALTER TABLE reports ADD COLUMN review_time TIMESTAMP')
            print("✓ review_time 字段添加成功")
        else:
            print("\n✓ review_time 字段已存在")

        # 6. 添加review_comment字段（审核意见）
        if 'review_comment' not in reports_columns:
            print("\n添加 review_comment 字段...")
            cursor.execute('ALTER TABLE reports ADD COLUMN review_comment TEXT')
            print("✓ review_comment 字段添加成功")
        else:
            print("\n✓ review_comment 字段已存在")

        # 7. 添加generated_report_path字段（生成的报告文件路径）
        if 'generated_report_path' not in reports_columns:
            print("\n添加 generated_report_path 字段...")
            cursor.execute('ALTER TABLE reports ADD COLUMN generated_report_path TEXT')
            print("✓ generated_report_path 字段添加成功")
        else:
            print("\n✓ generated_report_path 字段已存在")

        # 8. 扩展template_field_mappings表，支持更复杂的字段配置
        cursor.execute("PRAGMA table_info(template_field_mappings)")
        field_mapping_columns = [col[1] for col in cursor.fetchall()]
        print(f"\n当前template_field_mappings表字段: {field_mapping_columns}")

        # 添加field_display_name字段（字段显示名称，对应[]内容）
        if 'field_display_name' not in field_mapping_columns:
            print("\n添加 field_display_name 字段...")
            cursor.execute('ALTER TABLE template_field_mappings ADD COLUMN field_display_name TEXT')
            print("✓ field_display_name 字段添加成功")
        else:
            print("\n✓ field_display_name 字段已存在")

        # 添加is_required字段（是否必填）
        if 'is_required' not in field_mapping_columns:
            print("\n添加 is_required 字段...")
            cursor.execute('ALTER TABLE template_field_mappings ADD COLUMN is_required BOOLEAN DEFAULT 0')
            print("✓ is_required 字段添加成功")
        else:
            print("\n✓ is_required 字段已存在")

        # 添加default_value字段（默认值，对应;前的内容）
        if 'default_value' not in field_mapping_columns:
            print("\n添加 default_value 字段...")
            cursor.execute('ALTER TABLE template_field_mappings ADD COLUMN default_value TEXT')
            print("✓ default_value 字段添加成功")
        else:
            print("\n✓ default_value 字段已存在")

        # 添加placeholder字段（占位符，对应()内容）
        if 'placeholder' not in field_mapping_columns:
            print("\n添加 placeholder 字段...")
            cursor.execute('ALTER TABLE template_field_mappings ADD COLUMN placeholder TEXT')
            print("✓ placeholder 字段添加成功")
        else:
            print("\n✓ placeholder 字段已存在")

        # 9. 创建报告字段值表（存储报告的实际填写值）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS report_field_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                field_mapping_id INTEGER NOT NULL,
                field_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
                FOREIGN KEY (field_mapping_id) REFERENCES template_field_mappings (id) ON DELETE CASCADE
            )
        ''')
        print("\n✓ report_field_values 表已就绪")

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_report_field_values_report_id ON report_field_values(report_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_report_field_values_field_mapping_id ON report_field_values(field_mapping_id)')

        # 10. 提交更改
        conn.commit()

        print("\n" + "="*60)
        print("数据库迁移 V3 完成!")
        print("="*60)

        # 验证迁移结果
        cursor.execute("PRAGMA table_info(reports)")
        updated_columns = [col[1] for col in cursor.fetchall()]
        print(f"\n更新后的reports表字段: {updated_columns}")

        return True

    except Exception as e:
        print(f"\n迁移失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    print("水质检测报告系统 - 数据库迁移 V3")
    print("添加报告审核功能相关字段")
    print()

    success = migrate_database()

    if success:
        print("\n✓ 迁移成功完成")
        print("\n新增功能:")
        print("  - 报告审核流程（draft/pending/approved/rejected）")
        print("  - 审核人和审核时间记录")
        print("  - 审核意见")
        print("  - 报告模板关联")
        print("  - 生成报告文件路径存储")
        print("  - 字段配置增强（显示名、必填、默认值、占位符）")
        print("  - 报告字段值存储")
    else:
        print("\n✗ 迁移失败")
