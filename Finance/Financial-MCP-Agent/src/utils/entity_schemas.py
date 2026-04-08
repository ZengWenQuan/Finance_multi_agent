from pydantic import BaseModel, Field
from typing import List, Optional

class StockEntity(BaseModel):
    """
    金融分析任务中的股票实体提取模型。
    用于 vLLM 的 Guided Decoding 或 LangChain 的 with_structured_output。
    """
    stock_name: Optional[str] = Field(None, description="公司名称或简称，如 '嘉友国际'")
    stock_code: Optional[str] = Field(None, description="6位纯数字股票代码，如 '603871'；如果无法提取，返回 '-1'")
    market_prefix: Optional[str] = Field(None, description="市场前缀，'sh' 表示上海/科创板，'sz' 表示深圳/创业板")
    full_code: Optional[str] = Field(None, description="标准化后的完整代码，必须是前缀在前的格式，如 'sh.603871'、'sz.000001'、'sh.688981'；不要输出 '603871.sh' 或 '688981.sz'；如果无法提取，返回 '-1'")
    analysis_intent: List[str] = Field(
        default_factory=list, 
        description="解析出的分析维度，可选值：fundamental (基本面), technical (技术面), value (估值), news (新闻)"
    )
    is_financial_query: bool = Field(
        ..., 
        description="判断用户输入是否真正包含股票分析请求。如果只是闲聊，设为 false"
    )
    thought: str = Field(
        ..., 
        description="模型在提取信息时的内部思考，简要说明提取逻辑"
    )
