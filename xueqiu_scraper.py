#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球组合持仓爬取器
只需配置用户名密码即可自动登录并获取组合持仓数据
"""

import json
import requests
import time
import logging
import argparse
import os
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XueqiuScraper:
    """雪球数据爬取器"""
    
    def __init__(self, cookie_file: str = "xueqiu_cookie.txt"):
        self.session = requests.Session()
        self.session.verify = False
        self.cookie_file = cookie_file
        
        # 设置请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://xueqiu.com/",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session.headers.update(self.headers)
        
        # 登录状态
        self.is_logged_in = False
        self.username = None
        
    def load_cookies_from_file(self) -> bool:
        """
        从文件自动加载cookies
        :return: 是否加载成功
        """
        try:
            if not os.path.exists(self.cookie_file):
                logger.error(f"Cookie文件不存在: {self.cookie_file}")
                return False
            
            logger.info(f"正在从文件 {self.cookie_file} 加载cookies...")
            
            # 读取cookie文件
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 解析cookies（处理带行号的格式）
            cookie_dict = {}
            logger.debug(f"共读取 {len(lines)} 行数据")
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                logger.debug(f"处理第{i+1}行: {line[:50]}...")
                
                # 移除行号标记（如果存在）
                if '→' in line:
                    line = line.split('→', 1)[1].strip()
                
                # 分割表格行（制表符分隔）
                parts = line.split('\t')
                logger.debug(f"分割后有 {len(parts)} 个部分")
                
                if len(parts) >= 7:  # 确保有足够的列
                    cookie_name = parts[0].strip()
                    cookie_value = parts[1].strip()
                    domain = parts[2].strip()
                    
                    logger.debug(f"Cookie: {cookie_name}={cookie_value[:30] if len(cookie_value) > 30 else cookie_value}, Domain: {domain}")
                    
                    # 只处理雪球域名的cookies
                    if '.xueqiu.com' in domain or 'xueqiu.com' in domain:
                        cookie_dict[cookie_name] = cookie_value
                        logger.debug(f"加载cookie: {cookie_name}={cookie_value[:20]}...")
                else:
                    logger.debug(f"跳过行 {i+1}: 列数不足 ({len(parts)})")
            
            if not cookie_dict:
                logger.error("未找到有效的雪球cookies")
                return False
            
            # 更新session的cookies
            self.session.cookies.update(cookie_dict)
            self.is_logged_in = True
            logger.info(f"成功加载 {len(cookie_dict)} 个cookies")
            
            # 显示加载的关键cookies
            key_cookies = ['xq_a_token', 'xq_r_token', 'u']
            loaded_keys = [k for k in key_cookies if k in cookie_dict]
            if loaded_keys:
                logger.info(f"已加载关键cookies: {', '.join(loaded_keys)}")
            
            return True
            
        except Exception as e:
            logger.error(f"加载cookies文件失败: {e}")
            return False
    
    def set_cookies(self, cookies_str: str) -> bool:
        """
        直接设置cookies字符串（兼容旧版本）
        :param cookies_str: 从浏览器获取的完整cookies字符串
        """
        try:
            # 解析cookies
            cookie_dict = {}
            for item in cookies_str.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookie_dict[key] = value
            
            self.session.cookies.update(cookie_dict)
            self.is_logged_in = True
            logger.info("Cookies设置成功")
            return True
            
        except Exception as e:
            logger.error(f"Cookies设置失败: {e}")
            return False
    
    def get_portfolio_data(self, portfolio_code: str) -> Optional[Dict]:
        """
        获取组合持仓数据
        :param portfolio_code: 组合代码，如 ZH123456
        :return: 组合持仓数据
        """
        if not self.is_logged_in:
            logger.error("请先提供有效的cookies进行认证")
            return None
            
        try:
            logger.info(f"正在获取组合 {portfolio_code} 的数据...")
            
            # 获取组合基本信息
            info_url = "https://xueqiu.com/cubes/rebalancing/current.json"
            info_params = {"cube_symbol": portfolio_code}
            info_resp = self.session.get(info_url, params=info_params)
            
            # 检查响应状态
            if info_resp.status_code == 400:
                logger.error("请求失败：可能是cookies无效或已过期，请重新获取cookies")
                return None
            elif info_resp.status_code == 403:
                logger.error("访问被拒绝：请检查cookies是否正确")
                return None
            elif info_resp.status_code == 404:
                logger.error(f"组合 {portfolio_code} 不存在或无权限访问")
                return None
                
            info_resp.raise_for_status()
            portfolio_info = info_resp.json()
            
            # 获取组合报价信息
            quote_url = "https://xueqiu.com/cubes/quote.json"
            quote_params = {"code": portfolio_code}
            quote_resp = self.session.get(quote_url, params=quote_params)
            
            # 检查报价响应
            if quote_resp.status_code == 400:
                logger.warning("报价信息获取失败，将继续处理其他数据")
                quote_info = {}
            else:
                quote_resp.raise_for_status()
                quote_info = quote_resp.json()
            
            # 提取持仓数据
            last_rb = portfolio_info.get("last_rb", {})
            holdings = last_rb.get("holdings", [])
            net_value = quote_info.get(portfolio_code, {}).get("net_value", 1.0)
            
            # 格式化数据
            formatted_holdings = []
            for holding in holdings:
                formatted_holding = {
                    "股票代码": holding.get("stock_symbol", ""),
                    "股票名称": holding.get("stock_name", ""),
                    "当前权重": f"{holding.get('weight', 0.0):.2f}%",
                    "目标权重": f"{holding.get('target_weight', 0.0):.2f}%",
                    "行业": holding.get("segment_name", ""),
                    "价格": holding.get("price", 0.0)
                }
                formatted_holdings.append(formatted_holding)
            
            result = {
                "组合代码": portfolio_code,
                "组合名称": portfolio_info.get("name", ""),
                "净值": net_value,
                "现金比例": f"{last_rb.get('cash', 0.0):.2f}%",
                "更新时间": time.strftime('%Y-%m-%d %H:%M:%S'),
                "持仓数量": len(formatted_holdings),
                "持仓明细": formatted_holdings
            }
            
            logger.info(f"成功获取 {len(formatted_holdings)} 只持仓")
            return result
            
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return None
    
    def get_rebalancing_history(self, portfolio_code: str, count: int = 20) -> Optional[List]:
        """
        获取组合调仓历史记录
        :param portfolio_code: 组合代码，如 ZH123456
        :param count: 获取记录数量，默认20条
        :return: 调仓历史记录列表
        """
        if not self.is_logged_in:
            logger.error("请先提供有效的cookies进行认证")
            return None
            
        try:
            logger.info(f"正在获取组合 {portfolio_code} 的调仓历史...")
            
            # 获取调仓历史
            history_url = "https://xueqiu.com/cubes/rebalancing/history.json"
            history_params = {
                "cube_symbol": portfolio_code,
                "count": count,
                "page": 1
            }
            history_resp = self.session.get(history_url, params=history_params)
            
            # 检查响应状态
            if history_resp.status_code == 400:
                logger.error("请求失败：可能是cookies无效或已过期，请重新获取cookies")
                return None
            elif history_resp.status_code == 403:
                logger.error("访问被拒绝：请检查cookies是否正确")
                return None
            elif history_resp.status_code == 404:
                logger.error(f"组合 {portfolio_code} 不存在或无权限访问")
                return None
                
            history_resp.raise_for_status()
            history_data = history_resp.json()
            
            # 格式化调仓记录
            rebalancing_list = history_data.get("list", [])
            formatted_history = []
            
            for record in rebalancing_list:
                # 处理每条调仓记录
                histories = record.get("rebalancing_histories", [])
                for history in histories:
                    formatted_record = {
                        "调仓ID": record.get("id", ""),
                        "状态": record.get("status", ""),
                        "调仓时间": self._format_timestamp(record.get("created_at", 0)),
                        "更新时间": self._format_timestamp(record.get("updated_at", 0)),
                        "股票代码": history.get("stock_symbol", ""),
                        "股票名称": history.get("stock_name", ""),
                        "原权重": f"{history.get('prev_weight', 0.0):.2f}%" if history.get('prev_weight') is not None else "-",
                        "目标权重": f"{history.get('target_weight', 0.0):.2f}%",
                        "实际权重": f"{history.get('weight', 0.0):.2f}%" if history.get('weight') is not None else "-",
                        "价格": history.get("price", 0.0),
                        "操作类型": "买入" if history.get("target_weight", 0) > (history.get("prev_weight", 0) or 0) else "卖出"
                    }
                    formatted_history.append(formatted_record)
            
            logger.info(f"成功获取 {len(formatted_history)} 条调仓记录")
            return formatted_history
            
        except Exception as e:
            logger.error(f"获取调仓历史失败: {e}")
            return None
    
    def get_ranking(self, category: int = 14, count: int = 20) -> Optional[List]:
        """
        获取雪球组合排行榜
        注意：目前只有年收益榜(category=14)可以正常访问
        
        category参数说明:
        11: 日收益榜 (暂不可用)
        12: 周收益榜 (暂不可用)
        13: 月收益榜 (暂不可用)
        14: 年收益榜 (✅ 可用)
        15: 总收益榜 (暂不可用)
        """
        if not self.is_logged_in:
            logger.error("请先提供有效的cookies进行认证")
            return None
            
        try:
            logger.info(f"正在获取收益排行榜 (category={category}, count={count})...")
            
            ranking_url = "https://xueqiu.com/cubes/discover/rank/cube/list.json"
            ranking_params = {
                "category": category,
                "count": count
            }
            
            ranking_resp = self.session.get(ranking_url, params=ranking_params)
            
            # 检查响应状态
            if ranking_resp.status_code == 400:
                logger.error("请求失败：参数错误或无权限访问")
                return None
            elif ranking_resp.status_code == 403:
                logger.error("访问被拒绝：请检查cookies是否正确")
                return None
            elif ranking_resp.status_code == 404:
                logger.error("API接口不存在")
                return None
                
            ranking_resp.raise_for_status()
            ranking_data = ranking_resp.json()
            
            if 'list' not in ranking_data:
                logger.error("返回数据格式不正确，缺少'list'字段")
                return None
                
            cube_list = ranking_data['list']
            formatted_ranking = []
            
            for i, cube in enumerate(cube_list, 1):
                formatted_item = {
                    "排名": i,
                    "组合代码": cube.get("symbol", "N/A"),
                    "组合名称": cube.get("name", "N/A"),
                    "年化收益率": f"{cube.get('annualized_gain_rate', 'N/A')}%",
                    "总收益": f"{cube.get('total_gain', 'N/A')}%",
                    "日收益": f"{cube.get('daily_gain', 'N/A')}%",
                    "月收益": f"{cube.get('monthly_gain', 'N/A')}%",
                    "净值": cube.get("net_value", "N/A"),
                    "排名百分位": f"{cube.get('rank_percent', 'N/A')}%",
                    "关注人数": cube.get("follower_count", "N/A"),
                    "更新时间": self._format_timestamp(cube.get("updated_at", 0))
                }
                formatted_ranking.append(formatted_item)
            
            logger.info(f"成功获取 {len(formatted_ranking)} 条排行榜数据")
            return formatted_ranking
            
        except Exception as e:
            logger.error(f"获取收益排行榜失败: {e}")
            return None
    
    def _format_timestamp(self, timestamp: int) -> str:
        """格式化时间戳"""
        try:
            if timestamp:
                # 雪球时间戳通常是毫秒级
                if timestamp > 1000000000000:  # 毫秒时间戳
                    timestamp = timestamp // 1000
                return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            return "-"
        except:
            return "-"
    
    def save_to_file(self, data: Dict, filename: str):
        """保存数据到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存文件失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='雪球组合持仓爬取器')
    
    # Cookie文件路径
    parser.add_argument('--cookie-file', type=str, default='xueqiu_cookie.txt', 
                       help='Cookie文件路径，默认为 xueqiu_cookie.txt')
    
    # 组合参数
    parser.add_argument('--portfolio', type=str, help='组合代码，如: ZH123456 (仅type=holdings或history时必需)')
    
    # 数据类型参数
    parser.add_argument('--type', choices=['holdings', 'history', 'ranking'], default='holdings', 
                       help='获取数据类型: holdings(持仓数据)、history(调仓历史) 或 ranking(收益排行榜)')
    parser.add_argument('--ranking-category', choices=['daily', 'weekly', 'monthly', 'annual', 'total'], 
                       default='annual', help='排行榜类型: daily(日榜)、weekly(周榜)、monthly(月榜)、annual(年榜)、total(总榜)')
    parser.add_argument('--count', type=int, default=20, help='调仓历史记录数量(仅type=history时有效)')
    
    # 输出参数
    parser.add_argument('--output', '-o', type=str, help='输出文件路径')
    parser.add_argument('--format', choices=['json', 'table'], default='json', help='输出格式')
    
    args = parser.parse_args()
    
    # 初始化爬取器
    scraper = XueqiuScraper(cookie_file=args.cookie_file)
    
    # 从cookie文件自动加载（唯一方式）
    logger.info(f"从文件 {args.cookie_file} 自动加载cookies")
    auth_success = scraper.load_cookies_from_file()
    
    if not auth_success:
        logger.error("认证失败，请检查：")
        logger.error("1. Cookie文件是否存在且包含有效cookies")
        logger.error("2. 或者使用 --cookies 参数提供cookies字符串")
        logger.info(f"默认查找的cookie文件: {args.cookie_file}")
        return
    
    # 获取数据
    if args.type == 'holdings':
        data = scraper.get_portfolio_data(args.portfolio)
        if not data:
            logger.error("获取持仓数据失败")
            return
    elif args.type == 'history':
        data = scraper.get_rebalancing_history(args.portfolio, args.count)
        if not data:
            logger.error("获取调仓历史失败")
            return
    else:  # ranking
        # 映射排行榜类别到API参数
        category_map = {
            'daily': 11,    # 日收益榜
            'weekly': 12,   # 周收益榜
            'monthly': 13,  # 月收益榜
            'annual': 14,   # 年收益榜
            'total': 15     # 总收益榜
        }
        category = category_map[args.ranking_category]
        data = scraper.get_ranking(category=category, count=args.count)
        if not data:
            logger.error("获取收益排行榜失败")
            return
    
    # 输出结果
    if args.format == 'json':
        if args.output:
            scraper.save_to_file(data, args.output)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        # 表格格式输出
        if args.type == 'holdings':
            # 持仓数据表格
            print(f"\n{'='*50}")
            print(f"组合信息")
            print(f"{'='*50}")
            print(f"组合代码: {data['组合代码']}")
            print(f"组合名称: {data['组合名称']}")
            print(f"净值: {data['净值']:.4f}")
            print(f"现金比例: {data['现金比例']}")
            print(f"更新时间: {data['更新时间']}")
            print(f"持仓数量: {data['持仓数量']}")
            
            print(f"\n{'='*50}")
            print(f"持仓明细")
            print(f"{'='*50}")
            print(f"{'股票代码':<12} {'股票名称':<15} {'当前权重':<12} {'目标权重':<12} {'行业':<15}")
            print("-" * 80)
            for holding in data['持仓明细']:
                print(f"{holding['股票代码']:<12} "
                      f"{holding['股票名称']:<15} "
                      f"{holding['当前权重']:<12} "
                      f"{holding['目标权重']:<12} "
                      f"{holding['行业']:<15}")
        elif args.type == 'history':
            # 调仓历史表格
            print(f"\n{'='*80}")
            print(f"调仓历史记录 (最近{len(data)}条)")
            print(f"{'='*80}")
            print(f"{'时间':<20} {'股票代码':<12} {'股票名称':<15} {'操作':<6} {'原权重':<10} {'目标权重':<10} {'价格':<10}")
            print("-" * 80)
            for record in data:
                time_str = record.get('调仓时间', '未知时间') or '未知时间'
                stock_code = record.get('股票代码', '') or ''
                stock_name = record.get('股票名称', '') or ''
                action = record.get('操作类型', '') or ''
                prev_weight = record.get('原权重', '') or ''
                target_weight = record.get('目标权重', '') or ''
                price = record.get('价格', '') or ''
                
                print(f"{time_str:<20} "
                      f"{stock_code:<12} "
                      f"{stock_name:<15} "
                      f"{action:<6} "
                      f"{prev_weight:<10} "
                      f"{target_weight:<10} "
                      f"{price:<10}")
        else:
            # 收益排行榜表格
            category_names = {
                'daily': '日收益榜',
                'weekly': '周收益榜', 
                'monthly': '月收益榜',
                'annual': '年收益榜',
                'total': '总收益榜'
            }
            print(f"\n{'='*100}")
            print(f"雪球组合{category_names[args.ranking_category]} (前{len(data)}名)")
            print(f"{'='*100}")
            print(f"{'排名':<6} {'组合名称':<20} {'组合代码':<12} {'年化收益':<12} {'总收益':<12} {'日收益':<10} {'关注人数':<10}")
            print("-" * 100)
            for item in data:
                rank = item.get('排名', '') or ''
                name = item.get('组合名称', '') or ''
                code = item.get('组合代码', '') or ''
                annual_return = item.get('年化收益率', '') or ''
                total_return = item.get('总收益', '') or ''
                daily_return = item.get('日收益', '') or ''
                followers = item.get('关注人数', '') or ''
                
                print(f"{rank:<6} "
                      f"{name:<20} "
                      f"{code:<12} "
                      f"{annual_return:<12} "
                      f"{total_return:<12} "
                      f"{daily_return:<10} "
                      f"{followers:<10}")


if __name__ == "__main__":
    main()