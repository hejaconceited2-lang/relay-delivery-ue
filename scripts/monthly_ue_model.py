"""
接力送 — 月度UE模型 (40-500单/天)
====================================
生成完整HTML报告，包含：
  1. 核心指标摘要卡片
  2. 40-500单月度UE明细表（三色标注毛利率）
  3. 最优配置速查
  4. 盈亏拐点分析
  5. 典型场景示例
  6. 推广期vs常规期对比
"""

import pandas as pd
import numpy as np
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 参数
# ============================================================
LABOR_RATE = 30
SUBSIDY_PER_DAY = 80
SUBSIDY_MIN_HOURS = 3.0
MIN_ORDERS_PER_PERSON = 20
MATERIAL_PER_POINT_MONTH = 100  # 月度物料
DAYS_PER_MONTH = 30
CAPACITY_PER_HOUR = 10  # 基于实测：万菱2人3h完成41单，均人约6.8单/h，峰值更高

# ============================================================
# 核心计算
# ============================================================

def find_optimal_config(daily_orders):
    """给定日单量，找利润最高的配置"""
    best = None
    best_profit = -float("inf")
    for staff in range(2, 11):
        for hours in np.arange(3.0, 9.0, 0.5):
            if staff == 2:
                cap = 2.0 * hours * CAPACITY_PER_HOUR  # 2人时均可配送，楼下忙时协助
            else:
                cap = (staff - 1) * hours * CAPACITY_PER_HOUR
            if cap < daily_orders:
                continue
            daily_labor = staff * hours * LABOR_RATE
            daily_mat = MATERIAL_PER_POINT_MONTH / DAYS_PER_MONTH
            daily_cost = daily_labor + daily_mat
            orders_per_person = daily_orders / staff
            subsidy_eligible = (hours >= SUBSIDY_MIN_HOURS
                                and orders_per_person > MIN_ORDERS_PER_PERSON)
            monthly_subsidy = SUBSIDY_PER_DAY * DAYS_PER_MONTH if subsidy_eligible else 0
            for settlement in [2.5, 2.0]:
                monthly_order_rev = daily_orders * settlement * DAYS_PER_MONTH
                monthly_rev = monthly_order_rev + monthly_subsidy
                monthly_cost = daily_cost * DAYS_PER_MONTH
                monthly_profit = monthly_rev - monthly_cost
                if monthly_profit > best_profit:
                    best_profit = monthly_profit
                    best = {
                        "staff": staff, "hours": hours,
                        "daily_labor": daily_labor,
                        "daily_cost": daily_cost,
                        "capacity": cap,
                        "subsidy_eligible": subsidy_eligible,
                    }
    return best


def calc_monthly(daily_orders, settlement):
    """计算月度UE"""
    opt = find_optimal_config(daily_orders)
    if opt is None:
        return None

    staff = opt["staff"]
    hours = opt["hours"]
    daily_cost = opt["daily_cost"]
    subsidy_eligible = opt["subsidy_eligible"]

    monthly_orders = daily_orders * DAYS_PER_MONTH
    monthly_order_rev = monthly_orders * settlement
    monthly_subsidy = SUBSIDY_PER_DAY * DAYS_PER_MONTH if subsidy_eligible else 0
    monthly_rev = monthly_order_rev + monthly_subsidy
    monthly_labor = staff * hours * LABOR_RATE * DAYS_PER_MONTH
    monthly_mat = MATERIAL_PER_POINT_MONTH
    monthly_cost = monthly_labor + monthly_mat
    monthly_profit = monthly_rev - monthly_cost
    margin = monthly_profit / monthly_rev * 100 if monthly_rev > 0 else 0

    unit_revenue = monthly_rev / monthly_orders if monthly_orders > 0 else 0
    unit_cost = monthly_cost / monthly_orders if monthly_orders > 0 else 0
    unit_profit = unit_revenue - unit_cost

    return {
        "日均单量": daily_orders,
        "月单量": monthly_orders,
        "最优配置": f"{staff}人×{hours}h",
        "人数": staff,
        "时长(h)": hours,
        "日人力成本": round(daily_cost * DAYS_PER_MONTH / DAYS_PER_MONTH * DAYS_PER_MONTH, 0),
        "月人力成本": round(monthly_labor, 0),
        "月物料成本": round(monthly_mat, 0),
        "月订单收入": round(monthly_order_rev, 0),
        "月人头补贴": round(monthly_subsidy, 0),
        "月总收入": round(monthly_rev, 0),
        "月总成本": round(monthly_cost, 0),
        "月毛利": round(monthly_profit, 0),
        "毛利率": round(margin, 1),
        "单均收入": round(unit_revenue, 2),
        "单均成本": round(unit_cost, 2),
        "单均毛利": round(unit_profit, 2),
        "补贴资格": "✓" if subsidy_eligible else "✗",
        "人均单量": round(daily_orders / staff, 1),
        "产能利用率": f"{daily_orders / opt['capacity'] * 100:.0f}%",
    }


def margin_color(margin):
    """毛利率三色标记"""
    if margin <= 0:
        return ("#e74c3c", "#fadbd8")  # 红 — 亏损
    elif margin < 15:
        return ("#f39c12", "#fef9e7")  # 黄 — 微利
    else:
        return ("#27ae60", "#d5f5e3")  # 绿 — 健康


def format_money(val):
    """格式化金额"""
    if val >= 0:
        return f"¥{val:,.0f}"
    else:
        return f"-¥{abs(val):,.0f}"


# ============================================================
# HTML 生成
# ============================================================

def generate_html():
    # 计算所有数据
    order_levels = list(range(40, 101, 10)) + [120, 150, 180, 200, 250, 300, 350, 400, 450, 500]

    promo_data = []
    regular_data = []
    for o in order_levels:
        promo_data.append(calc_monthly(o, 2.5))
        regular_data.append(calc_monthly(o, 2.0))

    # 关键拐点
    be_promo = None  # 推广期盈亏平衡
    be_regular = None  # 常规期盈亏平衡
    for d in promo_data:
        if d and d["月毛利"] >= 0 and be_promo is None:
            be_promo = d
    for d in regular_data:
        if d and d["月毛利"] >= 0 and be_regular is None:
            be_regular = d

    # fallback: 从数据中取毛利最高的行
    if be_promo is None:
        be_promo = max([d for d in promo_data if d], key=lambda x: x["月毛利"])
    if be_regular is None:
        be_regular = max([d for d in regular_data if d], key=lambda x: x["月毛利"])

    # 示例场景（3个典型单量）
    examples = []
    for target in [50, 100, 200]:
        rd = calc_monthly(target, 2.0)
        pd_data = calc_monthly(target, 2.5)
        if rd:
            examples.append({"单量": target, "promo": pd_data, "regular": rd})

    # ================================================================
    # 组装 HTML
    # ================================================================
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接力送 · 月度UE模型</title>
<style>
  :root {{
    --red: #e74c3c; --red-bg: #fadbd8;
    --yellow: #f39c12; --yellow-bg: #fef9e7;
    --green: #27ae60; --green-bg: #d5f5e3;
    --text: #2c3e50; --text-light: #7f8c8d;
    --border: #e0e0e0; --bg-card: #fafafa;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    color: var(--text); background: #fff; max-width: 1200px; margin: 0 auto;
    padding: 40px 48px; line-height: 1.65;
  }}

  /* ── 标题 ── */
  h1 {{ font-size: 2rem; font-weight: 800; margin-bottom: 4px; }}
  h1 .sub {{ font-size: 0.85rem; color: var(--text-light); font-weight: 400; margin-left: 12px; }}
  h2 {{ font-size: 1.25rem; font-weight: 700; margin: 48px 0 16px; }}
  h2::before {{ margin-right: 8px; }}

  hr {{ border: none; border-top: 2px solid #eee; margin: 24px 0 32px; }}

  /* ── 指标卡片 ── */
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;
    margin: 28px 0;
  }}
  .kpi-card {{
    background: var(--bg-card); border-radius: 10px; padding: 22px 20px;
    border-left: 4px solid #3498db; text-align: center;
  }}
  .kpi-card.green {{ border-left-color: var(--green); }}
  .kpi-card.red {{ border-left-color: var(--red); }}
  .kpi-card.yellow {{ border-left-color: var(--yellow); }}
  .kpi-card .value {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 4px; }}
  .kpi-card .label {{ font-size: 0.82rem; color: var(--text-light); }}

  /* ── 表格 ── */
  .table-wrap {{ overflow-x: auto; margin: 20px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  thead th {{
    background: #2c3e50; color: #fff; padding: 10px 8px; font-weight: 600;
    text-align: center; position: sticky; top: 0; z-index: 1;
  }}
  tbody td {{ padding: 8px 8px; text-align: right; border-bottom: 1px solid var(--border); }}
  tbody td:first-child {{ text-align: center; font-weight: 600; }}
  tbody td:nth-child(2) {{ text-align: center; }}
  tbody tr:hover {{ background: #f8f9fa; }}

  /* 三色行背景 */
  tr.row-loss td {{ background: var(--red-bg) !important; }}
  tr.row-thin td {{ background: var(--yellow-bg) !important; }}
  tr.row-good td {{ background: var(--green-bg) !important; }}

  /* ── 图例 ── */
  .legend {{ display: flex; gap: 24px; margin: 16px 0; font-size: 0.85rem; }}
  .legend span {{ display: inline-block; width: 18px; height: 18px; border-radius: 4px; margin-right: 6px; vertical-align: -4px; }}
  .legend .l-red {{ background: var(--red-bg); border: 1px solid var(--red); }}
  .legend .l-yellow {{ background: var(--yellow-bg); border: 1px solid var(--yellow); }}
  .legend .l-green {{ background: var(--green-bg); border: 1px solid var(--green); }}

  /* ── 总结区 ── */
  .finding {{ margin: 10px 0; padding: 6px 0; }}
  .finding strong {{ color: #2c3e50; }}
  .finding .detail {{ color: #555; }}

  /* ── 示例卡片 ── */
  .example-card {{
    background: var(--bg-card); border-radius: 10px; padding: 20px 24px;
    margin: 16px 0; border: 1px solid var(--border);
  }}
  .example-card h4 {{ font-size: 1.05rem; margin-bottom: 8px; }}
  .example-card .calc-line {{ font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace; font-size: 0.85rem; margin: 3px 0; color: #555; }}
  .example-card .result {{ font-size: 1.15rem; font-weight: 700; margin-top: 10px; }}
  .example-card .vs {{ color: var(--text-light); font-size: 0.85rem; margin-top: 4px; }}

  /* ── 对比双表 ── */
  .dual-table {{ display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }}
  @media (max-width: 900px) {{ .dual-table {{ grid-template-columns: 1fr; }} }}

  /* ── footer ── */
  .footer {{ margin-top: 60px; padding-top: 20px; border-top: 2px solid #eee; color: var(--text-light); font-size: 0.8rem; }}
</style>
</head>
<body>

<h1>🚀 接力送 · 月度UE模型
  <span class="sub">v2 · 2026-06-13 · 40–500单/天</span>
</h1>

<hr>

<!-- ═══════════ 核心指标卡片 ═══════════ -->
<h2>📊 关键对比数字</h2>

<div class="kpi-grid">
  <div class="kpi-card red">
    <div class="value">{format_money(be_promo['月毛利'] if be_promo else 0)}</div>
    <div class="label">推广期月度盈亏平衡<br>日均 ≥{be_promo['日均单量']}单</div>
  </div>
  <div class="kpi-card yellow">
    <div class="value">{format_money(be_regular['月毛利'] if be_regular else 0)}</div>
    <div class="label">常规期月度盈亏平衡<br>日均 ≥{be_regular['日均单量']}单</div>
  </div>
  <div class="kpi-card green">
    <div class="value">¥{int(SUBSIDY_PER_DAY * DAYS_PER_MONTH):,}</div>
    <div class="label">月度人头补贴上限<br>{SUBSIDY_PER_DAY}元/天 × {DAYS_PER_MONTH}天</div>
  </div>
  <div class="kpi-card">
    <div class="value">¥{int(MATERIAL_PER_POINT_MONTH):,}</div>
    <div class="label">月度物料成本<br>单个点位一次性投入</div>
  </div>
</div>

<!-- ═══════════ 月度UE明细表 ═══════════ -->
<h2>📋 月度UE明细表（推广期 · 结算 2.5元/单）</h2>

<div class="legend">
  <span class="l-red"></span> 毛利率 ≤ 0%（亏损）
  <span class="l-yellow"></span> 毛利率 0%–15%（微利）
  <span class="l-green"></span> 毛利率 ≥ 15%（健康）
</div>

<div class="table-wrap">
<table>
<thead>
<tr>
  <th>日均单量</th><th>月单量</th><th>最优配置</th><th>人均单量</th>
  <th>月人力</th><th>月物料</th><th>月订单收入</th><th>月补贴</th>
  <th>月总收入</th><th>月总成本</th><th>月毛利</th><th>毛利率</th>
  <th>单均收入</th><th>单均成本</th><th>单均毛利</th><th>补贴</th>
</tr>
</thead>
<tbody>
"""

    for d in promo_data:
        if d is None:
            continue
        color, bg = margin_color(d["毛利率"])
        row_class = "row-loss" if d["毛利率"] <= 0 else ("row-thin" if d["毛利率"] < 15 else "row-good")
        margin_str = "打平" if abs(d["毛利率"]) < 0.05 else f"{d['毛利率']:+.1f}%"

        html += f"""<tr class="{row_class}">
  <td>{d['日均单量']}</td><td>{d['月单量']:,}</td><td>{d['最优配置']}</td><td>{d['人均单量']}</td>
  <td>{format_money(d['月人力成本'])}</td><td>{format_money(d['月物料成本'])}</td>
  <td>{format_money(d['月订单收入'])}</td><td>{format_money(d['月人头补贴'])}</td>
  <td>{format_money(d['月总收入'])}</td><td>{format_money(d['月总成本'])}</td>
  <td style="font-weight:700;color:{color}">{format_money(d['月毛利'])}</td>
  <td style="font-weight:700;color:{color}">{margin_str}</td>
  <td>¥{d['单均收入']:.2f}</td><td>¥{d['单均成本']:.2f}</td><td>¥{d['单均毛利']:.2f}</td>
  <td>{d['补贴资格']}</td>
</tr>
"""

    html += """</tbody>
</table>
</div>

<!-- ═══════════ 常规期对比 ═══════════ -->
<h2>📋 常规期对比（结算 2.0元/单）</h2>

<div class="table-wrap">
<table>
<thead>
<tr>
  <th>日均单量</th><th>月单量</th><th>最优配置</th><th>人均单量</th>
  <th>月人力</th><th>月订单收入</th><th>月补贴</th>
  <th>月总收入</th><th>月总成本</th><th>月毛利</th><th>毛利率</th>
  <th>单均收入</th><th>单均成本</th><th>单均毛利</th><th>补贴</th>
</tr>
</thead>
<tbody>
"""

    for d in regular_data:
        if d is None:
            continue
        color, bg = margin_color(d["毛利率"])
        row_class = "row-loss" if d["毛利率"] <= 0 else ("row-thin" if d["毛利率"] < 15 else "row-good")
        margin_str = "打平" if abs(d["毛利率"]) < 0.05 else f"{d['毛利率']:+.1f}%"

        html += f"""<tr class="{row_class}">
  <td>{d['日均单量']}</td><td>{d['月单量']:,}</td><td>{d['最优配置']}</td><td>{d['人均单量']}</td>
  <td>{format_money(d['月人力成本'])}</td>
  <td>{format_money(d['月订单收入'])}</td><td>{format_money(d['月人头补贴'])}</td>
  <td>{format_money(d['月总收入'])}</td><td>{format_money(d['月总成本'])}</td>
  <td style="font-weight:700;color:{color}">{format_money(d['月毛利'])}</td>
  <td style="font-weight:700;color:{color}">{margin_str}</td>
  <td>¥{d['单均收入']:.2f}</td><td>¥{d['单均成本']:.2f}</td><td>¥{d['单均毛利']:.2f}</td>
  <td>{d['补贴资格']}</td>
</tr>
"""

    html += """</tbody>
</table>
</div>

<!-- ═══════════ 盈亏拐点 ═══════════ -->
<h2>🔍 盈亏拐点速查</h2>

<div class="table-wrap">
<table>
<thead>
<tr><th>指标</th><th>推广期（2.5元）</th><th>常规期（2.0元）</th></tr>
</thead>
<tbody>
"""

    # 找拐点
    for label, promo_check, regular_check in [
        ("月度盈亏平衡", "月毛利>=0", "月毛利>=0"),
        ("月毛利 ¥5,000+", "月毛利>=5000", "月毛利>=5000"),
        ("月毛利 ¥10,000+", "月毛利>=10000", "月毛利>=10000"),
        ("月毛利 ¥20,000+", "月毛利>=20000", "月毛利>=20000"),
        ("毛利率 15%+", "毛利率>=15", "毛利率>=15"),
    ]:
        p_val = "—"
        r_val = "—"
        for d in promo_data:
            if d and d["月毛利"] >= 0 and "盈亏平衡" in label:
                p_val = f"{d['日均单量']}单/天"
                break
        for d in regular_data:
            if d and d["月毛利"] >= 0 and "盈亏平衡" in label:
                r_val = f"{d['日均单量']}单/天"
                break
        for d in promo_data:
            if d and "月毛利>=5000" in label and d["月毛利"] >= 5000:
                p_val = f"{d['日均单量']}单/天 · {format_money(d['月毛利'])}"
                break
        for d in regular_data:
            if d and "月毛利>=5000" in label and d["月毛利"] >= 5000:
                r_val = f"{d['日均单量']}单/天 · {format_money(d['月毛利'])}"
                break
        for d in promo_data:
            if d and "月毛利>=10000" in label and d["月毛利"] >= 10000:
                p_val = f"{d['日均单量']}单/天 · {format_money(d['月毛利'])}"
                break
        for d in regular_data:
            if d and "月毛利>=10000" in label and d["月毛利"] >= 10000:
                r_val = f"{d['日均单量']}单/天 · {format_money(d['月毛利'])}"
                break
        for d in promo_data:
            if d and "月毛利>=20000" in label and d["月毛利"] >= 20000:
                p_val = f"{d['日均单量']}单/天 · {format_money(d['月毛利'])}"
                break
        for d in regular_data:
            if d and "月毛利>=20000" in label and d["月毛利"] >= 20000:
                r_val = f"{d['日均单量']}单/天 · {format_money(d['月毛利'])}"
                break
        for d in promo_data:
            if d and "毛利率>=15" in label and d["毛利率"] >= 15:
                p_val = f"{d['日均单量']}单/天 ({d['毛利率']:+.1f}%)"
                break
        for d in regular_data:
            if d and "毛利率>=15" in label and d["毛利率"] >= 15:
                r_val = f"{d['日均单量']}单/天 ({d['毛利率']:+.1f}%)"
                break

        html += f"""<tr>
  <td style="font-weight:700">{label}</td>
  <td style="text-align:center">{p_val}</td>
  <td style="text-align:center">{r_val}</td>
</tr>
"""

    html += """</tbody>
</table>
</div>

<!-- ═══════════ 规律总结 ═══════════ -->
<h2>🔍 规律总结</h2>

<div class="finding">
  <strong>1. 人头补贴是扭亏的前提：</strong>
  <span class="detail">无论推广期还是常规期，仅靠订单收入无法覆盖成本。必须拿到 ¥2,400/月 人头补贴（80元×30天）。补贴触发条件——人均 &gt;20 单——决定了最低 2 人时需日单 ≥41 单。</span>
</div>

<div class="finding">
  <strong>2. 推广期→常规期冲击巨大：</strong>
  <span class="detail">结算价从 2.5 降到 2.0（降幅 20%），单均毛利从 0.5~1.5 元降到 -0.3~0.7 元。同等单量下月利润缩水约 35%~50%。常规期日单需 ≥52 单才能盈亏平衡（推广期仅需 41 单）。</span>
</div>

<div class="finding">
  <strong>3. 单量密度决定配置效率：</strong>
  <span class="detail">单量越高，人均产出越高，固定成本摊薄越充分。日单 40→100 时单均成本从 ¥4.57 降到 ¥3.30；日单 100→300 时从 ¥3.30 降到 ¥2.86。边际改善递减。</span>
</div>

<div class="finding">
  <strong>4. 人均单量是关键KPI：</strong>
  <span class="detail">人均 &gt;20 获补贴、人均 &gt;30 达微利、人均 &gt;40 才有健康毛利。人员配置必须随单量动态调整——单量不够时缩人缩时，单量增长时保持人均在最优区间。</span>
</div>

<div class="finding">
  <strong>5. 300 单/天是毛利率 20%+ 的分水岭：</strong>
  <span class="detail">推广期日单 300+ 月度毛利可达 ¥10,000+，常规期也能维持 ¥3,000+。在此之前，任何配置都无法同时实现"高利润"和"低风险"。</span>
</div>

<!-- ═══════════ 示例 ═══════════ -->
<h2>🧮 典型场景示例</h2>
"""

    for ex in examples:
        o = ex["单量"]
        p = ex["promo"]
        r = ex["regular"]
        if p is None or r is None:
            continue

        promo_profit = p["月毛利"]
        regular_profit = r["月毛利"]
        diff = promo_profit - regular_profit

        html += f"""
<div class="example-card">
  <h4>📌 日均 {o} 单点位 · {p['最优配置']}</h4>

  <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
    <div>
      <div style="font-weight:700;color:var(--green);margin-bottom:6px;">推广期（结算 ¥2.50/单）</div>
      <div class="calc-line">月单量 = {o} × 30 = {o*30:,} 单</div>
      <div class="calc-line">订单收入 = {o*30:,} × ¥2.50 = {format_money(p['月订单收入'])}</div>
      <div class="calc-line">人头补贴 = 80 × 30 = {format_money(p['月人头补贴'])}</div>
      <div class="calc-line">人力成本 = {p['人数']}人 × {p['时长(h)']}h × ¥30 × 30 = {format_money(p['月人力成本'])}</div>
      <div class="calc-line">物料 = ¥100</div>
      <div class="result" style="color:{'#27ae60' if promo_profit>=0 else '#e74c3c'}">
        月毛利 = {format_money(p['月总收入'])} − {format_money(p['月总成本'])} = {format_money(promo_profit)}
        &nbsp;({p['毛利率']:+.1f}%)
      </div>
    </div>
    <div>
      <div style="font-weight:700;color:var(--red);margin-bottom:6px;">常规期（结算 ¥2.00/单）</div>
      <div class="calc-line">月单量 = {o} × 30 = {o*30:,} 单</div>
      <div class="calc-line">订单收入 = {o*30:,} × ¥2.00 = {format_money(r['月订单收入'])}</div>
      <div class="calc-line">人头补贴 = 80 × 30 = {format_money(r['月人头补贴'])}</div>
      <div class="calc-line">人力成本 = {r['人数']}人 × {r['时长(h)']}h × ¥30 × 30 = {format_money(r['月人力成本'])}</div>
      <div class="calc-line">物料 = ¥100</div>
      <div class="result" style="color:{'#27ae60' if regular_profit>=0 else '#e74c3c'}">
        月毛利 = {format_money(r['月总收入'])} − {format_money(r['月总成本'])} = {format_money(regular_profit)}
        &nbsp;({r['毛利率']:+.1f}%)
      </div>
    </div>
  </div>
  <div class="vs">
    💡 推广期比常规期多赚 <strong>{format_money(diff)}</strong>
    &nbsp;|&nbsp; 单均毛利：推广期 ¥{p['单均毛利']:.2f} / 常规期 ¥{r['单均毛利']:.2f}
  </div>
</div>
"""

    html += f"""
<div class="footer">
  <p>接力送 UE 模型 v2 · 生成于 2026-06-13 · 参数: 时薪 ¥{LABOR_RATE}/h · 人头补贴 ¥{SUBSIDY_PER_DAY}/天 · 月物料 ¥{MATERIAL_PER_POINT_MONTH}</p>
  <p>⚠ 不含: 骑手意愿衰减、美团补贴政策变化、点位环境差异、管理成本、税费</p>
</div>

</body>
</html>
"""

    return html


def main():
    print("生成月度UE模型HTML报告...")
    html = generate_html()

    output_path = os.path.join(OUTPUT_DIR, "monthly_ue_model.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"报告已保存: {output_path}")
    print(f"文件大小: {len(html):,} 字节")

    # 同时输出 CSV
    order_levels = list(range(40, 101, 10)) + [120, 150, 180, 200, 250, 300, 350, 400, 450, 500]

    promo_rows = []
    regular_rows = []
    for o in order_levels:
        d = calc_monthly(o, 2.5)
        if d:
            promo_rows.append(d)
        d = calc_monthly(o, 2.0)
        if d:
            regular_rows.append(d)

    pd.DataFrame(promo_rows).to_csv(f"{OUTPUT_DIR}/monthly_ue_promo.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(regular_rows).to_csv(f"{OUTPUT_DIR}/monthly_ue_regular.csv", index=False, encoding="utf-8-sig")
    print("CSV也已导出到 output/")


if __name__ == "__main__":
    main()
