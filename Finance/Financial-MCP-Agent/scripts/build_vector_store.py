"""
重建本地向量库：注入上证50/深证100指数成分股知识文档。
与 graph_store.json 对齐。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.vector_service import VectorService

DATA_DIR = PROJECT_ROOT / "data"
VECTOR_STORE = DATA_DIR / "vector_store"

# 复用 build_graph_store.py 中的成分股数据
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
    {"code": "601816", "name": "京沪高铁", "market": "sh", "industry": "铁路运输", "weight_pct": 0.82},
    {"code": "600104", "name": "上汽集团", "market": "sh", "industry": "汽车", "weight_pct": 0.79},
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
    {"code": "300450", "name": "先导智能", "market": "sz", "industry": "锂电设备"},
    {"code": "002372", "name": "伟星新材", "market": "sz", "industry": "建材"},
    {"code": "300661", "name": "圣邦股份", "market": "sz", "industry": "模拟芯片"},
    {"code": "300285", "name": "国瓷材料", "market": "sz", "industry": "陶瓷材料"},
    {"code": "300223", "name": "北京君正", "market": "sz", "industry": "存储芯片"},
    {"code": "000725", "name": "京东方A", "market": "sz", "industry": "面板"},
    {"code": "002466", "name": "天齐锂业", "market": "sz", "industry": "锂矿"},
    {"code": "002714", "name": "牧原股份", "market": "sz", "industry": "生猪养殖"},
    {"code": "000768", "name": "中航西飞", "market": "sz", "industry": "军工"},
    {"code": "300308", "name": "中际旭创", "market": "sz", "industry": "光模块"},
    {"code": "300750", "name": "宁德时代", "market": "sz", "industry": "动力电池"},
    {"code": "002049", "name": "紫光国微", "market": "sz", "industry": "芯片"},
]

# 去重
seen = set()
sse50_unique = []
for s in SSE50_STOCKS:
    if s["code"] not in seen:
        seen.add(s["code"])
        sse50_unique.append(s)
SSE50_STOCKS = sse50_unique

seen = set()
szse100_unique = []
for s in SZSE100_STOCKS:
    if s["code"] not in seen:
        seen.add(s["code"])
        szse100_unique.append(s)
SZSE100_STOCKS = szse100_unique

# ============================================================
# 行业知识库（为每个行业生成简介文档，增强检索召回）
# ============================================================
INDUSTRY_KNOWLEDGE = {
    "银行": "银行业是中国金融体系的核心。主要业务包括存贷款、理财、信用卡、投行等。监管机构为中国银保监会。关键指标：净息差、不良贷款率、资本充足率、ROE。A股主要银行股包括工商银行、招商银行、建设银行、农业银行、中国银行、兴业银行、交通银行、光大银行、民生银行、江苏银行、宁波银行、平安银行等。银行板块与宏观经济周期高度相关，受货币政策（降息/降准）直接影响。",
    "保险": "保险行业分为寿险、财险和再保险。中国主要上市保险公司有中国平安、中国人寿、中国太保、新华保险等。关键指标：保费收入、新业务价值、内含价值、投资收益率。保险资金是A股市场重要机构投资者。",
    "白酒": "白酒是中国特有的消费品行业，具有高毛利、强品牌壁垒特征。高端白酒代表：贵州茅台、五粮液、泸州老窖、山西汾酒、洋河股份。关键指标：营收增速、毛利率、经销商库存、批零价差。白酒行业受消费升级和商务宴请需求驱动。",
    "半导体": "半导体行业是信息技术的基础，分为设计（fabless）、制造（foundry）、封测（OSAT）三大环节。A股半导体公司：中芯国际（制造）、寒武纪（AI芯片）、海光信息（CPU）、北方华创（设备）、中微公司（刻蚀设备）、紫光国微（芯片）、圣邦股份（模拟芯片）。关键指标：营收、毛利率、产能利用率。受国产替代和AI需求驱动。",
    "新能源": "新能源产业链包括动力电池（宁德时代、亿纬锂能、欣旺达）、锂矿（赣锋锂业、天齐锂业）、光伏（阳光电源、晶澳科技）、新能源汽车（比亚迪）。关键指标：装机量、渗透率、产能利用率、原材料价格。受碳中和政策和全球能源转型驱动。",
    "医药": "医药行业包括化学药、中药、生物制药、医疗器械、CRO/CMO等子行业。A股代表公司：恒瑞医药（创新药）、药明康德（CRO）、迈瑞医疗（器械）、爱尔眼科（眼科）、云南白药（中药）、智飞生物（疫苗）、沃森生物（疫苗）、华东医药。关键指标：研发投入、管线进度、集采影响。",
    "家电": "家电行业是中国优势制造业，分为白电（空调/冰箱/洗衣机）和小家电。代表公司：美的集团、格力电器、海尔智家、苏泊尔。关键指标：出货量、毛利率、外销占比。受地产周期和消费升级影响。",
    "有色金属": "有色金属包括铜、铝、锂、钴、稀土等。A股代表公司：紫金矿业（铜金）、洛阳钼业（钴铜）、北方稀土（稀土）、赣锋锂业/天齐锂业（锂）。关键指标：金属价格、产量、成本。与全球经济周期和新能源需求高度相关。",
    "煤炭": "煤炭行业是中国传统能源基础。代表公司：中国神华、陕西煤业。关键指标：煤价、产量、长协占比。受能源政策和供需格局影响。",
    "券商": "券商（证券公司）是资本市场中介，业务包括经纪、投行、资管、自营。A股代表公司：中信证券、国泰君安、华泰证券、东方财富（互联网券商）、招商证券。关键指标：日均成交额、投行承销规模、自营收益。与市场行情高度正相关。",
    "基建": "基建行业包括建筑施工、铁路、公路等。代表公司：中国建筑、中国中铁、中国交建、中国铁建、京沪高铁、大秦铁路。关键指标：新签合同额、订单转化率。受财政政策和专项债发行影响。",
    "石油化工": "石油化工行业包括上游勘探开采（中国石油、中国神华）和下游炼化（中国石化）。关键指标：油价、炼化利润、产销量。与国际油价高度相关。",
    "食品饮料": "食品饮料行业包括乳制品（伊利股份）、调味品（海天味业）、保健品（汤臣倍健）等。关键指标：营收增速、毛利率、渠道渗透率。具有防御属性，受消费升级驱动。",
    "科技": "科技行业涵盖软件、AI、网络安全等。代表公司：科大讯飞（AI）、金山办公（办公软件）、奇安信（网络安全）、中科创达（智能OS）、同花顺（金融IT）、广联达（建筑信息化）。关键指标：研发投入占比、用户增长、ARR。",
    "军工": "军工行业包括航空、航天、兵器、舰船等。代表公司：中航西飞（飞机）、中航光电（连接器）、中国通号（轨道交通信号）。关键指标：军品订单、毛利率。具有逆周期属性，受国防预算驱动。",
}


def build_vector_store():
    """构建向量库文档列表"""
    docs = []
    doc_idx = 0

    # ---- 上证50指数总览 ----
    sse50_stock_lines = []
    for s in SSE50_STOCKS:
        weight = f"权重{s['weight_pct']}%" if s.get("weight_pct") else ""
        sse50_stock_lines.append(
            f"- {s['name']}（{s['market']}.{s['code']}），行业：{s['industry']}，{weight}"
        )
    docs.append({
        "doc_id": f"index:sse50:{doc_idx}",
        "session_id": -1,
        "stock_code": None,
        "company_name": "上证50指数",
        "title": "上证50指数(000016.SH)成分股名单",
        "content": (
            "## 上证50指数成分股名单\n\n"
            "上证50指数（代码：000016.SH）由上海证券交易所于2004年1月2日发布，"
            "从沪市选取规模大、流动性好的最具代表性的50只股票作为样本股，"
            "综合反映上海证券市场最具市场影响力的一批龙头企业的整体表现。\n\n"
            "### 成分股列表\n" + "\n".join(sse50_stock_lines) + "\n\n"
            "### 行业分布\n"
            "上证50以金融（银行+保险+券商）和能源资源为权重主力，"
            "近年来半导体（寒武纪、海光信息、中芯国际、中微公司）和消费（贵州茅台、伊利股份）权重持续提升。"
        ),
        "metadata": {"source": "上证50指数", "type": "index_overview"},
    })
    doc_idx += 1

    # ---- 深证100指数总览 ----
    szse100_stock_lines = []
    for s in SZSE100_STOCKS:
        szse100_stock_lines.append(
            f"- {s['name']}（{s['market']}.{s['code']}），行业：{s['industry']}"
        )
    docs.append({
        "doc_id": f"index:szse100:{doc_idx}",
        "session_id": -1,
        "stock_code": None,
        "company_name": "深证100指数",
        "title": "深证100指数(399330.SZ)成分股名单",
        "content": (
            "## 深证100指数成分股名单\n\n"
            "深证100指数（代码：399330.SZ）是深交所旗舰型成分指数，"
            "选取深市A股中市值大、流动性好的100只股票作为成分股，"
            "反映深圳市场核心优质上市公司股价变动走势。\n\n"
            "### 成分股列表\n" + "\n".join(szse100_stock_lines) + "\n\n"
            "### 行业分布\n"
            "深证100以新能源（宁德时代、比亚迪）、科技（海康威视、科大讯飞）、"
            "医药（迈瑞医疗、爱尔眼科、智飞生物）和消费（五粮液、美的集团）为核心权重。"
        ),
        "metadata": {"source": "深证100指数", "type": "index_overview"},
    })
    doc_idx += 1

    # ---- 上证50每只成分股生成独立文档 ----
    for s in SSE50_STOCKS:
        full_code = f"{s['market']}.{s['code']}"
        docs.append({
            "doc_id": f"stock:sse50:{doc_idx}",
            "session_id": -1,
            "stock_code": full_code,
            "company_name": s["name"],
            "title": f"{s['name']}（{full_code}）基本信息",
            "content": (
                f"## {s['name']}（{full_code}）\n\n"
                f"- **股票代码**：{full_code}\n"
                f"- **所属行业**：{s['industry']}\n"
                f"- **所属指数**：上证50指数（000016.SH）\n"
                + (f"- **指数权重**：{s['weight_pct']}%\n" if s.get("weight_pct") else "")
                + f"- **上市交易所**：上海证券交易所\n"
                + (f"- **行业简介**：{INDUSTRY_KNOWLEDGE.get(s['industry'], '')}" if s['industry'] in INDUSTRY_KNOWLEDGE else "")
            ),
            "metadata": {"source": "上证50指数", "type": "stock_info", "industry": s["industry"]},
        })
        doc_idx += 1

    # ---- 深证100每只成分股生成独立文档 ----
    for s in SZSE100_STOCKS:
        full_code = f"{s['market']}.{s['code']}"
        docs.append({
            "doc_id": f"stock:szse100:{doc_idx}",
            "session_id": -1,
            "stock_code": full_code,
            "company_name": s["name"],
            "title": f"{s['name']}（{full_code}）基本信息",
            "content": (
                f"## {s['name']}（{full_code}）\n\n"
                f"- **股票代码**：{full_code}\n"
                f"- **所属行业**：{s['industry']}\n"
                f"- **所属指数**：深证100指数（399330.SZ）\n"
                f"- **上市交易所**：深圳证券交易所\n"
                + (f"- **行业简介**：{INDUSTRY_KNOWLEDGE.get(s['industry'], '')}" if s['industry'] in INDUSTRY_KNOWLEDGE else "")
            ),
            "metadata": {"source": "深证100指数", "type": "stock_info", "industry": s["industry"]},
        })
        doc_idx += 1

    # ---- 行业知识文档 ----
    for industry, knowledge in INDUSTRY_KNOWLEDGE.items():
        docs.append({
            "doc_id": f"industry:{doc_idx}",
            "session_id": -1,
            "stock_code": None,
            "company_name": None,
            "title": f"{industry}行业概况",
            "content": f"## {industry}行业概况\n\n{knowledge}",
            "metadata": {"source": "行业知识库", "type": "industry_knowledge"},
        })
        doc_idx += 1

    return docs


def main():
    docs = build_vector_store()
    vector_service = VectorService(VECTOR_STORE)
    count = vector_service.replace_documents(docs)

    print("向量库已清空重建")
    print(f"  文档总数: {count}")
    print(f"  元数据清单: {vector_service.docs_path}")
    print(f"  FAISS 索引目录: {vector_service.index_dir}")

    # 统计
    types = {}
    for d in docs:
        t = d.get("metadata", {}).get("type", "unknown")
        types[t] = types.get(t, 0) + 1

    industries = {}
    for d in docs:
        ind = d.get("metadata", {}).get("industry")
        if ind:
            industries[ind] = industries.get(ind, 0) + 1

    print(f"\n  文档类型分布:")
    for t, cnt in sorted(types.items()):
        print(f"    {t}: {cnt}")

    print(f"\n  覆盖行业数: {len(industries)}")
    print(f"  覆盖股票数: {types.get('stock_info', 0)}")

    # 两个指数交叉成分股
    sse50_codes = {s["code"] for s in SSE50_STOCKS}
    szse100_codes = {s["code"] for s in SZSE100_STOCKS}
    overlap = sse50_codes & szse100_codes
    if overlap:
        print(f"\n  上证50与深证100交叉成分股: {len(overlap)}只")


if __name__ == "__main__":
    main()
