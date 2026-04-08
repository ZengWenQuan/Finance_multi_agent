"""
宏观经济数据工具，用于MCP服务器
包含获取利率、货币供应量数据等工具
"""
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP
from src.data_source_interface import FinancialDataSource
from src.tools.base import call_macro_data_tool

logger = logging.getLogger(__name__)


def register_macroeconomic_tools(app: FastMCP, active_data_source: FinancialDataSource):
    """
    向MCP应用注册宏观经济数据工具

    参数:
        app: FastMCP应用实例
        active_data_source: 活跃的金融数据源
    """

    @app.tool()
    def get_deposit_rate_data(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定日期范围内的【存款基准利率】数据（活期、定期）。

        [2. 适用场景与触发词]
        - 存款利率、活期利率、定期存款利息、逆回购利率相关参考。
        """
        return call_macro_data_tool(
            "get_deposit_rate_data",
            active_data_source.get_deposit_rate_data,
            "存款利率",
            start_date, end_date
        )

    @app.tool()
    def get_loan_rate_data(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定日期范围内的【贷款基准利率/LPR】数据。

        [2. 适用场景与触发词]
        - LPR、贷款利率、1年期/5年期贷款利息。
        """
        return call_macro_data_tool(
            "get_loan_rate_data",
            active_data_source.get_loan_rate_data,
            "贷款利率",
            start_date, end_date
        )

    @app.tool()
    def get_required_reserve_ratio_data(start_date: Optional[str] = None, end_date: Optional[str] = None, year_type: str = '0') -> str:
        """
        [1. 核心定义]
        获取指定日期范围内的【存款准备金率】调整数据。

        [2. 适用场景与触发词]
        - 降准、存款准备金率、大型金融机构准备金。
        """
        # 对year_type进行基本验证
        if year_type not in ['0', '1']:
            logger.warning(f"Invalid year_type requested: {year_type}")
            return f"Error: Invalid year_type '{year_type}'. Valid options are '0' (announcement date) or '1' (effective date)."

        return call_macro_data_tool(
            "get_required_reserve_ratio_data",
            active_data_source.get_required_reserve_ratio_data,
            "存款准备金率",
            start_date, end_date,
            year_type=year_type
        )

    @app.tool()
    def get_money_supply_data_month(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定日期范围内的【月度分项货币供应量】数据（M0、M1、M2）。

        [2. 适用场景与触发词]
        - M2增速、M1货币供应量、剪刀差。
        """
        # 如果需要，可以添加对YYYY-MM格式的特定验证
        return call_macro_data_tool(
            "get_money_supply_data_month",
            active_data_source.get_money_supply_data_month,
            "月度货币供应量",
            start_date, end_date
        )

    @app.tool()
    def get_money_supply_data_year(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定年份范围内的【年度总货币供应量及外汇储备】数据。

        [2. 适用场景与触发词]
        - 年度广义货币供应量、外汇储备总额。
        """
        # 如果需要，可以添加对YYYY格式的特定验证
        return call_macro_data_tool(
            "get_money_supply_data_year",
            active_data_source.get_money_supply_data_year,
            "年度货币供应量",
            start_date, end_date
        )

    # @app.tool()
    # def get_shibor_data(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    #     """
    #     获取指定日期范围内的SHIBOR（上海银行间同业拆放利率）数据

    #     参数:
    #         start_date: 可选的开始日期，格式为'YYYY-MM-DD'
    #         end_date: 可选的结束日期，格式为'YYYY-MM-DD'

    #     返回:
    #         包含SHIBOR数据的Markdown表格或错误消息
    #     """
    #     return call_macro_data_tool(
    #         "get_shibor_data",
    #         active_data_source.get_shibor_data,
    #         "SHIBOR",
    #         start_date, end_date
    #     )
