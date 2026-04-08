from __future__ import annotations

import os
import re
import urllib.parse
from datetime import datetime
from typing import Callable

import requests
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from src.utils.analysis_quality import sanitize_company_name
from src.utils.entity_schemas import StockEntity
from src.utils.logging_config import setup_logger
from src.utils.state_definition import AgentState


logger = setup_logger(__name__)
load_dotenv(override=True)

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional dependency fallback
    BeautifulSoup = None


def normalize_stock_code(raw_code: str | None) -> str | None:
    if not raw_code:
        return None

    code = str(raw_code).strip().lower()
    if code == "-1":
        return "-1"
    if len(code) == 6 and code.isdigit():
        return code
    if len(code) == 9 and code[:2] in {"sh", "sz"} and code[2] == "." and code[3:].isdigit():
        return code[3:]
    if len(code) == 8 and code[:2] in {"sh", "sz"} and code[2:].isdigit():
        return code[2:]

    match = re.search(r"(\d{6})", code)
    if match:
        return match.group(1)

    return code


def extract_stock_info(query: str) -> tuple[str | None, str | None]:
    stock_code = None
    company_name = None
    normalized_query = re.sub(r"\s+", " ", query).strip()

    patterns = [
        r"请帮我分析一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]",
        r"分析一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]",
        r"分析\s*([^（(]+?)\s*[（(](\d{5,6})[)）]",
        r"我想了解一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]",
        r"帮我看看\s*([^（(]+?)\s*[（(](\d{5,6})[)）]",
        r"^([^（(]+?)\s*[（(](\d{5,6})[)）]",
    ]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            company_name = match.group(1).strip()
            stock_code = match.group(2)
            return company_name, stock_code

    reverse_patterns = [
        r"分析\s*[（(](\d{5,6})[)）]\s*([^）)]+)",
        r"帮我看看\s*[（(](\d{5,6})[)）]\s*([^）)]+?)(?:\s*这只|\s*这个)?\s*股票",
    ]
    for pattern in reverse_patterns:
        match = re.search(pattern, query)
        if match:
            stock_code = match.group(1)
            company_name = match.group(2).strip()
            return company_name, stock_code

    company_patterns = [
        r"帮我分析下\s*([^0-9（）()\s的报告]+?)(?:\s*的报告|\s*报告|\s|$)",
        r"帮我分析一下\s*([^0-9（）()\s]+?)(?:\s*的报告|\s*报告|\s*的|\s|$)",
        r"分析一下\s*([^0-9（）()\s]+?)(?:\s*的|\s|$)",
        r"给我分析一下\s*([^0-9（）()\s]+?)(?:\s*的|\s|$)",
        r"分析\s*([^0-9（）()\s]+)",
        r"([^0-9（）()\s]+)\s*(?:这只|这个|的)?\s*股票",
        r"了解一下\s*([^0-9（）()\s]+?)(?:\s*的|\s|$)",
        r"([^0-9（）()\s]+?)\s*的\s*(?:财务表现|盈利能力|现金流状况|资产负债情况|技术面|股价走势|技术指标|技术面表现|估值水平|市盈率|市净率|估值|投资风险|风险因素|风险评估|投资价值|股票|基本面情况|基本面|财务状况)",
        r"([^0-9（）()\s]+?)\s*在\s*[^0-9（）()\s]*\s*中(?:\s*的)?",
        r"([^0-9（）()\s]+?)\s*面临",
    ]
    for pattern in company_patterns:
        match = re.search(pattern, normalized_query)
        if match:
            company_name = match.group(1).strip()
            break

    code_patterns = [
        r"\b(\d{5,6})\b",
        r"(\d{5,6})\s*(?:这个|这只)?\s*股票\s*值得买",
        r"(\d{5,6})\s*这个\s*股票\s*最近表现",
    ]
    for pattern in code_patterns:
        match = re.search(pattern, query)
        if match:
            stock_code = match.group(1)
            break

    company_name = sanitize_company_name(company_name)

    return company_name, stock_code


def _extract_from_baidu_text(text_content: str, target_company: str | None) -> tuple[str | None, str | None]:
    """
    从百度搜索页面文本中提取股票信息。
    优先从 "公司名(6位代码)" 配对模式提取，否则用 LLM 兜底。
    """
    # 策略1：精确匹配 "公司名(代码)" 或 "代码 公司名" 配对
    pair_patterns = [
        r"([一-龥A-Za-z0-9·]{2,15})\s*[（(]\s*(\d{6})\s*[)）]",
        r"(\d{6})\s*[-_\s]\s*([一-龥A-Za-z0-9·]{2,15})",
    ]
    for pattern in pair_patterns:
        match = re.search(pattern, text_content[:3000])
        if match:
            name = match.group(1).strip()
            code = match.group(2).strip()
            # 清洗名称中的垃圾词
            for word in ["股票", "百度", "官网", "新浪", "东方财富", "证券", "行情", "查询", "搜索"]:
                name = name.replace(word, "").strip()
            if len(name) >= 2 and code.isdigit() and len(code) == 6:
                return name, code

    # 策略2：用 LLM 从文本中提取
    if target_company:
        try:
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_COMPATIBLE_MODEL"),
                api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY"),
                base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
                temperature=0,
                max_tokens=200,
            )
            prompt = f"""从以下百度搜索结果中提取"{target_company}"对应的A股股票代码和公司全称。

只返回JSON，格式：{{"company_name": "公司名", "stock_code": "6位代码"}}
如果找不到，返回：{{"company_name": null, "stock_code": null}}

百度搜索结果（前2000字）：
{text_content[:2000]}"""
            result = llm.invoke(prompt)
            import json
            # 尝试解析 LLM 返回的 JSON
            content = result.content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            data = json.loads(content)
            name = data.get("company_name")
            code = data.get("stock_code")
            if name and code and len(str(code)) == 6 and str(code).isdigit():
                return str(name).strip(), str(code).strip()
        except Exception as e:
            logger.warning(f"LLM 百度文本提取失败: {e}")

    return None, None


def search_baidu_stock_info(query: str) -> tuple[str | None, str | None]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.baidu.com/",
    }

    session = requests.Session()
    session.headers.update(headers)

    # 从原始查询中提取公司名用于精准搜索
    target_company = None
    name_match = re.search(r"([一-龥A-Za-z]{2,15})", query)
    if name_match:
        target_company = name_match.group(1).strip()
        # 过滤常见动词
        stop_verbs = ["分析", "帮我", "看看", "查询", "搜索", "了解一下", "给我", "想"]
        for verb in stop_verbs:
            if target_company == verb:
                target_company = None
                break

    # 搜索词：精准化，搜"公司名 股票代码 A股"
    search_keyword = f"{target_company or query} 股票代码 A股" if target_company else f"{query} 股票代码 A股"
    encoded_query = urllib.parse.quote(search_keyword)
    search_url = f"https://www.baidu.com/s?wd={encoded_query}&ie=utf-8"

    logger.info(f"百度兜底检索开始，keyword={search_keyword}")

    try:
        try:
            session.get("https://www.baidu.com", timeout=10)
        except Exception as e:
            logger.info(f"百度首页预热失败，继续直接搜索: {e}")

        response = session.get(search_url, timeout=15)
        response.raise_for_status()
        response_text = response.text
        logger.info(f"百度兜底检索响应成功，status={response.status_code}, length={len(response_text)}")

        if "百度安全验证" in response_text or "安全验证" in response_text:
            logger.warning("百度兜底检索触发安全验证，放弃兜底。")
            return None, None

        if BeautifulSoup is not None:
            soup = BeautifulSoup(response_text, "html.parser")
            page_text = soup.get_text(" ", strip=True)
        else:
            logger.warning("bs4 未安装，百度兜底切换为简化文本解析。")
            page_text = re.sub(r"<[^>]+>", " ", response_text)

        found_name, found_code = _extract_from_baidu_text(page_text, target_company)

        logger.info(f"百度兜底检索结果: company_name={found_name}, stock_code={found_code}")
        return found_name, found_code

    except Exception as e:
        logger.warning(f"百度兜底检索失败: {e}")
        return None, None


async def extract_entities_from_query(
    user_query: str,
    debug_printer: Callable[[str], None] | None = None,
) -> tuple[str | None, str | None]:
    company_name = None
    stock_code = None

    extractor_llm = ChatOpenAI(
        model=os.getenv("OPENAI_COMPATIBLE_MODEL"),
        api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY"),
        base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
        temperature=0,
        max_tokens=800,
        extra_body={
            "guided_json": StockEntity.model_json_schema()
        },
    ).with_structured_output(StockEntity)

    try:
        extraction_prompt = f"""分析以下金融查询，提取核心股票实体信息：

用户查询: '{user_query}'

输出要求：
1. `stock_code` 只输出 6 位数字代码，如 `603871`、`000001`、`688981`
2. `market_prefix` 只输出 `sh` 或 `sz`
3. `full_code` 必须输出“前缀在前”的标准格式，如 `sh.603871`、`sz.000001`、`sh.688981`
4. 不要输出 `603871.sh`、`688981.sz`、`sh688981` 这类格式
5. 如果无法提取到股票代码，`stock_code` 和 `full_code` 都返回 `-1`
6. 如果只能提取到公司名，无法确定股票代码，也必须返回 `-1`
"""
        extraction_result = await extractor_llm.ainvoke(extraction_prompt)
        company_name = sanitize_company_name(extraction_result.stock_name)
        stock_code = normalize_stock_code(extraction_result.stock_code or extraction_result.full_code)
        if stock_code == "-1":
            stock_code = None
        logger.info(f"AI 提取结果 - 公司: {company_name}, 代码: {stock_code}")
    except Exception as e:
        logger.error(f"AI 实体提取发生异常: {e}")

    regex_company_name, regex_stock_code = extract_stock_info(user_query)
    regex_company_name = sanitize_company_name(regex_company_name)
    if regex_company_name and (not company_name or len(regex_company_name) < len(company_name)):
        company_name = regex_company_name
    if not stock_code and regex_stock_code:
        stock_code = regex_stock_code

    if not company_name or not stock_code:
        if debug_printer:
            debug_printer("第一轮提取信息不完整，正在使用百度检索兜底...")
        logger.info(
            f"第一轮提取信息不完整，触发百度兜底: company_name={company_name}, stock_code={stock_code}"
        )
        # 传入已知公司名（如有）提高搜索精准度
        baidu_query = company_name or user_query
        baidu_company_name, baidu_stock_code = search_baidu_stock_info(baidu_query)
        if not company_name and baidu_company_name:
            company_name = sanitize_company_name(baidu_company_name)
        if not stock_code and baidu_stock_code:
            stock_code = normalize_stock_code(baidu_stock_code)
        logger.info(f"百度兜底完成: company_name={company_name}, stock_code={stock_code}")
        if debug_printer:
            debug_printer(
                f"百度兜底结果: company_name={company_name or 'None'}, stock_code={stock_code or 'None'}"
            )

    return company_name, stock_code


def build_initial_state(user_query: str, company_name: str | None, stock_code: str | None) -> AgentState:
    current_datetime = datetime.now()
    current_date_cn = current_datetime.strftime("%Y年%m月%d日")
    current_date_en = current_datetime.strftime("%Y-%m-%d")
    current_weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][current_datetime.weekday()]
    current_time = current_datetime.strftime("%H:%M:%S")
    current_time_info = f"{current_date_cn} ({current_date_en}) {current_weekday_cn} {current_time}"

    initial_data = {
        "query": user_query,
        "current_date": current_date_en,
        "current_date_cn": current_date_cn,
        "current_time": current_time,
        "current_weekday_cn": current_weekday_cn,
        "current_time_info": current_time_info,
        "analysis_timestamp": current_datetime.isoformat(),
    }

    if company_name:
        initial_data["company_name"] = company_name

    if stock_code:
        if stock_code.startswith("6"):
            initial_data["stock_code"] = f"sh.{stock_code}"
        elif stock_code.startswith("0") or stock_code.startswith("3"):
            initial_data["stock_code"] = f"sz.{stock_code}"
        else:
            initial_data["stock_code"] = stock_code

    return AgentState(messages=[], data=initial_data, metadata={})
