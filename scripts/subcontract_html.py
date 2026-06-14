"""
接力送 · 分包分润 交互式可视化
============================
生成单个自包含 HTML 文件，含 JavaScript 交互控件和 Chart.js 图表。
可部署到 GitHub Pages。
"""

import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════
# 模型参数
# ═══════════════════════════════════════════════════
LABOR_RATE = 30
MAT_MONTH = 100
MAT_DAILY = MAT_MONTH / 30
DAYS = 30
CAPACITY = 12
MIN_OPP = 20
ANCHOR_H = 3.0
SPLIT = 0.5

PHASES = {
    "Phase1": {"rider_fee": 1.0, "settlement": 2.5, "subsidy": True,  "label": "Phase 1 · 引流期",       "color": "#27ae60", "desc": "骑手付¥1.00 结算¥2.50 补贴有"},
    "Phase2": {"rider_fee": 2.0, "settlement": 2.5, "subsidy": True,  "label": "Phase 2 · 长期补贴",     "color": "#2980b9", "desc": "骑手付¥2.00 结算¥2.50 补贴有"},
    "Phase3": {"rider_fee": 2.0, "settlement": 2.0, "subsidy": False, "label": "Phase 3 · 补贴归零",     "color": "#e74c3c", "desc": "骑手付¥2.00 结算¥2.00 补贴无"},
}


def rider_vol_mult(fee):
    surplus = 3.0 - fee
    ratio = surplus / 3.0
    if ratio >= 0.7:   return 1.0
    elif ratio >= 0.5: return 0.95 - (0.7 - ratio) * 2.5
    elif ratio >= 0.3: return 0.50 - (0.5 - ratio) * 1.5
    elif ratio >= 0.15: return 0.25 - (0.3 - ratio) * 1.2
    else:              return max(0.05, ratio * 0.6)


def optimal_staffing(daily_orders):
    best, best_cost = None, float("inf")
    for n in range(0, 15):
        for h in [2.0, 2.5, 3.0]:
            total_h = ANCHOR_H + n * h
            if CAPACITY * total_h < daily_orders:
                continue
            cost = total_h * LABOR_RATE
            if cost < best_cost:
                best_cost = cost
                tp = 1 + n
                opp = daily_orders / tp
                best = (tp, total_h, opp, opp >= MIN_OPP, n, h)
    if best is None:
        for n in range(0, 31):
            if 20 * n + 21 >= daily_orders:
                tp = 1 + n
                total_h = ANCHOR_H + n * 2.0
                opp = daily_orders / tp
                return tp, total_h, opp, opp >= MIN_OPP, n, 2.0
        tp, total_h, n = 31, ANCHOR_H + 60, 30
        return tp, total_h, daily_orders / 31, False, n, 2.0
    return best


def calc_subcontract(daily_orders, phase_key):
    p = PHASES[phase_key]
    actual = max(5, int(daily_orders * rider_vol_mult(p["rider_fee"])))
    tp, th, opp, sub_ok, n_peak, peak_h = optimal_staffing(actual)
    daily_sub = (tp - 1) * 80 if (p["subsidy"] and sub_ok) else 0
    daily_rev = actual * (p["settlement"] + p["rider_fee"]) + daily_sub
    daily_labor = th * LABOR_RATE
    daily_profit = daily_rev - daily_labor - MAT_DAILY

    return {
        "daily_orders": daily_orders,
        "actual_orders": actual,
        "phase_label": p["label"],
        "rider_fee": p["rider_fee"],
        "settlement": p["settlement"],
        "subsidy_ok": sub_ok and p["subsidy"],
        "total_people": tp,
        "total_hours": round(th, 1),
        "n_peak": n_peak,
        "peak_h": peak_h,
        "opp": round(opp, 1),
        "daily_settlement": round(actual * p["settlement"], 0),
        "daily_rider_fee": round(actual * p["rider_fee"], 0),
        "daily_subsidy": round(daily_sub, 0),
        "daily_revenue": round(daily_rev, 0),
        "daily_labor": round(daily_labor, 0),
        "daily_material": round(MAT_DAILY, 0),
        "daily_profit": round(daily_profit, 0),
        "monthly_settlement": round(actual * p["settlement"] * DAYS, 0),
        "monthly_rider_fee": round(actual * p["rider_fee"] * DAYS, 0),
        "monthly_subsidy": round(daily_sub * DAYS, 0),
        "monthly_revenue": round(daily_rev * DAYS, 0),
        "monthly_labor": round(daily_labor * DAYS, 0),
        "monthly_material": MAT_MONTH,
        "monthly_profit": round(daily_profit * DAYS, 0),
        "monthly_margin": round(daily_profit * DAYS / (daily_rev * DAYS) * 100, 1) if daily_rev > 0 else 0,
        "platform_share": round(daily_profit * DAYS * SPLIT, 0),
        "operator_share": round(daily_profit * DAYS * SPLIT, 0),
        "per_order_operator": round(daily_profit * SPLIT / actual, 2) if actual else 0,
        "staffing_label": f"1锚+{n_peak}峰×{peak_h}h" if peak_h == int(peak_h) else f"1锚+{n_peak}峰×{peak_h:.1f}h",
    }


def fm(v):
    if v >= 0:
        return f"¥{v:+,.0f}"
    return f"-¥{abs(v):,.0f}"


def fmt_cn(n):
    """中文数字格式化"""
    if n >= 10000:
        return f"{n/10000:.1f}万"
    return f"{n:,.0f}"


# ═══════════════════════════════════════════════════
# 预计算数据
# ═══════════════════════════════════════════════════
ORDER_LEVELS = [20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 180, 200, 250, 300, 400, 500]
TABLE_DATA = {}
for pk in PHASES:
    TABLE_DATA[pk] = [calc_subcontract(o, pk) for o in ORDER_LEVELS]

# 图表数据：密集点用于曲线
DENSE_ORDERS = list(range(30, 510, 5))
CHART_DATA = {}
for pk in PHASES:
    CHART_DATA[pk] = [calc_subcontract(o, pk) for o in DENSE_ORDERS]

TABLE_JSON = json.dumps(TABLE_DATA, ensure_ascii=False)
CHART_JSON = json.dumps(CHART_DATA, ensure_ascii=False)
ORDER_LEVELS_JSON = json.dumps(ORDER_LEVELS)
DENSE_ORDERS_JSON = json.dumps(DENSE_ORDERS)


def class_for(val, threshold_good=15, threshold_thin=0):
    if val >= threshold_good: return "g"
    if val >= threshold_thin: return "t"
    return "l"


def build_main_table():
    """三阶段分润主表"""
    rows = ""
    for i, orders in enumerate(ORDER_LEVELS):
        rows += "<tr>"
        rows += f'<td class="t-order">{orders}</td>'
        for pk in PHASES:
            d = TABLE_DATA[pk][i]
            cls = class_for(d["monthly_margin"])
            color = "#27ae60" if d["monthly_profit"] >= 0 else "#e74c3c"
            sub_icon = "✅" if d["subsidy_ok"] else "❌"
            rows += f'<td>{d["actual_orders"]}</td>'
            rows += f'<td class="t-cfg">{d["staffing_label"]}</td>'
            rows += f'<td>{d["total_people"]}</td>'
            rows += f'<td class="t-{cls}" style="font-weight:700;color:{color}">{d["monthly_profit"]:+,.0f}</td>'
            rows += f'<td class="t-{cls}" style="font-weight:700;color:{color}">{d["operator_share"]:+,.0f}</td>'
            rows += f'<td class="t-{cls}" style="color:{color}">{d["monthly_margin"]:+.1f}%</td>'
            rows += f'<td>{sub_icon}</td>'
        rows += "</tr>\n"
    return rows


def build_html():
    table_rows = build_main_table()

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接力送 · 分包分润模型</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{
  --r:#e74c3c; --rb:#fadbd8; --y:#f39c12; --yb:#fef9e7;
  --g:#27ae60; --gb:#d5f5e3; --b:#2980b9; --bb:#d4e6f1;
  --t:#2c3e50; --l:#7f8c8d; --br:#e0e0e0; --bg:#fafafa;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--sans);color:var(--t);background:#fff;max-width:1100px;margin:0 auto;padding:28px 36px;line-height:1.68}}
h1{{font-size:1.7rem;font-weight:800;margin-bottom:2px}}
h1 .sub{{font-size:.78rem;color:var(--l);font-weight:400;margin-left:8px}}
h2{{font-size:1.12rem;font-weight:700;margin:34px 0 10px;padding-bottom:6px;border-bottom:2px solid #eee}}
h3{{font-size:.92rem;font-weight:700;margin:16px 0 6px}}
hr{{border:none;border-top:2px solid #eee;margin:16px 0}}

.tag{{display:inline-block;border-radius:4px;padding:2px 8px;font-size:.74rem;font-weight:700;margin-right:4px}}
.tag.g{{background:#d5f5e3;color:#1e8449}} .tag.r{{background:#fadbd8;color:#922b21}} .tag.b{{background:#d4e6f1;color:#1a5276}} .tag.y{{background:#fef9e7;color:#b7950b}}

.overview{{background:var(--bg);border-radius:10px;padding:20px 24px;margin:14px 0;border:1px solid var(--br);font-size:.88rem}}
.overview .flow{{display:flex;align-items:center;gap:10px;margin:12px 0;flex-wrap:wrap;font-size:.84rem}}
.overview .flow .box{{background:#fff;border:2px solid var(--b);border-radius:8px;padding:8px 12px;text-align:center;font-weight:700;font-size:.84rem}}
.overview .flow .arrow{{font-size:1.1rem;color:var(--l)}}
.overview ul{{margin:6px 0 0 16px}} .overview li{{margin:2px 0;font-size:.82rem}}

.controls{{background:var(--bg);border-radius:10px;padding:18px 22px;margin:16px 0;border:1px solid var(--br);display:flex;flex-wrap:wrap;gap:18px;align-items:center}}
.controls label{{font-size:.82rem;font-weight:700;color:var(--l);margin-right:4px}}
.controls input[type=range]{{width:220px;accent-color:var(--b)}}
.controls select{{padding:4px 10px;border:2px solid var(--b);border-radius:6px;font-size:.84rem;font-family:var(--sans)}}
.controls .val{{font-size:1.1rem;font-weight:800;color:var(--b);min-width:50px;text-align:center}}

.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}}
.kpi{{background:var(--bg);border-radius:10px;padding:14px;text-align:center;border-left:4px solid var(--b)}}
.kpi .v{{font-size:1.3rem;font-weight:800;margin-bottom:2px}}
.kpi .lbl{{font-size:.74rem;color:var(--l)}}
.kpi.gr{{border-left-color:var(--g)}} .kpi.rd{{border-left-color:var(--r)}} .kpi.bl{{border-left-color:var(--b)}} .kpi.yl{{border-left-color:var(--y)}}

.table-wrap{{overflow-x:auto;margin:14px 0}}
table{{width:100%;border-collapse:collapse;font-size:.8rem}}
thead th{{background:#2c3e50;color:#fff;padding:8px 5px;font-weight:600;text-align:center;white-space:nowrap;position:sticky;top:0;z-index:2}}
thead th.phase1{{background:#1e8449}} thead th.phase2{{background:#1a5276}} thead th.phase3{{background:#922b21}}
tbody td{{padding:6px 5px;text-align:right;border-bottom:1px solid var(--br)}}
tbody td.t-order,tbody td.t-cfg{{text-align:center}}
tr:hover{{filter:brightness(.94)}}
tr.l td{{background:var(--rb)!important}}
tr.t td{{background:var(--yb)!important}}
tr.g td{{background:var(--gb)!important}}

.note{{border-radius:8px;padding:12px 16px;margin:16px 0;font-size:.84rem}}
.note.g{{background:#eaf7ea;border-left:4px solid var(--g)}}
.note.r{{background:#fdedec;border-left:4px solid var(--r)}}
.note.b{{background:#eaf2f8;border-left:4px solid var(--b)}}

.chart-row{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:16px 0}}
.chart-box{{background:#fff;border:1px solid var(--br);border-radius:10px;padding:16px}}
.chart-box canvas{{max-height:350px}}

.footer{{margin-top:36px;padding-top:12px;border-top:2px solid #eee;color:var(--l);font-size:.72rem}}

@media(max-width:768px){{
  .kpis{{grid-template-columns:repeat(2,1fr)}}
  .chart-row{{grid-template-columns:1fr}}
  .controls{{flex-direction:column;align-items:flex-start}}
}}
</style>
</head>
<body>

<h1>🤝 接力送 · 分包分润模型<span class="sub">平台出资 · 运营方出力 · 五五分润</span></h1>
<hr>

<!-- ═══════════════════════════════════ 模式概述 ═══════════════════════════════════ -->
<h2>📐 分包模式</h2>
<div class="overview">
  <h3>怎么分</h3>
  <div class="flow">
    <div class="box">🏢 平台方<br><small>出资建点<br>垫付人力+物料</small></div>
    <div class="arrow">→</div>
    <div class="box">📦 收入池<br><small>美团结算 + 骑手费<br>+ 人头补贴</small></div>
    <div class="arrow">→</div>
    <div class="box">➖ 扣成本<br><small>人力¥30/h<br>物料¥100/月</small></div>
    <div class="arrow">→</div>
    <div class="box" style="border-color:var(--g)">💰 净利<br><small>平台 50%<br>运营方 50%</small></div>
  </div>

  <h3>双方权责</h3>
  <table style="font-size:.8rem;margin-top:8px">
  <thead><tr><th style="width:15%">角色</th><th>承担</th><th>不承担</th></tr></thead>
  <tbody>
  <tr><td style="font-weight:700;color:var(--b)">平台方（公司）</td>
    <td>点位踩点·物业签约·物料布置 · 美团系统对接 · <b>按月垫付人力工资</b> · 月度分润打款</td>
    <td>日常运营管理 · 人员招聘排班</td></tr>
  <tr><td style="font-weight:700;color:var(--g)">运营方（分包商）</td>
    <td>人员招聘·排班·考勤 · 每日配送执行 · 服务质量保障 · 现场异常处理</td>
    <td>启动资金 · 物料费用 · 美团对接</td></tr>
  </tbody></table>

  <h3>三阶段参数</h3>
  <table style="font-size:.8rem;margin-top:8px">
  <thead><tr><th>阶段</th><th>骑手付费</th><th>美团结算</th><th>人头补贴</th><th>单量保留率</th><th>运营方月分成(200单点)</th></tr></thead>
  <tbody>
  <tr class="g"><td>Phase 1 · 引流期</td><td>¥1.00</td><td>¥2.50</td><td>(T−1)×¥80 ✅</td><td>95-100%</td><td style="font-weight:700;color:var(--g)">{TABLE_DATA['Phase1'][12]['operator_share']:+,.0f}</td></tr>
  <tr class="t"><td>Phase 2 · 长期补贴</td><td>¥2.00</td><td>¥2.50</td><td>(T−1)×¥80 ✅</td><td>13-25%</td><td style="font-weight:700;color:var(--y)">{TABLE_DATA['Phase2'][12]['operator_share']:+,.0f}</td></tr>
  <tr class="l"><td>Phase 3 · 补贴归零</td><td>¥2.00</td><td>¥2.00</td><td>❌</td><td>13-25%</td><td style="font-weight:700;color:var(--r)">{TABLE_DATA['Phase3'][12]['operator_share']:+,.0f}</td></tr>
  </tbody></table>
</div>

<!-- ═══════════════════════════════════ 交互式计算器 ═══════════════════════════════════ -->
<h2>🎛️ 分润计算器</h2>
<div class="controls" id="calculator">
  <div>
    <label>日单量</label>
    <input type="range" id="orderSlider" min="20" max="500" value="100" step="5" oninput="updateCalc()">
    <span class="val" id="orderVal">100</span> 单/天
  </div>
  <div>
    <label>阶段</label>
    <select id="phaseSelect" onchange="updateCalc()">
      <option value="Phase1">Phase 1 · 引流期</option>
      <option value="Phase2">Phase 2 · 长期补贴</option>
      <option value="Phase3">Phase 3 · 补贴归零</option>
    </select>
  </div>
</div>

<div class="kpis" id="kpiRow">
  <div class="kpi gr"><div class="v" id="kpiOpShare">—</div><div class="lbl">运营方月分成</div></div>
  <div class="kpi bl"><div class="v" id="kpiPfShare">—</div><div class="lbl">平台方月分成</div></div>
  <div class="kpi yl"><div class="v" id="kpiProfit">—</div><div class="lbl">月度净利</div></div>
  <div class="kpi rd"><div class="v" id="kpiMargin">—</div><div class="lbl">净利率</div></div>
</div>

<!-- 详细数据卡片 -->
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0;font-size:.82rem" id="detailCards">
  <div style="background:var(--bb);border-radius:8px;padding:12px">
    <strong>📊 订单</strong><br>
    基准: <span id="detBase">—</span> 单/天<br>
    实际: <span id="detActual">—</span> 单/天<br>
    月单量: <span id="detMonthly">—</span> 单
  </div>
  <div style="background:var(--gb);border-radius:8px;padding:12px">
    <strong>💰 月收入</strong><br>
    结算: <span id="detSettle">—</span><br>
    骑手费: <span id="detRider">—</span><br>
    补贴: <span id="detSub">—</span><br>
    <b>合计: <span id="detRev">—</span></b>
  </div>
  <div style="background:var(--rb);border-radius:8px;padding:12px">
    <strong>📋 排班 & 成本</strong><br>
    配置: <span id="detStaff">—</span><br>
    人数: <span id="detPeople">—</span> | 工时: <span id="detHours">—</span>h<br>
    人力: <span id="detLabor">—</span> + 物料: <span id="detMat">—</span><br>
    单均运营方分成: <span id="detPerOrder">—</span>
  </div>
</div>

<!-- ═══════════════════════════════════ 图表区 ═══════════════════════════════════ -->
<h2>📈 分润曲线 & 拆解</h2>

<div class="chart-row">
  <div class="chart-box">
    <h3 style="margin-bottom:10px">运营方月分成 · 三阶段对比</h3>
    <canvas id="chartCurves"></canvas>
  </div>
  <div class="chart-box">
    <h3 style="margin-bottom:10px">当前场景收入拆解</h3>
    <canvas id="chartWaterfall"></canvas>
  </div>
</div>

<div class="chart-row">
  <div class="chart-box">
    <h3 style="margin-bottom:10px">Phase 断崖：单均运营方分成</h3>
    <canvas id="chartPerOrder"></canvas>
  </div>
  <div class="chart-box">
    <h3 style="margin-bottom:10px">多点打包 · 总收益</h3>
    <canvas id="chartPortfolio"></canvas>
  </div>
</div>

<!-- ═══════════════════════════════════ 主数据表 ═══════════════════════════════════ -->
<h2>📋 三阶段分润总表</h2>
<div class="info" style="font-size:.8rem;color:var(--l);margin-bottom:8px">
  <span class="tag g">健康 ≥15%</span><span class="tag y">微利 0-15%</span><span class="tag r">亏损</span>
  绿/黄/红行 = Phase 1 净利率；其余两阶段颜色独立标注
</div>

<div class="table-wrap">
<table id="mainTable">
<thead>
<tr>
  <th rowspan="2">基准<br>单量</th>
  <th colspan="7" class="phase1">Phase 1 · 引流期</th>
  <th colspan="7" class="phase2">Phase 2 · 长期补贴</th>
  <th colspan="7" class="phase3">Phase 3 · 补贴归零</th>
</tr>
<tr>
  <th>实际</th><th>排班</th><th>人</th><th>月净利</th><th>运营方</th><th>利率</th><th>补贴</th>
  <th>实际</th><th>排班</th><th>人</th><th>月净利</th><th>运营方</th><th>利率</th><th>补贴</th>
  <th>实际</th><th>排班</th><th>人</th><th>月净利</th><th>运营方</th><th>利率</th><th>补贴</th>
</tr>
</thead>
<tbody>
{table_rows}
</tbody>
</table>
</div>

<!-- ═══════════════════════════════════ 总结 ═══════════════════════════════════ -->
<h2>🔍 关键发现</h2>

<div class="note g">
  <strong>✅ Phase 1 · 分包唯一「甜区」：</strong>40单盈亏平衡，100单运营方月得¥3,000+，200单¥7,000+，500单¥26,000+。这是运营方最有动力的阶段。必须在前2周内把每个点冲到200+单。
</div>

<div class="note b">
  <strong>⚠️ Phase 2 · 生死关：</strong>200单点位运营方分成从¥7,082暴跌至¥2,275（−68%）。&lt;100单的点位运营方月分不到¥300。<b>Phase 1冲不到200单的点位，Phase 2对运营方毫无吸引力。</b>
</div>

<div class="note r">
  <strong>❌ Phase 3 · 全线亏损：</strong>补贴归零后运营方零分成，平台方独自承担全部亏损。500单的点位运营方也仅得¥2,725/月。Phase 2结束前必须找到新模式或关停。
</div>

<div class="note" style="background:#fef9e7;border-left:4px solid var(--y)">
  <strong>⚡ 激励风险：</strong>运营方控制排班但不承担人力成本——可能倾向于多报人头（每多1人×2h，补贴+¥80，成本仅+¥60，净赚¥20）。<b>必须设人效红线 ≥12单/h</b>，低于基准的超额人力成本从运营方分成中扣除。
</div>

<div class="footer">
  <p>参数: 时薪¥30/h · 月物料¥100 · 人均产能12单/h（基于实测571单，成熟点位中位12.9） · 补贴门槛人均≥20单 · 分润比例50:50 · 2026-06-14</p>
  <p>分包分润模型 · 数据来源: relay_delivery_model / three_phase_model / renxiao_analysis</p>
</div>

<!-- ═══════════════════════════════════ JavaScript ═══════════════════════════════════ -->
<script>
const TABLE_DATA = {TABLE_JSON};
const CHART_DATA = {CHART_JSON};
const ORDER_LEVELS = {ORDER_LEVELS_JSON};
const DENSE_ORDERS = {DENSE_ORDERS_JSON};

const PHASE_COLORS = {{ Phase1: "#27ae60", Phase2: "#2980b9", Phase3: "#e74c3c" }};
const PHASE_LABELS = {{ Phase1: "引流期", Phase2: "长期补贴", Phase3: "补贴归零" }};

function fm(v) {{ return v >= 0 ? "¥" + v.toLocaleString("en-US", {{signDisplay:"exceptZero"}}) : "-¥" + Math.abs(v).toLocaleString("en-US"); }}

function findClosest(orders) {{
  const d = CHART_DATA[document.getElementById("phaseSelect").value];
  let best = d[0];
  let bestDiff = Math.abs(d[0].daily_orders - orders);
  for (let i = 1; i < d.length; i++) {{
    const diff = Math.abs(d[i].daily_orders - orders);
    if (diff < bestDiff) {{ bestDiff = diff; best = d[i]; }}
  }}
  return best;
}}

function updateCalc() {{
  const orders = parseInt(document.getElementById("orderSlider").value);
  const phase = document.getElementById("phaseSelect").value;
  document.getElementById("orderVal").textContent = orders;
  const d = findClosest(orders);

  document.getElementById("kpiOpShare").textContent = fm(d.operator_share);
  document.getElementById("kpiPfShare").textContent = fm(d.platform_share);
  document.getElementById("kpiProfit").textContent = fm(d.monthly_profit);
  document.getElementById("kpiMargin").textContent = (d.monthly_margin >= 0 ? "+" : "") + d.monthly_margin.toFixed(1) + "%";

  const kpiOp = document.getElementById("kpiOpShare").parentElement;
  kpiOp.className = d.operator_share >= 3000 ? "kpi gr" : (d.operator_share >= 0 ? "kpi yl" : "kpi rd");
  const kpiPf = document.getElementById("kpiPfShare").parentElement;
  kpiPf.className = d.platform_share >= 3000 ? "kpi bl" : (d.platform_share >= 0 ? "kpi yl" : "kpi rd");

  document.getElementById("detBase").textContent = d.daily_orders;
  document.getElementById("detActual").textContent = d.actual_orders;
  document.getElementById("detMonthly").textContent = (d.actual_orders * 30).toLocaleString();
  document.getElementById("detSettle").textContent = fm(d.monthly_settlement);
  document.getElementById("detRider").textContent = fm(d.monthly_rider_fee);
  document.getElementById("detSub").textContent = fm(d.monthly_subsidy);
  document.getElementById("detRev").textContent = fm(d.monthly_revenue);
  document.getElementById("detStaff").textContent = d.staffing_label;
  document.getElementById("detPeople").textContent = d.total_people;
  document.getElementById("detHours").textContent = d.total_hours;
  document.getElementById("detLabor").textContent = fm(d.monthly_labor);
  document.getElementById("detMat").textContent = "¥" + d.monthly_material;
  document.getElementById("detPerOrder").textContent = "¥" + d.per_order_operator.toFixed(2);

  updateWaterfallChart(d);
}}

// ═══════ Chart 1: 三阶段分成曲线 ═══════
let chartCurvesInst = null;
function initCurvesChart() {{
  const ctx = document.getElementById("chartCurves").getContext("2d");
  const datasets = [];
  for (const [pk, color] of Object.entries(PHASE_COLORS)) {{
    datasets.push({{
      label: PHASE_LABELS[pk],
      data: CHART_DATA[pk].map(d => ({{x: d.daily_orders, y: d.operator_share}})),
      borderColor: color,
      backgroundColor: color + "15",
      fill: false,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2.5,
    }});
  }}
  chartCurvesInst = new Chart(ctx, {{
    type: "line",
    data: {{ datasets }},
    options: {{
      responsive: true,
      interaction: {{ intersect: false, mode: "index" }},
      plugins: {{
        tooltip: {{
          callbacks: {{
            label: ctx => ctx.dataset.label + ": " + fm(ctx.parsed.y) + "/月",
          }}
        }},
        legend: {{ position: "bottom", labels: {{ usePointStyle: true, padding: 20, font: {{size:11}} }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: "基准日单量（单）" }}, min: 30, max: 500 }},
        y: {{ title: {{ display: true, text: "运营方月分成（元）" }},
          ticks: {{ callback: v => "¥" + (v/1000).toFixed(0) + "k" }},
          grid: {{ color: "#e0e0e0" }}
        }}
      }}
    }}
  }});
}}

// ═══════ Chart 2: 收入拆解瀑布图 ═══════
let chartWaterfallInst = null;
function initWaterfallChart() {{
  const ctx = document.getElementById("chartWaterfall").getContext("2d");
  chartWaterfallInst = new Chart(ctx, {{
    type: "bar",
    data: {{ labels: [], datasets: [] }},
    options: {{
      responsive: true,
      plugins: {{
        tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ": " + fm(ctx.parsed.y) }} }},
        legend: {{ position: "bottom", labels: {{ usePointStyle: true, font: {{size:10}} }} }}
      }},
      scales: {{
        x: {{ stacked: true }},
        y: {{ stacked: true, ticks: {{ callback: v => "¥" + v.toLocaleString() }},
          grid: {{ color: "#e0e0e0" }}
        }}
      }}
    }}
  }});
  updateWaterfallChart(findClosest(100));
}}

function updateWaterfallChart(d) {{
  if (!chartWaterfallInst) return;
  const settle = d.monthly_settlement;
  const rider = d.monthly_rider_fee;
  const sub = d.monthly_subsidy;
  const labor = -d.monthly_labor;
  const mat = -d.monthly_material;
  const profit = settle + rider + sub + labor + mat;

  const labels = ["美团结算", "骑手费", "人头补贴", "人力成本", "物料摊销"];
  const revData = [settle, rider, sub, 0, 0];
  const costData = [0, 0, 0, labor, mat];
  const profitMark = profit >= 0 ? profit : 0;
  const lossMark = profit < 0 ? profit : 0;

  chartWaterfallInst.data.labels = labels;
  chartWaterfallInst.data.datasets = [
    {{
      label: "收入项",
      data: revData,
      backgroundColor: ["#3498db", "#1abc9c", "#27ae60", "transparent", "transparent"],
      borderColor: "#fff", borderWidth: 1, borderRadius: 4,
    }},
    {{
      label: "成本项",
      data: costData,
      backgroundColor: ["transparent", "transparent", "transparent", "#e74c3c", "#c0392b"],
      borderColor: "#fff", borderWidth: 1, borderRadius: 4,
    }},
  ];
  chartWaterfallInst.update();

  // Update note below chart
  const opShare = d.operator_share;
  const pfShare = d.platform_share;
  const noteEl = document.getElementById("waterfallNote");
  if (noteEl) {{
    noteEl.innerHTML = `<strong>净利 ${{fm(profit)}}</strong> → 运营方 <b style="color:var(--g)">${{fm(opShare)}}</b> · 平台方 <b style="color:var(--b)">${{fm(pfShare)}}</b>`;
  }}
}}

// ═══════ Chart 3: 单均运营方分成 ═══════
function initPerOrderChart() {{
  const ctx = document.getElementById("chartPerOrder").getContext("2d");
  const datasets = [];
  for (const [pk, color] of Object.entries(PHASE_COLORS)) {{
    datasets.push({{
      label: PHASE_LABELS[pk],
      data: CHART_DATA[pk].map(d => ({{x: d.daily_orders, y: d.per_order_operator}})),
      borderColor: color,
      backgroundColor: color + "10",
      fill: false,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2.5,
    }});
  }}
  new Chart(ctx, {{
    type: "line",
    data: {{ datasets }},
    options: {{
      responsive: true,
      interaction: {{ intersect: false, mode: "index" }},
      plugins: {{
        tooltip: {{
          callbacks: {{
            label: ctx => ctx.dataset.label + ": ¥" + ctx.parsed.y.toFixed(2) + "/单",
          }}
        }},
        legend: {{ position: "bottom", labels: {{ usePointStyle: true, padding: 20, font: {{size:11}} }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: "基准日单量（单）" }}, min: 30, max: 500 }},
        y: {{ title: {{ display: true, text: "运营方单均分成（元/单）" }},
          grid: {{ color: "#e0e0e0" }}
        }}
      }}
    }}
  }});
}}

// ═══════ Chart 4: 多点打包 ═══════
function initPortfolioChart() {{
  const ctx = document.getElementById("chartPortfolio").getContext("2d");
  const points = [
    {{ name: "大点 200单", phase: "Phase1", orders: 200 }},
    {{ name: "中点A 100单", phase: "Phase1", orders: 100 }},
    {{ name: "中点B 80单", phase: "Phase1", orders: 80 }},
    {{ name: "小点A 60单", phase: "Phase1", orders: 60 }},
    {{ name: "小点B 40单", phase: "Phase1", orders: 40 }},
  ];

  function calcFor(phaseKey) {{
    return points.map(pt => {{
      const d = CHART_DATA[phaseKey].find(dd => dd.daily_orders === pt.orders);
      return d || {{ operator_share: 0, platform_share: 0 }};
    }});
  }}

  const p1 = calcFor("Phase1");
  const p2 = calcFor("Phase2");

  new Chart(ctx, {{
    type: "bar",
    data: {{
      labels: points.map(p => p.name),
      datasets: [
        {{
          label: "Phase 1 运营方",
          data: p1.map(d => d.operator_share),
          backgroundColor: "#27ae60aa", borderColor: "#27ae60", borderWidth: 1, borderRadius: 4,
        }},
        {{
          label: "Phase 1 平台方",
          data: p1.map(d => d.platform_share),
          backgroundColor: "#3498dbaa", borderColor: "#3498db", borderWidth: 1, borderRadius: 4,
        }},
        {{
          label: "Phase 2 运营方",
          data: p2.map(d => d.operator_share),
          backgroundColor: "#e74c3caa", borderColor: "#e74c3c", borderWidth: 1, borderRadius: 4,
        }},
        {{
          label: "Phase 2 平台方",
          data: p2.map(d => d.platform_share),
          backgroundColor: "#2980b9aa", borderColor: "#2980b9", borderWidth: 1, borderRadius: 4,
        }},
      ]
    }},
    options: {{
      responsive: true,
      plugins: {{
        tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ": " + fm(ctx.parsed.y) }} }},
        legend: {{ position: "bottom", labels: {{ usePointStyle: true, font: {{size:10}} }} }}
      }},
      scales: {{
        y: {{
          title: {{ display: true, text: "月分成（元）" }},
          ticks: {{ callback: v => "¥" + v.toLocaleString() }},
          grid: {{ color: "#e0e0e0" }}
        }}
      }}
    }}
  }});

  // 合计标注
  const p1Op = p1.reduce((s,d) => s + d.operator_share, 0);
  const p2Op = p2.reduce((s,d) => s + d.operator_share, 0);
  const el = document.getElementById("portfolioNote");
  if (el) {{
    el.innerHTML = `5点打包 Phase 1 运营方合计: <b style="color:var(--g)">${{fm(p1Op)}}/月</b> → Phase 2: <b style="color:var(--r)">${{fm(p2Op)}}/月</b> (降幅${{((1-p2Op/p1Op)*100).toFixed(0)}}%)`;
  }}
}}

// ═══════ 初始化 ═══════
window.addEventListener("DOMContentLoaded", () => {{
  initCurvesChart();
  initWaterfallChart();
  initPerOrderChart();
  initPortfolioChart();
  updateCalc();
}});
</script>

<!-- 图表备注区 -->
<div style="font-size:.8rem;color:var(--l);margin-top:4px">
  <span id="waterfallNote"></span>
</div>
<div style="font-size:.8rem;color:var(--l);margin-top:4px">
  <span id="portfolioNote"></span>
</div>

</body>
</html>'''

    return html


def main():
    print("生成分包分润交互式HTML...")
    html = build_html()
    path = os.path.join(OUTPUT_DIR, "subcontract_profit_share.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已保存: {path} ({len(html):,} 字节)")
    print(f"\n可在浏览器中打开: file:///{path}")
    print(f"或部署到 GitHub Pages 后在线查看。")


if __name__ == "__main__":
    main()
