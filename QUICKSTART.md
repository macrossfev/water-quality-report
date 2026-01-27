# 水质检测报告系统 - 快速开始指南

## 系统简介
水质检测报告系统V2是一个用于管理水质检测样品、指标和生成检测报告的Web应用系统。

## 最新更新 (2026-01-27)
- ✅ 新增样品类型备注功能
- ✅ 新增检测指标限值和检测方法
- ✅ 新增分组筛选和搜索功能
- ✅ 新增专项管理页面（样品类型、检测指标）
- ✅ 支持自定义分组管理

详细更新说明请查看: [SYSTEM_UPDATE_SUMMARY.md](SYSTEM_UPDATE_SUMMARY.md)

## 系统要求
- Python 3.8+
- 依赖包: Flask, openpyxl, python-docx, pandas 等

## 快速开始

### 方法1: 使用启动脚本（推荐）

```bash
cd /home/macrossfev/water-quality-report
./start.sh
```

### 方法2: 手动启动

1. **安装依赖**（首次运行）:
```bash
pip3 install -r requirements.txt
```

2. **运行数据库迁移**（如果是从旧版本升级）:
```bash
python3 migrate_database.py
```

3. **启动应用**:
```bash
python3 app_v2.py
```

4. **访问系统**:
- 打开浏览器访问: http://localhost:5000
- 默认管理员账号: `admin`
- 默认密码: `admin123`

## 主要功能

### 1. 样品类型管理
- 路径: 主页 → 样品类型管理 → 进入管理
- 功能: 管理样品类型、代码和备注信息
- 支持: 搜索、分页、导入导出Excel

### 2. 检测指标管理
- 路径: 主页 → 检测指标管理 → 进入管理
- 功能: 管理检测指标、限值、检测方法和分组
- 支持: 分组筛选、搜索、分页、导入导出Excel

### 3. 模板配置
- 路径: 主页 → 模板管理标签页
- 功能: 配置不同样品类型需要检测的指标
- 支持: 导入导出模板JSON

### 4. 报告填写
- 路径: 主页 → 报告填写标签页
- 功能: 创建新的检测报告
- 支持: 批量导入Excel

### 5. 报告查询
- 路径: 主页 → 报告查询标签页
- 功能: 查询和管理已创建的报告
- 支持: 导出Excel、Word格式

### 6. 数据管理
- 路径: 主页 → 数据管理标签页（仅管理员）
- 功能: 数据备份、恢复、操作日志查看

## 常见问题

### Q1: 如何添加新的样品类型？
A: 主页 → 样品类型管理 → 进入管理 → 点击"添加样品类型"按钮

### Q2: 如何设置检测指标的限值？
A: 主页 → 检测指标管理 → 进入管理 → 编辑相应指标 → 填写"限值"字段

### Q3: 如何添加自定义分组？
A: 主页 → 检测指标管理 → 进入管理 → 点击"管理分组" → 添加分组

### Q4: 系统分组可以删除吗？
A: 不可以。"理化指标"、"微生物指标"、"重金属指标"为系统分组，不可删除。

### Q5: 如何搜索样品或指标？
A: 在专项管理页面顶部的搜索框中输入关键词，支持按名称或备注搜索。

### Q6: 数据库在哪里？
A: `database/water_quality_v2.db`

### Q7: 如何备份数据？
A: 登录后，进入"数据管理"标签页，点击"创建备份"按钮。

## 目录结构

```
water-quality-report/
├── app_v2.py                      # 主应用程序
├── models_v2.py                   # 数据库模型
├── migrate_database.py            # 数据库迁移脚本
├── auth.py                        # 用户认证模块
├── start.sh                       # 启动脚本
├── requirements.txt               # Python依赖
├── README.md                      # 项目说明
├── QUICKSTART.md                  # 本文档
├── SYSTEM_UPDATE_SUMMARY.md       # 系统更新说明
├── database/                      # 数据库目录
│   └── water_quality_v2.db
├── templates/                     # HTML模板
│   ├── index_v2.html             # 主页面
│   ├── login.html                # 登录页面
│   ├── sample_types_manager.html # 样品类型管理
│   └── indicators_manager.html   # 检测指标管理
├── static/                        # 静态资源
│   ├── js/
│   └── css/
├── exports/                       # 导出文件目录
├── backups/                       # 备份文件目录
└── sample/                        # 示例数据
    └── 报告模版.xlsx
```

## 开发者信息

### 技术栈
- 后端: Flask 3.0.0 + SQLite
- 前端: Bootstrap 5.3.0 + Vanilla JavaScript
- 文档生成: openpyxl, python-docx

### API端点
详细的API文档请参考 `SYSTEM_UPDATE_SUMMARY.md` 文档中的"技术说明"部分。

## 注意事项

1. **首次使用**: 如果是从旧版本升级，请先运行 `migrate_database.py` 进行数据库迁移
2. **浏览器**: 推荐使用Chrome、Firefox或Edge浏览器
3. **数据安全**: 定期备份数据库文件
4. **密码安全**: 首次登录后请修改默认密码

## 获取帮助

如有问题或建议，请查看:
- 系统更新说明: `SYSTEM_UPDATE_SUMMARY.md`
- 升级计划: `UPGRADE_PLAN.md`（如果存在）

## 更新历史

- **2026-01-27**: V2版本更新
  - 新增样品类型备注功能
  - 新增检测指标限值和检测方法
  - 新增专项管理页面
  - 优化搜索和分页功能

- 更早版本请查看git历史记录

---

**祝您使用愉快！**
