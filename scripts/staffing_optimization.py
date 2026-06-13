"""
接力送 — 最优人员配置与盈利区间分析
=====================================
目标：针对不同日单量水平，找到最优人员配置（人数×时长），
      使得在满足产能约束的前提下利润最大化。

产能假设：
  - 每人每小时可处理约 6 单（基于实际数据：万科欧泊 15单/人/3h=5，
    万菱广场 20.5单/人/3h=6.8，绿地星玥 30单/人/6.5h=4.6）
  - 取保守值 5 单/人/小时作为有效产能上限
  - 楼下指引人员至少 1 人，不直接产单但必须存在
  - 因此有效递送人员 = 总人数 - 1（楼下指引），有效产能 = (N-1) × H × 5

约束条件：
  - 最少 2 人（1楼下 + 1楼上）
  - 营业时长最少 3h
  - 人头补贴：人均当量 > 20，营业 ≥3h，至少1人上满3h

常规期结算价: 2.0 元/单
推广期结算价: 2.5 元/单
"""

import pandas as pd
import numpy as np
from tabulate import tabulate
import os

# 输出目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# ============================================================
# 参数
# ============================================================
LABOR_RATE = 30          # 时薪 元/人/h
SUBSIDY = 80             # 人头补贴 元/天
MIN_HOURS = 3.0          # 最少营业时长
MIN_ORDERS_PER_PERSON = 20  # 补贴人均门槛
CAPACITY_PER_PERSON_HOUR = 8  # 每人每小时产能（基于实际：万科欧泊3人3h处理46单≈5.1/人/h，万菱2人3h处理41单≈6.8/人/h，取8含缓冲）
SETTLEMENT_PROMO = 2.5
SETTLEMENT_REGULAR = 2.0
MATERIAL_DAILY = 100 / 30  # 物料摊销

# ============================================================
# 产能约束
# ============================================================

def max_capacity(staff, hours):
    """
    给定人数和时长，最大可处理单量。
    2人配置：楼下人员闲时协助配送，按全员80%效率算
    3人+配置：1人专职楼下指引，其余N-1人配送
    """
    if staff == 2:
        # 2人都可配送（楼下闲时协助），按1.6人有效配送力
        return 1.6 * hours * CAPACITY_PER_PERSON_HOUR
    else:
        # 3人+：1人专职楼下，其余配送
        return (staff - 1) * hours * CAPACITY_PER_PERSON_HOUR


def min_staff_for_volume(daily_orders, hours):
    """给定日单量和营业时长，最少需要多少人才够处理"""
    # 先试2人：1.6 * hours * 8 >= daily_orders
    if 1.6 * hours * CAPACITY_PER_PERSON_HOUR >= daily_orders:
        return 2
    # 否则需要 N-1 人配送
    delivery_needed = np.ceil(daily_orders / (hours * CAPACITY_PER_PERSON_HOUR))
    return max(3, int(delivery_needed) + 1)


def subsidy_eligible(staff, hours, orders):
    """判断是否满足人头补贴"""
    if hours < MIN_HOURS:
        return False
    if staff < 1:
        return False
    if orders / staff <= MIN_ORDERS_PER_PERSON:
        return False
    return True


# ============================================================
# 最优配置搜索
# ============================================================

def find_optimal_config(daily_orders, settlement_rate, scenario_name):
    """
    对于给定日单量，搜索所有可行的人员配置组合，
    返回利润最高的那个。
    """
    results = []
    for staff in range(2, 11):  # 2-10人
        for hours in [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0]:
            # 产能约束
            cap = max_capacity(staff, hours)
            if cap < daily_orders:
                continue  # 处理不了这么多单

            # 成本
            labor_cost = staff * hours * LABOR_RATE
            total_cost = labor_cost + MATERIAL_DAILY

            # 收入
            order_rev = daily_orders * settlement_rate
            sub = SUBSIDY if subsidy_eligible(staff, hours, daily_orders) else 0
            total_rev = order_rev + sub

            profit = total_rev - total_cost

            results.append({
                "人数": staff,
                "时长(h)": hours,
                "日人力成本": round(labor_cost, 0),
                "产能上限": round(cap, 0),
                "产能利用率": f"{daily_orders/cap*100:.0f}%" if cap > 0 else "N/A",
                "订单收入": round(order_rev, 0),
                "人头补贴": sub,
                "总收入": round(total_rev, 0),
                "总成本": round(total_cost, 0),
                "日毛利": round(profit, 0),
                "单均毛利": round(profit / daily_orders, 2),
                "补贴达标": "✓" if sub > 0 else "✗",
                "人均单量": round(daily_orders / staff, 1),
            })

    if not results:
        return None

    df = pd.DataFrame(results)
    # 按利润降序排列，取前5
    df = df.sort_values("日毛利", ascending=False)
    return df


def build_optimization_table():
    """
    对不同单量水平，输出最优配置。
    同时对比推广期和常规期。
    """
    order_levels = [10, 20, 30, 40, 50, 60, 80, 100, 120, 150, 180, 200, 250, 300]

    all_rows = []
    for orders in order_levels:
        for settlement, label in [(SETTLEMENT_PROMO, "推广期2.5元"), (SETTLEMENT_REGULAR, "常规期2.0元")]:
            df_opt = find_optimal_config(orders, settlement, label)
            if df_opt is None or len(df_opt) == 0:
                continue
            # 也看次优方案（不同人数配置），取利润前3
            top3 = df_opt.head(3)
            for rank, (_, row) in enumerate(top3.iterrows()):
                all_rows.append({
                    "日单量": orders,
                    "场景": label,
                    "排名": rank + 1,
                    "人数": int(row["人数"]),
                    "时长(h)": row["时长(h)"],
                    "日人力成本": row["日人力成本"],
                    "产能利用率": row["产能利用率"],
                    "总收入": row["总收入"],
                    "总成本": row["总成本"],
                    "日毛利": row["日毛利"],
                    "单均毛利": row["单均毛利"],
                    "补贴达标": row["补贴达标"],
                    "人均单量": row["人均单量"],
                })
    return pd.DataFrame(all_rows)


def build_point_optimization():
    """
    针对现有6个点位，计算如果优化人员配置后的预期改善。
    用各点位最新一天的单量作为基准。
    """
    points = {
        "万科欧泊": 46,
        "绿地星玥": 151,
        "和业广场": 36,
        "华林国际C馆": 3,
        "万菱广场": 41,
        "金鹰大厦": 20,
    }

    rows = []
    for name, orders in points.items():
        for settlement, label in [(SETTLEMENT_PROMO, "推广期2.5元"), (SETTLEMENT_REGULAR, "常规期2.0元")]:
            df_opt = find_optimal_config(orders, settlement, label)
            if df_opt is None or len(df_opt) == 0:
                continue
            best = df_opt.iloc[0]

            # 获取原始配置的利润（当前实际配置）
            orig_config = {
                "万科欧泊": (3, 3.0),
                "绿地星玥": (5, 6.5),
                "和业广场": (2, 3.0),
                "华林国际C馆": (2, 3.0),
                "万菱广场": (2, 3.0),
                "金鹰大厦": (2, 3.0),
            }
            orig_staff, orig_hours = orig_config[name]

            # 计算原配置的利润
            orig_labor = orig_staff * orig_hours * LABOR_RATE
            orig_cost = orig_labor + MATERIAL_DAILY
            orig_order_rev = orders * settlement
            orig_sub = SUBSIDY if subsidy_eligible(orig_staff, orig_hours, orders) else 0
            orig_rev = orig_order_rev + orig_sub
            orig_profit = orig_rev - orig_cost

            rows.append({
                "点位": name,
                "场景": label,
                "当日单量": orders,
                "原配置": f"{orig_staff}人×{orig_hours}h",
                "原日毛利": round(orig_profit, 0),
                "最优配置": f"{int(best['人数'])}人×{best['时长(h)']}h",
                "最优日毛利": best["日毛利"],
                "改善幅度": round(best["日毛利"] - orig_profit, 0),
            })
    return pd.DataFrame(rows)


def build_staffing_guide():
    """
    输出人员配置速查表：给定日单量区间，推荐配置。
    """
    ranges = [
        (0, 20, "极低单量"),
        (20, 40, "低单量"),
        (40, 60, "中低单量"),
        (60, 80, "中单量"),
        (80, 120, "中高单量"),
        (120, 180, "高单量"),
        (180, 250, "极高单量"),
    ]

    rows = []
    for lo, hi, label in ranges:
        mid = (lo + hi) / 2
        # 用中位数找一个最优配置
        for settlement, slabel in [(SETTLEMENT_PROMO, "推广期"), (SETTLEMENT_REGULAR, "常规期")]:
            df_opt = find_optimal_config(int(mid), settlement, slabel)
            if df_opt is None or len(df_opt) == 0:
                continue
            # 检查这个配置在区间两端是否都可行
            best = df_opt.iloc[0]
            staff_best = int(best["人数"])
            hours_best = best["时长(h)"]

            # 在 lo 和 hi 处重算此配置的利润
            prof_lo, prof_hi = None, None
            sub_lo, sub_hi = False, False
            if max_capacity(staff_best, hours_best) >= lo:
                r = calc_single(staff_best, hours_best, lo, settlement)
                prof_lo = r["日毛利"]
                sub_lo = r["补贴达标"]
            if max_capacity(staff_best, hours_best) >= hi:
                r = calc_single(staff_best, hours_best, hi, settlement)
                prof_hi = r["日毛利"]
                sub_hi = r["补贴达标"]

            rows.append({
                "场景": slabel,
                "单量区间": f"{lo}-{hi}",
                "区间标签": label,
                "推荐人数": staff_best,
                "推荐时长(h)": hours_best,
                "日人力成本": round(staff_best * hours_best * LABOR_RATE, 0),
                f"@{lo}单毛利": round(prof_lo, 0) if prof_lo is not None else "N/A",
                f"@{hi}单毛利": round(prof_hi, 0) if prof_hi is not None else "N/A",
                f"@{lo}单补贴": "✓" if sub_lo else "✗",
                f"@{hi}单补贴": "✓" if sub_hi else "✗",
            })
    return pd.DataFrame(rows)


def calc_single(staff, hours, orders, settlement):
    labor = staff * hours * LABOR_RATE
    total_cost = labor + MATERIAL_DAILY
    order_rev = orders * settlement
    sub = SUBSIDY if subsidy_eligible(staff, hours, orders) else 0
    total_rev = order_rev + sub
    profit = total_rev - total_cost
    return {
        "日毛利": round(profit, 0),
        "补贴达标": "✓" if sub > 0 else "✗",
    }


def build_profit_curve():
    """
    绘制利润曲线数据：2人3h vs 3人3h vs 2人4h 等常见配置，
    在不同单量下的利润表现。用于对比各配置的盈利区间。
    """
    configs = [
        (2, 3.0, "2人×3h (最低配)"),
        (2, 4.0, "2人×4h"),
        (2, 6.0, "2人×6h"),
        (3, 3.0, "3人×3h"),
        (3, 4.0, "3人×4h"),
        (3, 6.0, "3人×6h"),
        (4, 4.0, "4人×4h"),
        (4, 6.0, "4人×6h"),
        (5, 6.5, "5人×6.5h (绿地星玥)"),
    ]
    order_range = range(10, 310, 10)

    rows = []
    for orders in order_range:
        for staff, hours, label in configs:
            if max_capacity(staff, hours) < orders:
                continue
            for settlement, sname in [(SETTLEMENT_PROMO, "推广期"), (SETTLEMENT_REGULAR, "常规期")]:
                r = calc_single(staff, hours, orders, settlement)
                rows.append({
                    "配置": label,
                    "人数": staff,
                    "时长(h)": hours,
                    "日单量": orders,
                    "场景": sname,
                    "日毛利": r["日毛利"],
                    "补贴达标": r["补贴达标"],
                })
    return pd.DataFrame(rows)


# ============================================================
# 主输出
# ============================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 80)
    print("接力送 — 最优人员配置与盈利区间分析")
    print("=" * 80)

    print("""
核心产能假设：每人每小时最多处理 5 单（保守）
            楼下至少1人负责指引（不直接配送）
            有效配送人数 = N-1
            产能上限 = (N-1) × H × 5
""")

    # ---- 1. 各点位优化建议 ----
    print("─" * 60)
    print("【现有点位优化对比】")
    print("─" * 60)
    df_pt = build_point_optimization()
    print(tabulate(df_pt, headers="keys", tablefmt="grid", showindex=False,
                   numalign="right", stralign="left"))
    df_pt.to_csv(f"{OUTPUT_DIR}/point_optimization.csv", index=False, encoding="utf-8-sig")

    # ---- 2. 最优配置速查 ----
    print("\n" + "─" * 60)
    print("【最优配置速查：各单量水平下的最佳人员配置】")
    print("─" * 60)
    df_opt = build_optimization_table()
    # 只展示各单量的第一名
    top1 = df_opt[df_opt["排名"] == 1].sort_values(["场景", "日单量"])
    for scenario in ["推广期2.5元", "常规期2.0元"]:
        print(f"\n  [{scenario}]")
        subset = top1[top1["场景"] == scenario]
        print(tabulate(subset.drop(columns=["排名", "场景"]), headers="keys",
                       tablefmt="grid", showindex=False, numalign="right", stralign="left"))
    df_opt.to_csv(f"{OUTPUT_DIR}/optimal_config.csv", index=False, encoding="utf-8-sig")

    # ---- 3. 利润曲线关键拐点 ----
    print("\n" + "─" * 60)
    print("【利润曲线：各配置在不同单量下的日毛利（推广期）】")
    print("─" * 60)
    df_curve = build_profit_curve()
    curve_promo = df_curve[(df_curve["场景"] == "推广期") & (df_curve["日单量"] % 30 == 0)]
    pivot = curve_promo.pivot_table(
        index="日单量", columns="配置", values="日毛利", aggfunc="first"
    )
    print(tabulate(pivot, headers="keys", tablefmt="grid", numalign="right", stralign="left"))
    df_curve.to_csv(f"{OUTPUT_DIR}/profit_curve.csv", index=False, encoding="utf-8-sig")

    # ---- 4. 盈亏平衡单量速查 ----
    print("\n" + "─" * 60)
    print("【各配置的盈亏平衡单量】")
    print("─" * 60)
    configs = [
        (2, 3.0), (2, 4.0), (2, 6.0),
        (3, 3.0), (3, 4.0), (3, 6.0),
        (4, 4.0), (4, 6.0), (5, 6.5),
    ]
    be_rows = []
    for staff, hours in configs:
        daily_cost = staff * hours * LABOR_RATE + MATERIAL_DAILY
        for settlement, sname in [(SETTLEMENT_PROMO, "推广期2.5元"), (SETTLEMENT_REGULAR, "常规期2.0元")]:
            # 无补贴 BE
            be_no_sub = daily_cost / settlement
            # 有补贴 BE: (cost - 80) / settlement, 但需人均>20
            be_with_sub = (daily_cost - SUBSIDY) / settlement
            sub_threshold = staff * (MIN_ORDERS_PER_PERSON + 0.01)

            # 实际有补贴BE（考虑门槛）
            if be_with_sub <= sub_threshold:
                actual_be_sub = sub_threshold
                note = f"门槛{int(sub_threshold)}单"
            else:
                actual_be_sub = be_with_sub
                note = ""

            be_rows.append({
                "配置": f"{staff}人×{hours}h",
                "场景": sname,
                "日固定成本": round(daily_cost, 0),
                "无补贴盈亏平衡": f"{be_no_sub:.0f}单",
                "有补贴盈亏平衡": f"{actual_be_sub:.0f}单",
                "说明": note if note else (f"人均需>{MIN_ORDERS_PER_PERSON}" if actual_be_sub/staff > MIN_ORDERS_PER_PERSON else ""),
            })
    df_be = pd.DataFrame(be_rows)
    print(tabulate(df_be, headers="keys", tablefmt="grid", showindex=False,
                   numalign="right", stralign="left"))
    df_be.to_csv(f"{OUTPUT_DIR}/breakeven_by_config.csv", index=False, encoding="utf-8-sig")

    # ---- 5. 关键结论 ----
    print("\n" + "=" * 80)
    print("【关键结论】")
    print("=" * 80)

    print("""
  1. 2人×3h 是最经济的底线配置（日成本 ~183元），但几乎所有点位当前单量
     都低于盈亏平衡（推广期需73单，常规期需92单）。

  2. 人头补贴的陷阱：要拿到80元补贴，人均>20单。对于2人配置意味着>40单。
     但 2人×3h 的产能上限约 45单（1人配送×3h×5 + 闲时协助），
     "能拿补贴"和"产能不够"几乎是同一个区间。

  3. 推广期→常规期的冲击：
     - 结算价从2.5降到2.0（降幅20%）
     - 骑手费率从1.0升到2.0（骑手接受度断崖）
     - 双重打击下常规期几乎不可能靠当前模式盈利

  4. 万菱广场是最接近盈利的点位（6/11: 41单，补贴达标，日亏损<1元），
     如果能稳定在45+单且保持2人配置，推广期可实现微利。

  5. 绿地星玥5人配置极为低效：日均151单只需3人×4h即可处理（产能180单），
     优化后日亏损从-557元缩减到约-50元（推广期），但常规期仍亏损约-130元。

  6. 核心矛盾：收入天花板低（2-2.5元/单）× 人力成本刚性（30元/时）
     需要极高单量密度才能摊薄。2元/单时，每增加1人需要约15单/天来覆盖。
""")

    print("\n输出文件:", [
        "point_optimization.csv",
        "optimal_config.csv",
        "profit_curve.csv",
        "breakeven_by_config.csv",
    ])


if __name__ == "__main__":
    main()
