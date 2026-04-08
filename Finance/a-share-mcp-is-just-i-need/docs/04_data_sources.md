# 数据源

当前数据源：
- `src/baostock_data_source.py` 中的 `BaostockDataSource`

为什么要这个类：
- `FinancialDataSource` 定义了抽象接口
- `BaostockDataSource` 用 Baostock API 实现接口
- 工具函数依赖接口，而不是依赖具体实现

关键行为：
- 用登录上下文管理器管理 Baostock 会话
- 区分“无数据”和“接口错误”
- 字段列表格式统一处理

模型辅助分析：
- 新闻爬取与情感/风险分析是扩展能力
- 不是 `FinancialDataSource` 接口要求的一部分
- 应视为可选功能，路径用环境变量可配置
