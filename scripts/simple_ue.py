"""
接力送 — 简化UE模型
====================
输入：日均单量
输出：月度P&L

有补贴场景：结算¥2.5 + 人头补贴(T-1)×80
兼职提效分析：不同人均产能下的UE敏感性
"""

import os
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RATE = 30          # 时薪
MAT = 100          # 月物料
DAYS = 30          # 月天数
MIN_OPP = 20       # 补贴人均门槛
CAP = 12           # 人均产能 单/h（基于renxiao实测：成熟点位中位12.9单/h，取12保守）


def fmt_cfg(n, h):
    """格式化排班 → '3h×1人 + 2h×3人'"""
    h_str = f"{h:.1f}h" if h != int(h) else f"{h:.0f}h"
    return f"3h×1人 + {h_str}×{n}人"


def best_cfg(orders, settlement, has_sub, cap=CAP):
    """找利润最高的(N, H)，cap为可选人均产能参数"""
    best_p = -float("inf")
    best = None
    for n in range(1, 31):
        for h in [2.0, 2.5, 3.0]:
            capacity = cap * n * h + 4 * h + 18
            if capacity < orders:
                continue
            tp = n + 1
            th = 3 + n * h
            cost = th * RATE + MAT / DAYS
            sub = (tp - 1) * 80 if (has_sub and orders / tp >= MIN_OPP) else 0
            rev = orders * settlement + sub
            p = rev - cost
            if p > best_p:
                best_p = p
                best = (n, h, tp, th, round(cost, 0), round(sub, 0), round(p, 0),
                        orders / tp >= MIN_OPP and has_sub, round(orders / tp, 1))
    return best


VOLUMES = [20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 180, 200, 250, 300, 400, 500]

# ═══════ Part 1: 有补贴UE ═══════
print(f"{'单量':>5s} | {'有补贴(结算2.5+人头补贴)':>44s}")
print(f"{'':>5s} | {'排班':>22s} {'人':>3s} {'人均':>5s} {'月利':>9s} {'利率':>6s}")
print("-" * 65)

results = []
for orders in VOLUMES:
    b = best_cfg(orders, 2.5, True)
    n, h, tp, th, cost, sub, dp, ok, opp = b
    m_profit = dp * DAYS
    m_rev = (orders * 2.5 + sub) * DAYS
    margin = m_profit / m_rev * 100 if m_rev > 0 else 0

    cfg = fmt_cfg(n, h)
    sub_mark = "✓" if ok else "✗"

    print(f"{orders:5d} | {cfg:>22s} {tp:2d}人 {opp:4.1f} {m_profit:+9,.0f} {margin:+5.1f}%")

    results.append({
        "日均单量": orders,
        "配置": cfg, "人数": tp,
        "人均": opp, "日补贴": sub,
        "月毛利": m_profit, "毛利率": f"{margin:.1f}%",
        "补贴达标": sub_mark,
    })

# ═══════ Part 2: 兼职提效敏感性分析 ═══════
# 用最小可行人力（最省工时）来找配置，避免补贴激励导致的过度配置
# 这样才能看到提效的真实成本节省
print(f"\n{'='*80}")
print("兼职提效敏感性分析：不同人均产能下的最小可行配置")
print(f"{'='*80}")

CAPS = [12, 15, 18]  # 人均产能 单/h


def lean_cfg(orders, cap):
    """找满足单量的最省工时配置（不受补贴激励扭曲）"""
    best_th = float("inf")
    best = None
    for n in range(1, 31):
        for h in [2.0, 2.5, 3.0]:
            capacity = cap * n * h + 4 * h + 18
            if capacity < orders:
                continue
            th = 3 + n * h  # 总工时
            if th < best_th:
                best_th = th
                tp = n + 1
                cost = th * RATE + MAT / DAYS
                sub = (tp - 1) * 80 if (orders / tp >= MIN_OPP) else 0
                rev = orders * 2.5 + sub
                p = rev - cost
                best = (n, h, tp, th, round(cost, 0), round(sub, 0), round(p, 0),
                        orders / tp >= MIN_OPP, round(orders / tp, 1))
    return best


print(f"{'单量':>5s} | {'CAP=12 (当前)':>35s} | {'CAP=15 (提效25%)':>35s} | {'CAP=18 (提效50%)':>35s}")
print(f"{'':>5s} | {'配置 人数 工时 月利 利率':>33s} | {'配置 人数 工时 月利 利率':>33s} | {'配置 人数 工时 月利 利率':>33s}")
print("-" * 120)

eff_results = {}
for orders in VOLUMES:
    row = []
    for cap in CAPS:
        b = lean_cfg(orders, cap)
        if b:
            n, h, tp, th, cost, sub, dp, ok, opp = b
            m_profit = dp * DAYS
            m_rev = (orders * 2.5 + sub) * DAYS
            margin = m_profit / m_rev * 100 if m_rev > 0 else 0
            row.append({
                "人数": tp, "月利": m_profit, "利率": margin,
                "配置": fmt_cfg(n, h), "人均": opp, "日补贴": sub,
                "工时": th, "补贴达标": "✓" if ok else "✗",
                "配送员数": n, "配送工时": h
            })
        else:
            row.append(None)

    parts = []
    for r in row:
        if r:
            parts.append(f"{r['配置']:>18s} {r['人数']:2d}人 {r['工时']:4.1f}h {r['月利']:+9,.0f} {r['利率']:+6.1f}%")
        else:
            parts.append("N/A")
    print(f"{orders:5d} | {parts[0]} | {parts[1]} | {parts[2]}")
    eff_results[orders] = row


# ═══════ HTML ═══════

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>接力送 · UE模型</title>
<style>
  :root{--r:#e74c3c;--rb:#fadbd8;--y:#f39c12;--yb:#fef9e7;--g:#27ae60;--gb:#d5f5e3;--b:#2980b9;--bb:#d4e6f1;--t:#2c3e50;--l:#7f8c8d;--br:#e0e0e0;--bg:#fafafa}
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--t);background:#fff;max-width:1000px;margin:0 auto;padding:36px 40px;line-height:1.7}
  h1{font-size:1.8rem;font-weight:800;margin-bottom:4px}
  h1 .sub{font-size:.8rem;color:var(--l);font-weight:400;margin-left:10px}
  h2{font-size:1.15rem;font-weight:700;margin:36px 0 10px}
  h3{font-size:.95rem;font-weight:700;margin:16px 0 6px}
  hr{border:none;border-top:2px solid #eee;margin:18px 0}
  table{width:100%;border-collapse:collapse;font-size:.84rem;margin:12px 0}
  thead th{background:#2c3e50;color:#fff;padding:9px 7px;font-weight:600;text-align:center;white-space:nowrap}
  tbody td{padding:7px 7px;text-align:right;border-bottom:1px solid var(--br)}
  tbody td:first-child{text-align:center;font-weight:700}
  tr:hover{filter:brightness(.95)}
  tr.l td{background:var(--rb)!important}
  tr.t td{background:var(--yb)!important}
  tr.g td{background:var(--gb)!important}
  .info{font-size:.84rem;color:var(--l);margin:4px 0 12px}
  .tag{display:inline-block;border-radius:4px;padding:2px 8px;font-size:.76rem;font-weight:700;margin-right:5px}
  .tag.g{background:#d5f5e3;color:#1e8449}
  .tag.r{background:#fadbd8;color:#922b21}
  .tag.b{background:#d4e6f1;color:#1a5276}
  .overview{background:var(--bg);border-radius:10px;padding:22px 26px;margin:18px 0;border:1px solid var(--br);font-size:.9rem}
  .overview .flow{display:flex;align-items:center;gap:12px;margin:14px 0;flex-wrap:wrap}
  .overview .flow .box{background:#fff;border:2px solid var(--b);border-radius:8px;padding:10px 14px;text-align:center;font-weight:700;font-size:.88rem}
  .overview .flow .arrow{font-size:1.2rem;color:var(--l)}
  .overview ul{margin:8px 0 0 18px}
  .overview li{margin:3px 0;font-size:.85rem}
  .note{border-radius:8px;padding:12px 16px;margin:18px 0;font-size:.86rem}
  .note.g{background:#eaf7ea;border-left:4px solid var(--g)}
  .note.r{background:#fdedec;border-left-color:var(--r)}
  .footer{margin-top:40px;padding-top:12px;border-top:2px solid #eee;color:var(--l);font-size:.74rem}
</style></head>
<body>
<h1>🚀 接力送 · UE 模型<span class="sub">2026-06-13</span></h1>
<hr>

<!-- ═══════ 营运逻辑 ═══════ -->
<h2>📐 项目营运逻辑</h2>
<div class="overview">
  <h3>做什么</h3>
  <p>美团骑手将外卖送至楼下 → 我方配送员接手，完成<strong>上楼到户</strong>的最后一段配送。骑手省掉爬楼时间，我方赚取二段配送费。</p>

  <h3>怎么运转</h3>
  <div class="flow">
    <div class="box">🏍️ 美团骑手<br><small>送到楼下</small></div>
    <div class="arrow">→</div>
    <div class="box">🙋 楼下指引员<br><small>3h×1人<br>登记餐品、引导骑手</small></div>
    <div class="arrow">→</div>
    <div class="box">🏃 上楼配送员<br><small>2-3h×N人<br>高峰期接力送上楼</small></div>
    <div class="arrow">→</div>
    <div class="box">✅ 到户<br><small>完成配送</small></div>
  </div>

  <h3>怎么赚钱</h3>
  <ul>
    <li><strong>订单结算：</strong>每单 ¥2.50（骑手付 ¥2.00 + 美团补贴 ¥0.50，长期有效）</li>
    <li><strong>人头补贴：</strong>每天 (总人数−1) × ¥80，条件：点位营业 ≥3h、人均配送 ≥20单</li>
    <li><strong>前两周引流期：</strong>美团额外补贴骑手端，骑手仅付 ¥1.00，我方仍结算 ¥2.50</li>
  </ul>

  <h3>怎么排班</h3>
  <ul>
    <li><strong>楼下指引员：</strong>3h×1人（固定），负责楼下登记引导，闲时协助配送。满足点位 ≥3h 考勤要求</li>
    <li><strong>上楼配送员：</strong>2-3h×N人（弹性），仅覆盖午高峰时段。单量增长时优先增加配送员人数，而非延长工时</li>
    <li>每人每小时约处理 12 单（基于renxiao实测数据），产能随人数线性增长</li>
  </ul>

  <h3>补贴节奏（两阶段）</h3>
  <table style="font-size:.82rem">
  <thead><tr><th>阶段</th><th>时长</th><th>骑手付费</th><th>我方结算</th><th>美团每单补贴</th><th>人头补贴</th></tr></thead>
  <tbody>
  <tr><td>Phase 1 · 引流期</td><td>前2周</td><td>¥1.00</td><td>¥2.50</td><td>¥1.50</td><td>(T−1)×¥80 ✅</td></tr>
  <tr><td>Phase 2 · 长期补贴</td><td>长期</td><td>¥2.00</td><td>¥2.50</td><td>¥0.50</td><td>(T−1)×¥80 ✅</td></tr>
  </tbody></table>
</div>

<!-- ═══════ Part 1: 有补贴UE ═══════ -->
<h2>📋 Part 1 · 有补贴 UE</h2>
<div class="info"><span class="tag g">结算 ¥2.50/单</span><span class="tag b">人头补贴 (T−1)×¥80/天</span>补贴条件：人均 ≥20单 · 营业 ≥3h</div>
<table>
<thead><tr>
  <th>日均单量</th><th>排班</th><th>人数</th><th>人均</th>
  <th>日补贴</th><th>月订单收入</th><th>月人头补贴</th><th>月总成本</th><th>月毛利</th><th>毛利率</th><th>补贴</th>
</tr></thead><tbody>
"""

for r in results:
    m = r["月毛利"]
    mr = float(r["毛利率"].rstrip("%"))
    cls = "g" if mr >= 15 else ("t" if mr >= 0 else "l")
    orders = r["日均单量"]
    monthly_order_rev = orders * 2.5 * DAYS
    monthly_sub = r["日补贴"] * DAYS
    monthly_cost = monthly_order_rev + monthly_sub - m

    html += f"""<tr class="{cls}">
<td>{orders}</td><td>{r['配置']}</td><td>{r['人数']}</td><td>{r['人均']}</td>
<td>¥{r['日补贴']:.0f}</td>
<td>¥{monthly_order_rev:,.0f}</td><td>¥{monthly_sub:,.0f}</td><td>¥{monthly_cost:,.0f}</td>
<td style="font-weight:700;color:{'var(--g)' if m>=0 else 'var(--r)'}">{m:+,.0f}</td>
<td style="color:{'var(--g)' if mr>=0 else 'var(--r)'}">{mr:+.1f}%</td>
<td>{r['补贴达标']}</td>
</tr>"""

html += """</tbody></table>
<div class="note g"><strong>💡 有补贴阶段：</strong>40单盈亏平衡，60单月利¥2,900，100单月利¥7,100，200单¥17,600，500单¥49,100。每增1个配送员(2h)，日补贴+¥80、成本仅+¥60，净贡献+¥20/天。<strong>规模经济。</strong></div>

<!-- ═══════ Part 2: 兼职提效对UE的影响 ═══════ -->
<h2>📋 Part 2 · 兼职每小时提效对整体UE的影响</h2>
<div class="info">上楼配送员人均产能从<strong>12单/h</strong>提升至<strong>15单/h</strong>、<strong>18单/h</strong>时，整体UE变化。提效路径：路线优化、电梯优先级、熟手效应。</div>
<table>
<thead><tr>
  <th>日均单量</th>
  <th>人数 (12)</th><th>月毛利 (12)</th><th>利率 (12)</th>
  <th>人数 (15)</th><th>月毛利 (15)</th><th>利率 (15)</th>
  <th>人数 (18)</th><th>月毛利 (18)</th><th>利率 (18)</th>
</tr></thead><tbody>
"""

for orders in VOLUMES:
    row = eff_results[orders]
    r12, r15, r18 = row[0], row[1], row[2]

    def cell(val, fmt_str):
        if val is None:
            return "N/A"
        return fmt_str.format(val)

    cls12 = "g" if r12 and r12["利率"] >= 15 else ("t" if r12 and r12["利率"] >= 0 else "l")
    cls15 = "g" if r15 and r15["利率"] >= 15 else ("t" if r15 and r15["利率"] >= 0 else "l")
    cls18 = "g" if r18 and r18["利率"] >= 15 else ("t" if r18 and r18["利率"] >= 0 else "l")

    # Use the best class among the three for row coloring
    best_margin = max(
        r12["利率"] if r12 else -999,
        r15["利率"] if r15 else -999,
        r18["利率"] if r18 else -999
    )
    cls = "g" if best_margin >= 15 else ("t" if best_margin >= 0 else "l")

    def profit_cell(r_data):
        if r_data is None:
            return '<td>N/A</td>'
        m = r_data["月利"]
        color = "var(--g)" if m >= 0 else "var(--r)"
        return f'<td style="font-weight:700;color:{color}">{m:+,.0f}</td>'

    def margin_cell(r_data):
        if r_data is None:
            return '<td>N/A</td>'
        mr = r_data["利率"]
        color = "var(--g)" if mr >= 0 else "var(--r)"
        return f'<td style="color:{color}">{mr:+.1f}%</td>'

    html += f"""<tr class="{cls}">
<td>{orders}</td>
<td>{r12['人数'] if r12 else 'N/A'}</td>{profit_cell(r12)}{margin_cell(r12)}
<td>{r15['人数'] if r15 else 'N/A'}</td>{profit_cell(r15)}{margin_cell(r15)}
<td>{r18['人数'] if r18 else 'N/A'}</td>{profit_cell(r18)}{margin_cell(r18)}
</tr>"""

# 计算关键节点的提效差异（使用利润最优配置下的对比：同样人数，提效后可用更短工时）
# Part 1 利润最优配置在不同 CAP 下的对比
v100_p1 = best_cfg(100, 2.5, True, 12)
v100_p1_15 = best_cfg(100, 2.5, True, 15)
v100_p1_18 = best_cfg(100, 2.5, True, 18)
v200_p1 = best_cfg(200, 2.5, True, 12)
v200_p1_15 = best_cfg(200, 2.5, True, 15)
v200_p1_18 = best_cfg(200, 2.5, True, 18)
v500_p1 = best_cfg(500, 2.5, True, 12)
v500_p1_15 = best_cfg(500, 2.5, True, 15)
v500_p1_18 = best_cfg(500, 2.5, True, 18)

# 利润最优配置下，补贴激励倾向于多配人，提效后最佳配置可能不变
# 但在同等利润下，提效创造了富余产能，可支撑更高的单量峰值
# 真正的提效价值体现在：同等人力下可承接更多单量

# 计算各体量下的有效产能利用率
def capacity_utilization(orders, cap):
    """同等利润最优配置下的产能利用率"""
    b = best_cfg(orders, 2.5, True, cap)
    if not b:
        return None
    n, h, tp, th, cost, sub, dp, ok, opp = b
    max_cap = cap * n * h + 4 * h + 18
    return orders / max_cap * 100 if max_cap > 0 else 0

util_12_100 = capacity_utilization(100, 12)
util_15_100 = capacity_utilization(100, 15)
util_18_100 = capacity_utilization(100, 18)
util_12_200 = capacity_utilization(200, 12)
util_15_200 = capacity_utilization(200, 15)
util_18_200 = capacity_utilization(200, 18)
util_12_500 = capacity_utilization(500, 12)
util_15_500 = capacity_utilization(500, 15)
util_18_500 = capacity_utilization(500, 18)

html += """</tbody></table>
<div class="note g">
  <strong>📈 提效杠杆效应 — 最小可行配置视角：</strong><br>
  上表为<strong>最小工时可行配置</strong>（非利润最优），单独衡量提效对人力需求的压缩效果。<br><br>
  <strong>提效至15单/h（+25%）：</strong>中低单量段人力需求基本不变；高单量段（200+）可减少1-6人，工时压缩15-25%。<br>
  <strong>提效至18单/h（+50%）：</strong>大部分单量段可减少1-2人或压缩工时，200单以下效果显著；500单段从17人降至10人，工时从43h降至30h。<br><br>
  <strong>⚠️ 补贴激励的抵消效应：</strong>当前补贴结构下（每增1人·2h，成本+¥60，补贴+¥80，净赚¥20），利润最优解倾向<strong>多配人</strong>。提效节省的人力如果直接减员，会同时损失补贴收入，净效果可能为负。<br>
  因此提效的<strong>真正价值</strong>不在减员，而在：<br>
  ① <strong>产能富余：</strong>同等配置下产能利用率从CAP12的80-90%降至CAP18的55-65%，可承接单量高峰而不崩溃<br>
  ② <strong>增长弹性：</strong>单量增长时无需等比增人，边际成本递减<br>
  ③ <strong>降补贴后的生存能力：</strong>一旦补贴退出，高效率是盈亏平衡的唯一出路<br>
</div>
"""

html += """<div class="footer"><p>参数: 时薪¥30/h · 月物料¥100 · 人均产能12单/h（基于renxiao实测6点位571单，成熟点位中位12.9单/h） · 补贴门槛人均≥20单 · 当前仅展示有补贴场景 · 2026-06-14</p></div>
</body></html>"""

with open(f"{OUTPUT_DIR}/simple_ue.html", "w", encoding="utf-8") as f:
    f.write(html)

pd.DataFrame(results).to_csv(f"{OUTPUT_DIR}/simple_ue.csv", index=False, encoding="utf-8-sig")

print("\n输出: simple_ue.html, simple_ue.csv")
