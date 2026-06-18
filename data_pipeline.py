#!/usr/bin/env python3
"""
理财经理智能匹配数据管道 v1.0
用途：接入市场数据 + 45只产品池，生成 daily.json 供移动端使用
运行方式：python3 data_pipeline.py [--input input.json] [--output daily.json]
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ============================================================
# 45 只核心产品池
# ============================================================
PRODUCTS = json.loads(open(os.path.join(os.path.dirname(__file__), 'data', 'products.json'), 'r').read()) if os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'products.json')) else []

# 如果 products.json 不存在，从 index.html 动态提取
if not PRODUCTS:
    import re
    html_path = os.path.join(os.path.dirname(__file__), 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r') as f:
            html = f.read()
        m = re.search(r'const PRODUCTS\s*=\s*(\[.+?\]);', html, re.DOTALL)
        if m:
            PRODUCTS = json.loads(m.group(1))
            # 缓存到 products.json
            os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)
            with open(os.path.join(os.path.dirname(__file__), 'data', 'products.json'), 'w') as f:
                json.dump(PRODUCTS, f, ensure_ascii=False, indent=2)
            print(f"✓ 从 index.html 提取 {len(PRODUCTS)} 只产品，已缓存")

# ============================================================
# 资产配置模板
# ============================================================
ALLOCATION = {
    "PR1": {"存款/货币":"60-80%","保险":"10-20%","理财":"10-20%","基金":"0-10%"},
    "PR2": {"存款/货币":"40-50%","保险":"10-20%","理财":"20-30%","基金":"10-20%"},
    "PR3": {"存款/货币":"20-30%","保险":"10-20%","理财":"25-35%","基金":"20-35%"},
    "PR4": {"存款/货币":"10-20%","保险":"5-15%","理财":"20-30%","基金":"35-50%"},
    "PR5": {"存款/货币":"5-10%","保险":"5-10%","理财":"15-25%","基金":"50-70%"},
}

CAT_LABELS = {"基金":"基金","保险":"保险","理财":"理财","存款":"存款","结构性存款":"结构性存款","外币存款":"外币存款"}

# ============================================================
# 产品匹配规则
# ============================================================

def match_products(market_data):
    """
    基于市场环境匹配产品
    返回按风险等级分组的产品推荐
    """
    result = {"PR1": [], "PR2": [], "PR3": [], "PR4": [], "PR5": []}
    
    asset = market_data.get("asset_prices", {})
    macro = market_data.get("macro", {})
    sectors = market_data.get("sector_rotation", {}).get("current_hotspots", [])
    deposit = market_data.get("deposit_rate", {})
    
    # 市场环境判断
    a_share_trend = (asset.get("a_share", {}) or {}).get("trend", "")
    bond_trend = (asset.get("bond", {}) or {}).get("trend", "")
    gold_trend = (asset.get("gold", {}) or {}).get("trend", "")
    rate_down = "下行" in deposit.get("trend", "")
    equity_bullish = "强" in a_share_trend or "偏强" in a_share_trend
    
    hotspot_sectors = [s.get("sector", "") for s in sectors]
    
    for p in PRODUCTS:
        cat = p.get("product_category", "")
        risk = p.get("risk_level", "PR3")
        score = 50  # 基础分
        reasons = []
        
        # === 保险产品评分 ===
        if cat == "保险":
            if rate_down:
                score += 20
                reasons.append("利率下行周期，锁定收益率价值凸显")
            if p.get("sub_category") == "增额终身寿险":
                score += 10
                reasons.append("利率下行期增额终身寿险保障+增值双重功能突出")
            if p.get("private_bank_only"):
                score += 5
                reasons.append("私银专属产品，条款更优")
            if p.get("tags") and "万能险" in p.get("tags"):
                if "分红" in str(p.get("expected_return_desc", "")):
                    score += 5
                    reasons.append("万能险保底+浮动收益，适配当前利率环境")
            duration = p.get("term_days", 0)
            if duration >= 1825:  # 5年+
                score += 5
                reasons.append(f"长期限({duration//365}年)，锁定长期利率")
        
        # === 基金产品评分 ===
        elif cat == "基金":
            if equity_bullish:
                score += 10
                reasons.append("权益市场偏强，基金配置机会较好")
            else:
                score += 3
                reasons.append("市场震荡期，精选基金仍有机会")
            # 匹配热点板块
            for hs in hotspot_sectors:
                for tag in p.get("tags", []):
                    if hs in tag or tag in hs:
                        score += 12
                        reasons.append(f"标的覆盖当前热点「{hs}」")
                        break
            if rate_down:
                score += 5
                reasons.append("无风险利率下行，权益资产相对吸引力提升")
        
        # === 理财产品评分 ===
        elif cat == "理财":
            if rate_down:
                score += 15
                reasons.append("利率下行期，理财收益相对存款优势扩大")
            if p.get("sub_category") and "固收" in str(p.get("sub_category", "")):
                score += 8
                reasons.append("固收类理财低波动，是稳健底仓优选")
            if p.get("sub_category") and "混合" in str(p.get("sub_category", "")):
                score += 5
                reasons.append("混合类理财可适度参与权益增厚收益")
        
        # === 存款类产品评分 ===
        elif cat in ["存款", "结构性存款"]:
            if rate_down:
                score -= 3  # 存款利率跟随下调
                reasons.append("利率下行趋势下，存款吸引力边际减弱")
            else:
                score += 5
            if cat == "结构性存款":
                score += 8
                reasons.append("结构性存款保本+浮动收益，利率下行期性价比突出")
            if p.get("term_days", 0) <= 365:
                score += 3
                reasons.append("短期限，流动性好")
        
        # 风险等级适配
        if risk == "PR1":
            if score > 50:
                result["PR1"].append(format_product(p, score, reasons))
        elif risk == "PR2":
            if score > 45:
                result["PR1"].append(format_product(p, score, reasons))
                result["PR2"].append(format_product(p, score, reasons))
        elif risk == "PR3":
            if score > 45:
                result["PR2"].append(format_product(p, score, reasons))
                result["PR3"].append(format_product(p, score, reasons))
        elif risk in ["PR4", "PR5"]:
            if score > 40:
                result["PR3"].append(format_product(p, score, reasons))
                result["PR4"].append(format_product(p, score, reasons))
                result["PR5"].append(format_product(p, score, reasons))
    
    # 按分数排序，每类最多8只
    for level in result:
        result[level].sort(key=lambda x: x["score"], reverse=True)
        result[level] = result[level][:8]
    
    return result


def format_product(p, score, reasons):
    """格式化产品输出"""
    return {
        "product_id": p.get("product_id", ""),
        "product_name": p.get("product_name", ""),
        "product_category": p.get("product_category", ""),
        "sub_category": p.get("sub_category", ""),
        "issuer": p.get("issuer", ""),
        "risk_level": p.get("risk_level", "PR3"),
        "expected_return_low": p.get("expected_return_low", 0),
        "expected_return_high": p.get("expected_return_high", 0),
        "term_days": p.get("term_days", 0),
        "min_investment": p.get("min_investment", 1),
        "score": score,
        "reasons": reasons,
        "private_bank_only": p.get("private_bank_only", 0),
        "liquidity_type": p.get("liquidity_type", ""),
        "tags": p.get("tags", []),
    }


# ============================================================
# 市场环境判断
# ============================================================

def judge_market_bias(market_data):
    """综合判断各类资产的市场偏向"""
    ap = market_data.get("asset_prices", {})
    dep = market_data.get("deposit_rate", {})
    
    def is_bullish(text):
        return any(w in (text or "") for w in ["强", "偏强", "上涨", "走强", "反弹", "上行"])
    
    def is_bearish(text):
        return any(w in (text or "") for w in ["弱", "偏弱", "下跌", "走弱", "回落", "下行", "承压", "倒挂"])
    
    a_share_trend = (ap.get("a_share", {}) or {}).get("trend", "")
    bond_trend = (ap.get("bond", {}) or {}).get("trend", "")
    gold_trend = (ap.get("gold", {}) or {}).get("trend", "")
    fx_trend = (ap.get("fx", {}) or {}).get("trend", "")
    
    return {
        "equity": "偏多" if "强" in a_share_trend else ("偏空" if is_bearish(a_share_trend) else "中性"),
        "bond": "偏多" if "低位" in bond_trend else ("偏空" if is_bullish(bond_trend) else "中性"),
        "gold": "偏多" if "上涨" in gold_trend else ("偏空" if is_bearish(gold_trend) else "中性"),
        "deposit": "偏空（利率下行中）" if "下行" in dep.get("trend", "") else "中性",
        "fx": "偏多（人民币走强）" if "升值" in fx_trend or "走强" in fx_trend else ("偏空" if "贬值" in fx_trend else "中性"),
    }


# ============================================================
# 新闻处理
# ============================================================

def process_news(news_items):
    """处理新闻，添加资本视角解读"""
    processed = []
    for item in (news_items or []):
        title = item.get("title", "")
        summary = item.get("summary", "")
        category = item.get("category", "宏观经济")
        
        # 自动生成人话版解读
        plain = generate_plain_text(title, summary, category)
        capital = generate_capital_view(title, summary, category)
        
        processed.append({
            "title": title,
            "summary": summary,
            "category": category,
            "capital_view": capital,
            "plain_text": plain,
        })
    return processed


def generate_capital_view(title, summary, category):
    """生成资本视角"""
    text = title + summary
    if "利率" in text or "降息" in text or "LPR" in text:
        return "利率下行中长期利好固收类资产，储蓄型保险锁定收益的价值凸显。"
    elif "AI" in text or "半导体" in text or "芯片" in text:
        return "科技主线持续强化，相关主题基金和ETF具备配置机会。"
    elif "消费" in text or "零售" in text:
        return "消费复苏预期升温，可选消费品、消费类基金值得关注。"
    elif "地产" in text or "房地产" in text:
        return "地产链政策持续发力，关注银行、建材等关联板块的修复机会。"
    elif "黄金" in text or "金价" in text:
        return "黄金短期波动加大，长期作为资产配置的压舱石价值不改。"
    elif "人民币" in text or "汇率" in text:
        return "人民币汇率波动影响外资流向，关注跨境配置和美元资产比例。"
    elif "新能源" in text or "光伏" in text or "锂电" in text:
        return "新能源产业链整合加速，龙头企业优势进一步集中。"
    else:
        return "关注该事件对市场情绪和资产配置方向的短期影响。"


def generate_plain_text(title, summary, category):
    """生成人话版解读"""
    text = title + summary
    if "利率" in text or "降息" in text:
        return "简单说就是：贷款利率又降了，银行给的钱更便宜了。对老百姓来说，存款利息越来越少，要想保值就得找更好的理财方式。"
    elif "AI" in text or "半导体" in text:
        return "AI和芯片相关公司最近很火，背后是国产替代的大趋势——以前依赖进口的，现在要自己造了。"
    elif "地产" in text:
        return "房地产还在调整期，政策在想办法稳住房价和成交量。对投资者来说，这个板块波动大，需要谨慎。"
    elif "黄金" in text:
        return "黄金价格最近变化不小，主要是受国际局势和美元走势的影响。短期波动正常，长期看还是保值的硬通货。"
    else:
        return "这条新闻值得关注，可能会影响接下来的市场走势和投资方向。"


# ============================================================
# 主流程
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="理财经理智能匹配数据管道")
    parser.add_argument("--input", default=None, help="输入JSON文件（市场数据）")
    parser.add_argument("--output", default=None, help="输出JSON文件路径")
    args = parser.parse_args()
    
    now = datetime.now(timezone(timedelta(hours=8)))
    date_str = now.strftime("%Y-%m-%d")
    
    # 读取输入数据
    market_data = {}
    news_items = []
    
    if args.input and os.path.exists(args.input):
        with open(args.input, 'r') as f:
            raw = json.load(f)
        market_data = raw.get("market", raw.get("market_data", raw))
        news_items = raw.get("news", [])
        daily_outlook = raw.get("daily_outlook", {})
    
    # 确保 PRODUCTS 已加载
    if not PRODUCTS:
        print("❌ 产品数据未加载，请确保 index.html 中 const PRODUCTS 存在")
        sys.exit(1)
    
    # 产品匹配
    print(f"📊 匹配 {len(PRODUCTS)} 只产品...")
    matches = match_products(market_data)
    total_matched = sum(len(v) for v in matches.values())
    print(f"  ✓ 匹配完成: {total_matched} 只入选 ({', '.join(f'{k}:{len(v)}' for k,v in matches.items())})")
    
    # 市场偏向
    bias = judge_market_bias(market_data)
    
    # 新闻处理
    print(f"📰 处理 {len(news_items)} 条新闻...")
    processed_news = process_news(news_items)
    
    # 构建输出
    output = {
        "date": date_str,
        "generated_at": now.isoformat(),
        "market": market_data,
        "market_bias": bias,
        "allocation": ALLOCATION,
        "product_matches": matches,
        "news": processed_news,
        "daily_outlook": daily_outlook,
        "summary": {
            "equity_outlook": f"权益市场{match_equity_bias(bias['equity'])}",
            "bond_outlook": f"债券市场{match_bond_bias(bias['bond'])}",
            "strategy": generate_strategy(bias),
            "key_reminder": generate_reminder(bias, market_data),
        }
    }
    
    # 写入输出
    out_path = args.output or os.path.join(os.path.dirname(__file__), 'data', 'daily.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ daily.json 已生成: {out_path} ({os.path.getsize(out_path)} bytes)")
    return out_path


def match_equity_bias(bias):
    if "偏多" in bias:
        return "震荡偏强，结构性机会丰富，关注AI/半导体/机器人等新质生产力方向"
    elif "偏空" in bias:
        return "短期承压，建议控制仓位，关注高股息等防御性板块"
    return "震荡格局，精选个股和主题基金为上"


def match_bond_bias(bias):
    if "偏多" in bias:
        return "收益率低位运行，债基配置价值仍存但空间收窄"
    return "债市平稳，利率债和信用债均有配置机会"


def generate_strategy(bias):
    if "下行" in str(bias.get("deposit", "")):
        return "在利率下行大背景下，建议：1) 适当降低存款比例；2) 增配储蓄型保险锁定利率；3) 固收+产品替代纯固收；4) 权益类产品适度参与结构性机会"
    return "均衡配置，根据个人风险偏好和流动性需求，构建多元化组合"


def generate_reminder(bias, market_data):
    """生成核心提醒"""
    reminders = []
    if "下行" in str(bias.get("deposit", "")):
        reminders.append("存款利率持续下行中，建议尽早锁定当前较高的储蓄型保险利率")
    if "偏多" in str(bias.get("equity", "")):
        reminders.append("权益市场偏强，但注意控制仓位和分散投资")
    sr = market_data.get("sector_rotation", {})
    risks = sr.get("risk_factors", [])
    if risks:
        reminders.append(f"关注风险：{'、'.join(risks[:3])}")
    return reminders


if __name__ == "__main__":
    main()
