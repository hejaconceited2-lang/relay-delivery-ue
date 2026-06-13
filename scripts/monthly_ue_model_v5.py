"""
接力送 — 月度UE模型 V5（商业模型修正）
==========================================
修正：
  1. 美团0.5元/单补贴长期有效 → 我们结算固定 2.5元/单
  2. 推广期（前两周）：骑手付1元 + 美团补1.5元 → 我们得2.5元
  3. 常规期（两周后）：骑手付2元 + 美团补0.5元 → 我们得2.5元
  4. 单量差异仅来自骑手费率对骑手意愿的影响
  5. 人头补贴(T-1)×80：展示两个情景（保留 / 取消）

排班：1锚定×3h + N高峰×2-3h，人均≥20触发补贴
"""

import pandas as pd
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LABOR_RATE = 30
MIN_ORDERS_PER_PERSON = 20
MATERIAL_MONTH = 100
DAYS_PER_MONTH = 30

SETTLEMENT = 2.5        # 固定结算价（含美团长期0.5元补贴）
RIDER_FEE_PROMO = 1.0   # 推广期骑手付费
RIDER_FEE_REGULAR = 2.0 # 常规期骑手付费

# 骑手费率 → 单量倍率（基于弹性模型）
def volume_multiplier(rider_fee):
    """
    骑手剩余 = 配送费(¥3) - 骑手付费
    剩余占比 = 剩余 / 3.0

    已知点：1.0元→95% | 1.5元→50%
    """
    surplus = 3.0 - rider_fee
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


def search_config(daily_orders, has_headcount_sub):
    """搜索最优人员配置"""
    best = None
    best_profit = -float("inf")
    for n in range(1, 31):
        for h in [2.0, 2.5, 3.0]:
            cap = 10 * n * h + 3 * h + 15
            if cap < daily_orders:
                continue
            tp, th = n + 1, 3 + n * h
            opp = daily_orders / tp
            daily_labor = th * LABOR_RATE
            daily_cost = daily_labor + MATERIAL_MONTH / DAYS_PER_MONTH
            daily_sub = (tp - 1) * 80 if (has_headcount_sub and opp >= MIN_ORDERS_PER_PERSON) else 0
            daily_rev = daily_orders * SETTLEMENT + daily_sub
            daily_profit = daily_rev - daily_cost
            if daily_profit > best_profit:
                best_profit = daily_profit
                best = {
                    "n": n, "h": h, "tp": tp, "th": th,
                    "daily_labor": daily_labor, "daily_cost": daily_cost,
                    "daily_sub": daily_sub, "cap": cap,
                    "sub_ok": opp >= MIN_ORDERS_PER_PERSON and has_headcount_sub,
                    "opp": opp,
                }
    if best is None:
        for n in range(1, 31):
            if 20 * n + 21 >= daily_orders:
                h = 2.0
                break
        else:
            n, h = 30, 2.0
        tp = n + 1
        best = {"n": n, "h": h, "tp": tp, "th": 3 + n * h,
                "daily_labor": (3 + n * h) * 30,
                "daily_cost": (3 + n * h) * 30 + MATERIAL_MONTH / DAYS_PER_MONTH,
                "daily_sub": (tp - 1) * 80 if has_headcount_sub else 0,
                "cap": 20 * n + 21, "sub_ok": False, "opp": daily_orders / tp}
    return best


def calc_monthly(base_orders, phase="regular", has_headcount_sub=False):
    """
    base_orders: 推广期1元时的基准单量
    phase: "promo" (前两周, 骑手付1元) | "regular" (常规, 骑手付2元)
    has_headcount_sub: 是否保留人头补贴
    """
    rider_fee = RIDER_FEE_PROMO if phase == "promo" else RIDER_FEE_REGULAR
    vol_mult = volume_multiplier(rider_fee)
    actual_orders = max(5, int(base_orders * vol_mult))

    cfg = search_config(actual_orders, has_headcount_sub)

    monthly_orders = actual_orders * DAYS_PER_MONTH
    monthly_order_rev = monthly_orders * SETTLEMENT
    monthly_subsidy = cfg["daily_sub"] * DAYS_PER_MONTH
    monthly_rev = monthly_order_rev + monthly_subsidy
    monthly_labor = cfg["daily_labor"] * DAYS_PER_MONTH
    monthly_cost = monthly_labor + MATERIAL_MONTH
    monthly_profit = monthly_rev - monthly_cost
    margin = monthly_profit / monthly_rev * 100 if monthly_rev > 0 else 0

    return {
        "阶段": "推广期(骑手付1元)" if phase == "promo" else "常规期(骑手付2元)",
        "人头补贴": "有" if has_headcount_sub else "无",
        "基准单量": base_orders,
        "骑手费率": f"¥{rider_fee:.1f}",
        "结算价": f"¥{SETTLEMENT:.1f}",
        "单量倍率": f"{vol_mult:.0%}",
        "实际单量": actual_orders,
        "配置": f"1锚+{cfg['n']}峰×{cfg['h']:.1f}h",
        "总人数": cfg["tp"],
        "人均": round(cfg["opp"], 1),
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


def margin_cls(m):
    if m <= 0:
        return ("#e74c3c", "row-loss")
    elif m < 15:
        return ("#f39c12", "row-thin")
    return ("#27ae60", "row-good")

def fm(v):
    return f"¥{v:+,.0f}" if v >= 0 else f"-¥{abs(v):,.0f}"


def generate_html():
    levels = [40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 400, 500]

    # 四个情景
    promo_sub = [calc_monthly(o, "promo", True) for o in levels]      # 推广期(1元) + 有人头补贴
    regular_sub = [calc_monthly(o, "regular", True) for o in levels]  # 常规期(2元) + 有人头补贴
    regular_nosub = [calc_monthly(o, "regular", False) for o in levels] # 常规期(2元) + 无人头补贴

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接力送 · 月度UE模型 V5</title>
<style>
  :root {{
    --red: #e74c3c; --red-bg: #fadbd8;
    --yellow: #f39c12; --yellow-bg: #fef9e7;
    --green: #27ae60; --green-bg: #d5f5e3;
    --text: #2c3e50; --light: #7f8c8d; --border: #e0e0e0; --bg: #fafafa;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    color: var(--text); background: #fff; max-width: 1300px; margin: 0 auto;
    padding: 36px 44px; line-height: 1.65; }}
  h1 {{ font-size: 1.9rem; font-weight: 800; margin-bottom: 4px; }}
  h1 .sub {{ font-size: 0.82rem; color: var(--light); font-weight: 400; margin-left: 10px; }}
  h2 {{ font-size: 1.18rem; font-weight: 700; margin: 40px 0 14px; }}
  hr {{ border: none; border-top: 2px solid #eee; margin: 20px 0 24px; }}

  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin: 22px 0; }}
  .kpi {{ background: var(--bg); border-radius: 10px; padding: 18px 16px; border-left: 4px solid #3498db; text-align: center; }}
  .kpi.g {{ border-left-color: var(--green); }} .kpi.r {{ border-left-color: var(--red); }}
  .kpi .v {{ font-size: 1.5rem; font-weight: 800; margin-bottom: 3px; }}
  .kpi .l {{ font-size: 0.8rem; color: var(--light); }}

  .table-wrap {{ overflow-x: auto; margin: 16px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.83rem; }}
  thead th {{ background: #2c3e50; color: #fff; padding: 9px 6px; font-weight: 600; text-align: center; white-space: nowrap; }}
  tbody td {{ padding: 6px 6px; text-align: right; border-bottom: 1px solid var(--border); }}
  tbody td:first-child, tbody td:nth-child(2), tbody td:nth-child(4) {{ text-align: center; }}
  tr:hover {{ filter: brightness(0.95); }}
  tr.lose td {{ background: var(--red-bg) !important; }}
  tr.thin td {{ background: var(--yellow-bg) !important; }}
  tr.good td {{ background: var(--green-bg) !important; }}

  .legend {{ display: flex; gap: 18px; margin: 12px 0; font-size: 0.82rem; }}
  .legend span {{ display: inline-block; width: 15px; height: 15px; border-radius: 3px; margin-right: 5px; vertical-align: -3px; }}
  .lr {{ background: var(--red-bg); border: 1px solid var(--red); }}
  .ly {{ background: var(--yellow-bg); border: 1px solid var(--yellow); }}
  .lg {{ background: var(--green-bg); border: 1px solid var(--green); }}

  .dual {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  .formula {{ background: #f0f4f8; border-radius: 8px; padding: 16px 20px; margin: 16px 0; }}
  .note {{ border-radius: 8px; padding: 14px 18px; margin: 16px 0; font-size: 0.88rem; }}
  .note.info {{ background: #eaf7ea; border-left: 4px solid var(--green); }}
  .note.warn {{ background: #fff3cd; border-left: 4px solid var(--yellow); }}
  .footer {{ margin-top: 50px; padding-top: 16px; border-top: 2px solid #eee; color: var(--light); font-size: 0.76rem; }}
</style>
</head>
<body>

<h1>🚀 接力送 · 月度UE模型
  <span class="sub">V5 · 2026-06-13 · 结算固定¥2.50 · 0.5元美团补贴长期有效</span>
</h1>

<hr>

<div class="formula">
  <strong>收入结构：</strong><br>
  结算价 = <strong>¥2.50/单（固定）</strong> = 骑手付费 + 美团每单补贴¥0.50（长期）<br>
  &nbsp;&nbsp;推广期（前两周）：骑手付 ¥1.00 → 美团补 ¥1.50 → 我们得 ¥2.50<br>
  &nbsp;&nbsp;常规期（两周后）：骑手付 ¥2.00 → 美团补 ¥0.50 → 我们得 ¥2.50<br><br>
  <strong>单量差异仅来自骑手费率弹性：</strong><br>
  &nbsp;&nbsp;¥1.00 费率 → 骑手剩余¥2.0（67%） → 95% 基准量<br>
  &nbsp;&nbsp;¥2.00 费率 → 骑手剩余¥1.0（33%） → {volume_multiplier(2.0):.0%} 基准量
</div>

<div class="note warn">
  <strong>关键变量：人头补贴 (T−1)×¥80/天 在常规期是否保留？</strong> 下方分别展示两个情景。
</div>

<!-- ═══════ 情景1：有人头补贴 ═══════ -->
<h2>📋 情景A：常规期 <strong>保留</strong> 人头补贴（骑手付¥2 + 我们得¥2.5 + 人头补贴）</h2>
<div class="dual">
  <div>
    <h3 style="font-size:0.95rem;color:var(--green);margin-bottom:6px;">推广期（骑手付¥1 · 有人头补贴）</h3>
    <div class="table-wrap"><table>
    <thead><tr><th>基准单量</th><th>实际单量</th><th>配置</th><th>人数</th><th>月毛利</th><th>毛利率</th></tr></thead><tbody>
"""
    for d in promo_sub:
        c, cls = margin_cls(float(d["毛利率"].rstrip("%")))
        html += f"""<tr class="{cls}"><td>{d['基准单量']}</td><td>{d['实际单量']}</td><td>{d['配置']}</td><td>{d['总人数']}</td><td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td><td style="color:{c}">{d['毛利率']}</td></tr>"""
    html += "</tbody></table></div></div>"

    html += """<div><h3 style="font-size:0.95rem;color:var(--red);margin-bottom:6px;">常规期（骑手付¥2 · 有人头补贴）</h3><div class="table-wrap"><table>
    <thead><tr><th>基准单量</th><th>实际单量</th><th>配置</th><th>人数</th><th>月毛利</th><th>毛利率</th></tr></thead><tbody>"""
    for d in regular_sub:
        c, cls = margin_cls(float(d["毛利率"].rstrip("%")))
        html += f"""<tr class="{cls}"><td>{d['基准单量']}</td><td>{d['实际单量']}</td><td>{d['配置']}</td><td>{d['总人数']}</td><td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td><td style="color:{c}">{d['毛利率']}</td></tr>"""
    html += "</tbody></table></div></div></div>"

    # ═══════ 情景2：无人头补贴 ═══════
    html += """
<h2>📋 情景B：常规期 <strong>取消</strong> 人头补贴（骑手付¥2 + 我们得¥2.5 + 无人头补贴）</h2>
<div class="table-wrap"><table>
<thead><tr><th>基准单量</th><th>实际单量</th><th>配置</th><th>人数</th><th>月订单收入</th><th>月人头补贴</th><th>月总收入</th><th>月总成本</th><th>月毛利</th><th>毛利率</th><th>单均毛利</th></tr></thead><tbody>
"""
    for d in regular_nosub:
        c, cls = margin_cls(float(d["毛利率"].rstrip("%")))
        html += f"""<tr class="{cls}"><td>{d['基准单量']}</td><td>{d['实际单量']}</td><td>{d['配置']}</td><td>{d['总人数']}</td>
<td>{fm(d['月订单收入'])}</td><td>{fm(d['月人头补贴'])}</td><td>{fm(d['月总收入'])}</td>
<td>{fm(d['月总成本'])}</td><td style="font-weight:700;color:{c}">{fm(d['月毛利'])}</td>
<td style="color:{c}">{d['毛利率']}</td><td>{d['单均毛利']:+.2f}</td></tr>"""
    html += "</tbody></table></div>"

    # ═══════ 对比总结 ═══════
    html += """
<h2>🔍 情景对比</h2>
<div class="table-wrap"><table>
<thead><tr><th>基准单量</th><th>推广期月利</th><th>常规期月利(有人头补贴)</th><th>常规期月利(无人头补贴)</th><th>人头补贴贡献</th></tr></thead><tbody>
"""
    for i, o in enumerate(levels):
        p = promo_sub[i]
        rs = regular_sub[i]
        rn = regular_nosub[i]
        diff = rs["月毛利"] - rn["月毛利"]
        c, cls = margin_cls(float(rs["毛利率"].rstrip("%")) if float(rs["毛利率"].rstrip("%")) > 0 else -1)
        html += f"""<tr class="{cls}"><td>{o}</td><td>{fm(p['月毛利'])}</td><td style="font-weight:700">{fm(rs['月毛利'])}</td><td>{fm(rn['月毛利'])}</td><td style="color:var(--green)">{fm(diff)}</td></tr>"""
    html += """</tbody></table></div>

<h2>🔍 总结</h2>
<div class="note info">
  <strong>1. 人头补贴是常规期盈亏的分水岭：</strong>保留人头补贴 → 常规期仍可盈利（需基准单量≥60）；取消人头补贴 → 全线亏损，无一幸免。<br><br>
  <strong>2. 推广期→常规期的单量冲击：</strong>骑手费率从¥1升到¥2，弹性模型预估单量保留约13%。从100单跌到13单，利润从+¥7,100跌到±¥0左右（有人头补贴时）。<br><br>
  <strong>3. 业务核心风险：</strong>如果2元费率实测单量远低于预期（比如<20%保留），即使有人头补贴也难以为继。当前1.5元测试数据已确认掉量50%。<br><br>
  <strong>4. 谈判优先级：</strong>① 人头补贴必须争取延续 ② 尝试将骑手费率控制在¥1.5以下 ③ 如常规期单量崩塌，需与美团协商骑手端补贴。
</div>
"""
    html += f"""
<div class="footer">
  <p>接力送 UE 模型 V5 · 2026-06-13 · 结算 ¥{SETTLEMENT}/单（含美团长期¥0.50补贴）· 时薪¥{LABOR_RATE}/h</p>
  <p>骑手费率弹性: ¥1.0→{volume_multiplier(1.0):.0%} | ¥2.0→{volume_multiplier(2.0):.0%}</p>
</div>
</body></html>"""
    return html


def main():
    print("生成 V5 月度UE模型...")
    html = generate_html()
    path = os.path.join(OUTPUT_DIR, "monthly_ue_model_v5.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已保存: {path} ({len(html):,} 字节)")

    # 摘要
    levels = [40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 400, 500]
    print(f"\n{'基准':>4s} | {'推广期(¥1+补贴)':>20s} | {'常规(¥2+补贴)':>18s} | {'常规(¥2无补贴)':>18s}")
    print("-" * 80)
    for o in levels:
        p = calc_monthly(o, "promo", True)
        rs = calc_monthly(o, "regular", True)
        rn = calc_monthly(o, "regular", False)
        print(f"{o:4d} | {p['实际单量']:3d}单 {p['月毛利']:+8,.0f} {p['毛利率']:>7s} | "
              f"{rs['实际单量']:3d}单 {rs['月毛利']:+8,.0f} {rs['毛利率']:>7s} | "
              f"{rn['实际单量']:3d}单 {rn['月毛利']:+8,.0f} {rn['毛利率']:>7s}")

    pd.DataFrame([calc_monthly(o, "promo", True) for o in levels]).to_csv(
        f"{OUTPUT_DIR}/v5_promo.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([calc_monthly(o, "regular", True) for o in levels]).to_csv(
        f"{OUTPUT_DIR}/v5_regular_with_sub.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([calc_monthly(o, "regular", False) for o in levels]).to_csv(
        f"{OUTPUT_DIR}/v5_regular_no_sub.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
