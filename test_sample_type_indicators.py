"""
测试样品类型和检测项目关联功能
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

def login(username='admin', password='admin123'):
    """登录获取会话"""
    session = requests.Session()
    response = session.post(f'{BASE_URL}/login', data={
        'username': username,
        'password': password
    })
    if response.status_code == 200:
        print("✓ 登录成功")
        return session
    else:
        print("✗ 登录失败")
        return None

def test_create_sample_type_with_indicators(session):
    """测试创建样品类型并关联检测项目"""
    print("\n=== 测试1: 创建样品类型并关联检测项目 ===")

    # 首先获取所有检测项目
    response = session.get(f'{BASE_URL}/api/indicators')
    if response.status_code != 200:
        print("✗ 获取检测项目失败")
        return None

    indicators = response.json()
    print(f"找到 {len(indicators)} 个检测项目")

    # 选择前3个检测项目
    indicator_ids = [ind['id'] for ind in indicators[:3]]
    print(f"选择的检测项目ID: {indicator_ids}")

    # 创建样品类型
    data = {
        'name': '测试样品类型',
        'code': 'TEST001',
        'description': '这是一个测试样品类型',
        'remark': '用于功能测试',
        'indicator_ids': indicator_ids
    }

    response = session.post(
        f'{BASE_URL}/api/sample-types',
        json=data,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 201:
        result = response.json()
        sample_type_id = result['id']
        print(f"✓ 样品类型创建成功，ID: {sample_type_id}")
        return sample_type_id
    else:
        print(f"✗ 创建失败: {response.text}")
        return None

def test_get_sample_type_with_indicators(session, sample_type_id):
    """测试获取样品类型及其关联的检测项目"""
    print("\n=== 测试2: 获取样品类型详情 ===")

    response = session.get(f'{BASE_URL}/api/sample-types/{sample_type_id}')

    if response.status_code == 200:
        result = response.json()
        print(f"✓ 样品类型名称: {result['name']}")
        print(f"✓ 样品类型代码: {result['code']}")
        print(f"✓ 关联的检测项目数量: {len(result.get('indicator_ids', []))}")
        print(f"✓ 检测项目ID列表: {result.get('indicator_ids', [])}")
        return True
    else:
        print(f"✗ 获取失败: {response.text}")
        return False

def test_update_sample_type_indicators(session, sample_type_id):
    """测试更新样品类型的检测项目关联"""
    print("\n=== 测试3: 更新样品类型的检测项目关联 ===")

    # 获取所有检测项目
    response = session.get(f'{BASE_URL}/api/indicators')
    indicators = response.json()

    # 选择后5个检测项目
    indicator_ids = [ind['id'] for ind in indicators[-5:]]
    print(f"更新为检测项目ID: {indicator_ids}")

    data = {
        'name': '测试样品类型（已更新）',
        'code': 'TEST001',
        'description': '这是一个测试样品类型（已更新）',
        'remark': '用于功能测试',
        'indicator_ids': indicator_ids
    }

    response = session.put(
        f'{BASE_URL}/api/sample-types/{sample_type_id}',
        json=data,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        print("✓ 样品类型更新成功")

        # 再次获取验证
        response = session.get(f'{BASE_URL}/api/sample-types/{sample_type_id}')
        result = response.json()
        print(f"✓ 更新后的检测项目数量: {len(result.get('indicator_ids', []))}")
        print(f"✓ 更新后的检测项目ID列表: {result.get('indicator_ids', [])}")
        return True
    else:
        print(f"✗ 更新失败: {response.text}")
        return False

def test_get_template_indicators(session, sample_type_id):
    """测试通过template-indicators API获取样品类型的检测项目"""
    print("\n=== 测试4: 获取样品类型的检测项目列表 ===")

    response = session.get(f'{BASE_URL}/api/template-indicators?sample_type_id={sample_type_id}')

    if response.status_code == 200:
        result = response.json()
        print(f"✓ 获取到 {len(result)} 个检测项目")
        for item in result[:3]:  # 只显示前3个
            print(f"  - {item.get('indicator_name', 'N/A')} ({item.get('group_name', 'N/A')})")
        return True
    else:
        print(f"✗ 获取失败: {response.text}")
        return False

def test_delete_sample_type(session, sample_type_id):
    """测试删除样品类型"""
    print("\n=== 测试5: 删除测试样品类型 ===")

    response = session.delete(f'{BASE_URL}/api/sample-types/{sample_type_id}')

    if response.status_code == 200:
        print("✓ 样品类型删除成功")
        return True
    else:
        print(f"✗ 删除失败: {response.text}")
        return False

def main():
    """主测试函数"""
    print("="*60)
    print("样品类型和检测项目关联功能测试")
    print("="*60)

    # 登录
    session = login()
    if not session:
        print("\n测试失败：无法登录")
        return

    # 测试创建
    sample_type_id = test_create_sample_type_with_indicators(session)
    if not sample_type_id:
        print("\n测试失败：无法创建样品类型")
        return

    # 测试获取
    if not test_get_sample_type_with_indicators(session, sample_type_id):
        print("\n警告：获取样品类型详情失败")

    # 测试更新
    if not test_update_sample_type_indicators(session, sample_type_id):
        print("\n警告：更新样品类型失败")

    # 测试通过template-indicators获取
    if not test_get_template_indicators(session, sample_type_id):
        print("\n警告：获取检测项目列表失败")

    # 清理：删除测试数据
    test_delete_sample_type(session, sample_type_id)

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == '__main__':
    main()
