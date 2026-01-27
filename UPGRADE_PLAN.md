# 水质检测报告系统升级方案

## 一、技术架构改造

### 1.1 新增依赖包
```txt
Flask==3.0.0
openpyxl==3.1.2
python-docx==1.1.0        # Word文档生成
reportlab==4.0.7          # PDF生成
flask-login==0.6.3        # 用户登录管理
werkzeug==3.0.1           # 密码加密
pandas==2.1.4             # Excel批量导入
```

### 1.2 新数据库结构设计

#### 用户表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'admin' 或 'reporter'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### 公司表 (companies)
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### 样品类型表 (sample_types)
```sql
CREATE TABLE sample_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- 出厂水、水源水等
    code TEXT NOT NULL UNIQUE,            -- 样品类型缩写
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### 检测项目分组表 (indicator_groups)
```sql
CREATE TABLE indicator_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,            -- 理化指标、微生物指标等
    sort_order INTEGER DEFAULT 0,         -- 排序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### 检测指标表 (indicators) - 改造
```sql
CREATE TABLE indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,                     -- 新增:分组ID
    name TEXT NOT NULL UNIQUE,
    unit TEXT,
    default_value TEXT,                   -- 新增:默认值
    description TEXT,
    sort_order INTEGER DEFAULT 0,         -- 新增:排序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES indicator_groups (id) ON DELETE SET NULL
)
```

#### 模板-检测项目关联表 (template_indicators)
```sql
CREATE TABLE template_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_type_id INTEGER NOT NULL,
    indicator_id INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT 0,        -- 是否必填
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sample_type_id) REFERENCES sample_types (id) ON DELETE CASCADE,
    FOREIGN KEY (indicator_id) REFERENCES indicators (id) ON DELETE CASCADE,
    UNIQUE(sample_type_id, indicator_id)
)
```

#### 报告表 (reports) - 改造
```sql
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_number TEXT NOT NULL UNIQUE,   -- 新增:报告编号
    sample_number TEXT NOT NULL,          -- 新增:样品编号
    company_id INTEGER,                   -- 新增:公司ID
    sample_type_id INTEGER NOT NULL,      -- 新增:样品类型ID
    detection_person TEXT,                -- 新增:检测人
    review_person TEXT,                   -- 新增:审核人
    detection_date DATE,                  -- 新增:检测日期
    remark TEXT,
    created_by INTEGER,                   -- 新增:创建人ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE SET NULL,
    FOREIGN KEY (sample_type_id) REFERENCES sample_types (id),
    FOREIGN KEY (created_by) REFERENCES users (id)
)
```

#### 报告数据表 (report_data) - 改造
```sql
CREATE TABLE report_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    indicator_id INTEGER NOT NULL,
    measured_value TEXT,
    remark TEXT,
    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
    FOREIGN KEY (indicator_id) REFERENCES indicators (id)
)
```

#### 报告模板配置表 (report_templates)
```sql
CREATE TABLE report_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,                    -- 报告表头公司名称
    report_title TEXT,                    -- 报告标题
    footer_text TEXT,                     -- 报告落款
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### 操作日志表 (operation_logs)
```sql
CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    operation_type TEXT NOT NULL,         -- 模板修改、报告填写、导出等
    operation_detail TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
```

## 二、功能模块实现计划

### 2.1 模板管理模块
**后端API:**
- `POST /api/sample-types` - 创建样品类型
- `GET /api/sample-types` - 获取所有样品类型
- `PUT /api/sample-types/<id>` - 更新样品类型
- `DELETE /api/sample-types/<id>` - 删除样品类型
- `POST /api/indicator-groups` - 创建检测项目分组
- `POST /api/template-indicators` - 为模板添加检测项目
- `POST /api/templates/export` - 导出模板JSON
- `POST /api/templates/import` - 导入模板JSON

**前端功能:**
- 样品类型列表展示与CRUD
- 检测项目分组管理
- 拖拽排序功能
- JSON导入导出按钮

### 2.2 权限系统
**后端API:**
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/current-user` - 获取当前用户
- `POST /api/users` - 创建用户(仅管理员)

**前端功能:**
- 登录页面
- Session管理
- 权限控制(管理员/填写人不同菜单)

### 2.3 报告填写模块
**后端API:**
- `GET /api/reports/history` - 获取历史报告(支持搜索)
- `POST /api/reports/validate-number` - 校验样品编号
- `POST /api/reports/batch-import` - 批量导入Excel

**前端功能:**
- 联动下拉框(选择样品类型→自动渲染检测项目)
- 实时校验
- 历史记录查询与复用
- Excel上传与解析

### 2.4 报告导出模块
**后端API:**
- `GET /api/reports/<id>/export/word` - 导出Word
- `GET /api/reports/<id>/export/pdf` - 导出PDF
- `GET /api/reports/<id>/export/excel` - 导出Excel

**库选择:**
- Word: python-docx
- PDF: reportlab
- Excel: openpyxl(已有)

### 2.5 数据备份与日志
**后端API:**
- `POST /api/backup/create` - 创建备份
- `POST /api/backup/restore` - 恢复备份
- `GET /api/logs` - 获取操作日志

**实现方式:**
- 备份:拷贝SQLite数据库文件+JSON文件到backup目录
- 日志:每个关键操作写入operation_logs表

## 三、前端界面改造

### 3.1 新布局结构
```
├── 登录页 (login.html)
└── 主界面 (index.html)
    ├── Tab1: 模板管理 (仅管理员可见)
    ├── Tab2: 报告填写
    ├── Tab3: 报告查询
    └── Tab4: 数据管理 (备份/日志,仅管理员可见)
```

### 3.2 UI优化
- 使用Bootstrap 5的Toast组件显示操作提示
- 表单验证使用原生HTML5 + JavaScript
- 表格使用DataTables插件(可选)
- 模态框展示详情

## 四、数据迁移方案

### 4.1 迁移策略
由于数据库结构变化较大,建议:
1. 保留旧数据库备份
2. 创建新数据库结构
3. 编写迁移脚本将旧数据转换到新结构
4. 旧的indicators/detection_methods/limit_standards表数据转为新的indicators+groups结构

### 4.2 迁移脚本
```python
# migrate.py - 数据迁移脚本
def migrate_old_to_new():
    # 1. 备份旧数据库
    # 2. 创建新表结构
    # 3. 迁移indicators数据(去掉detection_methods和limit_standards)
    # 4. 迁移reports数据(需要补充新字段)
    pass
```

## 五、实施步骤

1. ✅ 分析现有系统架构,评估改造方案
2. 设计新的数据库架构
3. 实现用户权限系统
4. 实现模板管理模块
5. 改造报告填写模块
6. 实现多格式导出
7. 实现备份与日志
8. 重构前端界面
9. 数据迁移与测试
10. 优化与部署

## 六、注意事项

1. **兼容性**: 保留数据迁移入口,不直接删除旧数据
2. **安全性**: 密码使用werkzeug.security加密
3. **性能**: SQLite对于单用户系统足够,后期可迁移到MySQL
4. **备份**: 自动备份机制+手动备份按钮双保险
5. **日志**: 记录关键操作,便于审计和问题排查
