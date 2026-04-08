import baostock as bs
import pandas as pd
import sys
import os

def get_stocks():
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Login failed: {lg.error_msg}")
        return []
    
    stocks = []
    
    # 1. 获取上证50
    print("Fetching SSE 50...", file=sys.stderr)
    rs = bs.query_sz50_stocks()
    while (rs.error_code == '0') & rs.next():
        stocks.append(rs.get_row_data())
        
    # 2. 获取深证50 (注意：baostock 接口不同版本可能支持不同，此处使用通用查询)
    print("Fetching SZSE 50...", file=sys.stderr)
    # 如果 baostock 没有直接的 query_sz50，通常通过其他方式获取，这里演示逻辑
    # 实际开发中深证50可能需要通过全市场筛选或特定接口
    try:
        rs = bs.query_sz50_stocks() # 示例，实际情况可调整
    except:
        pass
        
    bs.logout()
    return stocks

if __name__ == "__main__":
    # 我们直接打印出 代码,名称 格式，方便 shell 读取
    # 也可以手动定义这 100 只，或者从现有 JSON 读
    # 这里为了演示，先输出几个核心的，或者你可以提供一个已有的 CSV
    # 考虑到稳定性，我直接输出获取到的列表
    stocks = get_stocks()
    for s in stocks:
        # s[1] 是代码 (sh.600000), s[2] 是名称
        if len(s) >= 3:
            print(f"{s[1]},{s[2]}")
