"""
指数相关工具，用于MCP服务器
包含获取指数成分股的工具
"""
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP
from src.data_source_interface import FinancialDataSource
from src.tools.base import call_index_constituent_tool

logger = logging.getLogger(__name__)


def register_index_tools(app: FastMCP, active_data_source: FinancialDataSource):
    """
    向MCP应用注册指数相关工具

    参数:
        app: FastMCP应用实例
        active_data_source: 活跃的金融数据源
    """

    @app.tool()
    def get_stock_industry(code: Optional[str] = None, date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定股票或全市场股票的【行业分类】数据。

        [2. 适用场景与触发词]
        当询问某只股票属于什么行业，或者想获取某个行业下的所有股票时调用：
        - 行业归属、申万行业/中信行业分类。
        - 某板块或概念包含哪些股票。

        [3. 排他约束 (防混淆)]
        - ⚠️ 若用户询问“某公司属于什么行业”，请优先使用此工具，不要使用 get_stock_basic_info。
        - 如果只查单只股票的基础档案（如公司全称、上市日期），建议使用 get_stock_basic_info。
        """
        log_msg = f"Tool 'get_stock_industry' called for code={code or 'all'}, date={date or 'latest'}"
        logger.info(log_msg)
        try:
            # 如果需要，可以添加日期验证
            df = active_data_source.get_stock_industry(code=code, date=date)
            logger.info(
                f"Successfully retrieved industry data for {code or 'all'}, {date or 'latest'}.")
            from src.formatting.markdown_formatter import format_df_to_markdown
            return format_df_to_markdown(df)

        except Exception as e:
            logger.exception(
                f"Exception processing get_stock_industry: {e}")
            return f"Error: An unexpected error occurred: {e}"

    @app.tool()
    def get_sz50_stocks(date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定日期的【上证50/深证50】指数成分股名单。

        [2. 适用场景与触发词]
        - 查询上证50、深证50包含哪些股票。
        - 某指数成分股调整、权重股。
        
        [3. 排他约束]
        - ⚠️ 严禁使用此工具查询指数的历史点位或走势（请使用 get_historical_k_data，并将代码改为对应指数代码如 sh.000001）。
        - 严禁查询具体股票的历史行情走势。
        """
        return call_index_constituent_tool(
            "get_sz50_stocks",
            active_data_source.get_sz50_stocks,
            "深证50",
            date
        )

    @app.tool()
    def get_hs300_stocks(date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定日期的【沪深300】指数成分股名单。

        [2. 适用场景与触发词]
        - 沪深300指数包含哪些股票。
        - 沪深300权重股、成分股调整。
        
        [3. 排他约束]
        - ⚠️ 严禁使用此工具查询指数的历史点位或走势（请使用 get_historical_k_data，并将代码改为对应指数代码如 sh.000300）。
        - 严禁查询具体股票的历史行情走势。
        """
        return call_index_constituent_tool(
            "get_hs300_stocks",
            active_data_source.get_hs300_stocks,
            "沪深300",
            date
        )

    @app.tool()
    def get_zz500_stocks(date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定日期的【中证500】指数成分股名单。

        [2. 适用场景与触发词]
        - 中证500指数包含哪些股票。
        - 中小盘优质股名录、中证500权重。
        
        [3. 排他约束]
        - ⚠️ 严禁使用此工具查询指数的历史点位或走势（请使用 get_historical_k_data，并将代码改为对应指数代码如 sh.000905）。
        - 严禁查询具体股票的历史行情走势。
        """
        return call_index_constituent_tool(
            "get_zz500_stocks",
            active_data_source.get_zz500_stocks,
            "中证500",
            date
        )
