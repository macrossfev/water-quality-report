# 水质检测报告系统

一款轻量化的水质检测报告管理Web应用，支持自定义水质指标、检测方法、限值标准，并可生成Excel格式的检测报告。

## 功能特性

- **指标管理**：自定义水质检测指标（如pH值、溶解氧、COD等）
- **检测方法管理**：为每个指标配置多种检测方法和标准代号
- **限值标准管理**：设置不同标准的限值范围（如地表水I-V类标准）
- **报告创建**：快速录入检测数据，自动关联指标、方法和标准
- **历史查询**：查看和管理所有历史报告
- **Excel导出**：一键导出格式化的Excel检测报告

## 技术栈

- **后端**：Python 3.x + Flask
- **数据库**：SQLite
- **前端**：HTML5 + Bootstrap 5 + Vanilla JavaScript
- **Excel处理**：openpyxl

## 安装步骤

### 1. 克隆或下载项目

```bash
cd water-quality-report
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行应用

```bash
python app.py
```

### 4. 访问系统

打开浏览器访问：`http://localhost:5000`

## 使用指南

### 第一步：添加水质指标

1. 进入"指标管理"标签页
2. 输入指标名称（如"pH值"）、单位（如"无量纲"）
3. 点击"添加指标"

### 第二步：配置检测方法

1. 进入"检测方法"标签页
2. 选择对应的指标
3. 输入检测方法名称（如"玻璃电极法"）和标准代号（如"GB/T 6920-1986"）
4. 点击"添加方法"

### 第三步：设置限值标准

1. 进入"限值标准"标签页
2. 选择对应的指标
3. 输入标准名称（如"地表水III类标准"）
4. 设置限值范围：
   - **最小值和最大值**：用于范围型标准（如6.0-9.0）
   - **固定值**：用于固定值标准（如≤5mg/L）
5. 点击"添加标准"

### 第四步：创建检测报告

1. 进入"创建报告"标签页
2. 填写报告基本信息（报告名称、采样地点、日期等）
3. 点击"添加检测项"按钮，为每个检测项：
   - 选择检测指标
   - 选择检测方法（可选）
   - 选择限值标准（可选）
   - 输入检测值
   - 选择是否合格
4. 点击"提交报告"

### 第五步：查看和导出报告

1. 进入"历史报告"标签页
2. 点击报告行查看详细信息
3. 点击"导出Excel"按钮下载报告

## 项目结构

```
water-quality-report/
├── app.py                  # Flask主应用
├── models.py              # 数据库模型和初始化
├── requirements.txt       # Python依赖
├── README.md             # 使用说明
├── database/             # SQLite数据库文件目录
│   └── water_quality.db
├── exports/              # 导出的Excel文件目录
├── templates/            # HTML模板
│   └── index.html
└── static/               # 静态资源
    ├── css/
    └── js/
        └── app.js        # 前端JavaScript
```

## 数据库设计

### indicators（指标表）
- id：主键
- name：指标名称
- unit：单位
- description：描述

### detection_methods（检测方法表）
- id：主键
- indicator_id：关联指标
- method_name：方法名称
- standard_code：标准代号

### limit_standards（限值标准表）
- id：主键
- indicator_id：关联指标
- standard_name：标准名称
- min_value：最小值
- max_value：最大值
- exact_value：固定值

### reports（报告表）
- id：主键
- report_name：报告名称
- sample_location：采样地点
- sample_date：采样日期
- sampler：采样人员

### report_data（报告数据表）
- id：主键
- report_id：关联报告
- indicator_id：关联指标
- detection_method_id：关联检测方法
- measured_value：检测值
- limit_standard_id：关联限值标准
- is_qualified：是否合格

## 常见应用场景

### 示例1：地表水监测

1. 添加指标：pH值、溶解氧、高锰酸盐指数、COD、BOD5、氨氮、总磷、总氮等
2. 添加检测方法：对应的国标方法
3. 添加限值标准：地表水I-V类标准
4. 创建报告并录入检测数据

### 示例2：饮用水检测

1. 添加指标：GB 5749规定的各项指标
2. 配置相应的检测方法
3. 设置《生活饮用水卫生标准》限值
4. 创建报告进行合格判定

## 注意事项

1. 删除指标会级联删除相关的检测方法和限值标准
2. 数据库文件位于 `database/water_quality.db`，注意定期备份
3. 导出的Excel文件保存在 `exports/` 目录
4. 系统默认运行在5000端口，可在 `app.py` 中修改

## 未来扩展

- [ ] 用户权限管理
- [ ] 数据统计和图表展示
- [ ] 批量导入检测数据
- [ ] 报告模板自定义
- [ ] 移动端适配

## 许可证

MIT License

## 技术支持

如有问题或建议，欢迎提交Issue。
