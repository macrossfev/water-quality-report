from flask import Blueprint, render_template, session, redirect, url_for

pages_bp = Blueprint('pages_bp', __name__)

# ==================== 页面路由 ====================
@pages_bp.route('/login')
def login_page():
    """登录页面"""
    return render_template('login.html')

@pages_bp.route('/')
def index():
    """主页面 - 需要登录"""
    # 检查是否已登录
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('index_v2.html')

@pages_bp.route('/sample-types-manager')
def sample_types_manager():
    """样品类型管理专项页面"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('sample_types_manager.html')

@pages_bp.route('/indicators-manager')
def indicators_manager():
    """检测指标管理专项页面"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('indicators_manager.html')

@pages_bp.route('/report-template-manager')
def report_template_manager():
    """报告模版管理专项页面"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('report_template_manager.html')

@pages_bp.route('/raw-data-manager')
def raw_data_manager():
    """原始数据管理专项页面"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('raw_data_manager.html')

@pages_bp.route('/customers-manager')
def customers_manager():
    """客户管理专项页面"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('customers_manager.html')

@pages_bp.route('/report-templates')
def report_templates_page():
    """报告模版管理页面（新版，使用别名）"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('report_template_manager.html')
