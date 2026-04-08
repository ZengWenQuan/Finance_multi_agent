import operator
from typing import TypedDict, Sequence, Dict, Any, Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


def merge_dicts(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, d2 values overwrite d1."""
    if not d1: d1 = {}
    if not d2: d2 = {}
    return {**d1, **d2}


# --- 旧版 TypedDict 定义 (已注释) ---
# class AgentState(TypedDict):
#     messages: Annotated[Sequence[BaseMessage], operator.add]
#     data: Annotated[Dict[str, Any], merge_dicts]
#     metadata: Annotated[Dict[str, Any], merge_dicts]


# --- 新版 Pydantic 定义 (正式标准) ---
class AgentState(BaseModel):
    """
    金融分析智能体系统的状态模型。
    使用 Pydantic 提供运行时校验和更清晰的字段说明。
    """
    messages: Annotated[Sequence[BaseMessage], operator.add] = Field(
        default_factory=list,
        description="系统中所有智能体产生的消息历史记录"
    )
    
    data: Annotated[Dict[str, Any], merge_dicts] = Field(
        default_factory=dict,
        description="用于存储金融分析过程中产生的结构化数据、指标和中间结论"
    )
    
    metadata: Annotated[Dict[str, Any], merge_dicts] = Field(
        default_factory=dict,
        description="存储运行时元数据，如 Agent 耗时、执行戳等"
    )

    class Config:
        arbitrary_types_allowed = True
