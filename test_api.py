#!/usr/bin/env python3
"""
API测试脚本
用于测试水质检测报告系统的后端API
"""
import requests
import json

BASE_URL = "http://localhost:5000"
session = requests.Session()

def print_section(title):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_login():
    """测试用户登录"""
    print_section("测试1: 用户登录")

    # 测试登录
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })

    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✓ 登录成功")
        return True
    else:
        print("✗ 登录失败")
        return False

def test_current_user():
    """测试获取当前用户"""
    print_section("测试2: 获取当前用户信息")

    response = session.get(f"{BASE_URL}/api/auth/current-user")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✓ 获取用户信息成功")
        return True
    else:
        print("✗ 获取用户信息失败")
        return False

def test_indicator_groups():
    """测试检测项目分组"""
    print_section("测试3: 检测项目分组管理")

    # 获取分组列表
    response = session.get(f"{BASE_URL}/api/indicator-groups")
    print(f"获取分组列表 - 状态码: {response.status_code}")
    groups = response.json()
    print(f"现有分组: {json.dumps(groups, ensure_ascii=False, indent=2)}")

    # 创建新分组
    response = session.post(f"{BASE_URL}/api/indicator-groups", json={
        "name": "有机物指标",
        "sort_order": 4
    })
    print(f"\n创建新分组 - 状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    if response.status_code == 201:
        print("✓ 分组管理功能正常")
        return True
    else:
        print("✗ 分组管理功能异常")
        return False

def test_indicators():
    """测试检测指标"""
    print_section("测试4: 检测指标管理")

    # 创建检测指标
    response = session.post(f"{BASE_URL}/api/indicators", json={
        "group_id": 1,  # 理化指标
        "name": "pH值",
        "unit": "无量纲",
        "default_value": "",
        "description": "酸碱度",
        "sort_order": 1
    })
    print(f"创建指标 - 状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    # 获取指标列表
    response = session.get(f"{BASE_URL}/api/indicators")
    print(f"\n获取指标列表 - 状态码: {response.status_code}")
    indicators = response.json()
    print(f"指标数量: {len(indicators)}")
    if indicators:
        print(f"第一个指标: {json.dumps(indicators[0], ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✓ 指标管理功能正常")
        return True
    else:
        print("✗ 指标管理功能异常")
        return False

def test_sample_types():
    """测试样品类型"""
    print_section("测试5: 样品类型管理")

    # 创建样品类型
    response = session.post(f"{BASE_URL}/api/sample-types", json={
        "name": "出厂水",
        "code": "CCW",
        "description": "自来水厂出厂水"
    })
    print(f"创建样品类型 - 状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    # 获取样品类型列表
    response = session.get(f"{BASE_URL}/api/sample-types")
    print(f"\n获取样品类型列表 - 状态码: {response.status_code}")
    sample_types = response.json()
    print(f"样品类型: {json.dumps(sample_types, ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✓ 样品类型管理功能正常")
        return True
    else:
        print("✗ 样品类型管理功能异常")
        return False

def test_companies():
    """测试公司管理"""
    print_section("测试6: 公司管理")

    # 创建公司
    response = session.post(f"{BASE_URL}/api/companies", json={
        "name": "测试水务公司"
    })
    print(f"创建公司 - 状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    # 获取公司列表
    response = session.get(f"{BASE_URL}/api/companies")
    print(f"\n获取公司列表 - 状态码: {response.status_code}")
    companies = response.json()
    print(f"公司: {json.dumps(companies, ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✓ 公司管理功能正常")
        return True
    else:
        print("✗ 公司管理功能异常")
        return False

def test_template_indicators():
    """测试模板检测项目关联"""
    print_section("测试7: 模板检测项目关联")

    # 为样品类型添加检测项目
    response = session.post(f"{BASE_URL}/api/template-indicators", json={
        "sample_type_id": 1,
        "indicator_id": 1,
        "is_required": True,
        "sort_order": 1
    })
    print(f"添加模板检测项 - 状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    # 获取指定样品类型的检测项目
    response = session.get(f"{BASE_URL}/api/template-indicators?sample_type_id=1")
    print(f"\n获取模板检测项 - 状态码: {response.status_code}")
    template_indicators = response.json()
    print(f"模板检测项: {json.dumps(template_indicators, ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✓ 模板检测项目功能正常")
        return True
    else:
        print("✗ 模板检测项目功能异常")
        return False

def test_reports():
    """测试报告管理"""
    print_section("测试8: 报告管理")

    # 创建报告
    response = session.post(f"{BASE_URL}/api/reports", json={
        "sample_number": "20260125001",
        "company_id": 1,
        "sample_type_id": 1,
        "detection_person": "张三",
        "review_person": "李四",
        "detection_date": "2026-01-25",
        "remark": "测试报告",
        "data": [
            {
                "indicator_id": 1,
                "measured_value": "7.2",
                "remark": ""
            }
        ]
    })
    print(f"创建报告 - 状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

    if response.status_code == 201:
        report_id = result.get('id')

        # 获取报告详情
        response = session.get(f"{BASE_URL}/api/reports/{report_id}")
        print(f"\n获取报告详情 - 状态码: {response.status_code}")
        report_detail = response.json()
        print(f"报告详情: {json.dumps(report_detail, ensure_ascii=False, indent=2)}")

        print("✓ 报告管理功能正常")
        return True
    else:
        print("✗ 报告管理功能异常")
        return False

def test_backup():
    """测试备份功能"""
    print_section("测试9: 数据备份")

    # 创建备份
    response = session.post(f"{BASE_URL}/api/backup/create")
    print(f"创建备份 - 状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    # 获取备份列表
    response = session.get(f"{BASE_URL}/api/backup/list")
    print(f"\n获取备份列表 - 状态码: {response.status_code}")
    backups = response.json()
    print(f"备份列表: {json.dumps(backups, ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✓ 备份功能正常")
        return True
    else:
        print("✗ 备份功能异常")
        return False

def test_logs():
    """测试操作日志"""
    print_section("测试10: 操作日志")

    response = session.get(f"{BASE_URL}/api/logs?limit=10")
    print(f"获取操作日志 - 状态码: {response.status_code}")
    logs = response.json()
    print(f"日志数量: {len(logs)}")
    if logs:
        print(f"最近的日志:\n{json.dumps(logs[:3], ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✓ 日志功能正常")
        return True
    else:
        print("✗ 日志功能异常")
        return False

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  水质检测报告系统 API 测试")
    print("="*60)

    results = []

    # 执行测试
    results.append(("用户登录", test_login()))
    results.append(("获取当前用户", test_current_user()))
    results.append(("检测项目分组", test_indicator_groups()))
    results.append(("检测指标管理", test_indicators()))
    results.append(("样品类型管理", test_sample_types()))
    results.append(("公司管理", test_companies()))
    results.append(("模板检测项目", test_template_indicators()))
    results.append(("报告管理", test_reports()))
    results.append(("数据备份", test_backup()))
    results.append(("操作日志", test_logs()))

    # 输出测试结果汇总
    print_section("测试结果汇总")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:.<30} {status}")

    print(f"\n测试通过率: {passed}/{total} ({passed*100//total}%)")

    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")

if __name__ == "__main__":
    try:
        run_all_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print("请确保应用服务器已启动: python3 app_v2.py")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
