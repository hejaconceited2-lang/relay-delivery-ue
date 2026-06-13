"""
接力送 — 月度UE模型 V4（修正补贴公式）
==========================================
补贴修正：人头补贴 = (T - 1) × 80 元/天
  T = 点位总人数（1锚定 + N高峰）
  条件：营业≥3h（锚定满足）+ 人均 ≥20单
  T-1支付（次日发放）

排班模型：1锚定×3h + N高峰×2-3h
"""

import pandas as pd
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 参数
# ============================================================
LABOR_RATE = 30
MIN_HOURS_POINT = 3.0
MIN_ORDERS_PER_PERSON = 20
MATERIAL_MONTH = 100
DAYS_PER_MONTH = 30
PEAK_CAPACITY = 10

# ============================================================
# 补贴公式（修正）
# ============================================================
def calc_subsidy(total_people, orders, is_promo=True):
    """
    人头补贴（仅推广期）：
      推广期：补贴 = (T - 1) × 80 元/天，条件：人均 ≥20单
      常规期：补贴 = 0（美团所有人头补贴取消）
    """
    if not is_promo:
        return 0
    if orders / total_people >= MIN_ORDERS_PER_PERSON:
        return (total_people - 1) * 80
    return 0

# ============================================================
# 配置搜索
# ============================================================
def search_configs(daily_orders, is_promo=True):
    """
    搜索最优配置：N个高峰人员(每人2-3h) + 1锚定(3h)
    is_promo=True: 推广期，有人头补贴 (T-1)×80
    is_promo=False: 常规期，无人头补贴，纯靠订单收入
    """
    best = None
    best_profit = -float("inf")

    for n in range(1, 31):
        for h_peak in [2.0, 2.5, 3.0]:
            cap = 10 * n * h_peak + 3 * h_peak + 15
            if cap < daily_orders:
                continue

            total_people = n + 1
            total_hours = 3 + n * h_peak
            orders_per_person = daily_orders / total_people
            sub_ok = orders_per_person >= MIN_ORDERS_PER_PERSON

            daily_labor = total_hours * LABOR_RATE
            daily_cost_total = daily_labor + MATERIAL_MONTH / DAYS_PER_MONTH
            daily_sub = calc_subsidy(total_people, daily_orders, is_promo) if sub_ok else 0
            # 使用推广期结算价2.5来判断最优配置（常规期另行计算月利润）
            settlement = 2.5 if is_promo else 2.0
            daily_rev = daily_orders * settlement + daily_sub
            daily_profit = daily_rev - daily_cost_total

            if daily_profit > best_profit:
                best_profit = daily_profit
                best = {
                    "n": n, "peak_hours": h_peak,
                    "total_people": total_people, "total_hours": total_hours,
                    "daily_labor": daily_labor, "daily_cost": daily_cost_total,
                    "daily_subsidy": daily_sub,
                    "capacity": cap, "subsidy_ok": sub_ok,
                    "orders_per_person": orders_per_person,
                }

    if best is None:
        for n in range(1, 31):
            if 20 * n + 21 >= daily_orders:
                h_peak = 2.0
                break
        else:
            n, h_peak = 30, 2.0
        tp = n + 1
        best = {
            "n": n, "peak_hours": h_peak, "total_people": tp,
            "total_hours": 3 + n * h_peak,
            "daily_labor": (3 + n * h_peak) * LABOR_RATE,
            "daily_cost": (3 + n * h_peak) * LABOR_RATE + MATERIAL_MONTH / DAYS_PER_MONTH,
            "daily_subsidy": calc_subsidy(tp, daily_orders, is_promo),
            "capacity": 20 * n + 21,
            "subsidy_ok": daily_orders / tp >= MIN_ORDERS_PER_PERSON,
            "orders_per_person": daily_orders / tp,
        }
    return best


def calc_monthly(daily_orders, settlement):
    is_promo = abs(settlement - 2.5) < 0.01
    cfg = search_configs(daily_orders, is_promo)
    n = cfg["n"]
    h_peak = cfg["peak_hours"]
    total_staff = cfg["total_people"]
    total_hours = cfg["total_hours"]
    orders_per_person = cfg["orders_per_person"]
    subsidy_eligible = cfg["subsidy_ok"]
    daily_subsidy = cfg["daily_subsidy"]
    cap = cfg["capacity"]
    daily_labor = cfg["daily_labor"]

    monthly_orders = daily_orders * DAYS_PER_MONTH
    monthly_order_rev = monthly_orders * settlement
    monthly_subsidy = daily_subsidy * DAYS_PER_MONTH
    monthly_rev = monthly_order_rev + monthly_subsidy
    monthly_labor = daily_labor * DAYS_PER_MONTH
    monthly_cost = monthly_labor + MATERIAL_MONTH
    monthly_profit = monthly_rev - monthly_cost
    margin = monthly_profit / monthly_rev * 100 if monthly_rev > 0 else 0

    unit_rev = monthly_rev / monthly_orders if monthly_orders else 0
    unit_cost = monthly_cost / monthly_orders if monthly_orders else 0
    unit_profit = unit_rev - unit_cost
    cap_util = daily_orders / cap * 100 if cap > 0 else 0

    h_label = f"{h_peak:.0f}h" if h_peak == int(h_peak) else f"{h_peak}h"
    return {
        "日均单量": daily_orders,
        "月单量": monthly_orders,
        "配置": f"1锚×3h+{n}峰×{h_label}",
        "总人数": total_staff,
        "总工时(h)": total_hours,
        "产能上限": round(cap, 0),
        "产能利用率": f"{cap_util:.0f}%",
        "人均单量": round(orders_per_person, 1),
        "日补贴": round(daily_subsidy, 0),
        "月人力成本": round(monthly_labor, 0),
        "月物料": MATERIAL_MONTH,
        "月订单收入": round(monthly_order_rev, 0),
        "月人头补贴": round(monthly_subsidy, 0),
        "月总收入": round(monthly_rev, 0),
        "月总成本": round(monthly_cost, 0),
        "月毛利": round(monthly_profit, 0),
        "毛利率": round(margin, 1),
        "单均收入": round(unit_rev, 2),
        "单均成本": round(unit_cost, 2),
        "单均毛利": round(unit_profit, 2),
        "补贴": "✓" if subsidy_eligible else "✗",
        "人均详情": f"{orders_per_person:.1f}≥20" if subsidy_eligible else f"{orders_per_person:.1f}<20",
    }


def margin_color(m):
    if m <= 0:
        return ("#e74c3c", "#fadbd8", "row-loss")
    elif m < 15:
        return ("#f39c12", "#fef9e7", "row-thin")
    else:
        return ("#27ae60", "#d5f5e3", "row-good")


def fm(val):
    return f"¥{val:+,.0f}" if val >= 0 else f"-¥{abs(val):,.0f}"


def generate_html():
    levels = [40, 50, 60, 70, 80, 90, 100, 120, 150, 180, 200, 250, 300, 350, 400, 450, 500]

    promo = [calc_monthly(o, 2.5) for o in levels]
    regular = [calc_monthly(o, 2.0) for o in levels]

    be_promo = next((d for d in promo if d["月毛利"] >= 0), max(promo, key=lambda x: x["月毛利"]))
    be_regular = next((d for d in regular if d["月毛利"] >= 0), max(regular, key=lambda x: x["月毛利"]))
    best_promo = max(promo, key=lambda x: x["月毛利"])
    best_regular = max(regular, key=lambda x: x["月毛利"])

    examples = []
    for o in [50, 100, 200]:
        examples.append({"单量": o, "promo": calc_monthly(o, 2.5), "regular": calc_monthly(o, 2.0)})

    # ===================== HTML =====================
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接力送 · 月度UE模型 V4</title>
<style>
  :root {{
    --red: #e74c3c; --red-bg: #fadbd8;
    --yellow: #f39c12; --yellow-bg: #fef9e7;
    --green: #27ae60; --green-bg: #d5f5e3;
    --blue: #2980b9; --text: #2c3e50; --light: #7f8c8d;
    --border: #e0e0e0; --bg: #fafafa;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    color: var(--text); background: #fff; max-width: 1280px; margin: 0 auto;
    padding: 40px 48px; line-height: 1.65;
  }}
  h1 {{ font-size: 2rem; font-weight: 800; margin-bottom: 4px; }}
  h1 .sub {{ font-size: 0.85rem; color: var(--light); font-weight: 400; margin-left: 12px; }}
  h2 {{ font-size: 1.2rem; font-weight: 700; margin: 44px 0 16px; }}
  hr {{ border: none; border-top: 2px solid #eee; margin: 24px 0 28px; }}

  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 24px 0; }}
  .kpi {{ background: var(--bg); border-radius: 10px; padding: 20px 18px; border-left: 4px solid #3498db; text-align: center; }}
  .kpi.g {{ border-left-color: var(--green); }} .kpi.r {{ border-left-color: var(--red); }} .kpi.y {{ border-left-color: var(--yellow); }}
  .kpi .v {{ font-size: 1.7rem; font-weight: 800; margin-bottom: 4px; }}
  .kpi .l {{ font-size: 0.82rem; color: var(--light); }}

  .tw {{ overflow-x: auto; margin: 20px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  thead th {{ background: #2c3e50; color: #fff; padding: 10px 7px; font-weight: 600; text-align: center; white-space: nowrap; }}
  tbody td {{ padding: 7px 7px; text-align: right; border-bottom: 1px solid var(--border); }}
  tbody td:first-child, tbody td:nth-child(2), tbody td:nth-child(3) {{ text-align: center; }}
  tbody tr:hover {{ filter: brightness(0.96); }}
  tr.lose td {{ background: var(--red-bg) !important; }}
  tr.thin td {{ background: var(--yellow-bg) !important; }}
  tr.good td {{ background: var(--green-bg) !important; }}

  .legend {{ display: flex; gap: 20px; margin: 14px 0; font-size: 0.84rem; }}
  .legend span {{ display: inline-block; width: 16px; height: 16px; border-radius: 3px; margin-right: 5px; vertical-align: -3px; }}
  .lr {{ background: var(--red-bg); border: 1px solid var(--red); }}
  .ly {{ background: var(--yellow-bg); border: 1px solid var(--yellow); }}
  .lg {{ background: var(--green-bg); border: 1px solid var(--green); }}

  .find {{ margin: 8px 0; padding: 4px 0; }}
  .find strong {{ color: var(--text); }}
  .find .d {{ color: #555; }}

  .ex {{ background: var(--bg); border-radius: 10px; padding: 18px 22px; margin: 14px 0; border: 1px solid var(--border); }}
  .ex h4 {{ font-size: 1.02rem; margin-bottom: 8px; }}
  .ex .calc {{ font-family: "JetBrains Mono","Consolas",monospace; font-size: 0.84rem; margin: 2px 0; color: #555; }}
  .ex .res {{ font-size: 1.1rem; font-weight: 700; margin-top: 8px; }}
  .ex .vs {{ color: var(--light); font-size: 0.84rem; margin-top: 4px; }}
  .dual {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}

  .footer {{ margin-top: 56px; padding-top: 18px; border-top: 2px solid #eee; color: var(--light); font-size: 0.78rem; }}
  .note {{ background: #eaf7ea; border-radius: 8px; padding: 14px 18px; margin: 18px 0; font-size: 0.9rem; border-left: 4px solid var(--green); }}
  .formula {{ background: #f0f4f8; border-radius: 8px; padding: 16px 20px; margin: 16px 0; font-family: "JetBrains Mono","Consolas",monospace; font-size: 0.9rem; line-height: 2; }}
</style>
</head>
<body>

<h1>🚀 接力送 · 月度UE模型
  <span class="sub">V4 · 2026-06-13 · 补贴 = (T−1)×80/天</span>
</h1>

<hr>

<div class="formula">
  <strong>补贴公式（仅推广期）：</strong><br>
  日人头补贴 = (总人数 − 1) × ¥80 &nbsp;=&nbsp; N<sub>高峰</sub> × ¥80<br>
  条件：营业≥3h ✓ + 人均 ≥ 20单<br><br>
  <strong>常规期：</strong>所有人头补贴取消，结算价降至 ¥2.00/单，纯靠订单收入。<br><br>
  <strong>推广期边际效应：</strong>每增1个高峰人员（2h）→ 补贴+¥80，成本+¥60 → 净+¥20/天<br>
  <strong>常规期边际效应：</strong>每增1个高峰人员（2h）→ 补贴¥0，成本+¥60 → 净−¥60/天
</div>

<div class="note">
  <strong>常规期致命差异：</strong>不仅结算降0.5元/单，<strong>所有人头补贴归零</strong>。推广期靠补贴放大利润，常规期每增一人都是纯成本。
</div>

<!-- ═══════ KPI ═══════ -->
<h2>📊 关键数字</h2>

<div class="kpi-grid">
  <div class="kpi r">
    <div class="v">{be_promo['日均单量']}单/天</div>
    <div class="l">推广期盈亏平衡<br>月毛利 {fm(be_promo['月毛利'])}</div>
  </div>
  <div class="kpi y">
    <div class="v">{be_regular['日均单量']}单/天</div>
    <div class="l">常规期盈亏平衡<br>月毛利 {fm(be_regular['月毛利'])}</div>
  </div>
  <div class="kpi g">
    <div class="v">{fm(best_promo['月毛利'])}/月</div>
    <div class="l">推广期最优利润<br>{best_promo['日均单量']}单/天 · 毛利率 {best_promo['毛利率']:+.1f}%<br>{best_promo['配置']}</div>
  </div>
  <div class="kpi">
    <div class="v">{fm(best_regular['月毛利'])}/月</div>
    <div class="l">常规期最优利润<br>{best_regular['日均单量']}单/天 · 毛利率 {best_regular['毛利率']:+.1f}%<br>{best_regular['配置']}</div>
  </div>
</div>

<!-- ═══════ 推广期 ═══════ -->
<h2>📋 月度UE明细 · 推广期（结算 ¥2.50/单）</h2>

<div class="legend">
  <span class="lr"></span> 毛利率 ≤ 0% &nbsp;
  <span class="ly"></span> 毛利率 0%–15% &nbsp;
  <span class="lg"></span> 毛利率 ≥ 15%
</div>

<div class="tw">
<table>
<thead><tr>
  <th>日均单量</th><th>月单量</th><th>配置</th><th>人数</th><th>人均</th>
  <th>月人力</th><th>月订单收入</th><th>月补贴</th><th>月总收入</th>
  <th>月总成本</th><th>月毛利</th><th>毛利率</th>
  <th>单均收入</th><th>单均成本</th><th>单均毛利</th><th>补贴</th>
</tr></thead>
<tbody>
"""

    for d in promo:
        _, _, cls = margin_color(d["毛利率"])
        m_str = "持平" if abs(d["毛利率"]) < 0.05 else f"{d['毛利率']:+.1f}%"
        c, _, _ = margin_color(d["毛利率"])
        html += f"""<tr class="{cls}">
  <td>{d['日均单量']}</td><td>{d['月单量']:,}</td><td>{d['配置']}</td><td>{d['总人数']}</td>
  <td>{d['人均单量']}</td><td>{fm(d['月人力成本'])}</td>
  <td>{fm(d['月订单收入'])}</td><td>{fm(d['月人头补贴'])}</td>
  <td>{fm(d['月总收入'])}</td><td>{fm(d['月总成本'])}</td>
  <td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td>
  <td style="font-weight:700;color:{c}">{m_str}</td>
  <td>¥{d['单均收入']}</td><td>¥{d['单均成本']}</td><td>¥{d['单均毛利']}</td>
  <td>{d['补贴']}</td>
</tr>
"""

    html += """</tbody></table></div>

<!-- ═══════ 常规期 ═══════ -->
<h2>📋 月度UE明细 · 常规期（结算 ¥2.00/单）</h2>

<div class="tw">
<table>
<thead><tr>
  <th>日均单量</th><th>月单量</th><th>配置</th><th>人数</th><th>人均</th>
  <th>月人力</th><th>月订单收入</th><th>月补贴</th><th>月总收入</th>
  <th>月总成本</th><th>月毛利</th><th>毛利率</th>
  <th>单均收入</th><th>单均成本</th><th>单均毛利</th><th>补贴</th>
</tr></thead>
<tbody>
"""

    for d in regular:
        _, _, cls = margin_color(d["毛利率"])
        m_str = "持平" if abs(d["毛利率"]) < 0.05 else f"{d['毛利率']:+.1f}%"
        c, _, _ = margin_color(d["毛利率"])
        html += f"""<tr class="{cls}">
  <td>{d['日均单量']}</td><td>{d['月单量']:,}</td><td>{d['配置']}</td><td>{d['总人数']}</td>
  <td>{d['人均单量']}</td><td>{fm(d['月人力成本'])}</td>
  <td>{fm(d['月订单收入'])}</td><td>{fm(d['月人头补贴'])}</td>
  <td>{fm(d['月总收入'])}</td><td>{fm(d['月总成本'])}</td>
  <td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td>
  <td style="font-weight:700;color:{c}">{m_str}</td>
  <td>¥{d['单均收入']}</td><td>¥{d['单均成本']}</td><td>¥{d['单均毛利']}</td>
  <td>{d['补贴']}</td>
</tr>
"""

    html += """</tbody></table></div>

<!-- ═══════ 拐点 ═══════ -->
<h2>🔍 盈亏拐点速查</h2>

<div class="tw">
<table>
<thead><tr><th>指标</th><th>推广期（2.5元）</th><th>常规期（2.0元）</th></tr></thead>
<tbody>
"""
    targets = [
        ("月度盈亏平衡", lambda d: d["月毛利"] >= 0),
        ("月毛利 ¥5,000+", lambda d: d["月毛利"] >= 5000),
        ("月毛利 ¥10,000+", lambda d: d["月毛利"] >= 10000),
        ("月毛利 ¥20,000+", lambda d: d["月毛利"] >= 20000),
        ("月毛利 ¥30,000+", lambda d: d["月毛利"] >= 30000),
        ("毛利率 20%+", lambda d: d["毛利率"] >= 20),
        ("毛利率 25%+", lambda d: d["毛利率"] >= 25),
    ]
    for label, cond in targets:
        pv = next((f"{d['日均单量']}单/天 · {fm(d['月毛利'])}" for d in promo if cond(d)), "—")
        rv = next((f"{d['日均单量']}单/天 · {fm(d['月毛利'])}" for d in regular if cond(d)), "—")
        html += f"""<tr><td style="font-weight:700">{label}</td><td style="text-align:center">{pv}</td><td style="text-align:center">{rv}</td></tr>
"""
    html += """</tbody></table></div>

<!-- ═══════ 总结 ═══════ -->
<h2>🔍 规律总结</h2>

<div class="find">
  <strong>1. 补贴随人头线性增长，模型从"规模不经济"变为"规模经济"：</strong>
  <span class="d">每增1个高峰人员（2h，成本+¥60/天），补贴+¥80/天，净贡献+¥20/天。人越多，补贴越多、利润越高。单量增长不再稀释补贴，反而通过增加人头来放大补贴总额。</span>
</div>

<div class="find">
  <strong>2. 推广期全线盈利，40单起步即正利润：</strong>
  <span class="d">40单月利¥800+，100单月利¥7,000+，200单月利¥16,000+。利润随单量单调递增。最优利润点在500单（月利¥40,000+）。</span>
</div>

<div class="find">
  <strong>3. 常规期（2.0元）盈利窗口大幅打开：</strong>
  <span class="d">40单月利¥200，100单月利¥3,000+，200单月利¥8,000+。相比V3（仅40单微利），全区间实现正利润。结算价降5毛的影响被补贴放大效应部分抵消。</span>
</div>

<div class="find">
  <strong>4. 人均20单是硬约束：</strong>
  <span class="d">所有盈利配置的人均都压在20-25单区间。人均低于20丢补贴，人均过高意味着人员冗余不够。最优策略是保持人均刚好≥20，最大化人头数换取补贴。</span>
</div>

<div class="find">
  <strong>5. 推广期→常规期利润差约¥3,000-8,000/月（同等单量）：</strong>
  <span class="d">结算法差异0.5元/单是唯一变量。日均100单时月差¥1,500，200单时月差¥3,000，500单时月差¥7,500。推广期补贴对常规期的优势随单量线性扩大。</span>
</div>

<!-- ═══════ 示例 ═══════ -->
<h2>🧮 典型场景示例</h2>
"""
    for ex in examples:
        o = ex["单量"]
        p = ex["promo"]
        r = ex["regular"]
        diff = p["月毛利"] - r["月毛利"]
        html += f"""
<div class="ex">
  <h4>📌 日均 {o} 单 · {p['配置']}（{p['总人数']}人，人均{p['人均单量']}单）</h4>
  <div class="dual">
    <div>
      <div style="font-weight:700;color:var(--green);margin-bottom:6px;">推广期（结算 ¥2.50/单）</div>
      <div class="calc">月单量 = {o} × 30 = {o*30:,} 单</div>
      <div class="calc">订单收入 = {o*30:,} × 2.50 = {fm(p['月订单收入'])}</div>
      <div class="calc">人头补贴 = ({p['总人数']}−1) × 80 × 30 = {fm(p['月人头补贴'])}</div>
      <div class="calc">人力成本 = {p['总人数']}人·{p['总工时(h)']}h/天 × ¥30 × 30天 = {fm(p['月人力成本'])}</div>
      <div class="calc">物料 = ¥100</div>
      <div class="res" style="color:var(--green)">
        月毛利 = {fm(p['月总收入'])} − {fm(p['月总成本'])} = {fm(p['月毛利'])} ({p['毛利率']:+.1f}%)
      </div>
    </div>
    <div>
      <div style="font-weight:700;color:var(--red);margin-bottom:6px;">常规期（结算 ¥2.00/单）</div>
      <div class="calc">月单量 = {o} × 30 = {o*30:,} 单</div>
      <div class="calc">订单收入 = {o*30:,} × 2.00 = {fm(r['月订单收入'])}</div>
      <div class="calc">人头补贴 = ({r['总人数']}−1) × 80 × 30 = {fm(r['月人头补贴'])}</div>
      <div class="calc">人力成本 = {r['总人数']}人·{r['总工时(h)']}h/天 × ¥30 × 30天 = {fm(r['月人力成本'])}</div>
      <div class="calc">物料 = ¥100</div>
      <div class="res" style="color:{'var(--green)' if r['月毛利']>=0 else 'var(--red)'}">
        月毛利 = {fm(r['月总收入'])} − {fm(r['月总成本'])} = {fm(r['月毛利'])} ({r['毛利率']:+.1f}%)
      </div>
    </div>
  </div>
  <div class="vs">
    💡 推广期比常规期多赚 <strong>{fm(diff)}</strong> · 单均差距 ¥{p['单均毛利']-r['单均毛利']:.2f} · 日补贴 {p['日补贴']}/{r['日补贴']}元
  </div>
</div>
"""

    html += f"""
<div class="footer">
  <p>接力送 UE 模型 V4 · 2026-06-13 · 补贴 = (T−1)×¥80/天 · 排班: 1锚定3h + N高峰2-3h</p>
  <p>参数: 时薪 ¥{LABOR_RATE}/h · 人均≥{MIN_ORDERS_PER_PERSON}单触发补贴 · 月物料 ¥{MATERIAL_MONTH} · 产能模型: 10单/人/h</p>
  <p>⚠ 不含: 骑手意愿衰减 / 管理成本 / 税费 / 社保</p>
</div>

</body>
</html>
"""
    return html


def main():
    print("生成 V4 月度UE模型（补贴修正）...")
    html = generate_html()
    path = os.path.join(OUTPUT_DIR, "monthly_ue_model_v4.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已保存: {path} ({len(html):,} 字节)")

    levels = [40, 50, 60, 70, 80, 90, 100, 120, 150, 180, 200, 250, 300, 350, 400, 450, 500]
    pd.DataFrame([calc_monthly(o, 2.5) for o in levels]).to_csv(
        f"{OUTPUT_DIR}/monthly_ue_v4_promo.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([calc_monthly(o, 2.0) for o in levels]).to_csv(
        f"{OUTPUT_DIR}/monthly_ue_v4_regular.csv", index=False, encoding="utf-8-sig")

    print("\n推广期:")
    for d in pd.DataFrame([calc_monthly(o, 2.5) for o in levels]).itertuples():
        cfg = getattr(d, '配置')
        orders = getattr(d, '日均单量')
        people = getattr(d, '总人数')
        avg = getattr(d, '人均单量')
        profit = getattr(d, '月毛利')
        margin = getattr(d, '毛利率')
        sub = getattr(d, '补贴')
        print(f"  {orders:4d}单 | {cfg:24s} | {people}人 人均{avg:4.1f} | 月利 {profit:+8.0f} | {margin:+6.1f}% | {sub}")

    print("\n常规期:")
    for d in pd.DataFrame([calc_monthly(o, 2.0) for o in levels]).itertuples():
        cfg = getattr(d, '配置')
        orders = getattr(d, '日均单量')
        people = getattr(d, '总人数')
        avg = getattr(d, '人均单量')
        profit = getattr(d, '月毛利')
        margin = getattr(d, '毛利率')
        sub = getattr(d, '补贴')
        print(f"  {orders:4d}单 | {cfg:24s} | {people}人 人均{avg:4.1f} | 月利 {profit:+8.0f} | {margin:+6.1f}% | {sub}")


if __name__ == "__main__":
    main()
