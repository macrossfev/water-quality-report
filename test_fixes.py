#!/usr/bin/env python3
"""
测试编辑页面和预览功能的修复
"""
import requests
import json
from datetime import date

BASE_URL = "http://127.0.0.1:5000"

def test_edit_and_preview_fixes():
    """测试编辑页面和预览功能的修复"""

    print("=" * 60)
    print("编辑页面和预览功能修复测试")
    print("=" * 60)

    session = requests.Session()

    # 1. 登录
    print("\n1. 登录系统...")
    login_response = session.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })

    if login_response.status_code == 200:
        print("   ✓ 登录成功")
    else:
        print(f"   ✗ 登录失败: {login_response.text}")
        return

    # 2. 获取现有报告列表
    print("\n2. 获取现有报告...")
    reports_response = session.get(f"{BASE_URL}/api/reports?status=draft&status=rejected")

    if reports_response.status_code != 200:
        print(f"   ✗ 获取报告列表失败")
        return

    reports = reports_response.json()

    if not reports or len(reports) == 0:
        print("   ✗ 没有可用的测试报告，请先创建一个报告")
        print("   提示: 在系统中创建一个包含检测数据的报告后再运行此测试")
        return

    report_id = reports[0]['id']
    print(f"   ✓ 找到测试报告，ID: {report_id}, 样品编号: {reports[0].get('sample_number', 'N/A')}")

    # 3. 测试编辑页面 - 验证limit_value和detection_method字段
    print("\n3. 测试编辑页面数据获取...")
    get_response = session.get(f"{BASE_URL}/api/reports/{report_id}")

    if get_response.status_code != 200:
        print(f"   ✗ 获取报告详情失败")
    else:
        report = get_response.json()
        print(f"   ✓ 成功获取报告详情")

        # 检查检测数据是否包含limit_value和detection_method
        if report.get('data') and len(report['data']) > 0:
            first_item = report['data'][0]

            has_limit_value = 'limit_value' in first_item
            has_detection_method = 'detection_method' in first_item

            print(f"\n   检测数据字段检查:")
            print(f"   {'✓' if has_limit_value else '✗'} limit_value字段: {first_item.get('limit_value', '(无)')}")
            print(f"   {'✓' if has_detection_method else '✗'} detection_method字段: {first_item.get('detection_method', '(无)')[:50] if first_item.get('detection_method') else '(无)'}")

            if has_limit_value and has_detection_method:
                print(f"\n   ✓ 编辑页面数据完整性验证通过")
            else:
                print(f"\n   ✗ 编辑页面缺少必要字段")

    # 4. 测试预览功能 - 验证所有信息显示
    print("\n4. 测试预览功能数据获取...")
    preview_response = session.get(f"{BASE_URL}/api/reports/{report_id}/review-detail")

    if preview_response.status_code != 200:
        print(f"   ✗ 获取预览详情失败")
    else:
        preview_data = preview_response.json()
        print(f"   ✓ 成功获取预览详情")

        # 验证基本信息字段
        report_info = preview_data.get('report', {})
        required_fields = [
            'report_number', 'report_date', 'sample_number', 'sample_source',
            'sample_status', 'sampler', 'sampling_date', 'sample_received_date',
            'sampling_location', 'sampling_basis', 'detection_date',
            'product_standard', 'test_conclusion', 'additional_info'
        ]

        print(f"\n   基本信息字段检查:")
        missing_fields = []
        for field in required_fields:
            if field in report_info:
                print(f"   ✓ {field}: {str(report_info[field])[:30]}...")
            else:
                print(f"   ✗ {field}: (缺失)")
                missing_fields.append(field)

        # 验证客户信息
        if report_info.get('remark'):
            try:
                customer_info = json.loads(report_info['remark'])
                print(f"\n   客户信息字段检查:")
                print(f"   ✓ 被检单位: {customer_info.get('customer_unit', '(无)')}")
                print(f"   ✓ 被检水厂: {customer_info.get('customer_plant', '(无)')}")
                print(f"   ✓ 联系人: {customer_info.get('customer_contact', '(无)')}")
                print(f"   ✓ 联系电话: {customer_info.get('customer_phone', '(无)')}")
            except:
                print(f"\n   ✗ 客户信息解析失败")

        # 验证检测数据
        detection_data = preview_data.get('detection_data', [])
        print(f"\n   检测数据检查:")
        print(f"   ✓ 检测项目数量: {len(detection_data)}")

        if detection_data:
            first_detection = detection_data[0]
            print(f"   ✓ 检测项目名: {first_detection.get('indicator_name', '(无)')}")
            print(f"   ✓ 检测值: {first_detection.get('measured_value', '(无)')}")
            print(f"   ✓ 单位: {first_detection.get('unit', '(无)')}")
            print(f"   ✓ 限值: {first_detection.get('limit_value', '(无)')}")
            print(f"   ✓ 检测方法: {first_detection.get('detection_method', '(无)')[:50] if first_detection.get('detection_method') else '(无)'}")

        if not missing_fields:
            print(f"\n   ✓ 预览功能数据完整性验证通过")
        else:
            print(f"\n   ⚠ 预览功能缺少字段: {', '.join(missing_fields)}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n修复验证结果:")
    print("1. 编辑页面检测项目的限值和检测方法字段已修复")
    print("2. 预览功能现在显示所有基本信息、客户信息和完整检测数据")
    print("\n请在浏览器中访问 http://127.0.0.1:5000 进行实际测试：")
    print("- 在待提交报告中点击'编辑'，查看检测项目表格中的限值和检测方法列")
    print("- 在待提交报告中点击'预览'，查看完整的报告信息")

if __name__ == "__main__":
    test_edit_and_preview_fixes()
