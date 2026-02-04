#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移：添加合同管理功能
将合同管理系统的表结构整合到water_quality_v2.db
"""

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = 'database/water_quality_v2.db'

def migrate():
    """执行数据库迁移"""

    print('=' * 100)
    print('开始数据库迁移：添加合同管理功能')
    print('=' * 100)
    print()

    if not os.path.exists(DATABASE_PATH):
        print(f'错误：数据库文件不存在: {DATABASE_PATH}')
        return False

    # 备份数据库
    backup_path = f'backups/water_quality_v2_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    os.makedirs('backups', exist_ok=True)

    print(f'1. 备份数据库到: {backup_path}')
    import shutil
    shutil.copy2(DATABASE_PATH, backup_path)
    print('   ✓ 备份完成')
    print()

    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()

    try:
        # 启用外键
        cursor.execute('PRAGMA foreign_keys = ON')

        print('2. 创建合同管理表...')

        # 2.1 合同基本信息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_no VARCHAR(50) UNIQUE NOT NULL,
            client_company VARCHAR(200) NOT NULL,
            test_company VARCHAR(200) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            calculated_amount DECIMAL(10, 2),
            total_tests INTEGER,
            settlement_method VARCHAR(100),
            status VARCHAR(20) DEFAULT 'active',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print('   ✓ contracts (合同基本信息表)')

        # 2.2 水厂/区域信息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS plants (
            plant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            plant_name VARCHAR(100) NOT NULL,
            plant_type VARCHAR(50),
            plant_scale VARCHAR(100),
            location VARCHAR(200),
            contact_person VARCHAR(50),
            contact_phone VARCHAR(20),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE
        )
        ''')
        print('   ✓ plants (水厂/区域信息表)')

        # 2.3 检测项目表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            plant_id INTEGER,
            sample_type VARCHAR(50) NOT NULL,
            test_project VARCHAR(50) NOT NULL,
            unit_price DECIMAL(10, 4) NOT NULL,
            yearly_times INTEGER NOT NULL,
            actual_times INTEGER DEFAULT 0,
            total_cost DECIMAL(10, 2) NOT NULL,
            test_standard VARCHAR(100),
            frequency_type VARCHAR(20),
            is_batch BOOLEAN DEFAULT 0,
            points_per_batch INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE,
            FOREIGN KEY (plant_id) REFERENCES plants(plant_id) ON DELETE SET NULL
        )
        ''')
        print('   ✓ test_items (检测项目表)')

        # 2.4 月度执行计划表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_schedule (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            planned_times INTEGER NOT NULL,
            actual_times INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'pending',
            planned_date DATE,
            actual_date DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES test_items(item_id) ON DELETE CASCADE,
            UNIQUE(item_id, year, month)
        )
        ''')
        print('   ✓ monthly_schedule (月度执行计划表)')

        # 2.5 执行记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS execution_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            execution_date DATE NOT NULL,
            sample_count INTEGER NOT NULL,
            sampler VARCHAR(50),
            report_no VARCHAR(100),
            report_date DATE,
            report_status VARCHAR(20) DEFAULT 'pending',
            result_summary TEXT,
            abnormal_items TEXT,
            cost DECIMAL(10, 2),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (schedule_id) REFERENCES monthly_schedule(schedule_id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES test_items(item_id) ON DELETE CASCADE
        )
        ''')
        print('   ✓ execution_records (执行记录表)')

        # 2.6 合同联系人表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contract_contacts (
            contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            party VARCHAR(20) NOT NULL,
            role VARCHAR(50),
            name VARCHAR(50) NOT NULL,
            phone VARCHAR(20),
            email VARCHAR(100),
            address VARCHAR(200),
            is_primary BOOLEAN DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE
        )
        ''')
        print('   ✓ contract_contacts (合同联系人表)')

        # 2.7 报告接收记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_receipts (
            receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            receipt_type VARCHAR(20) NOT NULL,
            recipient VARCHAR(50),
            receipt_date DATE NOT NULL,
            courier_no VARCHAR(50),
            email VARCHAR(100),
            is_objected BOOLEAN DEFAULT 0,
            objection_date DATE,
            objection_content TEXT,
            objection_result TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (record_id) REFERENCES execution_records(record_id) ON DELETE CASCADE
        )
        ''')
        print('   ✓ report_receipts (报告接收记录表)')

        # 2.8 结算记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settlements (
            settlement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            settlement_period VARCHAR(20) NOT NULL,
            year INTEGER NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            total_tests INTEGER,
            settlement_amount DECIMAL(10, 2) NOT NULL,
            invoice_no VARCHAR(50),
            invoice_date DATE,
            payment_status VARCHAR(20) DEFAULT 'pending',
            payment_date DATE,
            payment_amount DECIMAL(10, 2),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE
        )
        ''')
        print('   ✓ settlements (结算记录表)')

        print()
        print('3. 创建索引...')

        # 创建索引
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_contract_no ON contracts(contract_no)',
            'CREATE INDEX IF NOT EXISTS idx_contract_dates ON contracts(start_date, end_date, status)',
            'CREATE INDEX IF NOT EXISTS idx_plant_contract ON plants(contract_id)',
            'CREATE INDEX IF NOT EXISTS idx_item_contract ON test_items(contract_id)',
            'CREATE INDEX IF NOT EXISTS idx_item_plant ON test_items(plant_id)',
            'CREATE INDEX IF NOT EXISTS idx_schedule_item ON monthly_schedule(item_id)',
            'CREATE INDEX IF NOT EXISTS idx_schedule_date ON monthly_schedule(year, month)',
            'CREATE INDEX IF NOT EXISTS idx_schedule_status ON monthly_schedule(status)',
            'CREATE INDEX IF NOT EXISTS idx_record_date ON execution_records(execution_date)',
            'CREATE INDEX IF NOT EXISTS idx_record_schedule ON execution_records(schedule_id)',
            'CREATE INDEX IF NOT EXISTS idx_contact_contract ON contract_contacts(contract_id)',
            'CREATE INDEX IF NOT EXISTS idx_settlement_contract ON settlements(contract_id)',
            'CREATE INDEX IF NOT EXISTS idx_settlement_period ON settlements(year, settlement_period)',
        ]

        for idx_sql in indexes:
            cursor.execute(idx_sql)
        print('   ✓ 已创建 13 个索引')

        print()
        print('4. 创建视图...')

        # 4.1 合同执行进度视图
        cursor.execute('''
        CREATE VIEW IF NOT EXISTS v_contract_progress AS
        SELECT
            c.contract_id,
            c.contract_no,
            c.client_company,
            c.start_date,
            c.end_date,
            c.total_amount,
            COUNT(DISTINCT ti.item_id) as total_items,
            SUM(ti.yearly_times) as planned_total_tests,
            SUM(ti.actual_times) as completed_total_tests,
            ROUND(CAST(SUM(ti.actual_times) AS FLOAT) * 100.0 /
                  NULLIF(SUM(ti.yearly_times), 0), 2) as completion_rate,
            SUM(CASE WHEN ms.status = 'completed' THEN 1 ELSE 0 END) as completed_schedules,
            COUNT(ms.schedule_id) as total_schedules
        FROM contracts c
        LEFT JOIN test_items ti ON c.contract_id = ti.contract_id
        LEFT JOIN monthly_schedule ms ON ti.item_id = ms.item_id
        GROUP BY c.contract_id
        ''')
        print('   ✓ v_contract_progress (合同执行进度视图)')

        # 4.2 月度执行汇总视图
        cursor.execute('''
        CREATE VIEW IF NOT EXISTS v_monthly_execution AS
        SELECT
            c.contract_no,
            c.client_company,
            ms.year,
            ms.month,
            p.plant_name,
            ti.sample_type,
            ti.test_project,
            ms.planned_times,
            ms.actual_times,
            ms.status,
            ti.unit_price,
            (ms.actual_times * ti.unit_price) as month_cost
        FROM monthly_schedule ms
        JOIN test_items ti ON ms.item_id = ti.item_id
        JOIN contracts c ON ti.contract_id = c.contract_id
        LEFT JOIN plants p ON ti.plant_id = p.plant_id
        ''')
        print('   ✓ v_monthly_execution (月度执行汇总视图)')

        # 4.3 水厂检测汇总视图
        cursor.execute('''
        CREATE VIEW IF NOT EXISTS v_plant_test_summary AS
        SELECT
            p.plant_id,
            p.plant_name,
            c.contract_no,
            COUNT(ti.item_id) as item_count,
            SUM(ti.yearly_times) as yearly_total_tests,
            SUM(ti.actual_times) as completed_tests,
            SUM(ti.total_cost) as total_cost,
            ROUND(CAST(SUM(ti.actual_times) AS FLOAT) * 100.0 /
                  NULLIF(SUM(ti.yearly_times), 0), 2) as completion_rate
        FROM plants p
        JOIN contracts c ON p.contract_id = c.contract_id
        LEFT JOIN test_items ti ON p.plant_id = ti.plant_id
        GROUP BY p.plant_id
        ''')
        print('   ✓ v_plant_test_summary (水厂检测汇总视图)')

        conn.commit()

        print()
        print('=' * 100)
        print('✓ 数据库迁移完成！')
        print('=' * 100)
        print()
        print('新增内容：')
        print('  - 8个合同管理表')
        print('  - 13个索引')
        print('  - 3个统计视图')
        print()

        return True

    except Exception as e:
        print(f'\n错误：迁移失败')
        print(f'错误信息: {str(e)}')
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    success = migrate()
    if success:
        print('数据库迁移成功！可以开始使用合同管理功能。')
    else:
        print('数据库迁移失败！请检查错误信息。')
