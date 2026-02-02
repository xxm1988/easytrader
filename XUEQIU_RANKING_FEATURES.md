# 雪球组合数据获取功能说明

## 🎯 当前支持的功能

### 1. 组合持仓数据获取 ✅
```bash
# 获取指定组合的持仓数据
python xueqiu_scraper.py --portfolio ZH3418063 --type holdings --format table
```

### 2. 调仓历史记录获取 ✅
```bash
# 获取组合的调仓历史记录
python xueqiu_scraper.py --portfolio ZH3418063 --type history --count 30 --format table
```

### 3. 收益排行榜获取 ✅
```bash
# 获取年收益排行榜（目前唯一可用的排行榜）
python xueqiu_scraper.py --type ranking --ranking-category annual --count 20 --format table

# 其他排行榜类型（暂不可用）
# python xueqiu_scraper.py --type ranking --ranking-category daily    # 日收益榜
# python xueqiu_scraper.py --type ranking --ranking-category weekly   # 周收益榜  
# python xueqiu_scraper.py --type ranking --ranking-category monthly  # 月收益榜
# python xueqiu_scraper.py --type ranking --ranking-category total    # 总收益榜
```

## 📊 输出格式

### 表格格式 (--format table)
直观的表格展示，适合快速浏览

### JSON格式 (--format json)
结构化的数据格式，适合程序处理和进一步分析

## 💡 使用技巧

### 1. 保存数据到文件
```bash
# 保存为JSON文件
python xueqiu_scraper.py --portfolio ZH3418063 --type holdings --output portfolio_data.json

# 保存排行榜数据
python xueqiu_scraper.py --type ranking --ranking-category annual --output ranking_data.json
```

### 2. 批量获取多个组合
```bash
#!/bin/bash
# Linux/Mac 批量获取脚本
portfolios=("ZH3418063" "ZH123456" "ZH789012")
for portfolio in "${portfolios[@]}"; do
    python xueqiu_scraper.py --portfolio "$portfolio" --type holdings --output "${portfolio}_data.json"
done
```

### 3. Windows批处理版本
```batch
@echo off
set portfolios=ZH3418063 ZH123456 ZH789012
for %%p in (%portfolios%) do (
    python xueqiu_scraper.py --portfolio %%p --type holdings --output %%p_data.json
)
```

## 🔧 高级用法

### 1. 在Python代码中调用
```python
from xueqiu_scraper import XueqiuScraper

# 创建爬虫实例
scraper = XueqiuScraper()

# 加载cookies
if scraper.load_cookies_from_file():
    # 获取持仓数据
    holdings = scraper.get_portfolio_data("ZH3418063")
    
    # 获取调仓历史
    history = scraper.get_rebalancing_history("ZH3418063", count=50)
    
    # 获取排行榜
    ranking = scraper.get_ranking(category=14, count=20)  # 年收益榜
    
    # 处理数据...
    print(f"持仓数量: {len(holdings['持仓明细'])}")
    print(f"调仓记录: {len(history)}条")
    print(f"排行榜: {len(ranking)}个组合")
```

### 2. 数据分析示例
```python
import json
from collections import Counter

# 获取排行榜数据
scraper = XueqiuScraper()
scraper.load_cookies_from_file()
ranking_data = scraper.get_ranking(category=14, count=100)

# 分析行业分布
industry_counter = Counter()
for item in ranking_data:
    # 这里可以根据需要提取更多信息进行分析
    pass

# 计算平均收益率
returns = [float(item['年化收益率'].rstrip('%')) for item in ranking_data if item['年化收益率'] != 'N/A%']
avg_return = sum(returns) / len(returns) if returns else 0
print(f"前100名平均年化收益率: {avg_return:.2f}%")
```

## ⚠️ 注意事项

1. **Cookies有效期**: 雪球cookies通常有效期约1个月，过期后需要重新获取
2. **请求频率**: 建议每次请求间隔10秒以上，避免被限制访问
3. **数据准确性**: 数据来源于雪球网站，仅供参考，不保证实时性
4. **排行榜限制**: 目前只有年收益榜可以正常访问，其他类型暂不可用

## 🆘 常见问题

### Q: 提示"认证失败"怎么办？
A: 检查以下几点：
- 确保`xueqiu_cookie.txt`文件存在且包含有效cookies
- 重新登录雪球网站获取新的cookies
- 检查cookies是否过期

### Q: 获取不到数据怎么办？
A: 
- 检查组合代码是否正确
- 确认该组合是否公开可见
- 查看控制台错误信息

### Q: 表格显示乱码怎么办？
A: 在Windows CMD中运行时可能会出现编码问题，建议：
- 使用PowerShell运行
- 或者使用`--format json`输出JSON格式

## 📈 数据字段说明

### 持仓数据字段
- 组合代码、组合名称
- 净值、现金比例
- 更新时间、持仓数量
- 持仓明细：股票代码、股票名称、当前权重、目标权重、行业

### 调仓历史字段
- 调仓ID、状态
- 调仓时间、更新时间
- 股票代码、股票名称
- 原权重、目标权重、实际权重
- 价格、操作类型

### 收益排行榜字段
- 排名、组合代码、组合名称
- 年化收益率、总收益、日收益、月收益
- 净值、排名百分位、关注人数
- 更新时间