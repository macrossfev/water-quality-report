# 已移除功能说明

## 日期：2026-01-27

## 移除的功能：模板配置编辑器

### 原因
根据需求，将检测项目配置功能整合到样品类型管理模块中，不再需要单独的模板配置编辑器。

### 系统流程说明
当前系统采用三步流程完成报告模板的创建：
1. **检测指标管理模块**：完成具体检测指标的编制
2. **样品类型管理模块**：将各不同检测指标选中并汇总在一起
3. **报告模板管理模块**：录入Excel模板，并最终形成报告模板（保留导入Excel功能）

### 保留的功能
- 数据库表（excel_report_templates, template_field_mappings等）仍然保留，因为报告生成功能仍需使用
- ReportGenerator类保留，用于生成报告
- 基础的模板查询API保留（报告生成需要）
- **report_template_manager.html** - 报告模板管理页面（已恢复，保留导入Excel功能）
- **/report-template-manager** 和 **/report-templates** 路由（已恢复）

### 已删除/禁用的内容

#### HTML文件（已移动到backups/removed_template_config/）
- templates/template_config_editor.html - 模板配置编辑器（已删除）

#### 禁用的页面路由（在app_v2.py中注释掉）
- /template-config-editor - 模板配置编辑器页面（已删除）

### 新增功能
- 样品类型管理界面增加了检测项目勾选功能
- 创建/编辑样品类型时可以直接关联检测项目
- 通过template_indicators表管理样品类型和检测项目的关联

### 数据迁移说明
不需要数据迁移。现有的excel_report_templates和template_indicators数据都保留，继续用于报告生成。

### 如需恢复
如需恢复模板管理功能：
1. 从backups/removed_template_config/恢复HTML文件到templates/
2. 取消app_v2.py中相关路由的注释
3. 重启应用
