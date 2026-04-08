"""
财务报表相关工具，用于MCP服务器
"""
import logging
from typing import List, Optional

from mcp.server.fastmcp import FastMCP
from src.data_source_interface import FinancialDataSource, NoDataFoundError, LoginError, DataSourceError
from src.tools.base import call_financial_data_tool

logger = logging.getLogger(__name__)


def safe_financial_report_fetch(
    func_name: str,
    data_source_func,
    report_type: str,
    code: str,
    start_date: str = None,
    end_date: str = None,
    year: str = None,
    quarter: int = None
) -> str:
    """
    安全的财务报表数据获取函数，统一处理所有异常和错误情况
    
    参数:
        func_name: 函数名称，用于日志记录
        data_source_func: 数据源函数
        report_type: 报告类型描述
        code: 股票代码
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        year: 年份（可选）
        quarter: 季度（可选）
        
    返回:
        Markdown格式的数据表格或错误消息
    """
    try:
        # 根据参数类型调用不同的数据源函数
        if year and quarter:
            df = data_source_func(code=code, year=year, quarter=quarter)
        elif start_date and end_date:
            df = data_source_func(code=code, start_date=start_date, end_date=end_date)
        else:
            raise ValueError("Invalid parameters provided")
        
        logger.info(f"Successfully retrieved {report_type} data for {code}")
        from src.formatting.markdown_formatter import format_df_to_markdown
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
        logger.exception(f"Exception processing {func_name} for {code}: {e}")
        return f"Error: An unexpected error occurred: {e}"


def register_financial_report_tools(app: FastMCP, active_data_source: FinancialDataSource):
    """
    向MCP应用注册财务报表相关工具

    参数:
        app: FastMCP应用实例
        active_data_source: 活跃的金融数据源
    """

    @app.tool()
    def get_profit_data(code: str, year: str, quarter: int) -> str:
        """
        [1. 核心定义]
        获取指定股票在特定季度的核心【盈利能力】指标。

        [2. 适用场景与触发词]
        当用户询问公司的盈利状况、赚钱效率、或提及以下指标时必须调用：
        - ROE (净资产收益率)。
        - 净利润、扣非净利润。
        - 销售净利率、毛利率、资产收益率。
        - EPS (每股收益)、每股主营业务收入。

        [3. 排他约束 (防混淆)]
        ⚠️ 严禁使用此工具查询以下内容：
        - 查询当前股价、历史K线（请用 get_historical_k_data）。
        - 查询资产总额、负债率（请用 get_balance_data）。
        - 查询营收/利润的"同比增长率"（请用 get_growth_data）。
        - 查询分红方案（请用 get_dividend_data）。

        [4. 参数防错]
        - code: Baostock格式的股票代码。
        - year: 4位数的年份字符串（如 '2023'）。
        - quarter: 季度数字（1, 2, 3, 或 4）。
        """
        return call_financial_data_tool(
            "get_profit_data",
            active_data_source.get_profit_data,
            "盈利能力",
            code, year, quarter
        )

    @app.tool()
    def get_operation_data(code: str, year: str, quarter: int) -> str:
        """
        [1. 核心定义]
        获取指定股票在特定季度的【营运能力】（资产周转效率）指标。

        [2. 适用场景与触发词]
        用于分析公司资产流转效率，包含以下指标：
        - 总资产周转率、应收账款周转率及周转天数。
        - 存货周转率及周转天数。

        [3. 排他约束 (防混淆)]
        - 如果要查利润或ROE，请用 get_profit_data。
        - 如果要查资产负债结构，请用 get_balance_data。
        """
        return call_financial_data_tool(
            "get_operation_data",
            active_data_source.get_operation_data,
            "营运能力",
            code, year, quarter
        )

    @app.tool()
    def get_growth_data(code: str, year: str, quarter: int) -> str:
        """
        [1. 核心定义]
        获取指定股票在特定季度的【成长能力】（同比增长）指标。

        [2. 适用场景与触发词]
        当用户询问公司业绩“增速”或“相较去年表现”时调用：
        - 营业总收入同比增长率 (YOYNI)。
        - 净利润同比增长率。
        - 净资产同比增长率、总资产同比增长率。
        - 扣非净利润同比。

        [3. 排他约束 (防混淆)]
        ⚠️ 严禁使用此工具查询：
        - 当季度绝对的利润数字或ROE（请用 get_profit_data）。
        - 基本资料或行业（请用 get_stock_basic_info）。
        """
        return call_financial_data_tool(
            "get_growth_data",
            active_data_source.get_growth_data,
            "成长能力",
            code, year, quarter
        )

    @app.tool()
    def get_balance_data(code: str, year: str, quarter: int) -> str:
        """
        [1. 核心定义]
        获取指定股票在特定季度的【资产负债表与偿债能力】核心数据。

        [2. 适用场景与触发词]
        当分析公司的财务健康、负债情况或资产规模时调用。特别是：
        - 资产负债率 (Debt Ratio)、流动比率、速动比率。
        - **核心科目**：【资产总额】、【负债总额】、所有者权益。
        - **具体债务**：短期借款、长期负债、应付债券。
        - 现金比率、权益乘数等安全性指标。

        [3. 排他约束 (防混淆)]
        ⚠️ 严禁使用此工具查询：
        - 盈利能力（如净利润、毛利率），请用 get_profit_data。
        - 公司是不是属于某个行业，请用 get_stock_basic_info。
        """
        return call_financial_data_tool(
            "get_balance_data",
            active_data_source.get_balance_data,
            "资产负债表",
            code, year, quarter
        )

    @app.tool()
    def get_cash_flow_data(code: str, year: str, quarter: int) -> str:
        """
        [1. 核心定义]
        获取指定股票在特定季度的【现金流量】数据及质量分析。

        [2. 适用场景与触发词]
        分析公司真实回款能力、现金流状况时调用：
        - 经营性现金流量净额、投资性/筹资性现金流。
        - **核心质量指标**：【现金到账率】、销售商品提供劳务收到的现金。
        - 经营性现金净流量/营业总收入 (CFO/营业收入比率)。

        [3. 排他约束 (防混淆)]
        - 不要把它和“利润表(get_profit_data)”混淆。
        - 不要把它和分红派息混淆（请用 get_dividend_data）。
        """
        return call_financial_data_tool(
            "get_cash_flow_data",
            active_data_source.get_cash_flow_data,
            "现金流量",
            code, year, quarter
        )

    @app.tool()
    def get_dupont_data(code: str, year: str, quarter: int) -> str:
        """
        [1. 核心定义]
        获取指定股票在特定季度的【杜邦分析】数据。

        [2. 适用场景与触发词]
        当用户明确要求进行“杜邦分析”或询问 ROE 核心分解时调用：
        - 归属母公司股东的净利润。
        - 资产回报率 (ROA)、**资产周转率 (Asset Turnover)**、**权益乘数**。
        - 净资产收益率 (ROE) 的拆解。

        [3. 排他约束 (防混淆)]
        - 如果用户单纯问“ROE是多少”，建议使用 get_profit_data。
        - 只有涉及“杜邦分析”明确意图时调用此工具最佳。
        """
        return call_financial_data_tool(
            "get_dupont_data",
            active_data_source.get_dupont_data,
            "杜邦分析",
            code, year, quarter
        )

    @app.tool()
    def get_performance_express_report(code: str, start_date: str, end_date: str) -> str:
        """
        [1. 核心定义]
        获取股票在指定日期范围内的【业绩快报】（未经审计的初步业绩）。

        [2. 适用场景与触发词]
        - 查询业绩快报公布内容、最新一季度的抢先财务概览。
        
        [4. 参数防错]
        - start_date / end_date: 报告发布的日期范围。
        """
        return safe_financial_report_fetch(
            "get_performance_express_report",
            active_data_source.get_performance_express_report,
            "业绩快报",
            code,
            start_date=start_date,
            end_date=end_date
        )

    @app.tool()
    def get_forecast_report(code: str, start_date: str, end_date: str) -> str:
        """
        [1. 核心定义]
        获取股票在指定日期范围内的【业绩预告】公告数据。

        [2. 适用场景与触发词]
        - 业绩预增、预减、扭亏为盈。
        - 公司发布的盈利预测数据段。
        """
        return safe_financial_report_fetch(
            "get_forecast_report",
            active_data_source.get_forecast_report,
            "业绩预告",
            code,
            start_date=start_date,
            end_date=end_date
        )
