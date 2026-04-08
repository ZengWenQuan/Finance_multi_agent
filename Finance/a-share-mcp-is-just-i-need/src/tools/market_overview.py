"""
市场概览工具，用于MCP服务器
包含获取交易日和所有股票数据的工具
"""
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP
from src.data_source_interface import FinancialDataSource, NoDataFoundError, LoginError, DataSourceError
from src.formatting.markdown_formatter import format_df_to_markdown

logger = logging.getLogger(__name__)


def safe_market_data_fetch(
    func_name: str,
    data_source_func,
    data_type: str,
    **kwargs
) -> str:
    """
    安全的市场数据获取函数，统一处理所有异常和错误情况
    
    参数:
        func_name: 函数名称，用于日志记录
        data_source_func: 数据源函数
        data_type: 数据类型描述
        **kwargs: 传递给数据源函数的关键字参数
        
    返回:
        Markdown格式的数据表格或错误消息
    """
    try:
        # 调用数据源函数
        df = data_source_func(**kwargs)
        logger.info(f"Successfully retrieved {data_type} data.")
        return format_df_to_markdown(df)
        
    except NoDataFoundError as e:
        logger.warning(f"NoDataFoundError: {e}")
        return f"Error: {e}"
    except LoginError as e:
        logger.error(f"LoginError: {e}")
        return f"Error: Could not connect to data source. {e}"
    except DataSourceError as e:
        logger.error(f"DataSourceError: {e}")
        return f"Error: An error occurred while fetching data. {e}"
    except ValueError as e:
        logger.warning(f"ValueError: {e}")
        return f"Error: Invalid input parameter. {e}"
    except Exception as e:
        logger.exception(f"Unexpected Exception processing {func_name}: {e}")
        return f"Error: An unexpected error occurred: {e}"


def register_market_overview_tools(app: FastMCP, active_data_source: FinancialDataSource):
    """
    向MCP应用注册市场概览工具

    参数:
        app: FastMCP应用实例
        active_data_source: 活跃的金融数据源
    """

    @app.tool()
    def get_trade_dates(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取指定范围内的所有【交易日与非交易日】明细及日历状态。

        [2. 适用场景与触发词]
        - 获取特定日期段里具体的每一个交易日和休市日的列表。
        - 某个月有哪些休假不开盘的日子。
        """
        logger.info(
            f"Tool 'get_trade_dates' called for range {start_date or 'default'} to {end_date or 'default'}")
        
        return safe_market_data_fetch(
            "get_trade_dates",
            active_data_source.get_trade_dates,
            "交易日",
            start_date=start_date,
            end_date=end_date
        )

    @app.tool()
    def get_all_stock(date: Optional[str] = None) -> str:
        """
        [1. 核心定义]
        获取全市场所有A股股票的代码、名单和【昨日交易状态】（是否ST、是否退市、是否正常交易）。

        [2. 适用场景与触发词]
        - 获取A股全市场上共有多少只股票。
        - 下载当日全部股票的列表清单。
        
        [3. 排他约束]
        ⚠️ 严禁使用此工具查询单只特定股票的情况，如果用户指定了股票名，绝对不要用它。
        """
        logger.info(
            f"Tool 'get_all_stock' called for date={date or 'default'}")
        
        return safe_market_data_fetch(
            "get_all_stock",
            active_data_source.get_all_stock,
            "所有股票",
            date=date
        )

