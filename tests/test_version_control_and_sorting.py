"""
测试样品类型版本控制和排序功能

测试内容：
1. 版本控制：创建、更新、并发冲突检测
2. 排序优化：间隔序号（0, 10, 20, 30...）
3. 并发场景：模拟多用户同时编辑

作者：System Test
日期：2026-02-07
"""

import requests
import json
import time

BASE_URL = 'http://localhost:5000'

def login(username='admin', password='admin123'):
    """登录获取会话"""
    session = requests.Session()
    response = session.post(f'{BASE_URL}/api/auth/login',
                          headers={'Content-Type': 'application/json'},
                          json={'username': username, 'password': password})
    if response.status_code == 200:
        print(f"✓ 用户 {username} 登录成功")
        return session
    else:
        print(f"✗ 用户 {username} 登录失败: {response.text}")
        return None

def test_version_on_create(session):
    """测试1：创建样品类型时版本号初始化"""
    print("\n" + "=" * 60)
    print("测试1: 创建样品类型时版本号初始化")
    print("=" * 60)

    # 获取一些检测项目用于关联
    response = session.get(f'{BASE_URL}/api/indicators')
    indicators = response.json()
    indicator_ids = [ind['id'] for ind in indicators[:5]]

    # 创建样品类型
    data = {
        'name': f'版本测试样品_{int(time.time())}',
        'code': f'VT{int(time.time())}',
        'description': '版本控制测试',
        'remark': '测试版本号初始化',
        'indicator_ids': indicator_ids
    }

    response = session.post(
        f'{BASE_URL}/api/sample-types',
        headers={'Content-Type': 'application/json'},
        json=data
    )

    if response.status_code == 201:
        result = response.json()
        sample_type_id = result['id']
        print(f"✓ 样品类型创建成功，ID: {sample_type_id}")

        # 获取详情检查版本号
        response = session.get(f'{BASE_URL}/api/sample-types/{sample_type_id}')
        sample_type = response.json()

        if 'version' in sample_type and sample_type['version'] == 1:
            print(f"✓ 版本号初始化正确: version = {sample_type['version']}")
        else:
            print(f"✗ 版本号初始化失败: {sample_type.get('version', 'None')}")
            return None

        return sample_type_id
    else:
        print(f"✗ 样品类型创建失败: {response.text}")
        return None

def test_version_on_update(session, sample_type_id):
    """测试2：更新样品类型时版本号递增"""
    print("\n" + "=" * 60)
    print("测试2: 更新样品类型时版本号递增")
    print("=" * 60)

    # 获取当前数据
    response = session.get(f'{BASE_URL}/api/sample-types/{sample_type_id}')
    sample_type = response.json()
    current_version = sample_type['version']
    print(f"当前版本号: {current_version}")

    # 更新样品类型
    data = {
        'name': sample_type['name'],
        'code': sample_type['code'],
        'description': '更新后的描述',
        'remark': sample_type.get('remark', ''),
        'indicator_ids': sample_type['indicator_ids'],
        'version': current_version  # 传递当前版本号
    }

    response = session.put(
        f'{BASE_URL}/api/sample-types/{sample_type_id}',
        headers={'Content-Type': 'application/json'},
        json=data
    )

    if response.status_code == 200:
        result = response.json()
        new_version = result.get('version')
        print(f"✓ 样品类型更新成功")
        print(f"新版本号: {new_version}")

        if new_version == current_version + 1:
            print(f"✓ 版本号递增正确: {current_version} -> {new_version}")
            return True
        else:
            print(f"✗ 版本号递增错误: 期望 {current_version + 1}，实际 {new_version}")
            return False
    else:
        print(f"✗ 更新失败: {response.text}")
        return False

def test_concurrent_conflict(session1, session2, sample_type_id):
    """测试3：并发编辑冲突检测"""
    print("\n" + "=" * 60)
    print("测试3: 并发编辑冲突检测")
    print("=" * 60)

    # 用户1获取数据
    response1 = session1.get(f'{BASE_URL}/api/sample-types/{sample_type_id}')
    data1 = response1.json()
    version1 = data1['version']
    print(f"用户1获取数据，版本号: {version1}")

    # 用户2也获取数据
    response2 = session2.get(f'{BASE_URL}/api/sample-types/{sample_type_id}')
    data2 = response2.json()
    version2 = data2['version']
    print(f"用户2获取数据，版本号: {version2}")

    # 用户1先保存
    update_data1 = {
        'name': data1['name'],
        'code': data1['code'],
        'description': '用户1的修改',
        'remark': data1.get('remark', ''),
        'indicator_ids': data1['indicator_ids'],
        'version': version1
    }

    response = session1.put(
        f'{BASE_URL}/api/sample-types/{sample_type_id}',
        headers={'Content-Type': 'application/json'},
        json=update_data1
    )

    if response.status_code == 200:
        result1 = response.json()
        print(f"✓ 用户1保存成功，新版本号: {result1.get('version')}")
    else:
        print(f"✗ 用户1保存失败: {response.text}")
        return False

    # 用户2尝试保存（使用旧版本号）
    update_data2 = {
        'name': data2['name'],
        'code': data2['code'],
        'description': '用户2的修改',
        'remark': data2.get('remark', ''),
        'indicator_ids': data2['indicator_ids'],
        'version': version2  # 使用旧版本号
    }

    response = session2.put(
        f'{BASE_URL}/api/sample-types/{sample_type_id}',
        headers={'Content-Type': 'application/json'},
        json=update_data2
    )

    if response.status_code == 409:
        error = response.json()
        print(f"✓ 用户2保存被拒绝（版本冲突）")
        print(f"✓ 冲突检测正常，错误信息: {error.get('error')}")
        return True
    elif response.status_code == 200:
        print(f"✗ 用户2保存成功（应该被拒绝）- 版本控制失败！")
        return False
    else:
        print(f"✗ 意外的响应状态: {response.status_code}")
        return False

def test_sort_order_intervals(session, sample_type_id):
    """测试4：检测项目排序使用间隔序号"""
    print("\n" + "=" * 60)
    print("测试4: 检测项目排序使用间隔序号")
    print("=" * 60)

    # 获取样品类型的检测项目
    response = session.get(f'{BASE_URL}/api/sample-types/{sample_type_id}/indicators')

    if response.status_code != 200:
        print(f"✗ 获取检测项目失败: {response.text}")
        return False

    result = response.json()
    indicators = result.get('indicators', [])

    if not indicators:
        print("⚠ 该样品类型没有关联检测项目，跳过测试")
        return True

    print(f"检测项目数量: {len(indicators)}")

    # 检查排序序号是否使用间隔值
    all_interval = True
    for idx, ind in enumerate(indicators):
        sort_order = ind.get('sort_order', 0)
        expected_order = idx * 10

        if sort_order == expected_order:
            print(f"  [{idx+1}] {ind['name']}: sort_order = {sort_order} ✓")
        else:
            print(f"  [{idx+1}] {ind['name']}: sort_order = {sort_order} (期望 {expected_order}) ✗")
            all_interval = False

    if all_interval:
        print(f"✓ 所有检测项目都使用间隔序号（10的倍数）")
        return True
    else:
        print(f"✗ 部分检测项目未使用间隔序号")
        return False

def test_update_preserves_sort_order(session):
    """测试5：更新样品类型时保持排序顺序"""
    print("\n" + "=" * 60)
    print("测试5: 更新样品类型时保持排序顺序")
    print("=" * 60)

    # 获取检测项目
    response = session.get(f'{BASE_URL}/api/indicators')
    indicators = response.json()

    # 创建一个测试样品类型，指定特定顺序的检测项目
    indicator_ids = [ind['id'] for ind in indicators[:6]]

    # 反转顺序以测试自定义排序
    custom_order = indicator_ids[::-1]

    data = {
        'name': f'排序测试_{int(time.time())}',
        'code': f'ST{int(time.time())}',
        'description': '排序保持测试',
        'remark': '',
        'indicator_ids': custom_order
    }

    response = session.post(
        f'{BASE_URL}/api/sample-types',
        headers={'Content-Type': 'application/json'},
        json=data
    )

    if response.status_code != 201:
        print(f"✗ 创建样品类型失败: {response.text}")
        return False

    sample_type_id = response.json()['id']
    print(f"✓ 创建样品类型成功，ID: {sample_type_id}")

    # 获取并验证排序
    response = session.get(f'{BASE_URL}/api/sample-types/{sample_type_id}/indicators')
    result = response.json()
    saved_indicators = result.get('indicators', [])
    saved_order = [ind['id'] for ind in saved_indicators]

    print(f"原始顺序: {custom_order}")
    print(f"保存顺序: {saved_order}")

    if saved_order == custom_order:
        print("✓ 排序顺序保持正确")

        # 清理测试数据
        session.delete(f'{BASE_URL}/api/sample-types/{sample_type_id}')
        return True
    else:
        print("✗ 排序顺序改变")
        session.delete(f'{BASE_URL}/api/sample-types/{sample_type_id}')
        return False

def cleanup_test_data(session, sample_type_id):
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("清理测试数据")
    print("=" * 60)

    response = session.delete(f'{BASE_URL}/api/sample-types/{sample_type_id}')
    if response.status_code == 200:
        print(f"✓ 测试数据已清理，样品类型ID: {sample_type_id}")
    else:
        print(f"⚠ 清理测试数据失败: {response.text}")

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("样品类型版本控制和排序功能测试套件")
    print("=" * 60)
    print(f"测试服务器: {BASE_URL}")
    print()

    # 登录两个会话（模拟两个用户）
    session1 = login('admin', 'admin123')
    session2 = login('admin', 'admin123')

    if not session1 or not session2:
        print("\n✗ 登录失败，测试终止")
        return

    results = {
        'passed': 0,
        'failed': 0,
        'total': 0
    }

    try:
        # 测试1：创建时版本号初始化
        sample_type_id = test_version_on_create(session1)
        results['total'] += 1
        if sample_type_id:
            results['passed'] += 1
        else:
            results['failed'] += 1
            print("\n✗ 测试1失败，后续测试将跳过")
            return

        # 测试2：更新时版本号递增
        results['total'] += 1
        if test_version_on_update(session1, sample_type_id):
            results['passed'] += 1
        else:
            results['failed'] += 1

        # 测试3：并发冲突检测
        results['total'] += 1
        if test_concurrent_conflict(session1, session2, sample_type_id):
            results['passed'] += 1
        else:
            results['failed'] += 1

        # 测试4：排序间隔序号
        results['total'] += 1
        if test_sort_order_intervals(session1, sample_type_id):
            results['passed'] += 1
        else:
            results['failed'] += 1

        # 测试5：排序顺序保持
        results['total'] += 1
        if test_update_preserves_sort_order(session1):
            results['passed'] += 1
        else:
            results['failed'] += 1

        # 清理测试数据
        cleanup_test_data(session1, sample_type_id)

    except Exception as e:
        print(f"\n✗ 测试过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()

    # 打印测试结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']} ✓")
    print(f"失败: {results['failed']} ✗")
    print(f"通过率: {results['passed']/results['total']*100 if results['total'] > 0 else 0:.1f}%")
    print("=" * 60)

    if results['failed'] == 0:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠ {results['failed']} 个测试失败")

if __name__ == '__main__':
    main()
