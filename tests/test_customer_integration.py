#!/usr/bin/env python3
"""
测试客户信息引入功能
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def test_customer_integration():
    """测试客户信息集成功能"""

    print("=" * 60)
    print("客户信息引入功能测试")
    print("=" * 60)

    # 创建会话以保持cookies
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

    headers = {}

    # 2. 获取客户列表
    print("\n2. 获取客户列表...")
    customers_response = session.get(f"{BASE_URL}/api/customers", headers=headers)

    if customers_response.status_code == 200:
        customers = customers_response.json()
        print(f"   ✓ 成功获取 {len(customers)} 条客户记录")

        if customers:
            # 显示第一条客户信息
            first_customer = customers[0]
            print(f"\n   示例客户信息:")
            print(f"   - ID: {first_customer.get('id')}")
            print(f"   - 被检单位: {first_customer.get('inspected_unit')}")
            print(f"   - 被检水厂: {first_customer.get('water_plant')}")
            print(f"   - 地址: {first_customer.get('unit_address')}")
            print(f"   - 联系人: {first_customer.get('contact_person')}")
            print(f"   - 电话: {first_customer.get('contact_phone')}")
            print(f"   - 邮箱: {first_customer.get('email')}")

            # 获取所有不重复的被检单位
            units = list(set([c.get('inspected_unit') for c in customers if c.get('inspected_unit')]))
            print(f"\n   ✓ 发现 {len(units)} 个不重复的被检单位")
            for unit in units:
                plants = [c.get('water_plant') for c in customers if c.get('inspected_unit') == unit]
                print(f"     - {unit}: {len(plants)} 个水厂")
        else:
            print("   ⚠ 客户列表为空，需要先添加客户数据")
            return
    else:
        print(f"   ✗ 获取客户列表失败: {customers_response.text}")
        return

    # 3. 获取样品类型列表
    print("\n3. 获取样品类型列表...")
    sample_types_response = session.get(f"{BASE_URL}/api/sample-types", headers=headers)

    if sample_types_response.status_code == 200:
        sample_types = sample_types_response.json()
        print(f"   ✓ 成功获取 {len(sample_types)} 个样品类型")

        if sample_types:
            first_sample_type = sample_types[0]
            sample_type_id = first_sample_type.get('id')
            sample_type_name = first_sample_type.get('name')
            print(f"   - 测试样品类型: {sample_type_name} (ID: {sample_type_id})")
        else:
            print("   ⚠ 样品类型列表为空")
            return
    else:
        print(f"   ✗ 获取样品类型失败: {sample_types_response.text}")
        return

    # 4. 获取检测指标
    print(f"\n4. 获取样品类型 {sample_type_name} 的检测指标...")
    indicators_response = session.get(
        f"{BASE_URL}/api/template-indicators?sample_type_id={sample_type_id}",
        headers=headers
    )

    if indicators_response.status_code == 200:
        indicators = indicators_response.json()
        print(f"   ✓ 成功获取 {len(indicators)} 个检测指标")
    else:
        print(f"   ✗ 获取检测指标失败: {indicators_response.text}")
        return

    # 5. 创建带客户信息的检测报告
    print("\n5. 创建带客户信息的检测报告...")

    # 使用第一个客户的信息
    test_customer = customers[0]
    test_sample_number = f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 构建报告数据（包含客户信息）
    customer_info = {
        "customer_unit": test_customer.get('inspected_unit', ''),
        "customer_plant": test_customer.get('water_plant', ''),
        "customer_address": test_customer.get('unit_address', ''),
        "customer_contact": test_customer.get('contact_person', ''),
        "customer_phone": test_customer.get('contact_phone', ''),
        "customer_email": test_customer.get('email', '')
    }

    report_data = {
        "sample_number": test_sample_number,
        "sample_type_id": sample_type_id,
        "detection_date": datetime.now().strftime('%Y-%m-%d'),
        "detection_person": "",
        "review_person": "",
        "remark": json.dumps(customer_info, ensure_ascii=False),
        "review_status": "draft",
        "data": [
            {
                "indicator_id": ind.get('indicator_id'),
                "measured_value": "测试值",
                "remark": "",
                "sort_order": idx
            }
            for idx, ind in enumerate(indicators[:3])  # 只使用前3个指标
        ]
    }

    print(f"   - 样品编号: {test_sample_number}")
    print(f"   - 样品类型: {sample_type_name}")
    print(f"   - 被检单位: {customer_info['customer_unit']}")
    print(f"   - 被检水厂: {customer_info['customer_plant']}")
    print(f"   - 检测项目数: {len(report_data['data'])}")

    create_response = session.post(
        f"{BASE_URL}/api/reports",
        headers=headers,
        json=report_data
    )

    if create_response.status_code == 201:
        created_report = create_response.json()
        report_id = created_report.get('id')
        print(f"   ✓ 报告创建成功 (ID: {report_id})")
    else:
        print(f"   ✗ 报告创建失败: {create_response.text}")
        return

    # 6. 验证报告中的客户信息
    print(f"\n6. 验证报告 {report_id} 中的客户信息...")
    get_response = session.get(f"{BASE_URL}/api/reports/{report_id}", headers=headers)

    if get_response.status_code == 200:
        report = get_response.json()
        print(f"   ✓ 成功获取报告详情")

        # 解析备注中的客户信息
        remark = report.get('remark', '{}')
        try:
            saved_customer_info = json.loads(remark)
            print(f"\n   保存的客户信息:")
            print(f"   - 被检单位: {saved_customer_info.get('customer_unit')}")
            print(f"   - 被检水厂: {saved_customer_info.get('customer_plant')}")
            print(f"   - 地址: {saved_customer_info.get('customer_address')}")
            print(f"   - 联系人: {saved_customer_info.get('customer_contact')}")
            print(f"   - 电话: {saved_customer_info.get('customer_phone')}")
            print(f"   - 邮箱: {saved_customer_info.get('customer_email')}")

            # 验证数据一致性
            if saved_customer_info == customer_info:
                print(f"\n   ✓ 客户信息保存正确")
            else:
                print(f"\n   ✗ 客户信息不一致")
        except json.JSONDecodeError:
            print(f"   ✗ 无法解析备注中的客户信息")
    else:
        print(f"   ✗ 获取报告详情失败: {get_response.text}")
        return

    # 7. 清理测试数据
    print(f"\n7. 清理测试数据...")
    delete_response = session.delete(f"{BASE_URL}/api/reports/{report_id}", headers=headers)

    if delete_response.status_code == 200:
        print(f"   ✓ 测试报告已删除")
    else:
        print(f"   ⚠ 删除测试报告失败: {delete_response.text}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_customer_integration()
