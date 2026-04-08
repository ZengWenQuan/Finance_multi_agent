from src.services.query_processing import build_initial_state, extract_stock_info, normalize_stock_code


def test_extract_stock_info_handles_byd_sample():
    company_name, stock_code = extract_stock_info("帮我看看比亚迪这只股票怎么样")
    assert company_name == "比亚迪"
    assert stock_code is None


def test_extract_stock_info_handles_report_style_query():
    company_name, stock_code = extract_stock_info("帮我分析下江西铜业的报告")
    assert company_name == "江西铜业"
    assert stock_code is None


def test_normalize_stock_code_variants():
    assert normalize_stock_code("sz.002594") == "002594"
    assert normalize_stock_code("sh600519") == "600519"
    assert normalize_stock_code("002594") == "002594"


def test_build_initial_state_formats_a_share_prefix():
    state = build_initial_state("分析比亚迪", "比亚迪", "002594")
    assert state.data["company_name"] == "比亚迪"
    assert state.data["stock_code"] == "sz.002594"
