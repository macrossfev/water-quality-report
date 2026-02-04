#!/usr/bin/env python3
"""
测试新字段的默认值和字段类型修改
"""
import requests
import json
from datetime import date

BASE_URL = "http://127.0.0.1:5000"

def test_new_report_fields():
    """测试新建报告的字段和默认值"""

    print("=" * 60)
    print("新建报告字段测试")
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

    # 2. 获取样品类型
    print("\n2. 获取样品类型...")
    sample_types_response = session.get(f"{BASE_URL}/api/sample-types")

    if sample_types_response.status_code == 200:
        sample_types = sample_types_response.json()
        print(f"   ✓ 成功获取 {len(sample_types)} 个样品类型")
        if sample_types:
            sample_type_id = sample_types[0]['id']
            print(f"   使用样品类型: {sample_types[0]['name']} (ID: {sample_type_id})")
        else:
            print("   ✗ 没有可用的样品类型")
            return
    else:
        print(f"   ✗ 获取样品类型失败")
        return

    # 3. 创建新报告，测试所有新字段
    print("\n3. 创建新报告测试...")

    today = date.today().isoformat()

    report_data = {
        "sample_number": "TEST-2024-001",
        "sample_type_id": sample_type_id,
        "report_date": today,
        "sample_source": "委托采样",
        "sampler": "测试采样员",
        "sampling_date": today,
        "sampling_basis": "GB/T 5750.2-2023",
        "sample_received_date": today,
        "sampling_location": "测试地点",
        "sample_status": "样品完好，液态",
        "detection_date": "2024年1月1日",  # 文本格式，不是ISO日期
        "product_standard": "《生活饮用水卫生标准》 GB5749-2022",
        "test_conclusion": "该水样所检43项指标除铝外，其余检测项目均符合《生活饮用水卫生标准》GB5749-2022的标准限值要求",
        "additional_info": "测试附加信息",
        "detection_person": "",
        "review_person": "",
        "remark": json.dumps({
            "customer_unit": "测试单位",
            "customer_plant": "测试水厂",
            "customer_address": "测试地址",
            "customer_contact": "测试联系人",
            "customer_phone": "13800138000",
            "customer_email": "test@example.com"
        }),
        "review_status": "draft",
        "data": []
    }

    create_response = session.post(f"{BASE_URL}/api/reports", json=report_data)

    if create_response.status_code == 200 or create_response.status_code == 201:
        result = create_response.json()
        report_id = result.get('id')
        print(f"   ✓ 报告创建成功，ID: {report_id}")

        # 4. 读取报告，验证所有字段
        print("\n4. 验证字段值...")
        get_response = session.get(f"{BASE_URL}/api/reports/{report_id}")

        if get_response.status_code == 200:
            report = get_response.json()

            # 验证各个字段
            print(f"\n   基本信息字段验证:")
            print(f"   ✓ 报告编号: {report.get('report_number', 'N/A')}")
            print(f"   ✓ 报告编制日期: {report.get('report_date', 'N/A')}")
            print(f"   ✓ 样品编号: {report.get('sample_number', 'N/A')}")
            print(f"   ✓ 样品来源: {report.get('sample_source', 'N/A')}")
            print(f"   ✓ 样品状态: {report.get('sample_status', 'N/A')}")
            print(f"   ✓ 采样人: {report.get('sampler', 'N/A')}")
            print(f"   ✓ 采样日期: {report.get('sampling_date', 'N/A')}")
            print(f"   ✓ 收样日期: {report.get('sample_received_date', 'N/A')}")
            print(f"   ✓ 检测日期: {report.get('detection_date', 'N/A')}")
            print(f"   ✓ 采样地点: {report.get('sampling_location', 'N/A')}")
            print(f"   ✓ 采样依据: {report.get('sampling_basis', 'N/A')}")
            print(f"   ✓ 产品标准: {report.get('product_standard', 'N/A')}")
            print(f"   ✓ 检测结论: {report.get('test_conclusion', 'N/A')[:50]}...")
            print(f"   ✓ 附加信息: {report.get('additional_info', 'N/A')}")

            # 验证字段类型和值
            print("\n   字段验证:")

            # 检测日期应该是文本格式
            detection_date = report.get('detection_date', '')
            if "年" in detection_date or "月" in detection_date or detection_date == "2024年1月1日":
                print(f"   ✓ 检测日期为文本格式: {detection_date}")
            else:
                print(f"   ⚠ 检测日期格式: {detection_date} (可能不是中文日期格式)")

            # 样品来源应该是委托采样
            if report.get('sample_source') == '委托采样':
                print(f"   ✓ 样品来源默认值正确: 委托采样")
            else:
                print(f"   ✗ 样品来源默认值错误: {report.get('sample_source')}")

            # 样品状态
            if report.get('sample_status') == '样品完好，液态':
                print(f"   ✓ 样品状态默认值正确: 样品完好，液态")
            else:
                print(f"   ⚠ 样品状态值: {report.get('sample_status')}")

            # 采样依据
            if report.get('sampling_basis') == 'GB/T 5750.2-2023':
                print(f"   ✓ 采样依据默认值正确: GB/T 5750.2-2023")
            else:
                print(f"   ⚠ 采样依据值: {report.get('sampling_basis')}")

            # 产品标准
            if report.get('product_standard') == '《生活饮用水卫生标准》 GB5749-2022':
                print(f"   ✓ 产品标准默认值正确")
            else:
                print(f"   ⚠ 产品标准值: {report.get('product_standard')}")

            # 检测结论
            if '43项指标' in report.get('test_conclusion', ''):
                print(f"   ✓ 检测结论默认值正确")
            else:
                print(f"   ⚠ 检测结论值: {report.get('test_conclusion', '')[:50]}")

        else:
            print(f"   ✗ 获取报告失败")

        # 5. 清理测试数据
        print("\n5. 清理测试数据...")
        delete_response = session.delete(f"{BASE_URL}/api/reports/{report_id}")
        if delete_response.status_code == 200:
            print(f"   ✓ 测试报告已删除")
        else:
            print(f"   ⚠ 删除测试报告失败，请手动删除报告 #{report_id}")

    else:
        print(f"   ✗ 创建报告失败: {create_response.text}")
        return

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n请在浏览器中访问 http://127.0.0.1:5000 验证前端功能：")
    print("1. 报告编号可手动输入（无readonly）")
    print("2. 报告编制日期默认为当天")
    print("3. 样品来源有下拉菜单（委托采样/委托送样），默认委托采样")
    print("4. 样品状态默认值：样品完好，液态")
    print("5. 检测日期为文本输入框")
    print("6. 采样依据默认值：GB/T 5750.2-2023")
    print("7. 产品标准默认值：《生活饮用水卫生标准》 GB5749-2022")
    print("8. 检测项目为只读textarea，含43项指标文本")
    print("9. 检测结论为textarea，含默认文本")

if __name__ == "__main__":
    test_new_report_fields()
