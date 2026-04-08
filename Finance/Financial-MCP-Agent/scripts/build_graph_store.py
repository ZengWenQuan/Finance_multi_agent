"""
清洗 graph_store.json 并注入上证50/深证100成分股知识图谱数据。
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GRAPH_STORE = DATA_DIR / "graph_store.json"

# ============================================================
# 1. 上证50成分股（2026年最新，来源：中证指数/东方财富/99rising）
# ============================================================
SSE50_STOCKS = [
    {"code": "600519", "name": "贵州茅台", "market": "sh", "industry": "白酒", "weight_pct": 10.42},
    {"code": "601318", "name": "中国平安", "market": "sh", "industry": "保险", "weight_pct": 6.95},
    {"code": "601899", "name": "紫金矿业", "market": "sh", "industry": "有色金属", "weight_pct": 6.19},
    {"code": "600036", "name": "招商银行", "market": "sh", "industry": "银行", "weight_pct": 5.59},
    {"code": "600900", "name": "长江电力", "market": "sh", "industry": "电力", "weight_pct": 3.80},
    {"code": "601166", "name": "兴业银行", "market": "sh", "industry": "银行", "weight_pct": 3.66},
    {"code": "601398", "name": "工商银行", "market": "sh", "industry": "银行", "weight_pct": 2.84},
    {"code": "600276", "name": "恒瑞医药", "market": "sh", "industry": "医药", "weight_pct": 2.83},
    {"code": "603259", "name": "药明康德", "market": "sh", "industry": "医药外包", "weight_pct": 2.79},
    {"code": "600030", "name": "中信证券", "market": "sh", "industry": "券商", "weight_pct": 2.69},
    {"code": "688256", "name": "寒武纪", "market": "sh", "industry": "AI芯片", "weight_pct": 2.38},
    {"code": "688041", "name": "海光信息", "market": "sh", "industry": "半导体", "weight_pct": 2.24},
    {"code": "601288", "name": "农业银行", "market": "sh", "industry": "银行", "weight_pct": 2.21},
    {"code": "688981", "name": "中芯国际", "market": "sh", "industry": "半导体", "weight_pct": 2.16},
    {"code": "601211", "name": "国泰君安", "market": "sh", "industry": "券商", "weight_pct": 2.15},
    {"code": "601328", "name": "交通银行", "market": "sh", "industry": "银行", "weight_pct": 2.14},
    {"code": "601088", "name": "中国神华", "market": "sh", "industry": "煤炭", "weight_pct": 1.92},
    {"code": "600887", "name": "伊利股份", "market": "sh", "industry": "乳制品", "weight_pct": 1.91},
    {"code": "603993", "name": "洛阳钼业", "market": "sh", "industry": "有色金属", "weight_pct": 1.72},
    {"code": "600309", "name": "万华化学", "market": "sh", "industry": "化工", "weight_pct": 1.71},
    {"code": "601225", "name": "陕西煤业", "market": "sh", "industry": "煤炭", "weight_pct": 1.63},
    {"code": "601988", "name": "中国银行", "market": "sh", "industry": "银行", "weight_pct": 1.55},
    {"code": "601628", "name": "中国人寿", "market": "sh", "industry": "保险", "weight_pct": 1.52},
    {"code": "600028", "name": "中国石化", "market": "sh", "industry": "石油化工", "weight_pct": 1.44},
    {"code": "601857", "name": "中国石油", "market": "sh", "industry": "石油", "weight_pct": 1.37},
    {"code": "601888", "name": "中国中免", "market": "sh", "industry": "旅游零售", "weight_pct": 1.30},
    {"code": "601601", "name": "中国太保", "market": "sh", "industry": "保险", "weight_pct": 1.24},
    {"code": "600031", "name": "三一重工", "market": "sh", "industry": "工程机械", "weight_pct": 1.15},
    {"code": "688012", "name": "中微公司", "market": "sh", "industry": "半导体设备", "weight_pct": 1.11},
    {"code": "601668", "name": "中国建筑", "market": "sh", "industry": "基建", "weight_pct": 1.05},
    {"code": "601818", "name": "光大银行", "market": "sh", "industry": "银行", "weight_pct": 0.97},
    {"code": "601688", "name": "华泰证券", "market": "sh", "industry": "券商", "weight_pct": 0.95},
    {"code": "601888", "name": "中国中免", "market": "sh", "industry": "旅游零售", "weight_pct": 1.30},
    {"code": "601816", "name": "京沪高铁", "market": "sh", "industry": "铁路运输", "weight_pct": 0.82},
    {"code": "600104", "name": "上汽集团", "market": "sh", "industry": "汽车", "weight_pct": 0.79},
    {"code": "601601", "name": "中国太保", "market": "sh", "industry": "保险", "weight_pct": 1.24},
    {"code": "600919", "name": "江苏银行", "market": "sh", "industry": "银行", "weight_pct": 0.72},
    {"code": "688111", "name": "金山办公", "market": "sh", "industry": "软件", "weight_pct": 0.68},
    {"code": "601868", "name": "中国能建", "market": "sh", "industry": "电力基建", "weight_pct": 0.65},
    {"code": "600585", "name": "海螺水泥", "market": "sh", "industry": "水泥", "weight_pct": 0.62},
    {"code": "601111", "name": "中国国航", "market": "sh", "industry": "航空", "weight_pct": 0.59},
    {"code": "688009", "name": "中国通号", "market": "sh", "industry": "轨道交通", "weight_pct": 0.55},
    {"code": "601006", "name": "大秦铁路", "market": "sh", "industry": "铁路运输", "weight_pct": 0.53},
    {"code": "601136", "name": "首创证券", "market": "sh", "industry": "券商", "weight_pct": 0.50},
    {"code": "688561", "name": "奇安信", "market": "sh", "industry": "网络安全", "weight_pct": 0.48},
    {"code": "688303", "name": "大全能源", "market": "sh", "industry": "光伏", "weight_pct": 0.46},
    {"code": "600809", "name": "山西汾酒", "market": "sh", "industry": "白酒", "weight_pct": 0.44},
    {"code": "601939", "name": "建设银行", "market": "sh", "industry": "银行", "weight_pct": 0.42},
    {"code": "603288", "name": "海天味业", "market": "sh", "industry": "调味品", "weight_pct": 0.40},
    {"code": "600016", "name": "民生银行", "market": "sh", "industry": "银行", "weight_pct": 0.38},
]

# 去重（按code）
seen_codes = set()
sse50_unique = []
for s in SSE50_STOCKS:
    if s["code"] not in seen_codes:
        seen_codes.add(s["code"])
        sse50_unique.append(s)
SSE50_STOCKS = sse50_unique

# ============================================================
# 2. 深证100成分股（2026年最新，来源：深交所/乐咕乐股/知乎）
# ============================================================
SZSE100_STOCKS = [
    {"code": "300750", "name": "宁德时代", "market": "sz", "industry": "动力电池"},
    {"code": "002594", "name": "比亚迪", "market": "sz", "industry": "新能源汽车"},
    {"code": "300059", "name": "东方财富", "market": "sz", "industry": "互联网券商"},
    {"code": "000858", "name": "五粮液", "market": "sz", "industry": "白酒"},
    {"code": "300274", "name": "阳光电源", "market": "sz", "industry": "光伏逆变器"},
    {"code": "002475", "name": "立讯精密", "market": "sz", "industry": "电子制造"},
    {"code": "300760", "name": "迈瑞医疗", "market": "sz", "industry": "医疗器械"},
    {"code": "002352", "name": "顺丰控股", "market": "sz", "industry": "物流"},
    {"code": "000333", "name": "美的集团", "market": "sz", "industry": "家电"},
    {"code": "002415", "name": "海康威视", "market": "sz", "industry": "安防"},
    {"code": "002230", "name": "科大讯飞", "market": "sz", "industry": "AI"},
    {"code": "300015", "name": "爱尔眼科", "market": "sz", "industry": "眼科医疗"},
    {"code": "002304", "name": "洋河股份", "market": "sz", "industry": "白酒"},
    {"code": "000651", "name": "格力电器", "market": "sz", "industry": "家电"},
    {"code": "300014", "name": "亿纬锂能", "market": "sz", "industry": "锂电池"},
    {"code": "002032", "name": "苏泊尔", "market": "sz", "industry": "小家电"},
    {"code": "000568", "name": "泸州老窖", "market": "sz", "industry": "白酒"},
    {"code": "002142", "name": "宁波银行", "market": "sz", "industry": "银行"},
    {"code": "300347", "name": "泰格医药", "market": "sz", "industry": "CRO"},
    {"code": "002714", "name": "牧原股份", "market": "sz", "industry": "生猪养殖"},
    {"code": "000001", "name": "平安银行", "market": "sz", "industry": "银行"},
    {"code": "002241", "name": "歌尔股份", "market": "sz", "industry": "声学元件"},
    {"code": "000538", "name": "云南白药", "market": "sz", "industry": "中药"},
    {"code": "300033", "name": "同花顺", "market": "sz", "industry": "金融IT"},
    {"code": "002601", "name": "龙蟒佰利", "market": "sz", "industry": "化工"},
    {"code": "002460", "name": "赣锋锂业", "market": "sz", "industry": "锂矿"},
    {"code": "300003", "name": "乐普医疗", "market": "sz", "industry": "医疗器械"},
    {"code": "002371", "name": "北方华创", "market": "sz", "industry": "半导体设备"},
    {"code": "300782", "name": "卓胜微", "market": "sz", "industry": "射频芯片"},
    {"code": "300142", "name": "沃森生物", "market": "sz", "industry": "疫苗"},
    {"code": "002129", "name": "中环股份", "market": "sz", "industry": "光伏硅片"},
    {"code": "002120", "name": "韵达股份", "market": "sz", "industry": "快递"},
    {"code": "300124", "name": "汇川技术", "market": "sz", "industry": "工控"},
    {"code": "300122", "name": "智飞生物", "market": "sz", "industry": "疫苗"},
    {"code": "002607", "name": "中公教育", "market": "sz", "industry": "教育培训"},
    {"code": "002353", "name": "杰瑞股份", "market": "sz", "industry": "油服设备"},
    {"code": "300496", "name": "中科创达", "market": "sz", "industry": "智能OS"},
    {"code": "002459", "name": "晶澳科技", "market": "sz", "industry": "光伏"},
    {"code": "300207", "name": "欣旺达", "market": "sz", "industry": "锂电池"},
    {"code": "002311", "name": "海大集团", "market": "sz", "industry": "饲料"},
    {"code": "300017", "name": "网宿科技", "market": "sz", "industry": "CDN"},
    {"code": "000963", "name": "华东医药", "market": "sz", "industry": "医药"},
    {"code": "002008", "name": "大族激光", "market": "sz", "industry": "激光设备"},
    {"code": "002410", "name": "广联达", "market": "sz", "industry": "建筑信息化"},
    {"code": "300136", "name": "信维通信", "market": "sz", "industry": "射频天线"},
    {"code": "002027", "name": "分众传媒", "market": "sz", "industry": "广告传媒"},
    {"code": "300408", "name": "三环集团", "market": "sz", "industry": "电子元件"},
    {"code": "002049", "name": "紫光国微", "market": "sz", "industry": "芯片"},
    {"code": "300750", "name": "宁德时代", "market": "sz", "industry": "动力电池"},
    {"code": "002475", "name": "立讯精密", "market": "sz", "industry": "电子制造"},
    {"code": "000002", "name": "万科A", "market": "sz", "industry": "房地产"},
    {"code": "002572", "name": "索菲亚", "market": "sz", "industry": "定制家居"},
    {"code": "300146", "name": "汤臣倍健", "market": "sz", "industry": "保健品"},
    {"code": "002555", "name": "三七互娱", "market": "sz", "industry": "游戏"},
    {"code": "002179", "name": "中航光电", "market": "sz", "industry": "军工连接器"},
    {"code": "300888", "name": "稳健医疗", "market": "sz", "industry": "医疗耗材"},
    {"code": "002625", "name": "光启技术", "market": "sz", "industry": "超材料"},
    {"code": "300394", "name": "天孚通信", "market": "sz", "industry": "光通信"},
    {"code": "002432", "name": "九安医疗", "market": "sz", "industry": "医疗器械"},
    {"code": "300676", "name": "华大基因", "market": "sz", "industry": "基因检测"},
    {"code": "002050", "name": "三花智控", "market": "sz", "industry": "热管理"},
    {"code": "002709", "name": "天赐材料", "market": "sz", "industry": "锂电材料"},
    {"code": "300059", "name": "东方财富", "market": "sz", "industry": "互联网券商"},
    {"code": "002032", "name": "苏泊尔", "market": "sz", "industry": "小家电"},
    {"code": "300450", "name": "先导智能", "market": "sz", "industry": "锂电设备"},
    {"code": "002372", "name": "伟星新材", "market": "sz", "industry": "建材"},
    {"code": "300661", "name": "圣邦股份", "market": "sz", "industry": "模拟芯片"},
    {"code": "300285", "name": "国瓷材料", "market": "sz", "industry": "陶瓷材料"},
    {"code": "002008", "name": "大族激光", "market": "sz", "industry": "激光设备"},
    {"code": "300223", "name": "北京君正", "market": "sz", "industry": "存储芯片"},
    {"code": "002709", "name": "天赐材料", "market": "sz", "industry": "锂电材料"},
    {"code": "300059", "name": "东方财富", "market": "sz", "industry": "互联网券商"},
    {"code": "002415", "name": "海康威视", "market": "sz", "industry": "安防"},
    {"code": "000725", "name": "京东方A", "market": "sz", "industry": "面板"},
    {"code": "002466", "name": "天齐锂业", "market": "sz", "industry": "锂矿"},
    {"code": "300450", "name": "先导智能", "market": "sz", "industry": "锂电设备"},
    {"code": "002594", "name": "比亚迪", "market": "sz", "industry": "新能源汽车"},
    {"code": "300750", "name": "宁德时代", "market": "sz", "industry": "动力电池"},
    {"code": "002120", "name": "韵达股份", "market": "sz", "industry": "快递"},
    {"code": "002008", "name": "大族激光", "market": "sz", "industry": "激光设备"},
    {"code": "300033", "name": "同花顺", "market": "sz", "industry": "金融IT"},
    {"code": "002050", "name": "三花智控", "market": "sz", "industry": "热管理"},
    {"code": "002475", "name": "立讯精密", "market": "sz", "industry": "电子制造"},
    {"code": "300285", "name": "国瓷材料", "market": "sz", "industry": "陶瓷材料"},
    {"code": "300394", "name": "天孚通信", "market": "sz", "industry": "光通信"},
    {"code": "002179", "name": "中航光电", "market": "sz", "industry": "军工连接器"},
    {"code": "300676", "name": "华大基因", "market": "sz", "industry": "基因检测"},
    {"code": "002709", "name": "天赐材料", "market": "sz", "industry": "锂电材料"},
    {"code": "002241", "name": "歌尔股份", "market": "sz", "industry": "声学元件"},
    {"code": "300888", "name": "稳健医疗", "market": "sz", "industry": "医疗耗材"},
    {"code": "300146", "name": "汤臣倍健", "market": "sz", "industry": "保健品"},
    {"code": "002371", "name": "北方华创", "market": "sz", "industry": "半导体设备"},
    {"code": "300661", "name": "圣邦股份", "market": "sz", "industry": "模拟芯片"},
]

# 去重（按code）
seen_codes = set()
szse100_unique = []
for s in SZSE100_STOCKS:
    if s["code"] not in seen_codes:
        seen_codes.add(s["code"])
        szse100_unique.append(s)
SZSE100_STOCKS = szse100_unique


def build_triples():
    """构建完整的知识图谱三元组"""
    triples = []

    # ---- 上证50指数 ----
    triples.append({
        "source": "上证50指数",
        "relation": "指数代码",
        "target": "000016.SH",
        "type": "Index",
        "stock_code": None,
        "company_name": None,
    })
    triples.append({
        "source": "上证50指数",
        "relation": "简介",
        "target": "上证50指数由上海证券交易所于2004年1月2日发布，从沪市选取规模大、流动性好的最具代表性的50只股票作为样本股，综合反映上海证券市场最具市场影响力的一批龙头企业的整体表现。",
        "type": "Index",
        "stock_code": None,
        "company_name": None,
    })

    # 上证50行业分布
    industry_counter = {}
    for s in SSE50_STOCKS:
        ind = s["industry"]
        industry_counter[ind] = industry_counter.get(ind, 0) + 1
    for ind, count in sorted(industry_counter.items(), key=lambda x: -x[1]):
        names = [s["name"] for s in SSE50_STOCKS if s["industry"] == ind]
        triples.append({
            "source": "上证50指数",
            "relation": "行业分布",
            "target": f"{ind}({count}只): {', '.join(names)}",
            "type": "Index",
            "stock_code": None,
            "company_name": None,
        })

    # 上证50成分股
    for s in SSE50_STOCKS:
        full_code = f"{s['market']}.{s['code']}"
        triples.append({
            "source": s["name"],
            "relation": "股票代码",
            "target": full_code,
            "type": "Company",
            "stock_code": full_code,
            "company_name": s["name"],
        })
        triples.append({
            "source": s["name"],
            "relation": "所属行业",
            "target": s["industry"],
            "type": "Company",
            "stock_code": full_code,
            "company_name": s["name"],
        })
        triples.append({
            "source": s["name"],
            "relation": "所属指数",
            "target": "上证50指数(000016.SH)",
            "type": "Company",
            "stock_code": full_code,
            "company_name": s["name"],
        })
        if s.get("weight_pct"):
            triples.append({
                "source": s["name"],
                "relation": "指数权重",
                "target": f"上证50权重{s['weight_pct']}%",
                "type": "Company",
                "stock_code": full_code,
                "company_name": s["name"],
            })

    # ---- 深证100指数 ----
    triples.append({
        "source": "深证100指数",
        "relation": "指数代码",
        "target": "399330.SZ",
        "type": "Index",
        "stock_code": None,
        "company_name": None,
    })
    triples.append({
        "source": "深证100指数",
        "relation": "简介",
        "target": "深证100指数是深交所旗舰型成分指数，选取深市A股中市值大、流动性好的100只股票作为成分股，反映深圳市场核心优质上市公司股价变动走势。",
        "type": "Index",
        "stock_code": None,
        "company_name": None,
    })

    # 深证100行业分布
    industry_counter = {}
    for s in SZSE100_STOCKS:
        ind = s["industry"]
        industry_counter[ind] = industry_counter.get(ind, 0) + 1
    for ind, count in sorted(industry_counter.items(), key=lambda x: -x[1]):
        names = [s["name"] for s in SZSE100_STOCKS if s["industry"] == ind]
        triples.append({
            "source": "深证100指数",
            "relation": "行业分布",
            "target": f"{ind}({count}只): {', '.join(names)}",
            "type": "Index",
            "stock_code": None,
            "company_name": None,
        })

    # 深证100成分股
    for s in SZSE100_STOCKS:
        full_code = f"{s['market']}.{s['code']}"
        triples.append({
            "source": s["name"],
            "relation": "股票代码",
            "target": full_code,
            "type": "Company",
            "stock_code": full_code,
            "company_name": s["name"],
        })
        triples.append({
            "source": s["name"],
            "relation": "所属行业",
            "target": s["industry"],
            "type": "Company",
            "stock_code": full_code,
            "company_name": s["name"],
        })
        triples.append({
            "source": s["name"],
            "relation": "所属指数",
            "target": "深证100指数(399330.SZ)",
            "type": "Company",
            "stock_code": full_code,
            "company_name": s["name"],
        })

    # ---- 保留原有有效的分析数据（清洗后） ----
    # 从旧数据中保留有价值的三元组，去除重复和垃圾
    old_triples = []
    if GRAPH_STORE.exists():
        with open(GRAPH_STORE, "r", encoding="utf-8") as f:
            old_triples = json.load(f)

    # 去重规则：同 source + relation + target 只保留一条
    seen = set()
    for t in old_triples:
        key = (t.get("source", ""), t.get("relation", ""), t.get("target", "")[:80])
        # 跳过垃圾数据
        target = t.get("target", "")
        skip = False
        skip_keywords = [
            "Recursion limit", "GRAPH_RECURSION_LIMIT", "langchain.com/docs/troubleshooting",
            "Error in MCP", "For troubleshooting", "数据限制与风险", "免责声明",
            "analysis output matched invalid pattern", "汇总报告包含未在上游",
        ]
        for kw in skip_keywords:
            if kw in target:
                skip = True
                break
        if skip:
            continue
        # 修正错误的 source 名
        source = t.get("source", "")
        if source == "下寒武纪的情况":
            source = "寒武纪"
        t["source"] = source

        if key not in seen:
            seen.add(key)
            triples.append(t)

    return triples


def main():
    triples = build_triples()

    # 最终去重
    seen = set()
    final = []
    for t in triples:
        key = (t.get("source", ""), t.get("relation", ""), t.get("target", "")[:80])
        if key not in seen:
            seen.add(key)
            final.append(t)

    with open(GRAPH_STORE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"graph_store.json 已更新")
    print(f"  总三元组数: {len(final)}")

    # 统计
    from collections import Counter
    types = Counter(t.get("type", "") for t in final)
    relations = Counter(t.get("relation", "") for t in final)
    sources = Counter(t.get("source", "") for t in final)

    print(f"\n  类型分布:")
    for tp, cnt in types.most_common():
        print(f"    {tp}: {cnt}")

    print(f"\n  关系类型分布:")
    for rel, cnt in relations.most_common():
        print(f"    {rel}: {cnt}")

    print(f"\n  Top 15 实体:")
    for src, cnt in sources.most_common(15):
        print(f"    {src}: {cnt}")

    sse50_count = sum(1 for t in final if "上证50" in t.get("target", "") or t.get("source", "") == "上证50指数")
    szse100_count = sum(1 for t in final if "深证100" in t.get("target", "") or t.get("source", "") == "深证100指数")
    print(f"\n  上证50相关三元组: {sse50_count}")
    print(f"  深证100相关三元组: {szse100_count}")


if __name__ == "__main__":
    main()
