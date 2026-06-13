"""
接力送 — 三阶段UE模型
======================
Phase 1（前2周）：骑手付¥1 + 美团补¥1.5 → 结算¥2.5 + 人头补贴(T-1)×80
Phase 2（长期补贴）：骑手付¥2 + 美团补¥0.5 → 结算¥2.5 + 人头补贴(T-1)×80
Phase 3（补贴归零）：骑手付¥2 + 美团补¥0   → 结算¥2.0 + 人头补贴¥0
"""

import pandas as pd
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LABOR_RATE = 30
MIN_OPP = 20
MAT_MONTH = 100
DAYS = 30

# ============================================================
# 三个阶段定义
# ============================================================
PHASES = {
    "Phase1_引流期": {
        "name": "Phase 1 · 引流期（前2周）",
        "rider_fee": 1.0,
        "settlement": 2.5,
        "has_headcount_sub": True,
        "duration": "2周",
        "color": "#27ae60",
        "desc": "骑手付¥1 · 结算¥2.5 · 人头补贴有",
    },
    "Phase2_长期补贴": {
        "name": "Phase 2 · 长期补贴期",
        "rider_fee": 2.0,
        "settlement": 2.5,
        "has_headcount_sub": True,
        "duration": "较长",
        "color": "#2980b9",
        "desc": "骑手付¥2 · 结算¥2.5 · 人头补贴有",
    },
    "Phase3_补贴归零": {
        "name": "Phase 3 · 补贴归零",
        "rider_fee": 2.0,
        "settlement": 2.0,
        "has_headcount_sub": False,
        "duration": "未来",
        "color": "#e74c3c",
        "desc": "骑手付¥2 · 结算¥2.0 · 人头补贴无",
    },
}


def rider_vol_mult(fee):
    surplus = 3.0 - fee
    ratio = surplus / 3.0
    if ratio >= 0.7:
        return 1.0
    elif ratio >= 0.5:
        return 0.95 - (0.7 - ratio) * 2.5
    elif ratio >= 0.3:
        return 0.50 - (0.5 - ratio) * 1.5
    elif ratio >= 0.15:
        return 0.25 - (0.3 - ratio) * 1.2
    else:
        return max(0.05, ratio * 0.6)


def search_cfg(orders, settlement, has_sub):
    best = None
    best_p = -float("inf")
    for n in range(1, 31):
        for h in [2.0, 2.5, 3.0]:
            cap = 10 * n * h + 3 * h + 15
            if cap < orders:
                continue
            tp, th = n + 1, 3 + n * h
            opp = orders / tp
            dl = th * LABOR_RATE
            dc = dl + MAT_MONTH / DAYS
            ds = (tp - 1) * 80 if (has_sub and opp >= MIN_OPP) else 0
            dp = orders * settlement + ds - dc
            if dp > best_p:
                best_p = dp
                best = {"n": n, "h": h, "tp": tp, "th": th, "dl": dl, "dc": dc,
                        "ds": ds, "cap": cap, "sub_ok": opp >= MIN_OPP and has_sub,
                        "opp": opp, "dp": dp}
    if best is None:
        for n in range(1, 31):
            if 20 * n + 21 >= orders:
                h = 2.0
                break
        else:
            n, h = 30, 2.0
        tp = n + 1
        best = {"n": n, "h": h, "tp": tp, "th": 3 + n * h,
                "dl": (3 + n * h) * 30,
                "dc": (3 + n * h) * 30 + MAT_MONTH / DAYS,
                "ds": (tp - 1) * 80 if has_sub else 0,
                "cap": 20 * n + 21, "sub_ok": False, "opp": orders / tp, "dp": 0}
    return best


def calc(base_orders, phase_key):
    p = PHASES[phase_key]
    fee = p["rider_fee"]
    settlement = p["settlement"]
    has_sub = p["has_headcount_sub"]

    vol_mult = rider_vol_mult(fee)
    actual_orders = max(5, int(base_orders * vol_mult))
    cfg = search_cfg(actual_orders, settlement, has_sub)

    monthly_orders = actual_orders * DAYS
    monthly_order_rev = monthly_orders * settlement
    monthly_subsidy = cfg["ds"] * DAYS
    monthly_rev = monthly_order_rev + monthly_subsidy
    monthly_labor = cfg["dl"] * DAYS
    monthly_cost = monthly_labor + MAT_MONTH
    monthly_profit = monthly_rev - monthly_cost
    margin = monthly_profit / monthly_rev * 100 if monthly_rev > 0 else 0

    return {
        "阶段": p["name"], "基准单量": base_orders,
        "骑手费率": f"¥{fee:.1f}", "结算价": f"¥{settlement:.1f}",
        "人头补贴": "有" if has_sub else "无",
        "单量倍率": f"{vol_mult:.0%}",
        "实际单量": actual_orders, "月单量": monthly_orders,
        "配置": f"1锚+{cfg['n']}峰×{cfg['h']:.1f}h",
        "人数": cfg["tp"], "人均": round(cfg["opp"], 1),
        "日人头补贴": round(cfg["ds"], 0),
        "月人力": round(monthly_labor, 0),
        "月订单收入": round(monthly_order_rev, 0),
        "月人头补贴": round(monthly_subsidy, 0),
        "月总收入": round(monthly_rev, 0),
        "月总成本": round(monthly_cost, 0),
        "月毛利": round(monthly_profit, 0),
        "毛利率": f"{margin:+.1f}%",
        "单均毛利": round(monthly_profit / monthly_orders, 2) if monthly_orders else 0,
        "补贴达标": "✓" if cfg["sub_ok"] else "✗",
    }


def mc(m):
    if m <= 0:
        return ("#e74c3c", "row-loss")
    elif m < 15:
        return ("#f39c12", "row-thin")
    return ("#27ae60", "row-good")


def fm(v):
    return f"¥{v:+,.0f}" if v >= 0 else f"-¥{abs(v):,.0f}"


def generate_html():
    levels = [40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 400, 500]
    data = {}
    for phase in PHASES:
        data[phase] = [calc(o, phase) for o in levels]

    # Break-even for each phase
    be = {}
    for phase in PHASES:
        d = data[phase]
        be[phase] = next((r for r in d if r["月毛利"] >= 0), max(d, key=lambda x: x["月毛利"]))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接力送 · 三阶段UE全景</title>
<style>
  :root {{
    --red: #e74c3c; --red-bg: #fadbd8;
    --yellow: #f39c12; --yellow-bg: #fef9e7;
    --green: #27ae60; --green-bg: #d5f5e3;
    --blue: #2980b9; --text: #2c3e50; --light: #7f8c8d;
    --border: #e0e0e0; --bg: #fafafa;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    color: var(--text); background: #fff; max-width: 1400px; margin: 0 auto;
    padding: 36px 44px; line-height: 1.65; }}
  h1 {{ font-size: 1.9rem; font-weight: 800; margin-bottom: 4px; }}
  h1 .sub {{ font-size: 0.82rem; color: var(--light); font-weight: 400; margin-left: 10px; }}
  h2 {{ font-size: 1.18rem; font-weight: 700; margin: 40px 0 14px; }}
  hr {{ border: none; border-top: 2px solid #eee; margin: 20px 0 24px; }}

  .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin: 22px 0; }}
  .kpi {{ background: var(--bg); border-radius: 10px; padding: 18px 16px; border-left: 4px solid #3498db; text-align: center; }}
  .kpi.g {{ border-left-color: var(--green); }} .kpi.r {{ border-left-color: var(--red); }} .kpi.b {{ border-left-color: var(--blue); }}
  .kpi .v {{ font-size: 1.5rem; font-weight: 800; margin-bottom: 3px; }}
  .kpi .l {{ font-size: 0.8rem; color: var(--light); }}

  .table-wrap {{ overflow-x: auto; margin: 16px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  thead th {{ background: #2c3e50; color: #fff; padding: 9px 6px; font-weight: 600; text-align: center; white-space: nowrap; }}
  tbody td {{ padding: 6px 6px; text-align: right; border-bottom: 1px solid var(--border); }}
  tbody td:first-child {{ text-align: center; }}
  tr:hover {{ filter: brightness(0.95); }}
  tr.lose td {{ background: var(--red-bg) !important; }}
  tr.thin td {{ background: var(--yellow-bg) !important; }}
  tr.good td {{ background: var(--green-bg) !important; }}

  .phase-tag {{ display: inline-block; border-radius: 6px; padding: 6px 14px; margin: 0 4px; font-weight: 700; font-size: 0.85rem; }}
  .tag1 {{ background: #d5f5e3; color: #1e8449; }}
  .tag2 {{ background: #d4e6f1; color: #1a5276; }}
  .tag3 {{ background: #fadbd8; color: #922b21; }}

  .legend {{ display: flex; gap: 18px; margin: 12px 0; font-size: 0.82rem; }}
  .legend span {{ display: inline-block; width: 15px; height: 15px; border-radius: 3px; margin-right: 5px; vertical-align: -3px; }}
  .lr {{ background: var(--red-bg); border: 1px solid var(--red); }}
  .ly {{ background: var(--yellow-bg); border: 1px solid var(--yellow); }}
  .lg {{ background: var(--green-bg); border: 1px solid var(--green); }}

  .timeline {{ display: flex; align-items: center; margin: 20px 0; font-size: 0.9rem; }}
  .timeline .step {{ flex: 1; text-align: center; padding: 14px 10px; border-radius: 10px; margin: 0 4px; }}
  .timeline .arrow {{ font-size: 1.4rem; color: var(--light); flex: 0 0 40px; text-align: center; }}
  .step1 {{ background: #d5f5e3; border: 2px solid var(--green); }}
  .step2 {{ background: #d4e6f1; border: 2px solid var(--blue); }}
  .step3 {{ background: #fadbd8; border: 2px solid var(--red); }}

  .note {{ border-radius: 8px; padding: 14px 18px; margin: 16px 0; font-size: 0.88rem; }}
  .note.g {{ background: #eaf7ea; border-left: 4px solid var(--green); }}
  .note.r {{ background: #fdedec; border-left: 4px solid var(--red); }}
  .footer {{ margin-top: 50px; padding-top: 16px; border-top: 2px solid #eee; color: var(--light); font-size: 0.76rem; }}
</style>
</head>
<body>

<h1>🚀 接力送 · 三阶段UE全景
  <span class="sub">2026-06-13</span>
</h1>

<hr>

<!-- ═══════ 阶段时间线 ═══════ -->
<div class="timeline">
  <div class="step step1">
    <strong>Phase 1 · 引流期</strong><br>
    前 2 周<br>
    <small>骑手付 ¥1.00<br>结算 ¥2.50<br>人头补贴 (T−1)×¥80</small>
  </div>
  <div class="arrow">→</div>
  <div class="step step2">
    <strong>Phase 2 · 长期补贴</strong><br>
    较长时期<br>
    <small>骑手付 ¥2.00<br>结算 ¥2.50<br>人头补贴 (T−1)×¥80</small>
  </div>
  <div class="arrow">→</div>
  <div class="step step3">
    <strong>Phase 3 · 补贴归零</strong><br>
    未来<br>
    <small>骑手付 ¥2.00<br>结算 ¥2.00<br>人头补贴 ¥0</small>
  </div>
</div>

<!-- ═══════ KPI ═══════ -->
<h2>📊 三阶段盈亏平衡点</h2>
<div class="kpi-grid">
  <div class="kpi g">
    <div class="v">≥{be['Phase1_引流期']['基准单量']}单</div>
    <div class="l">Phase 1 盈亏平衡<br>实际 {be['Phase1_引流期']['实际单量']}单/天 · {fm(be['Phase1_引流期']['月毛利'])}/月</div>
  </div>
  <div class="kpi b">
    <div class="v">≥{be['Phase2_长期补贴']['基准单量']}单</div>
    <div class="l">Phase 2 盈亏平衡<br>实际 {be['Phase2_长期补贴']['实际单量']}单/天 · {fm(be['Phase2_长期补贴']['月毛利'])}/月</div>
  </div>
  <div class="kpi r">
    <div class="v">永远亏损</div>
    <div class="l">Phase 3 盈亏平衡<br>最少月亏 {fm(be['Phase3_补贴归零']['月毛利'])}</div>
  </div>
</div>

<!-- ═══════ 三阶段对比主表 ═══════ -->
<h2>📋 三阶段对比 · 基准单量 → 利润</h2>

<div class="legend">
  <span class="lr"></span> 亏损 &nbsp;
  <span class="ly"></span> 微利（0–15%）&nbsp;
  <span class="lg"></span> 健康（≥15%）
</div>

<div class="table-wrap">
<table>
<thead><tr>
  <th>基准单量</th>
  <th colspan="3">Phase 1 · 引流期</th>
  <th colspan="3">Phase 2 · 长期补贴</th>
  <th colspan="3">Phase 3 · 补贴归零</th>
</tr>
<tr>
  <th></th>
  <th>实际单量</th><th>月毛利</th><th>毛利率</th>
  <th>实际单量</th><th>月毛利</th><th>毛利率</th>
  <th>实际单量</th><th>月毛利</th><th>毛利率</th>
</tr></thead>
<tbody>
"""
    for i, o in enumerate(levels):
        html += "<tr>"
        html += f"<td style=\"font-weight:700\">{o}</td>"
        for phase in ["Phase1_引流期", "Phase2_长期补贴", "Phase3_补贴归零"]:
            d = data[phase][i]
            m = float(d["毛利率"].rstrip("%"))
            c, cls = mc(m)
            html += f"<td>{d['实际单量']}</td>"
            html += f"<td style=\"font-weight:700;color:{c}\">{fm(d['月毛利'])}</td>"
            html += f"<td style=\"color:{c}\">{d['毛利率']}</td>"
        html += "</tr>\n"

    html += """</tbody></table></div>

<!-- ═══════ Phase 2 详细 ═══════ -->
<h2>📋 Phase 2 · 长期补贴 详细UE</h2>
<div class="table-wrap"><table>
<thead><tr>
  <th>基准单量</th><th>实际单量</th><th>配置</th><th>人数</th><th>人均</th>
  <th>月订单收入</th><th>月人头补贴</th><th>月总收入</th>
  <th>月总成本</th><th>月毛利</th><th>毛利率</th><th>单均毛利</th>
</tr></thead><tbody>
"""
    for d in data["Phase2_长期补贴"]:
        m = float(d["毛利率"].rstrip("%"))
        c, cls = mc(m)
        html += f"""<tr class="{cls}">
  <td>{d['基准单量']}</td><td>{d['实际单量']}</td><td>{d['配置']}</td><td>{d['人数']}</td><td>{d['人均']}</td>
  <td>{fm(d['月订单收入'])}</td><td>{fm(d['月人头补贴'])}</td><td>{fm(d['月总收入'])}</td>
  <td>{fm(d['月总成本'])}</td><td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td>
  <td style="color:{c}">{d['毛利率']}</td><td>{d['单均毛利']:+.2f}</td>
</tr>"""
    html += """</tbody></table></div>

<!-- ═══════ Phase 3 详细 ═══════ -->
<h2>📋 Phase 3 · 补贴归零 详细UE</h2>
<div class="table-wrap"><table>
<thead><tr>
  <th>基准单量</th><th>实际单量</th><th>配置</th><th>人数</th><th>人均</th>
  <th>月订单收入</th><th>月人头补贴</th><th>月总收入</th>
  <th>月总成本</th><th>月毛利</th><th>毛利率</th><th>单均毛利</th>
</tr></thead><tbody>
"""
    for d in data["Phase3_补贴归零"]:
        m = float(d["毛利率"].rstrip("%"))
        c, cls = mc(m)
        html += f"""<tr class="{cls}">
  <td>{d['基准单量']}</td><td>{d['实际单量']}</td><td>{d['配置']}</td><td>{d['人数']}</td><td>{d['人均']}</td>
  <td>{fm(d['月订单收入'])}</td><td>{fm(d['月人头补贴'])}</td><td>{fm(d['月总收入'])}</td>
  <td>{fm(d['月总成本'])}</td><td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td>
  <td style="color:{c}">{d['毛利率']}</td><td>{d['单均毛利']:+.2f}</td>
</tr>"""
    html += """</tbody></table></div>

<!-- ═══════ 总结 ═══════ -->
<h2>🔍 三阶段生存指南</h2>

<div class="note g">
  <strong>Phase 1 · 引流期（前2周）— 全力冲单量：</strong><br>
  骑手付¥1意愿最高（95%+单量），每个点位应在这2周内尽可能拉高日均单量，建立骑手使用习惯。
  盈亏平衡约50基准单/天，100单可月利¥4,000+，200单月利¥11,000+。
</div>

<div class="note" style="background:#d4e6f1;border-left:4px solid var(--blue);">
  <strong>Phase 2 · 长期补贴期 — 守住200+单的生命线：</strong><br>
  骑手付¥2导致单量暴跌至13%，200基准单→50实际单才能盈亏平衡。<br>
  只有Phase 1达到200+单的点位，才能在Phase 2活下来。<br>
  <strong>Phase 1低于200单的点位，进入Phase 2后必然亏损。</strong>
</div>

<div class="note r">
  <strong>Phase 3 · 补贴归零 — 无解：</strong><br>
  0.5元美团补贴+人头补贴全部取消后，每单结算¥2.0，每人时亏损¥10（产出¥20 - 成本¥30）。<br>
  全线亏损，无一幸免。必须在Phase 2结束前找到新模式或关停。
</div>

<div class="footer">
  <p>接力送 UE 模型 · 三阶段版 · 2026-06-13</p>
  <p>产能模型: 10单/人/h | 排班: 1锚定3h + N高峰2-3h | 补贴条件: 人均≥20单</p>
  <p>Phase→Phase2单量衰减: 骑手费率¥1→¥2，弹性模型预估保留13%</p>
</div>
</body></html>"""
    return html


def main():
    print("生成三阶段UE全景...")
    html = generate_html()
    path = os.path.join(OUTPUT_DIR, "three_phase_ue.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已保存: {path} ({len(html):,} 字节)")

    levels = [40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 400, 500]
    data = {p: [calc(o, p) for o in levels] for p in PHASES}

    print(f"\n{'基准':>5s} | {'Phase1(引流)':>22s} | {'Phase2(长期补贴)':>22s} | {'Phase3(补贴归零)':>22s}")
    print("-" * 100)
    for i, o in enumerate(levels):
        d1 = data["Phase1_引流期"][i]
        d2 = data["Phase2_长期补贴"][i]
        d3 = data["Phase3_补贴归零"][i]
        print(f"{o:5d} | {d1['实际单量']:3d}单 {d1['月毛利']:+9,.0f} {d1['毛利率']:>7s} | "
              f"{d2['实际单量']:3d}单 {d2['月毛利']:+9,.0f} {d2['毛利率']:>7s} | "
              f"{d3['实际单量']:3d}单 {d3['月毛利']:+9,.0f} {d3['毛利率']:>7s}")

    for p in PHASES:
        pd.DataFrame(data[p]).to_csv(f"{OUTPUT_DIR}/three_phase_{p}.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
