"""
股票市场数据工具，用于MCP服务器
"""
import logging
from typing import List, Optional, Callable, Any

from mcp.server.fastmcp import FastMCP
from src.data_source_interface import FinancialDataSource, NoDataFoundError, LoginError, DataSourceError
from src.formatting.markdown_formatter import format_df_to_markdown

logger = logging.getLogger(__name__)


def safe_data_fetch(
    func_name: str,
    data_source_func: Callable,
    *args,
    **kwargs
) -> str:
    """
    安全的数据获取函数，统一处理所有异常和错误情况
    
    参数:
        func_name: 函数名称，用于日志记录
        data_source_func: 数据源函数
        *args: 传递给数据源函数的参数
        **kwargs: 传递给数据源函数的关键字参数
        
    返回:
        Markdown格式的数据表格或错误消息
    """
    try:
        # 调用数据源函数
        df = data_source_func(*args, **kwargs)
        
        # 格式化结果
        logger.info(f"Successfully retrieved data for {func_name}, formatting to Markdown.")
        return format_df_to_markdown(df)
        
    except NoDataFoundError as e:
        logger.warning(f"NoDataFoundError for {func_name}: {e}")
        return f"Error: {e}"
    except LoginError as e:
        logger.error(f"LoginError for {func_name}: {e}")
        return f"Error: Could not connect to data source. {e}"
    except DataSourceError as e:
        logger.error(f"DataSourceError for {func_name}: {e}")
        return f"Error: An error occurred while fetching data. {e}"
    except ValueError as e:
        logger.warning(f"ValueError processing request for {func_name}: {e}")
        return f"Error: Invalid input parameter. {e}"
    except Exception as e:
        logger.exception(f"Unexpected Exception processing {func_name}: {e}")
        return f"Error: An unexpected error occurred: {e}"


def register_stock_market_tools(app: FastMCP, active_data_source: FinancialDataSource):
    """
    向MCP应用注册股票市场数据工具

    参数:
        app: FastMCP应用实例
        active_data_source: 活跃的金融数据源
    """

    @app.tool()
    def get_historical_k_data(
        code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjust_flag: str = "3",
        fields: Optional[List[str]] = None,
    ) -> str:
        """
        [1. 核心定义]
        获取中国A股股票的历史K线（OHLCV）走势和估值数据。

        [2. 适用场景与触发词]
        当你需要以下数据时必须调用此工具：
        - 历史股价（开盘价、收盘价、最高价、最低价）、成交量、成交额（Turnover Amount）。
        - 股票或指数的【涨跌幅】、收盘价百分比变化、当日涨幅。
        - 股票的历史估值（市盈率PE、市净率PB）。
        - 分析【行情走势】、【K线形态】、价格历史记录。
        - ⚠️ 获取【指数】（如沪深300 sh.000300、上证指数 sh.000001）的走势点位。

        [3. 排他约束 (防混淆)]
        ⚠️ 严禁使用此工具查询以下内容：
        - 查询当前日历或最新交易日（请使用 get_latest_trading_date）。
        - 查询公司的基本档案和所属行业（请使用 get_stock_basic_info）。
        - 查询杜邦分析或净资产收益率（请使用 get_dupont_data 或 get_profit_data）。

        [4. 参数防错]
        - code: Baostock格式的股票代码（必须加前缀，如 'sh.600000' 或 'sz.000001'）。
        - start_date 和 end_date: 必须提供，格式为'YYYY-MM-DD'。如果用户未指定，请先确认大致的时间范围或直接使用最近半年。
        - frequency: 数据频率（'d'日线, 'w'周线, 'm'月线 等，默认为'd'）。
        - adjust_flag: 复权标志（'1'前复权, '2'后复权, '3'不复权，默认为'3'）。
        """
        logger.info(
            f"Tool 'get_historical_k_data' called for {code} ({start_date}-{end_date}, freq={frequency}, adj={adjust_flag}, fields={fields})")
        
        # 验证频率和调整标志
        valid_freqs = ['d', 'w', 'm', '5', '15', '30', '60']
        valid_adjusts = ['1', '2', '3']
        if frequency not in valid_freqs:
            logger.warning(f"Invalid frequency requested: {frequency}")
            return f"Error: Invalid frequency '{frequency}'. Valid options are: {valid_freqs}"
        if adjust_flag not in valid_adjusts:
            logger.warning(f"Invalid adjust_flag requested: {adjust_flag}")
            return f"Error: Invalid adjust_flag '{adjust_flag}'. Valid options are: {valid_adjusts}"

        # 使用通用函数处理数据获取
        return safe_data_fetch(
            "get_historical_k_data",
            active_data_source.get_historical_k_data,
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjust_flag=adjust_flag,
            fields=fields,
        )

    @app.tool()
    def get_stock_basic_info(code: str, fields: Optional[List[str]] = None) -> str:
        """
        [1. 核心定义]
        获取中国A股股票的【静态】基本档案信息。

        [2. 适用场景与触发词]
        仅限于查询股票的固有属性，覆盖以下具体字段：
        - 股票名称、公司全称、代码。
        - 所属行业 (Industry) 分类。
        - 上市日期 (IPO Date)、上市信息。
        - 当前交易状态 (tradeStatus，如是否正常交易、是否停牌)。

        [3. 排他约束 (防混淆)]
        ⚠️ 严禁使用此工具查询以下内容，这是最常见的错误：
        - 严禁查询 EPS（每股收益）、ROE（净资产收益率）、利润等【财务盈利数据】（请使用 get_profit_data）。
        - 严禁查询 资产总额、负债率、流动比率等【资产负债数据】（请使用 get_balance_data）。
        - 严禁查询 营收增长、利润增长等【成长数据】（请使用 get_growth_data）。
        - 严禁查询 分红、送股、现金流量（请使用相关财务工具）。
        - 严禁查询 股价涨跌、成交量或换手率（请使用 get_historical_k_data）。
        - 严禁查询 行业分类。如果明确要查询某个公司属于什么行业，请务必使用 get_stock_industry。
        - 严禁用于生成综合分析报告。如果用户要求“分析”、“诊断”或“调研”某只股票，请务必使用 get_stock_analysis。

        [4. 参数防错]
        - code: Baostock格式的股票代码（必须包含前缀，如 'sh.600000'）。
        """
        logger.info(
            f"Tool 'get_stock_basic_info' called for {code} (fields={fields})")
        
        # 使用通用函数处理数据获取
        return safe_data_fetch(
            "get_stock_basic_info",
            active_data_source.get_stock_basic_info,
            code=code,
            fields=fields,
        )

    @app.tool()
    def get_dividend_data(code: str, year: str, year_type: str = "report") -> str:
        """
        [1. 核心定义]
        获取指定股票在特定年份的【分红与派息】送转信息。

        [2. 适用场景与触发词]
        当用户问题包含以下意图时调用：
        - 分红方案、派息情况、每股分红、现金分红。
        - 历年送股、转增股本记录。
        - 除权除息日期、分红预案公告。

        [3. 排他约束 (防混淆)]
        ⚠️ 注意：此工具只查询对股东的现金分派或送股行为。
        - 严禁用来查询公司的净利润额度或利润分配基础（请用 get_profit_data）。
        - 严禁用来查询现金流量表（请用 get_cash_flow_data）。

        [4. 参数防错]
        - code: Baostock格式的股票代码。
        - year: 4位数的年份字符串（如 '2023'）。如果是查询历年，需要多次调用或明确年份。
        - year_type: 默认为 'report'（预案公告年份）。
        """
        logger.info(
            f"Tool 'get_dividend_data' called for {code}, year={year}, year_type={year_type}")
        
        # 基本验证
        if year_type not in ['report', 'operate']:
            logger.warning(f"Invalid year_type requested: {year_type}")
            return f"Error: Invalid year_type '{year_type}'. Valid options are: 'report', 'operate'"
        if not year.isdigit() or len(year) != 4:
            logger.warning(f"Invalid year format requested: {year}")
            return f"Error: Invalid year '{year}'. Please provide a 4-digit year."

        # 使用通用函数处理数据获取
        return safe_data_fetch(
            "get_dividend_data",
            active_data_source.get_dividend_data,
            code=code,
            year=year,
            year_type=year_type,
        )

    @app.tool()
    def get_adjust_factor_data(code: str, start_date: str, end_date: str) -> str:
        """
        [1. 核心定义]
        获取指定股票在选定日期范围内的【复权因子】数据。

        [2. 适用场景与触发词]
        当进行技术分析或严谨的价格回溯，明确需要以下数据时调用：
        - 历史复权乘数。
        - 涨跌幅复权算法因子。
        - 计算前复权/后复权真实股价的底层调整常数。

        [3. 排他约束 (防混淆)]
        ⚠️ 注意：
        - 如果用户想要的是“复权后的历史股价走势”，请直接调用 `get_historical_k_data` 并设置 `adjust_flag` 即可，不要单独调用这个复权因子工具（除非用户明确要求查看“因子”本身）。
        - 严禁混淆“复权因子”和“分红数据”（查询具体分红派息金额请用 `get_dividend_data`）。
        """
        logger.info(
            f"Tool 'get_adjust_factor_data' called for {code} ({start_date} to {end_date})")
        
        # 使用通用函数处理数据获取
        return safe_data_fetch(
            "get_adjust_factor_data",
            active_data_source.get_adjust_factor_data,
            code=code,
            start_date=start_date,
            end_date=end_date,
        )
