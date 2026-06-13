"""
接力送 — 月度UE模型 V3（修正排班逻辑）
==========================================
修正点：
  1. 人均 ≥20单即可拿补贴（非 >20）
  2. 1人锚定3h（满足考勤）+ N人高峰2h，优先加人非加时
  3. 产能模型：高峰2h全员配送 + 锚定人员1h收尾
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
SUBSIDY_PER_DAY = 80
MIN_HOURS_POINT = 3.0      # 点位营业至少3h
MIN_ORDERS_PER_PERSON = 20  # 人均 ≥20 即可
MATERIAL_MONTH = 100
DAYS_PER_MONTH = 30
PEAK_CAPACITY = 10          # 高峰每人每小时处理单量

# 排班模型：
#   锚定人员：1人 × 3h（楼下指引 + 闲时协助配送）
#   高峰人员：N人 × 2h（纯楼上配送，覆盖午高峰）
#   总人数 = 1 + N
#   总工时 = 3 + 2N


def daily_cost(n_peak):
    """n_peak: 高峰配送人数"""
    total_hours = 3 + 2 * n_peak
    return total_hours * LABOR_RATE + MATERIAL_MONTH / DAYS_PER_MONTH


def search_configs(daily_orders):
    """
    搜索所有可行的人员配置（N个高峰人员，每人2h-2.5h），
    返回利润最高的 (N, peak_hours, subsidy_eligible)。

    产能模型（修正）：
      - 高峰重叠窗口（H小时）：锚定0.8 + N个高峰 = N+0.8 有效配送
        → (N+0.8) × H × 10 单
      - 锚定独守窗口（3-H小时）：0.5 × (3-H) × 10 单
      - 总产能 = 10H(N+0.8) + 5(3-H) = 10NH + 8H + 15 - 5H = 10NH + 3H + 15
      - 当H=2: 20N + 21；当H=2.5: 25N + 22.5

    约束：
      - N ≥ 1（至少1个高峰配送员）
      - H ∈ {2.0, 2.5}（高峰人员可工作2h或2.5h）
      - 产能 ≥ orders
      - 补贴：人均≥20 即 orders/(N+1) ≥ 20
    """
    best = None
    best_profit = -float("inf")

    for n in range(1, 26):  # 1-25个高峰人员
        for h_peak in [2.0, 2.5, 3.0]:  # 优先加人，现有人员可弹性到3h
            cap = 10 * n * h_peak + 3 * h_peak + 15
            if cap < daily_orders:
                continue

            total_hours = 3 + n * h_peak
            total_people = n + 1
            orders_per_person = daily_orders / total_people
            sub_ok = orders_per_person >= MIN_ORDERS_PER_PERSON

            daily_labor = total_hours * LABOR_RATE
            daily_cost_total = daily_labor + MATERIAL_MONTH / DAYS_PER_MONTH
            daily_rev = daily_orders * 2.5 + (SUBSIDY_PER_DAY if sub_ok else 0)
            daily_profit = daily_rev - daily_cost_total

            if daily_profit > best_profit:
                best_profit = daily_profit
                best = {
                    "n": n,
                    "peak_hours": h_peak,
                    "total_people": total_people,
                    "total_hours": total_hours,
                    "daily_labor": daily_labor,
                    "daily_cost": daily_cost_total,
                    "capacity": cap,
                    "subsidy_ok": sub_ok,
                    "orders_per_person": orders_per_person,
                }

    if best is None:
        # fallback: 最小产能N
        for n in range(1, 26):
            if 20 * n + 21 >= daily_orders:
                h_peak = 2.0
                break
        else:
            n, h_peak = 25, 2.0
        total_hours = 3 + n * h_peak
        total_people = n + 1
        best = {
            "n": n, "peak_hours": h_peak, "total_people": total_people,
            "total_hours": total_hours,
            "daily_labor": total_hours * LABOR_RATE,
            "daily_cost": total_hours * LABOR_RATE + MATERIAL_MONTH / DAYS_PER_MONTH,
            "capacity": 20 * n + 21,
            "subsidy_ok": daily_orders / total_people >= MIN_ORDERS_PER_PERSON,
            "orders_per_person": daily_orders / total_people,
        }

    return best


def calc_monthly(daily_orders, settlement):
    """计算月度UE"""
    cfg = search_configs(daily_orders)
    n = cfg["n"]
    h_peak = cfg["peak_hours"]
    total_staff = cfg["total_people"]
    total_hours = cfg["total_hours"]
    daily_labor = cfg["daily_labor"]
    daily_total_cost = cfg["daily_cost"]
    orders_per_person = cfg["orders_per_person"]
    subsidy_eligible = cfg["subsidy_ok"]
    cap = cfg["capacity"]

    monthly_orders = daily_orders * DAYS_PER_MONTH
    monthly_order_rev = monthly_orders * settlement
    monthly_subsidy = SUBSIDY_PER_DAY * DAYS_PER_MONTH if subsidy_eligible else 0
    monthly_rev = monthly_order_rev + monthly_subsidy
    monthly_labor = daily_labor * DAYS_PER_MONTH
    monthly_cost = monthly_labor + MATERIAL_MONTH
    monthly_profit = monthly_rev - monthly_cost
    margin = monthly_profit / monthly_rev * 100 if monthly_rev > 0 else 0

    unit_rev = monthly_rev / monthly_orders if monthly_orders else 0
    unit_cost = monthly_cost / monthly_orders if monthly_orders else 0
    unit_profit = unit_rev - unit_cost

    cap_util = daily_orders / cap * 100 if cap > 0 else 0

    h_label = f"{h_peak}h" if h_peak == int(h_peak) else f"{h_peak}h"
    return {
        "日均单量": daily_orders,
        "月单量": monthly_orders,
        "配置": f"1锚定×3h + {n}高峰×{h_label}",
        "总人数": total_staff,
        "总工时(h)": total_hours,
        "日人力": round(daily_labor, 0),
        "日总成本": round(daily_total_cost, 0),
        "产能上限": round(cap, 0),
        "产能利用率": f"{cap_util:.0f}%",
        "人均单量": round(orders_per_person, 1),
        "月人力成本": round(monthly_labor, 0),
        "月物料": MATERIAL_MONTH,
        "月订单收入": round(monthly_order_rev, 0),
        "月补贴": round(monthly_subsidy, 0),
        "月总收入": round(monthly_rev, 0),
        "月总成本": round(monthly_cost, 0),
        "月毛利": round(monthly_profit, 0),
        "毛利率": round(margin, 1),
        "单均收入": round(unit_rev, 2),
        "单均成本": round(unit_cost, 2),
        "单均毛利": round(unit_profit, 2),
        "补贴": "✓" if subsidy_eligible else "✗",
        "补贴人均": f"{orders_per_person:.1f}≥20" if subsidy_eligible else f"{orders_per_person:.1f}<20",
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

    promo, regular = [], []
    for o in levels:
        promo.append(calc_monthly(o, 2.5))
        regular.append(calc_monthly(o, 2.0))

    # 盈亏平衡点
    be_promo = next((d for d in promo if d["月毛利"] >= 0), max(promo, key=lambda x: x["月毛利"]))
    be_regular = next((d for d in regular if d["月毛利"] >= 0), max(regular, key=lambda x: x["月毛利"]))

    # 最优点（毛利最高）
    best_promo = max(promo, key=lambda x: x["月毛利"])
    best_regular = max(regular, key=lambda x: x["月毛利"])

    # 示例
    examples = []
    for o in [50, 100, 200]:
        examples.append({"单量": o, "promo": calc_monthly(o, 2.5), "regular": calc_monthly(o, 2.0)})

    # ===================== HTML =====================
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接力送 · 月度UE模型 V3</title>
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
    color: var(--text); background: #fff; max-width: 1200px; margin: 0 auto;
    padding: 40px 48px; line-height: 1.65;
  }}
  h1 {{ font-size: 2rem; font-weight: 800; margin-bottom: 4px; }}
  h1 .sub {{ font-size: 0.85rem; color: var(--light); font-weight: 400; margin-left: 12px; }}
  h2 {{ font-size: 1.2rem; font-weight: 700; margin: 44px 0 16px; }}
  hr {{ border: none; border-top: 2px solid #eee; margin: 24px 0 28px; }}

  /* KPI 卡片 */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 24px 0; }}
  .kpi {{ background: var(--bg); border-radius: 10px; padding: 20px 18px; border-left: 4px solid #3498db; text-align: center; }}
  .kpi.g {{ border-left-color: var(--green); }} .kpi.r {{ border-left-color: var(--red); }} .kpi.y {{ border-left-color: var(--yellow); }}
  .kpi .v {{ font-size: 1.7rem; font-weight: 800; margin-bottom: 4px; }}
  .kpi .l {{ font-size: 0.82rem; color: var(--light); }}

  /* 表格 */
  .tw {{ overflow-x: auto; margin: 20px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.86rem; }}
  thead th {{ background: #2c3e50; color: #fff; padding: 10px 7px; font-weight: 600; text-align: center; white-space: nowrap; }}
  tbody td {{ padding: 7px 7px; text-align: right; border-bottom: 1px solid var(--border); }}
  tbody td:first-child, tbody td:nth-child(2), tbody td:nth-child(3) {{ text-align: center; }}
  tbody tr:hover {{ filter: brightness(0.96); }}
  tr.lose td {{ background: var(--red-bg) !important; }}
  tr.thin td {{ background: var(--yellow-bg) !important; }}
  tr.good td {{ background: var(--green-bg) !important; }}

  /* 图例 */
  .legend {{ display: flex; gap: 20px; margin: 14px 0; font-size: 0.84rem; }}
  .legend span {{ display: inline-block; width: 16px; height: 16px; border-radius: 3px; margin-right: 5px; vertical-align: -3px; }}
  .legend .lr {{ background: var(--red-bg); border: 1px solid var(--red); }}
  .legend .ly {{ background: var(--yellow-bg); border: 1px solid var(--yellow); }}
  .legend .lg {{ background: var(--green-bg); border: 1px solid var(--green); }}

  /* 发现 */
  .find {{ margin: 8px 0; padding: 4px 0; }}
  .find strong {{ color: var(--text); }}
  .find .d {{ color: #555; }}

  /* 示例卡片 */
  .ex {{ background: var(--bg); border-radius: 10px; padding: 18px 22px; margin: 14px 0; border: 1px solid var(--border); }}
  .ex h4 {{ font-size: 1.02rem; margin-bottom: 8px; }}
  .ex .calc {{ font-family: "JetBrains Mono","Consolas",monospace; font-size: 0.84rem; margin: 2px 0; color: #555; }}
  .ex .res {{ font-size: 1.1rem; font-weight: 700; margin-top: 8px; }}
  .ex .vs {{ color: var(--light); font-size: 0.84rem; margin-top: 4px; }}
  .dual {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}

  .footer {{ margin-top: 56px; padding-top: 18px; border-top: 2px solid #eee; color: var(--light); font-size: 0.78rem; }}
  .note {{ background: #fff3cd; border-radius: 8px; padding: 14px 18px; margin: 18px 0; font-size: 0.9rem; }}
</style>
</head>
<body>

<h1>🚀 接力送 · 月度UE模型
  <span class="sub">V3 · 2026-06-13 · 1锚定3h + N高峰2h 排班</span>
</h1>

<hr>

<div class="note">
  <strong>排班逻辑：</strong>每点位1名锚定人员（3h，楼下指引+闲时配送，满足考勤） + N名高峰配送员（2h，仅午高峰上楼）。
  扩量时优先加高峰人员（每增1人 +2h工时、+20单产能），而非延长锚定工时。
  <strong>补贴条件：</strong>人均 ≥20单 / 营业≥3h / 至少1人上满3h。
</div>

<!-- ═══════ KPI 卡片 ═══════ -->
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
    <div class="v">{best_promo['日均单量']}单/天</div>
    <div class="l">推广期最优利润点<br>{fm(best_promo['月毛利'])}/月 · 毛利率 {best_promo['毛利率']:+.1f}%</div>
  </div>
  <div class="kpi">
    <div class="v">{fm(best_regular['月毛利'])}</div>
    <div class="l">常规期最优利润点<br>{best_regular['日均单量']}单/天 · 毛利率 {best_regular['毛利率']:+.1f}%</div>
  </div>
</div>

<!-- ═══════ 推广期明细表 ═══════ -->
<h2>📋 月度UE明细表 · 推广期（结算 ¥2.50/单）</h2>

<div class="legend">
  <span class="lr"></span> 毛利率 ≤ 0% &nbsp;
  <span class="ly"></span> 毛利率 0%–15% &nbsp;
  <span class="lg"></span> 毛利率 ≥ 15%
</div>

<div class="tw">
<table>
<thead>
<tr>
  <th>日均单量</th><th>月单量</th><th>配置</th><th>总人数</th>
  <th>人均</th><th>月人力</th>
  <th>月订单收入</th><th>月补贴</th><th>月总收入</th>
  <th>月总成本</th><th>月毛利</th><th>毛利率</th>
  <th>单均收入</th><th>单均成本</th><th>单均毛利</th><th>补贴</th>
</tr>
</thead>
<tbody>
"""

    for d in promo:
        _, _, cls = margin_color(d["毛利率"])
        m_str = "打平" if abs(d["毛利率"]) < 0.05 else f"{d['毛利率']:+.1f}%"
        c, _, _ = margin_color(d["毛利率"])
        html += f"""<tr class="{cls}">
  <td>{d['日均单量']}</td><td>{d['月单量']:,}</td><td>{d['配置']}</td><td>{d['总人数']}</td>
  <td>{d['人均单量']}</td><td>{fm(d['月人力成本'])}</td>
  <td>{fm(d['月订单收入'])}</td><td>{fm(d['月补贴'])}</td>
  <td>{fm(d['月总收入'])}</td><td>{fm(d['月总成本'])}</td>
  <td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td>
  <td style="font-weight:700;color:{c}">{m_str}</td>
  <td>¥{d['单均收入']}</td><td>¥{d['单均成本']}</td><td>¥{d['单均毛利']}</td>
  <td>{d['补贴']}</td>
</tr>
"""

    html += """</tbody></table></div>

<!-- ═══════ 常规期明细表 ═══════ -->
<h2>📋 月度UE明细表 · 常规期（结算 ¥2.00/单）</h2>

<div class="tw">
<table>
<thead>
<tr>
  <th>日均单量</th><th>月单量</th><th>配置</th><th>总人数</th>
  <th>人均</th><th>月人力</th>
  <th>月订单收入</th><th>月补贴</th><th>月总收入</th>
  <th>月总成本</th><th>月毛利</th><th>毛利率</th>
  <th>单均收入</th><th>单均成本</th><th>单均毛利</th><th>补贴</th>
</tr>
</thead>
<tbody>
"""

    for d in regular:
        _, _, cls = margin_color(d["毛利率"])
        m_str = "打平" if abs(d["毛利率"]) < 0.05 else f"{d['毛利率']:+.1f}%"
        c, _, _ = margin_color(d["毛利率"])
        html += f"""<tr class="{cls}">
  <td>{d['日均单量']}</td><td>{d['月单量']:,}</td><td>{d['配置']}</td><td>{d['总人数']}</td>
  <td>{d['人均单量']}</td><td>{fm(d['月人力成本'])}</td>
  <td>{fm(d['月订单收入'])}</td><td>{fm(d['月补贴'])}</td>
  <td>{fm(d['月总收入'])}</td><td>{fm(d['月总成本'])}</td>
  <td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td>
  <td style="font-weight:700;color:{c}">{m_str}</td>
  <td>¥{d['单均收入']}</td><td>¥{d['单均成本']}</td><td>¥{d['单均毛利']}</td>
  <td>{d['补贴']}</td>
</tr>
"""

    html += """</tbody></table></div>

<!-- ═══════ 盈亏拐点 ═══════ -->
<h2>🔍 盈亏拐点速查</h2>

<div class="tw">
<table>
<thead><tr><th>指标</th><th>推广期（2.5元）</th><th>常规期（2.0元）</th></tr></thead>
<tbody>
"""

    targets = [
        ("月度盈亏平衡", lambda d: d["月毛利"] >= 0),
        ("月毛利 ¥2,000+", lambda d: d["月毛利"] >= 2000),
        ("月毛利 ¥5,000+", lambda d: d["月毛利"] >= 5000),
        ("月毛利 ¥10,000+", lambda d: d["月毛利"] >= 10000),
        ("月毛利 ¥15,000+", lambda d: d["月毛利"] >= 15000),
        ("毛利率 15%+", lambda d: d["毛利率"] >= 15),
        ("毛利率 25%+", lambda d: d["毛利率"] >= 25),
    ]

    for label, cond in targets:
        pv = next((f"{d['日均单量']}单/天 · {fm(d['月毛利'])}" for d in promo if cond(d)), "未达到")
        rv = next((f"{d['日均单量']}单/天 · {fm(d['月毛利'])}" for d in regular if cond(d)), "未达到")
        html += f"""<tr><td style="font-weight:700">{label}</td><td style="text-align:center">{pv}</td><td style="text-align:center">{rv}</td></tr>
"""

    html += """</tbody></table></div>

<!-- ═══════ 总结 ═══════ -->
<h2>🔍 规律总结</h2>

<div class="find">
  <strong>1. 40单即可盈利（推广期）：</strong>
  <span class="d">1锚定3h + 1高峰2h，人均20单刚好触及补贴线。月利约¥260，单均¥0.22。</span>
</div>

<div class="find">
  <strong>2. 最优利润区间在50–80单：</strong>
  <span class="d">2人配置下人均25–40单，补贴稳固。推广期月利¥600–1,700，毛利率12–21%。此区间单均毛利最高（¥0.40–0.70），是盈利质量最好的阶段。</span>
</div>

<div class="find">
  <strong>3. 超过100单后利润反而递减：</strong>
  <span class="d">必须加人维持产能，人均被压低到刚好20单。每增1个高峰人员（+2h），日成本+¥60，但日补贴固定¥80。多出来的人力成本吃掉订单收入增长。</span>
</div>

<div class="find">
  <strong>4. 常规期（2.0元）利润极薄：</strong>
  <span class="d">40单打平、50–60单月利仅¥150–450。超过80单重新进入亏损区。结算价降5毛使整个盈利窗口收窄到40–80单区间。</span>
</div>

<div class="find">
  <strong>5. 规模化前提：提高结算价或降低人力成本：</strong>
  <span class="d">当前模型下，日单300+即使完美排班仍月亏¥2,000+。要么结算价回到2.5元以上，要么人力成本降至¥25/h以下，否则无法规模化。</span>
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
      <div class="calc">人头补贴 = 80 × 30 = {fm(2400)}</div>
      <div class="calc">人力成本 = {p['总人数']}人·{p['总工时(h)']}h/天 × ¥30 × 30天 = {fm(p['月人力成本'])}</div>
      <div class="calc">物料 = ¥100</div>
      <div class="res" style="color:{'#27ae60' if p['月毛利']>=0 else '#e74c3c'}">
        月毛利 = {fm(p['月总收入'])} − {fm(p['月总成本'])} = {fm(p['月毛利'])} ({p['毛利率']:+.1f}%)
      </div>
    </div>
    <div>
      <div style="font-weight:700;color:var(--red);margin-bottom:6px;">常规期（结算 ¥2.00/单）</div>
      <div class="calc">月单量 = {o} × 30 = {o*30:,} 单</div>
      <div class="calc">订单收入 = {o*30:,} × 2.00 = {fm(r['月订单收入'])}</div>
      <div class="calc">人头补贴 = 80 × 30 = {fm(2400)}</div>
      <div class="calc">人力成本 = {r['总人数']}人·{r['总工时(h)']}h/天 × ¥30 × 30天 = {fm(r['月人力成本'])}</div>
      <div class="calc">物料 = ¥100</div>
      <div class="res" style="color:{'#27ae60' if r['月毛利']>=0 else '#e74c3c'}">
        月毛利 = {fm(r['月总收入'])} − {fm(r['月总成本'])} = {fm(r['月毛利'])} ({r['毛利率']:+.1f}%)
      </div>
    </div>
  </div>
  <div class="vs">
    💡 推广期比常规期多赚 <strong>{fm(diff)}</strong> · 单均差距 ¥{p['单均毛利']-r['单均毛利']:.2f}
    · 配置: {p['配置']}
  </div>
</div>
"""

    html += f"""
<div class="footer">
  <p>接力送 UE 模型 V3 · 2026-06-13 · 排班: 1锚定3h + N高峰2h</p>
  <p>参数: 时薪 ¥{LABOR_RATE}/h · 人头补贴 ¥{SUBSIDY_PER_DAY}/天 · 月物料 ¥{MATERIAL_MONTH} · 人均≥{MIN_ORDERS_PER_PERSON}单触发补贴</p>
  <p>⚠ 不含: 骑手意愿衰减 / 管理成本 / 税费 / 社保 / 点位环境差异</p>
</div>

</body>
</html>
"""

    return html


def main():
    print("生成 V3 月度UE模型...")
    html = generate_html()

    path = os.path.join(OUTPUT_DIR, "monthly_ue_model_v3.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已保存: {path} ({len(html):,} 字节)")

    # CSV
    levels = [40, 50, 60, 70, 80, 90, 100, 120, 150, 180, 200, 250, 300, 350, 400, 450, 500]
    pd.DataFrame([calc_monthly(o, 2.5) for o in levels]).to_csv(
        f"{OUTPUT_DIR}/monthly_ue_v3_promo.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([calc_monthly(o, 2.0) for o in levels]).to_csv(
        f"{OUTPUT_DIR}/monthly_ue_v3_regular.csv", index=False, encoding="utf-8-sig")

    # 打印摘要
    print("\n推广期月度UE摘要:")
    for d in pd.DataFrame([calc_monthly(o, 2.5) for o in levels]).itertuples():
        print(f"  {getattr(d,'日均单量'):4d}单 | {getattr(d,'配置'):28s} | 人均{getattr(d,'人均单量'):5.1f} | 月毛利 {getattr(d,'月毛利'):+8.0f} | 毛利率 {getattr(d,'毛利率'):+6.1f}% | {getattr(d,'补贴')}")

    print("\n常规期月度UE摘要:")
    for d in pd.DataFrame([calc_monthly(o, 2.0) for o in levels]).itertuples():
        print(f"  {getattr(d,'日均单量'):4d}单 | {getattr(d,'配置'):28s} | 人均{getattr(d,'人均单量'):5.1f} | 月毛利 {getattr(d,'月毛利'):+8.0f} | 毛利率 {getattr(d,'毛利率'):+6.1f}% | {getattr(d,'补贴')}")


if __name__ == "__main__":
    main()
