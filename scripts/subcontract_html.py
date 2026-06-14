"""
接力送 · 分包分润页面（合作方面向）
=================================
生成简洁 HTML，匹配 simple_ue.html 风格。
纯表格 + 说明，无 JS 依赖，可直接部署 GitHub Pages。
"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════
# 参数（与 simple_ue.py 一致）
# ═══════════════════════════════════════════════════
RATE = 30
MAT = 100
DAYS = 30
MIN_OPP = 20
CAP = 12
ANCHOR_H = 3.0
SPLIT = 0.5  # 五五分润

PHASES = {
    "Phase1": {"rider_fee": 1.0, "settlement": 2.5, "subsidy": True,  "label": "Phase 1 · 引流期",   "duration": "前2周"},
    "Phase2": {"rider_fee": 2.0, "settlement": 2.5, "subsidy": True,  "label": "Phase 2 · 常规期",   "duration": "长期"},
}

VOLUMES = [20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 180, 200, 250, 300, 400, 500]


def rider_vol_mult(fee):
    surplus = 3.0 - fee
    ratio = surplus / 3.0
    if ratio >= 0.7:   return 1.0
    elif ratio >= 0.5: return 0.95 - (0.7 - ratio) * 2.5
    elif ratio >= 0.3: return 0.50 - (0.5 - ratio) * 1.5
    elif ratio >= 0.15: return 0.25 - (0.3 - ratio) * 1.2
    else:              return max(0.05, ratio * 0.6)


def fmt_cfg(n, h):
    h_str = f"{h:.1f}h" if h != int(h) else f"{h:.0f}h"
    return f"3h×1人 + {h_str}×{n}人"


def optimal_staffing(daily_orders):
    """找最省成本的可行排班: 返回 (n_peak, peak_h, total_people, total_hours, opp, subsidy_ok)"""
    best, best_cost = None, float("inf")
    for n in range(0, 15):
        for h in [2.0, 2.5, 3.0]:
            total_h = ANCHOR_H + n * h
            if CAP * total_h < daily_orders:
                continue
            cost = total_h * RATE
            if cost < best_cost:
                best_cost = cost
                tp = 1 + n
                opp = daily_orders / tp
                best = (n, h, tp, total_h, round(opp, 1), opp >= MIN_OPP)
    if best is None:
        for n in range(0, 31):
            if 20 * n + 21 >= daily_orders:
                tp = 1 + n
                total_h = ANCHOR_H + n * 2.0
                opp = daily_orders / tp
                return n, 2.0, tp, total_h, round(opp, 1), opp >= MIN_OPP
        return 30, 2.0, 31, ANCHOR_H + 60, round(daily_orders / 31, 1), False
    return best


def calc(daily_orders, phase_key):
    """计算分润，返回月度数据"""
    p = PHASES[phase_key]
    actual = max(5, int(daily_orders * rider_vol_mult(p["rider_fee"])))
    n, h, tp, th, opp, sub_ok = optimal_staffing(actual)

    daily_sub = (tp - 1) * 80 if (p["subsidy"] and sub_ok) else 0
    daily_rev = actual * (p["settlement"] + p["rider_fee"]) + daily_sub
    daily_labor = th * RATE
    daily_profit = daily_rev - daily_labor - MAT / DAYS

    monthly_rev = daily_rev * DAYS
    monthly_labor = daily_labor * DAYS
    monthly_profit = daily_profit * DAYS
    monthly_margin = monthly_profit / monthly_rev * 100 if monthly_rev > 0 else 0

    return {
        "actual": actual, "cfg": fmt_cfg(n, h), "tp": tp, "opp": opp,
        "monthly_settlement": round(actual * p["settlement"] * DAYS, 0),
        "monthly_rider_fee": round(actual * p["rider_fee"] * DAYS, 0),
        "monthly_subsidy": round(daily_sub * DAYS, 0),
        "monthly_revenue": round(monthly_rev, 0),
        "monthly_labor": round(monthly_labor, 0),
        "monthly_profit": round(monthly_profit, 0),
        "monthly_margin": round(monthly_margin, 1),
        "operator_share": round(monthly_profit * SPLIT, 0),
        "platform_share": round(monthly_profit * SPLIT, 0),
        "per_order_op": round(daily_profit * SPLIT / actual, 2) if actual else 0,
        "per_order_total": round(daily_profit / actual, 2) if actual else 0,
        "daily_subsidy": daily_sub,
        "subsidy_ok": sub_ok and p["subsidy"],
    }


def fm(v):
    return f"¥{v:+,.0f}" if v >= 0 else f"-¥{abs(v):,.0f}"


# ═══════════════════════════════════════════════════
# 预计算全部数据
# ═══════════════════════════════════════════════════
TABLE = {}
for pk in PHASES:
    TABLE[pk] = [calc(o, pk) for o in VOLUMES]


def build_main_table():
    """三阶段分润总表"""
    rows = ""
    for i, orders in enumerate(VOLUMES):
        d1 = TABLE["Phase1"][i]
        d2 = TABLE["Phase2"][i]

        # 行颜色以 Phase 1 为准（最乐观）
        m1 = d1["monthly_margin"]
        cls = "g" if m1 >= 15 else ("t" if m1 >= 0 else "l")

        color1 = "var(--g)" if d1["monthly_profit"] >= 0 else "var(--r)"
        color2 = "var(--g)" if d2["monthly_profit"] >= 0 else "var(--r)"

        rows += f"""<tr class="{cls}">
<td>{orders}</td>
<td>{d1['actual']}</td><td>{d1['cfg']}</td><td>{d1['tp']}</td><td>{d1['opp']}</td>
<td style="font-weight:700;color:{color1}">{fm(d1['monthly_profit'])}</td>
<td style="font-weight:700;color:{color1}">{fm(d1['operator_share'])}</td>
<td>{d1['per_order_op']:+.2f}</td>
<td style="color:{color1}">{d1['monthly_margin']:+.1f}%</td>
<td>{'✅' if d1['subsidy_ok'] else '❌'}</td>

<td>{d2['actual']}</td><td>{d2['cfg']}</td><td>{d2['tp']}</td><td>{d2['opp']}</td>
<td style="font-weight:700;color:{color2}">{fm(d2['monthly_profit'])}</td>
<td style="font-weight:700;color:{color2}">{fm(d2['operator_share'])}</td>
<td>{d2['per_order_op']:+.2f}</td>
<td style="color:{color2}">{d2['monthly_margin']:+.1f}%</td>
<td>{'✅' if d2['subsidy_ok'] else '❌'}</td>
</tr>"""
    return rows


def build_scenario_cards():
    """典型场景卡片"""
    scenarios = [
        ("小点位", 60),
        ("中等点位", 150),
        ("大点位", 200),
        ("超大点位", 300),
    ]
    cards = ""
    for label, orders in scenarios:
        i = VOLUMES.index(orders)
        d1 = TABLE["Phase1"][i]
        d2 = TABLE["Phase2"][i]
        cards += f"""<div style="background:var(--bg);border-radius:8px;padding:14px 16px;text-align:center;border:1px solid var(--br)">
  <div style="font-size:.8rem;color:var(--l)">{label} · {orders}单/天</div>
  <table style="font-size:.78rem;margin:8px 0 0">
  <tr><th style="background:none;padding:2px 6px"></th><th style="background:none;padding:2px 6px">Phase 1</th><th style="background:none;padding:2px 6px">Phase 2</th></tr>
  <tr><td style="text-align:left">月净利</td>
    <td style="color:{'var(--g)' if d1['monthly_profit']>=0 else 'var(--r)'};font-weight:700">{fm(d1['monthly_profit'])}</td>
    <td style="color:{'var(--g)' if d2['monthly_profit']>=0 else 'var(--r)'};font-weight:700">{fm(d2['monthly_profit'])}</td></tr>
  <tr><td style="text-align:left">你得分</td>
    <td style="color:var(--g);font-weight:700">{fm(d1['operator_share'])}</td>
    <td style="color:{'var(--g)' if d2['operator_share']>=0 else 'var(--r)'};font-weight:700">{fm(d2['operator_share'])}</td></tr>
  <tr><td style="text-align:left">单均</td>
    <td>{d1['per_order_op']:+.2f}</td><td>{d2['per_order_op']:+.2f}</td></tr>
  <tr><td style="text-align:left">排班</td>
    <td style="font-size:.72rem">{d1['tp']}人</td><td style="font-size:.72rem">{d2['tp']}人</td></tr>
  </table></div>"""
    return cards


def build_html():
    table_rows = build_main_table()
    cards = build_scenario_cards()

    # 找关键节点
    be1_idx = next(i for i, o in enumerate(VOLUMES) if TABLE["Phase1"][i]["monthly_profit"] >= 0)
    be2_idx = next(i for i, o in enumerate(VOLUMES) if TABLE["Phase2"][i]["monthly_profit"] >= 0)
    d200_p1 = TABLE["Phase1"][VOLUMES.index(200)]
    d200_p2 = TABLE["Phase2"][VOLUMES.index(200)]
    d100_p1 = TABLE["Phase1"][VOLUMES.index(100)]
    d60_p1 = TABLE["Phase1"][VOLUMES.index(60)]
    drop_200 = (1 - d200_p2["operator_share"] / d200_p1["operator_share"]) * 100 if d200_p1["operator_share"] > 0 else 100

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接力送 · 分包分润方案</title>
<style>
  :root{{--r:#e74c3c;--rb:#fadbd8;--y:#f39c12;--yb:#fef9e7;--g:#27ae60;--gb:#d5f5e3;--b:#2980b9;--bb:#d4e6f1;--t:#2c3e50;--l:#7f8c8d;--br:#e0e0e0;--bg:#fafafa}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--t);background:#fff;max-width:1100px;margin:0 auto;padding:36px 40px;line-height:1.7}}
  h1{{font-size:1.8rem;font-weight:800;margin-bottom:4px}}
  h1 .sub{{font-size:.8rem;color:var(--l);font-weight:400;margin-left:10px}}
  h2{{font-size:1.15rem;font-weight:700;margin:36px 0 10px}}
  h3{{font-size:.95rem;font-weight:700;margin:16px 0 6px}}
  hr{{border:none;border-top:2px solid #eee;margin:18px 0}}
  table{{width:100%;border-collapse:collapse;font-size:.82rem;margin:12px 0}}
  thead th{{background:#2c3e50;color:#fff;padding:9px 6px;font-weight:600;text-align:center;white-space:nowrap}}
  thead th.p1{{background:#1e8449}} thead th.p2{{background:#1a5276}} thead th.p3{{background:#922b21}}
  tbody td{{padding:6px 6px;text-align:right;border-bottom:1px solid var(--br)}}
  tbody td:first-child{{text-align:center;font-weight:700}}
  tr:hover{{filter:brightness(.95)}}
  tr.l td{{background:var(--rb)!important}} tr.t td{{background:var(--yb)!important}} tr.g td{{background:var(--gb)!important}}
  .info{{font-size:.84rem;color:var(--l);margin:4px 0 12px}}
  .tag{{display:inline-block;border-radius:4px;padding:2px 8px;font-size:.76rem;font-weight:700;margin-right:5px}}
  .tag.g{{background:#d5f5e3;color:#1e8449}} .tag.r{{background:#fadbd8;color:#922b21}} .tag.b{{background:#d4e6f1;color:#1a5276}}
  .overview{{background:var(--bg);border-radius:10px;padding:22px 26px;margin:18px 0;border:1px solid var(--br);font-size:.9rem}}
  .overview .flow{{display:flex;align-items:center;gap:10px;margin:14px 0;flex-wrap:wrap;font-size:.84rem}}
  .overview .flow .box{{background:#fff;border:2px solid var(--b);border-radius:8px;padding:10px 14px;text-align:center;font-weight:700;font-size:.86rem}}
  .overview .flow .arrow{{font-size:1.1rem;color:var(--l)}}
  .overview ul{{margin:8px 0 0 18px}}
  .overview li{{margin:3px 0;font-size:.85rem}}
  .note{{border-radius:8px;padding:12px 16px;margin:16px 0;font-size:.86rem}}
  .note.g{{background:#eaf7ea;border-left:4px solid var(--g)}}
  .note.r{{background:#fdedec;border-left:4px solid var(--r)}}
  .note.b{{background:#eaf2f8;border-left:4px solid var(--b)}}
  .note.y{{background:#fef9e7;border-left:4px solid var(--y)}}
  .card-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
  @media(max-width:768px){{.card-grid{{grid-template-columns:repeat(2,1fr)}}}}
  .footer{{margin-top:40px;padding-top:12px;border-top:2px solid #eee;color:var(--l);font-size:.74rem}}
  .tbl-wrap{{overflow-x:auto}}
</style></head>
<body>

<h1>🤝 接力送 · 分包分润方案<span class="sub">平台出资 · 运营方出力 · 利润五五分</span></h1>
<hr>

<!-- ═══════ 合作模式 ═══════ -->
<h2>📐 合作模式</h2>
<div class="overview">
  <h3>做什么</h3>
  <p>美团骑手将外卖送至楼宇大堂，<strong>你方人员</strong>接手完成<strong>上楼到户</strong>的最后一段配送。</p>
  <p>每单收入 = 美团结算 ¥2.50 + 骑手付费（引流期 ¥1.00 / 常规期 ¥2.00）+ 人头补贴。</p>

  <h3>怎么合作</h3>
  <div class="flow">
    <div class="box">🏢 我们（平台）<br><small>出资建点 · 物料<br>系统对接 · 垫付工资</small></div>
    <div class="arrow">→</div>
    <div class="box">📦 收入池<br><small>美团结算 + 骑手费<br>+ 人头补贴</small></div>
    <div class="arrow">→</div>
    <div class="box">➖ 扣成本<br><small>人力 ¥30/h<br>物料 ¥100/月</small></div>
    <div class="arrow">→</div>
    <div class="box" style="border-color:var(--g)">💰 净利五五分<br><small>你 50%<br>平台 50%</small></div>
  </div>

  <h3>你需要做什么</h3>
  <ul>
    <li><strong>招人排班：</strong>每个点位至少 1 人值守 3 小时（楼下指引 + 闲时配送），午高峰按单量增加上楼配送员（2-3h/人）</li>
    <li><strong>日常运营：</strong>接单、上楼配送、处理骑手和物业的日常问题</li>
    <li><strong>保证质量：</strong>配送时效 ≤15min，完好率 ≥99%</li>
  </ul>

  <h3>我们出什么</h3>
  <ul>
    <li><strong>全部启动资金：</strong>点位踩点、物业签约、货架物料（¥100/点位）、系统对接，你零投入启动</li>
    <li><strong>按月垫付工资：</strong>人力成本先从收入池扣除，你不需要自己掏钱发工资</li>
    <li><strong>月度结算分成：</strong>每月核算净利润，你分 50%，直接打款</li>
  </ul>

  <h3>补贴节奏（决定你的收入）</h3>
  <table style="font-size:.82rem">
  <thead><tr><th>阶段</th><th>时长</th><th>骑手付费</th><th>美团结算</th><th>人头补贴</th><th>单量变化</th></tr></thead>
  <tbody>
  <tr class="g"><td>Phase 1 · 引流期</td><td>前2周</td><td>¥1.00</td><td>¥2.50</td><td>(T−1)×¥80 ✅</td><td>95-100% 基准</td></tr>
  <tr class="t"><td>Phase 2 · 常规期</td><td>长期</td><td>¥2.00</td><td>¥2.50</td><td>(T−1)×¥80 ✅</td><td>13-25% 基准</td></tr>
  </tbody></table>
  <div style="font-size:.78rem;color:var(--l);margin-top:6px">* 补贴条件：营业≥3h 且人均≥20单。人头补贴公式: (总人数−1)×¥80/天。产能基准: 12单/h/人。</div>
</div>

<!-- ═══════ 场景速览 ═══════ -->
<h2>📊 典型点位速览</h2>
<div class="card-grid">
  {cards}
</div>

<!-- ═══════ 分润总表 ═══════ -->
<h2>📋 三阶段分润明细</h2>
<div class="info"><span class="tag g">健康 ≥15%</span><span class="tag b">微利 0-15%</span><span class="tag r">亏损</span>行颜色以 Phase 1 净利率为准。单均为你方每单到手金额。</div>
<div class="tbl-wrap">
<table>
<thead>
<tr>
  <th rowspan="2">日均<br>单量</th>
  <th colspan="9" class="p1">Phase 1 · 引流期（前2周）</th>
  <th colspan="9" class="p2">Phase 2 · 常规期（长期）</th>
</tr>
<tr>
  <th>实际</th><th>排班</th><th>人</th><th>人均</th><th>月净利</th><th style="color:#a5d6a7">你得分</th><th>单均</th><th>利率</th><th>补贴</th>
  <th>实际</th><th>排班</th><th>人</th><th>人均</th><th>月净利</th><th style="color:#a5d6a7">你得分</th><th>单均</th><th>利率</th><th>补贴</th>
</tr>
</thead>
<tbody>
{table_rows}
</tbody>
</table>
</div>

<!-- ═══════ 关键发现 ═══════ -->
<h2>🔍 你需要知道的</h2>

<div class="note g">
  <strong>✅ Phase 1（前2周）是甜区：</strong>盈亏平衡仅需 {VOLUMES[be1_idx]} 单/天。{VOLUMES.index(60)+1} 单/天你月得 {fm(d60_p1['operator_share'])}，100 单/天月得 {fm(d100_p1['operator_share'])}，200 单/天月得 {fm(d200_p1['operator_share'])}（单均 {d200_p1['per_order_op']:+.2f} 元）。单量越高，单均利润越高（规模效应）。
</div>

<div class="note y">
  <strong>⚠️ Phase 2 单量断崖：</strong>骑手费从 ¥1.00 涨到 ¥2.00 后，单量暴跌至 13-25%。盈亏平衡需 {VOLUMES[be2_idx]} 单/天（实际仅 {TABLE['Phase2'][be2_idx]['actual']} 单）。200 单点位你月得从 {fm(d200_p1['operator_share'])} 降至 {fm(d200_p2['operator_share'])}，降幅 {drop_200:.0f}%。<strong>Phase 1 冲不到 200 单的点位，Phase 2 几乎没有利润。</strong>
</div>

<div class="note b">
  <strong>💡 核心策略：Phase 1 全力冲单量。</strong>前 2 周引流期内，骑手只付 ¥1.00，单量最高、利润最好。2 周内把每个点位日均冲到 200+ 单，才能在 Phase 2 活下去。
</div>

<div class="footer">
  <p>参数: 时薪 ¥30/h · 月物料 ¥100 · 人均产能 12单/h（基于实测 571 单，成熟点位中位 12.9） · 补贴门槛 人均≥20单 · 月30天</p>
  <p>接力送 · 分包分润方案 · 合作方面向 · 2026-06-14</p>
</div>
</body></html>'''
    return html


def main():
    print("生成分包分润页面（合作方面向）...")
    html = build_html()
    path = os.path.join(OUTPUT_DIR, "subcontract_profit_share.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已保存: {path} ({len(html):,} 字节)")


if __name__ == "__main__":
    main()
