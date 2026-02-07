#!/usr/bin/env python3
"""
数据库迁移脚本：添加样品类型版本控制和优化排序序号

功能：
1. 为 sample_types 表添加 version 和 updated_at 字段
2. 将 template_indicators 表的 sort_order 从连续序号改为间隔序号（0,1,2... -> 0,10,20...）
3. 为现有数据初始化版本号为 1

作者：System Migration
日期：2026-02-07
"""

import sqlite3
import os
from datetime import datetime

# 数据库路径
DATABASE_PATH = 'database/water_quality_v2.db'

def migrate():
    """执行数据库迁移"""

    # 检查数据库是否存在
    if not os.path.exists(DATABASE_PATH):
        print(f"错误：数据库文件不存在: {DATABASE_PATH}")
        return False

    print("=" * 60)
    print("样品类型版本控制和排序优化迁移")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 备份数据库
    backup_path = f'backups/water_quality_v2_before_version_control_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    os.makedirs('backups', exist_ok=True)

    print(f"正在备份数据库到: {backup_path}")
    import shutil
    shutil.copy2(DATABASE_PATH, backup_path)
    print("✓ 数据库备份完成")
    print()

    # 连接数据库
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 开始事务
        cursor.execute('BEGIN TRANSACTION')

        # ========== 步骤1：检查并添加 version 字段 ==========
        print("步骤1：检查 sample_types 表结构...")
        cursor.execute("PRAGMA table_info(sample_types)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'version' not in columns:
            print("  添加 version 字段...")
            cursor.execute('ALTER TABLE sample_types ADD COLUMN version INTEGER DEFAULT 1')
            print("  ✓ version 字段添加成功")
        else:
            print("  ℹ version 字段已存在，跳过")

        # ========== 步骤2：检查并添加 updated_at 字段 ==========
        if 'updated_at' not in columns:
            print("  添加 updated_at 字段...")
            # SQLite不支持ALTER TABLE时使用CURRENT_TIMESTAMP，需要分两步
            cursor.execute('ALTER TABLE sample_types ADD COLUMN updated_at TIMESTAMP')
            cursor.execute("UPDATE sample_types SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
            print("  ✓ updated_at 字段添加成功")
        else:
            print("  ℹ updated_at 字段已存在，跳过")

        print()

        # ========== 步骤3：初始化现有数据的版本号 ==========
        print("步骤2：初始化现有样品类型的版本号...")
        cursor.execute('UPDATE sample_types SET version = 1 WHERE version IS NULL')
        updated_count = cursor.rowcount
        print(f"  ✓ 已初始化 {updated_count} 个样品类型的版本号为 1")
        print()

        # ========== 步骤4：优化排序序号（改为间隔值） ==========
        print("步骤3：优化检测项目排序序号...")

        # 获取所有样品类型
        cursor.execute('SELECT id, name FROM sample_types')
        sample_types = cursor.fetchall()

        total_updated = 0
        for sample_type in sample_types:
            sample_type_id = sample_type['id']
            sample_type_name = sample_type['name']

            # 获取该样品类型的所有检测项目（按当前排序）
            cursor.execute('''
                SELECT id, indicator_id, sort_order
                FROM template_indicators
                WHERE sample_type_id = ?
                ORDER BY sort_order, id
            ''', (sample_type_id,))

            indicators = cursor.fetchall()

            if not indicators:
                continue

            # 检查是否需要更新（如果已经是间隔序号则跳过）
            needs_update = False
            for idx, ind in enumerate(indicators):
                expected_order = idx * 10
                if ind['sort_order'] != expected_order:
                    needs_update = True
                    break

            if not needs_update:
                continue

            # 更新为间隔序号
            for idx, ind in enumerate(indicators):
                new_order = idx * 10
                cursor.execute('''
                    UPDATE template_indicators
                    SET sort_order = ?
                    WHERE id = ?
                ''', (new_order, ind['id']))

            print(f"  ✓ 已优化样品类型 [{sample_type_name}] 的 {len(indicators)} 个检测项目排序")
            total_updated += len(indicators)

        print(f"  ✓ 共优化 {total_updated} 个检测项目的排序序号")
        print()

        # ========== 步骤5：验证迁移结果 ==========
        print("步骤4：验证迁移结果...")

        # 验证 version 字段
        cursor.execute('SELECT COUNT(*) as cnt FROM sample_types WHERE version IS NULL')
        null_version_count = cursor.fetchone()['cnt']
        if null_version_count > 0:
            raise Exception(f"发现 {null_version_count} 个样品类型的版本号为空")
        print("  ✓ 所有样品类型都有有效的版本号")

        # 验证排序序号
        cursor.execute('''
            SELECT COUNT(*) as cnt
            FROM template_indicators
            WHERE sort_order % 10 != 0
        ''')
        non_interval_count = cursor.fetchone()['cnt']
        if non_interval_count > 0:
            print(f"  ⚠ 发现 {non_interval_count} 个检测项目使用非间隔序号（这可能是正常的）")
        else:
            print("  ✓ 所有检测项目都使用间隔序号")

        print()

        # 提交事务
        conn.commit()

        print("=" * 60)
        print("✓ 迁移成功完成！")
        print("=" * 60)
        print()
        print("迁移摘要：")
        print(f"  - 样品类型总数: {len(sample_types)}")
        print(f"  - 已优化排序的检测项目: {total_updated}")
        print(f"  - 备份文件: {backup_path}")
        print()
        print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return True

    except Exception as e:
        # 回滚事务
        conn.rollback()
        print()
        print("=" * 60)
        print("✗ 迁移失败！")
        print("=" * 60)
        print(f"错误信息: {str(e)}")
        print()
        print("数据库已回滚到迁移前状态")
        print(f"如需恢复，可使用备份文件: {backup_path}")
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    print()
    print("警告：此操作将修改数据库结构和数据")
    print("建议在执行前备份数据库（脚本会自动创建备份）")
    print()

    # 检查是否在正确的目录
    if not os.path.exists('database'):
        print("错误：请在项目根目录下运行此脚本")
        print("当前目录:", os.getcwd())
        exit(1)

    response = input("是否继续？(yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        print()
        success = migrate()
        exit(0 if success else 1)
    else:
        print("迁移已取消")
        exit(0)
