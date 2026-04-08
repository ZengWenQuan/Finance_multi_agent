"""
新闻爬虫工具模块
提供新闻搜索和爬取功能
"""

import logging
from typing import List, Dict
from mcp.server.fastmcp import FastMCP
from ..data_source_interface import FinancialDataSource

logger = logging.getLogger(__name__)

def register_news_crawler_tools(app: FastMCP, data_source: FinancialDataSource):
    """
    注册新闻爬虫工具
    
    Args:
        app: FastMCP应用实例
        data_source: 数据源实例
    """
    
    @app.tool()
    def crawl_news(query: str, top_k: int = 10) -> str:
        """
        [1. 核心定义]
        爬取全网最新新闻资讯，并调用本地 AI 模型进行【情感评分和风险标记】。

        [2. 适用场景与触发词]
        当你需要以下信息时必须调用此工具：
        - 查询公司的最新新闻、动态、舆论、公告。
        - 分析某只股票面临的市场风险、重大利空/利好。
        - 对特定行业的政策或大事件进行新闻报道搜索。

        [3. 排他约束 (防混淆)]
        ⚠️ 注意：这是系统内【唯一】能够获取新闻文本语义并提供风险评分机制的工具。如果用户的提问不是查数字表单，而是看重“发生了什么事”、“有何风险”、“新闻分析”，必须优先使用本工具。
        """
        try:
            logger.info(f"开始爬取新闻，查询词: {query}, 数量: {top_k}")
            result = data_source.crawl_news(query, top_k)
            logger.info(f"新闻爬取完成，返回结果长度: {len(result)}")
            return result
        except Exception as e:
            logger.error(f"爬取新闻时出错: {e}")
            return f"爬取新闻时出错: {str(e)}"
    
    