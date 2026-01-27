#!/bin/bash

echo "================================================"
echo "   水质检测报告系统 V2"
echo "================================================"
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python版本: $python_version"

# 检查数据库
if [ ! -f "database/water_quality_v2.db" ]; then
    echo "⚠ 未找到数据库，正在初始化..."
    python3 models_v2.py
    echo "✓ 数据库初始化完成"
else
    echo "✓ 数据库已存在"
fi

echo ""
echo "正在启动系统..."
echo "访问地址: http://localhost:5000"
echo "默认账号: admin / admin123"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "================================================"
echo ""

# 启动应用
python3 app_v2.py
