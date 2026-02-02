# 日期格式化说明

## 格式化函数
在所有HTML文件的<script>标签开始处添加：

```javascript
// 日期格式化：YYYY-MM-DD → YYYY年MM月DD日
function formatDateCN(dateStr) {
    if (!dateStr) return '';
    const match = dateStr.match(/(\d{4})-(\d{2})-(\d{2})/);
    if (match) return `${match[1]}年${match[2]}月${match[3]}日`;
    return dateStr;
}
```

## 使用位置
在显示日期的地方使用 formatDateCN()：
- 报告列表：${formatDateCN(report.sampling_date)}
- 原始数据：${formatDateCN(record.sampling_date)}
- 模板详情：${formatDateCN(template.created_at)}

## 注意
输入框（type="date"）保持原格式不变
