#!/usr/bin/env python3
"""
测试编辑报告功能
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def test_edit_report():
    """测试编辑报告功能"""

    print("=" * 60)
    print("编辑报告功能测试")
    print("=" * 60)

    # 创建会话
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

    # 2. 创建一个测试报告
    print("\n2. 创建测试报告...")

    # 获取样品类型
    sample_types = session.get(f"{BASE_URL}/api/sample-types").json()
    if not sample_types:
        print("   ✗ 没有样品类型")
        return

    sample_type_id = sample_types[0]['id']
    sample_type_name = sample_types[0]['name']

    # 获取检测指标
    indicators = session.get(f"{BASE_URL}/api/template-indicators?sample_type_id={sample_type_id}").json()

    # 创建报告
    test_sample_number = f"EDIT-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    report_data = {
        "sample_number": test_sample_number,
        "sample_type_id": sample_type_id,
        "detection_date": datetime.now().strftime('%Y-%m-%d'),
        "detection_person": "",
        "review_person": "",
        "remark": json.dumps({
            "customer_unit": "测试单位",
            "customer_plant": "测试水厂",
            "customer_address": "测试地址123号",
            "customer_contact": "张三",
            "customer_phone": "13800138000",
            "customer_email": "test@test.com"
        }, ensure_ascii=False),
        "review_status": "draft",
        "data": [
            {
                "indicator_id": ind['indicator_id'],
                "measured_value": "原始值",
                "remark": "",
                "sort_order": idx
            }
            for idx, ind in enumerate(indicators[:3])
        ]
    }

    create_response = session.post(f"{BASE_URL}/api/reports", json=report_data)

    if create_response.status_code == 201:
        report = create_response.json()
        report_id = report['id']
        print(f"   ✓ 测试报告创建成功 (ID: {report_id})")
        print(f"     样品编号: {test_sample_number}")
        print(f"     样品类型: {sample_type_name}")
        print(f"     检测项目数: {len(report_data['data'])}")
    else:
        print(f"   ✗ 创建报告失败: {create_response.text}")
        return

    # 3. 获取报告详情（模拟编辑页面加载）
    print(f"\n3. 加载报告 {report_id} 的详情...")
    detail_response = session.get(f"{BASE_URL}/api/reports/{report_id}")

    if detail_response.status_code == 200:
        report_detail = detail_response.json()
        print(f"   ✓ 成功获取报告详情")
        print(f"     样品编号: {report_detail['sample_number']}")
        print(f"     样品类型: {report_detail['sample_type_name']}")
        print(f"     检测数据数量: {len(report_detail['data'])}")

        # 解析客户信息
        customer_info = json.loads(report_detail['remark'])
        print(f"     客户信息:")
        print(f"       - 被检单位: {customer_info['customer_unit']}")
        print(f"       - 被检水厂: {customer_info['customer_plant']}")
        print(f"       - 地址: {customer_info['customer_address']}")
    else:
        print(f"   ✗ 获取报告详情失败: {detail_response.text}")
        return

    # 4. 编辑报告（修改样品编号、客户信息和检测值）
    print(f"\n4. 编辑报告...")

    new_sample_number = f"{test_sample_number}-EDITED"

    # 修改报告数据
    edited_data = {
        "sample_number": new_sample_number,  # 修改样品编号
        "sample_type_id": sample_type_id,
        "detection_date": report_detail['detection_date'],
        "detection_person": "",
        "review_person": "",
        "remark": json.dumps({
            "customer_unit": "编辑后单位",  # 修改客户信息
            "customer_plant": "编辑后水厂",
            "customer_address": "编辑后地址456号",
            "customer_contact": "李四",
            "customer_phone": "13900139000",
            "customer_email": "edited@test.com"
        }, ensure_ascii=False),
        "review_status": "draft",
        "data": [
            {
                "indicator_id": item['indicator_id'],
                "indicator_name": item.get('indicator_name', ''),
                "unit": item.get('unit', ''),
                "measured_value": f"编辑值{idx+1}",  # 修改检测值
                "limit_value": item.get('limit_value', ''),
                "detection_method": item.get('detection_method', ''),
                "remark": "",
                "sort_order": idx
            }
            for idx, item in enumerate(report_detail['data'])
        ]
    }

    print(f"   修改内容:")
    print(f"     - 样品编号: {test_sample_number} → {new_sample_number}")
    print(f"     - 被检单位: 测试单位 → 编辑后单位")
    print(f"     - 检测值: 原始值 → 编辑值1, 编辑值2, ...")

    # 提交编辑
    edit_response = session.put(f"{BASE_URL}/api/reports/{report_id}", json=edited_data)

    if edit_response.status_code == 200:
        print(f"   ✓ 报告编辑成功")
    else:
        print(f"   ✗ 报告编辑失败: {edit_response.text}")
        return

    # 5. 验证编辑结果
    print(f"\n5. 验证编辑结果...")
    verify_response = session.get(f"{BASE_URL}/api/reports/{report_id}")

    if verify_response.status_code == 200:
        verified_report = verify_response.json()
        print(f"   ✓ 成功获取编辑后的报告")

        # 验证样品编号
        if verified_report['sample_number'] == new_sample_number:
            print(f"   ✓ 样品编号已更新: {verified_report['sample_number']}")
        else:
            print(f"   ✗ 样品编号未更新")

        # 验证客户信息
        verified_customer = json.loads(verified_report['remark'])
        if verified_customer['customer_unit'] == '编辑后单位':
            print(f"   ✓ 客户信息已更新:")
            print(f"     - 被检单位: {verified_customer['customer_unit']}")
            print(f"     - 被检水厂: {verified_customer['customer_plant']}")
            print(f"     - 地址: {verified_customer['customer_address']}")
        else:
            print(f"   ✗ 客户信息未更新")

        # 验证检测值
        if verified_report['data'][0]['measured_value'] == '编辑值1':
            print(f"   ✓ 检测值已更新:")
            for idx, item in enumerate(verified_report['data']):
                print(f"     - {item['indicator_name']}: {item['measured_value']}")
        else:
            print(f"   ✗ 检测值未更新")
    else:
        print(f"   ✗ 验证失败: {verify_response.text}")
        return

    # 6. 测试提交审核
    print(f"\n6. 测试提交审核...")
    submit_response = session.post(f"{BASE_URL}/api/reports/{report_id}/submit")

    if submit_response.status_code == 200:
        print(f"   ✓ 报告已提交审核")

        # 验证状态
        status_check = session.get(f"{BASE_URL}/api/reports/{report_id}").json()
        if status_check['review_status'] == 'pending':
            print(f"   ✓ 审核状态已更新为: pending")
        else:
            print(f"   ✗ 审核状态未正确更新")
    else:
        print(f"   ✗ 提交审核失败: {submit_response.text}")

    # 7. 清理测试数据
    print(f"\n7. 清理测试数据...")
    delete_response = session.delete(f"{BASE_URL}/api/reports/{report_id}")

    if delete_response.status_code == 200:
        print(f"   ✓ 测试报告已删除")
    else:
        print(f"   ⚠ 删除测试报告失败: {delete_response.text}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_edit_report()
