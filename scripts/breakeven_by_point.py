"""
接力送 — 各点位盈亏平衡单量计算（不考虑骑手意愿）
==================================================
目标：针对每个点位，计算：
  1. 当前配置下的盈亏平衡单量
  2. 利润最大化时需跑到的单量（即产能上限）
  3. 优化配置（裁人或缩时）后的盈亏平衡单量

核心逻辑：
  - 日固定成本 = 人力 + 物料
  - 日收入 = 单量 × 结算价 + 80（若人均>20且营业≥3h）
  - 盈亏平衡：收入 = 成本

场景：
  A. 推广期（前两周）：结算 2.5 元/单，骑手付 1 元
  B. 常规期：结算 2.0 元/单，骑手付 2 元
"""

import pandas as pd
import numpy as np
from tabulate import tabulate
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# ============================================================
# 参数
# ============================================================
LABOR_RATE = 30
SUBSIDY = 80
MIN_HOURS = 3.0
MIN_ORDERS_PER_PERSON = 20
MATERIAL_DAILY = 100 / 30
CAPACITY_PER_HOUR = 8  # 每配送人员每小时产能

# ============================================================
# 各点位当前配置
# ============================================================
POINTS = {
    "万科欧泊":   {"staff": 3, "hours": 3.0, "latest_orders": 46},
    "绿地星玥":   {"staff": 5, "hours": 6.5, "latest_orders": 151},
    "和业广场":   {"staff": 2, "hours": 3.0, "latest_orders": 36},
    "华林国际C馆": {"staff": 2, "hours": 3.0, "latest_orders": 3},
    "万菱广场":   {"staff": 2, "hours": 3.0, "latest_orders": 41},
    "金鹰大厦":   {"staff": 2, "hours": 3.0, "latest_orders": 20},
}

# ============================================================
# 计算
# ============================================================

def daily_fixed_cost(staff, hours):
    return staff * hours * LABOR_RATE + MATERIAL_DAILY


def max_capacity(staff, hours):
    """该配置下每日最大可处理单量"""
    if staff == 2:
        delivery_equiv = 1.6  # 2人时楼下可协助
    else:
        delivery_equiv = staff - 1
    return delivery_equiv * hours * CAPACITY_PER_HOUR


def calc_profit(staff, hours, orders, settlement):
    """给定配置和单量，计算日利润"""
    order_rev = orders * settlement
    eligible = (hours >= MIN_HOURS and orders / staff > MIN_ORDERS_PER_PERSON)
    sub = SUBSIDY if eligible else 0
    total_rev = order_rev + sub
    cost = daily_fixed_cost(staff, hours)
    return total_rev - cost, eligible


def find_breakeven(staff, hours, settlement):
    """
    找到盈亏平衡单量（精确到整数）。
    考虑补贴门檻：人均>20单时触发80元补贴。
    """
    cost = daily_fixed_cost(staff, hours)
    cap = max_capacity(staff, hours)
    subsidy_threshold = int(staff * MIN_ORDERS_PER_PERSON) + 1  # 刚好>20人均

    # 情况1：无补贴，线性增长
    be_no_sub = cost / settlement

    # 情况2：有补贴（需先达到人均>20）
    if subsidy_threshold * settlement + SUBSIDY >= cost:
        # 达到补贴门槛即盈利
        be_with_sub = subsidy_threshold
    else:
        # 补贴门槛处仍亏损，需更多单量
        extra = (cost - (subsidy_threshold * settlement + SUBSIDY)) / settlement
        be_with_sub = subsidy_threshold + extra

    # 判断哪个BE在实际可达成范围内
    be_effective = None
    be_note = ""

    if be_no_sub <= cap:
        be_effective = be_no_sub
        be_note = "无补贴区"
    elif be_with_sub <= cap:
        be_effective = be_with_sub
        be_note = f"需达补贴门槛({subsidy_threshold}单)"
    else:
        # 产能不够，即使跑到极限也亏
        profit_at_cap, eligible = calc_profit(staff, hours, int(cap), settlement)
        be_effective = None
        be_note = f"产能不足，满产仍亏{abs(profit_at_cap):.0f}元"

    return {
        "be_no_sub": be_no_sub,
        "be_with_sub": be_with_sub,
        "be_effective": be_effective,
        "be_note": be_note,
        "capacity": cap,
        "subsidy_threshold": subsidy_threshold,
        "cost": cost,
    }


def find_optimal_config_for_point(orders_target, settlement):
    """
    给定目标单量，找利润最高的配置。
    搜索 2-8人, 3-8h 的所有组合。
    """
    best = None
    best_profit = -float('inf')
    for staff in range(2, 9):
        for hours in np.arange(3.0, 8.5, 0.5):
            cap = max_capacity(staff, hours)
            if cap < orders_target:
                continue
            profit, eligible = calc_profit(staff, hours, orders_target, settlement)
            if profit > best_profit:
                best_profit = profit
                best = {
                    "staff": staff, "hours": hours,
                    "cost": daily_fixed_cost(staff, hours),
                    "profit": profit, "eligible": eligible,
                    "capacity": cap,
                }
    return best


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 80)
    print("接力送 — 各点位盈亏平衡单量")
    print("=" * 80)
    print(f"""
参数：工时 {LABOR_RATE}元/h | 人头补贴 {SUBSIDY}元/天 | 补贴门槛 人均>{MIN_ORDERS_PER_PERSON}单
     产能 ≈ {CAPACITY_PER_HOUR}单/配送人/h | 物料摊销 {MATERIAL_DAILY:.1f}元/天
""")

    # ================================================================
    # Part 1: 现有点位分析
    # ================================================================
    print("─" * 60)
    print("【现有点位：当前配置下的盈亏平衡分析】")
    print("─" * 60)

    rows = []
    for name, cfg in POINTS.items():
        staff = cfg["staff"]
        hours = cfg["hours"]
        latest = cfg["latest_orders"]

        cost = daily_fixed_cost(staff, hours)
        cap = max_capacity(staff, hours)

        for settlement, slabel in [(2.5, "推广期"), (2.0, "常规期")]:
            be = find_breakeven(staff, hours, settlement)
            profit_now, elig_now = calc_profit(staff, hours, latest, settlement)
            profit_at_cap, elig_cap = calc_profit(staff, hours, int(cap), settlement)

            rows.append({
                "点位": name,
                "场景": slabel,
                "当前配置": f"{staff}人×{hours}h",
                "当前单量": latest,
                "当前日利润": f"{profit_now:+.0f}",
                "当前补贴": "✓" if elig_now else "✗",
                "日固定成本": f"{cost:.0f}",
                "产能上限": f"{cap:.0f}单",
                "无补贴BE": f"{be['be_no_sub']:.0f}单",
                "有补贴BE": f"{be['be_with_sub']:.0f}单",
                "实际需达单量": f"{be['be_effective']:.0f}单" if be['be_effective'] else "无法达成",
                "说明": be['be_note'],
                "满产利润": f"{profit_at_cap:+.0f}",
            })

    df = pd.DataFrame(rows)
    print(tabulate(df, headers="keys", tablefmt="grid", showindex=False,
                   numalign="right", stralign="left"))
    df.to_csv(f"{OUTPUT_DIR}/point_breakeven.csv", index=False, encoding="utf-8-sig")

    # ================================================================
    # Part 2: 最优配置下的盈亏平衡
    # ================================================================
    print("\n" + "─" * 60)
    print("【优化配置后：各点位在不同目标单量下的最优配置与利润】")
    print("─" * 60)

    opt_rows = []
    for name, cfg in POINTS.items():
        latest = cfg["latest_orders"]
        # 测试不同目标单量：当前、+20%、+50%、翻倍
        for mult, label in [(1.0, "当前单量"), (1.2, "+20%"), (1.5, "+50%"), (2.0, "翻倍")]:
            target = int(latest * mult)
            for settlement, slabel in [(2.5, "推广期"), (2.0, "常规期")]:
                opt = find_optimal_config_for_point(target, settlement)
                if opt is None:
                    continue
                opt_rows.append({
                    "点位": name,
                    "场景": slabel,
                    "目标单量": target,
                    "最优配置": f"{opt['staff']}人×{opt['hours']}h",
                    "日成本": f"{opt['cost']:.0f}",
                    "产能利用率": f"{target/opt['capacity']*100:.0f}%",
                    "补贴": "✓" if opt['eligible'] else "✗",
                    "日利润": f"{opt['profit']:+.0f}",
                })

    df_opt = pd.DataFrame(opt_rows)
    print(tabulate(df_opt, headers="keys", tablefmt="grid", showindex=False,
                   numalign="right", stralign="left"))
    df_opt.to_csv(f"{OUTPUT_DIR}/point_optimal_profit.csv", index=False, encoding="utf-8-sig")

    # ================================================================
    # Part 3: 死亡线 — 每个点位关停还是继续
    # ================================================================
    print("\n" + "─" * 60)
    print("【结论速查：各点位盈亏门槛】")
    print("─" * 60)

    summary_rows = []
    for name, cfg in POINTS.items():
        staff = cfg["staff"]
        hours = cfg["hours"]
        latest = cfg["latest_orders"]
        cost = daily_fixed_cost(staff, hours)

        # 最简配置：2人×3h

        # 2人×3h 推广期 BE
        be_min_promo = find_breakeven(2, 3.0, 2.5)
        be_min_regular = find_breakeven(2, 3.0, 2.0)

        # 当前利润
        profit_promo, _ = calc_profit(staff, hours, latest, 2.5)
        profit_regular, _ = calc_profit(staff, hours, latest, 2.0)

        summary_rows.append({
            "点位": name,
            "最新单量": latest,
            "当前配置": f"{staff}人×{hours}h",
            "当前日亏(推广期)": f"{profit_promo:+.0f}",
            "当前日亏(常规期)": f"{profit_regular:+.0f}",
            "最简配置(2人×3h)BE推广期": f"{be_min_promo['be_effective']:.0f}单" if be_min_promo['be_effective'] else "N/A",
            "最简配置(2人×3h)BE常规期": f"{be_min_regular['be_effective']:.0f}单" if be_min_regular['be_effective'] else "N/A",
            "单量缺口(推广期)": f"{max(0, (be_min_promo['be_effective'] or 999) - latest):.0f}单" if be_min_promo['be_effective'] else "N/A",
            "单量缺口(常规期)": f"{max(0, (be_min_regular['be_effective'] or 999) - latest):.0f}单" if be_min_regular['be_effective'] else "N/A",
        })

    df_sum = pd.DataFrame(summary_rows)
    print(tabulate(df_sum, headers="keys", tablefmt="grid", showindex=False,
                   numalign="right", stralign="left"))
    df_sum.to_csv(f"{OUTPUT_DIR}/point_gap_summary.csv", index=False, encoding="utf-8-sig")

    # ================================================================
    # Part 4: 2人×3h 精确盈利区间
    # ================================================================
    print("\n" + "─" * 60)
    print("【2人×3h最简配置：各单量下的精确利润（日成本183元）】")
    print("─" * 60)

    curve_rows = []
    for orders in range(10, 81, 5):
        for settlement, slabel in [(2.5, "推广期"), (2.0, "常规期")]:
            profit, elig = calc_profit(2, 3.0, orders, settlement)
            curve_rows.append({
                "单量": orders,
                "场景": slabel,
                "人均单量": orders / 2,
                "订单收入": orders * settlement,
                "补贴": SUBSIDY if elig else 0,
                "总收入": orders * settlement + (SUBSIDY if elig else 0),
                "日成本": 183,
                "日利润": f"{profit:+.0f}",
                "单均利润": f"{profit/orders:+.2f}" if orders > 0 else "N/A",
                "补贴达标": "✓" if elig else "✗",
            })
    df_curve = pd.DataFrame(curve_rows)
    # 展示推广期
    promo = df_curve[df_curve["场景"] == "推广期"]
    regular = df_curve[df_curve["场景"] == "常规期"]
    print("\n[推广期 2.5元]")
    print(tabulate(promo, headers="keys", tablefmt="grid", showindex=False, numalign="right"))
    print("\n[常规期 2.0元]")
    print(tabulate(regular, headers="keys", tablefmt="grid", showindex=False, numalign="right"))
    df_curve.to_csv(f"{OUTPUT_DIR}/min_config_profit_curve.csv", index=False, encoding="utf-8-sig")

    # ================================================================
    # 最终结论
    # ================================================================
    print("\n" + "=" * 80)
    print("【各点位需要跑到多少单才能盈利】")
    print("=" * 80)

    # 汇总：每个点位需要多少单
    print("""
  假设切换到最简配置（2人×3h，日成本183元）：

  推广期（结算2.5元）：
    盈亏平衡 41单（需拿到人头补贴，人均>20）
    或 73单（无补贴）

  常规期（结算2.0元）：
    盈亏平衡 52单（需拿到人头补贴，人均>20）
    或 92单（无补贴）

  各点位与盈利线的距离：
""")

    for name, cfg in POINTS.items():
        latest = cfg["latest_orders"]
        gap_promo = max(0, 41 - latest)
        gap_regular = max(0, 52 - latest)
        status = "✓ 已达" if latest >= 41 else f"差 {gap_promo} 单"
        status_reg = "✓ 已达" if latest >= 52 else f"差 {gap_regular} 单"

        print(f"  {name:12s}  最新{latest:3d}单  |  推广期BE=41单 {status:8s}  |  常规期BE=52单 {status_reg:8s}")

    print("""
  关键发现：
  - 万科欧泊(46单)、万菱广场(41单) 推广期已触达或接近盈亏平衡
  - 绿地星玥(151单) 单量够但5人成本太高，建议压缩到3-4人
  - 华林国际C馆(3单)、金鹰大厦(20单) 单量差距过大，短期内无望
  - 所有点位常规期(结算2.0元)均需进一步提升单量
""")

    print("\n输出文件:", [
        "point_breakeven.csv",
        "point_optimal_profit.csv",
        "point_gap_summary.csv",
        "min_config_profit_curve.csv",
    ])


if __name__ == "__main__":
    main()
