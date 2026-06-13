"""
接力送 — 非对称排班模型（高峰双人 + 低谷单人）
================================================
场景：办公楼午高峰 12:00 前后单量集中，12:30 后骤减
排班：1人覆盖3h（楼下指引+闲时协助配送）
      1人仅上2h高峰（纯楼上配送）

对比对称排班（2人×3h）与非对称排班（1人×3h + 1人×2h）的盈亏差异
"""

import pandas as pd
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
PEAK_CAPACITY_PER_HOUR = 8  # 高峰每人每小时产能

# ============================================================
# 排班方案
# ============================================================

SCHEDULES = {
    "对称-2人×3h": {
        "staff_A_hours": 3.0,  # 楼下指引（全程）
        "staff_B_hours": 3.0,  # 楼上配送（全程）
        "point_hours": 3.0,
        "total_headcount": 2,   # 补贴人均计算用
    },
    "对称-2人×4h": {
        "staff_A_hours": 4.0,
        "staff_B_hours": 4.0,
        "point_hours": 4.0,
        "total_headcount": 2,
    },
    "非对称-1人3h+1人2h": {
        "staff_A_hours": 3.0,  # 全程楼下
        "staff_B_hours": 2.0,  # 仅高峰配送
        "point_hours": 3.0,
        "total_headcount": 2,
    },
    "非对称-1人3h+1人2.5h": {
        "staff_A_hours": 3.0,
        "staff_B_hours": 2.5,
        "point_hours": 3.0,
        "total_headcount": 2,
    },
    "非对称-1人3h+1人1.5h": {
        "staff_A_hours": 3.0,
        "staff_B_hours": 1.5,
        "point_hours": 3.0,
        "total_headcount": 2,
    },
    "极简-1人3h(无人配送)": {
        "staff_A_hours": 3.0,  # 一个人全包，不可行但做参照
        "staff_B_hours": 0.0,
        "point_hours": 3.0,
        "total_headcount": 1,
    },
}


def labor_cost(schedule):
    return (schedule["staff_A_hours"] + schedule["staff_B_hours"]) * LABOR_RATE


def total_daily_cost(schedule):
    return labor_cost(schedule) + MATERIAL_DAILY


def peak_capacity(schedule):
    """
    高峰窗口产能：2人同时在场时的产能
    非高峰产能：仅A在场，需兼顾楼下+配送，效率打折
    """
    a_hrs = schedule["staff_A_hours"]
    b_hrs = schedule["staff_B_hours"]

    # 两人同时在场的时长为B的时长（B只上高峰）
    overlap_hours = min(a_hrs, b_hrs)

    # 重叠时段产能：2人配送（A可协助）× 8单/h
    overlap_capacity = 1.6 * overlap_hours * PEAK_CAPACITY_PER_HOUR

    # 非重叠时段产能：仅A一人，需兼顾楼下，效率打对折
    solo_hours = a_hrs - overlap_hours
    solo_capacity = 0.5 * solo_hours * PEAK_CAPACITY_PER_HOUR  # 兼顾楼下

    return overlap_capacity + solo_capacity


def subsidy_eligible(schedule, orders):
    """判断是否满足人头补贴三个条件"""
    h = schedule["point_hours"]
    n = schedule["total_headcount"]
    if h < MIN_HOURS:
        return False
    if n < 1:
        return False
    # 至少一人上满3h：staff_A 满足
    if schedule["staff_A_hours"] < MIN_HOURS:
        return False
    if n > 0 and orders / n <= MIN_ORDERS_PER_PERSON:
        return False
    return True


def calc_profit(schedule, orders, settlement):
    order_rev = orders * settlement
    eligible = subsidy_eligible(schedule, orders)
    sub = SUBSIDY if eligible else 0
    total_rev = order_rev + sub
    cost = total_daily_cost(schedule)
    return total_rev - cost, eligible


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 80)
    print("接力送 — 非对称排班 vs 对称排班 盈利对比")
    print("=" * 80)

    # ================================================================
    # Part 1: 各排班方案基础参数
    # ================================================================
    print("\n─" * 60)
    print("【排班方案对比】")
    print("─" * 60)

    sched_rows = []
    for name, sch in SCHEDULES.items():
        sched_rows.append({
            "方案": name,
            "A工时(h)": sch["staff_A_hours"],
            "B工时(h)": sch["staff_B_hours"],
            "总工时": sch["staff_A_hours"] + sch["staff_B_hours"],
            "日人力成本": f"{labor_cost(sch):.0f}",
            "日总成本": f"{total_daily_cost(sch):.0f}",
            "高峰产能": f"{peak_capacity(sch):.0f}单",
            "补贴人头数": sch["total_headcount"],
            "补贴门槛单量": sch["total_headcount"] * (MIN_ORDERS_PER_PERSON + 1),
        })
    df_sched = pd.DataFrame(sched_rows)
    print(tabulate(df_sched, headers="keys", tablefmt="grid", showindex=False,
                   numalign="right", stralign="left"))

    # ================================================================
    # Part 2: 各方案在不同单量下的利润（推广期 + 常规期）
    # ================================================================
    print("\n─" * 60)
    print("【各方案利润对比：推广期（2.5元） × 常规期（2.0元）】")
    print("─" * 60)

    # 排除1人方案（不可行），聚焦可对比的
    compare_schedules = ["对称-2人×3h", "对称-2人×4h",
                         "非对称-1人3h+1人2h", "非对称-1人3h+1人2.5h",
                         "非对称-1人3h+1人1.5h"]

    for settlement, slabel in [(2.5, "推广期 2.5元/单"), (2.0, "常规期 2.0元/单")]:
        print(f"\n  [{slabel}]")

        curve_data = {}
        for name in compare_schedules:
            sch = SCHEDULES[name]
            profits = []
            for orders in range(10, 81, 5):
                cap = peak_capacity(sch)
                if orders > cap:
                    profits.append(None)  # 超产能
                else:
                    p, elig = calc_profit(sch, orders, settlement)
                    profits.append(round(p, 0))
            curve_data[name] = profits

        # 建表
        df_curve = pd.DataFrame(curve_data,
                                index=[f"{o}单" for o in range(10, 81, 5)])
        df_curve.index.name = "单量"

        # 只展示关键单量点
        key_points = [10, 20, 30, 40, 41, 45, 50, 55, 60, 70, 80]
        df_key = df_curve.loc[[f"{o}单" for o in key_points if f"{o}单" in df_curve.index]]
        print(tabulate(df_key, headers="keys", tablefmt="grid", numalign="right"))

        df_curve.to_csv(f"{OUTPUT_DIR}/asymmetric_vs_symmetric_{slabel.replace(' ','_').replace('/','')}.csv",
                        index=True, encoding="utf-8-sig")

    # ================================================================
    # Part 3: 重点对比 — 对称2人×3h vs 非对称1人3h+1人2h
    # ================================================================
    print("\n" + "─" * 60)
    print("【核心对比：对称 vs 非对称，精确到每单】")
    print("─" * 60)

    sch_sym = SCHEDULES["对称-2人×3h"]
    sch_asym = SCHEDULES["非对称-1人3h+1人2h"]

    print(f"""
  对称排班：2人×3h → 6工时 → 人力{int(labor_cost(sch_sym))}元/天 → 总成本{total_daily_cost(sch_sym):.0f}元/天
  非对称排班：1人×3h + 1人×2h → 5工时 → 人力{int(labor_cost(sch_asym))}元/天 → 总成本{total_daily_cost(sch_asym):.0f}元/天
  日省成本：{total_daily_cost(sch_sym) - total_daily_cost(sch_asym):.0f}元/天（{- (total_daily_cost(sch_sym) - total_daily_cost(sch_asym)) / total_daily_cost(sch_sym) * 100:.0f}%）
""")

    detail_rows = []
    for orders in range(20, 81):
        cap_sym = peak_capacity(sch_sym)
        cap_asym = peak_capacity(sch_asym)

        for settlement, slabel in [(2.5, "推广期"), (2.0, "常规期")]:
            p_sym, e_sym = calc_profit(sch_sym, orders, settlement) if orders <= cap_sym else (None, None)
            p_asym, e_asym = calc_profit(sch_asym, orders, settlement) if orders <= cap_asym else (None, None)

            if p_sym is not None and p_asym is not None:
                diff = p_asym - p_sym
                detail_rows.append({
                    "单量": orders,
                    "场景": slabel,
                    "对称利润": f"{p_sym:+.0f}",
                    "非对称利润": f"{p_asym:+.0f}",
                    "非对称优势": f"{diff:+.0f}",
                    "对称补贴": "✓" if e_sym else "✗",
                    "非对称补贴": "✓" if e_asym else "✗",
                })

    df_detail = pd.DataFrame(detail_rows)
    # 只展示关键单量
    key = df_detail[df_detail["单量"].isin([20, 30, 35, 40, 41, 42, 45, 50, 55, 60, 70, 80])]
    print(tabulate(key, headers="keys", tablefmt="grid", showindex=False, numalign="right"))
    df_detail.to_csv(f"{OUTPUT_DIR}/asymmetric_detail.csv", index=False, encoding="utf-8-sig")

    # ================================================================
    # Part 4: 各点位应用非对称排班后的改善
    # ================================================================
    print("\n" + "─" * 60)
    print("【各点位切换到非对称排班的预估效果】")
    print("─" * 60)

    points = {
        "万科欧泊": 46,
        "万菱广场": 41,
        "和业广场": 36,
        "金鹰大厦": 20,
        "华林国际C馆": 3,
    }
    # 绿地星玥单量太大(151)，非对称2人模式产能不足，单独分析

    point_rows = []
    for name, orders in points.items():
        cap_asym = peak_capacity(sch_asym)  # 非对称2人产能约31单
        cap_sym4 = peak_capacity(SCHEDULES["对称-2人×4h"])  # 对称4h产能约51单

        for settlement, slabel in [(2.5, "推广期"), (2.0, "常规期")]:
            # 当前对称3h
            p_current, e_current = calc_profit(sch_sym, orders, settlement)
            # 非对称
            if orders <= cap_asym:
                p_asym, e_asym = calc_profit(sch_asym, orders, settlement)
                asym_note = f"{p_asym:+.0f}元"
            else:
                p_asym, e_asym = None, None
                asym_note = f"超产能({cap_asym:.0f}单)"

            # 如需扩产，对称4h
            if orders <= cap_sym4:
                p_sym4, e_sym4 = calc_profit(SCHEDULES["对称-2人×4h"], orders, settlement)
                sym4_note = f"{p_sym4:+.0f}元"
            else:
                sym4_note = "超产能"

            point_rows.append({
                "点位": name,
                "场景": slabel,
                "当前单量": orders,
                "当前(2人×3h)": f"{p_current:+.0f}元",
                "非对称(3h+2h)": asym_note,
                "对称(2人×4h)备选": sym4_note,
            })

    df_pt = pd.DataFrame(point_rows)
    print(tabulate(df_pt, headers="keys", tablefmt="grid", showindex=False, numalign="right"))
    df_pt.to_csv(f"{OUTPUT_DIR}/point_asymmetric_apply.csv", index=False, encoding="utf-8-sig")

    # ================================================================
    # Part 5: 非对称排班的关键约束分析
    # ================================================================
    print("\n" + "─" * 60)
    print("【非对称排班的产能天花板与补贴资格】")
    print("─" * 60)

    print(f"""
  非对称(1人×3h + 1人×2h) 关键约束：

  1. 产能上限：约 {peak_capacity(sch_asym):.0f} 单/天
     - 2h高峰双人窗口：约 {1.6 * 2 * PEAK_CAPACITY_PER_HOUR:.0f} 单（重叠2h内）
     - 1h单人收尾窗口：约 {0.5 * 1 * PEAK_CAPACITY_PER_HOUR:.0f} 单（兼顾楼下）
     → 如果单量 >{peak_capacity(sch_asym):.0f}，需要 B 延长工时或加人

  2. 补贴条件：
     - 营业≥3h ✓（A工作3h）
     - 至少1人上满3h ✓（A满足）
     - 人均>20单：需 >40单（2人均计人头）

  3. 盈亏平衡单量：
""")

    for settlement, slabel in [(2.5, "推广期2.5元"), (2.0, "常规期2.0元")]:
        cost_asym = total_daily_cost(sch_asym)
        # BE no subsidy
        be_no = cost_asym / settlement
        # BE with subsidy at threshold
        be_sub_threshold = 2 * (MIN_ORDERS_PER_PERSON + 0.01)
        rev_at_threshold = be_sub_threshold * settlement + SUBSIDY
        if rev_at_threshold >= cost_asym:
            be_effective = be_sub_threshold
            be_note = "达补贴门槛即盈利"
        else:
            extra = (cost_asym - rev_at_threshold) / settlement
            be_effective = be_sub_threshold + extra
            be_note = f"门槛({be_sub_threshold:.0f}单)+额外{extra:.0f}单"

        print(f"    {slabel}: 无补贴需 {be_no:.0f}单 | "
              f"有补贴需 {be_effective:.0f}单 ({be_note})")

    # ================================================================
    # Part 6: 最终结论
    # ================================================================
    print("\n" + "=" * 80)
    print("【结论】")
    print("=" * 80)

    profit_sym_46, _ = calc_profit(sch_sym, 46, 2.5)
    profit_asym_46, _ = calc_profit(sch_asym, 46, 2.5)
    profit_sym_41, _ = calc_profit(sch_sym, 41, 2.5)
    profit_asym_41, _ = calc_profit(sch_asym, 41, 2.5)

    print(f"""
  1. 非对称排班（1人×3h + 1人×2h）vs 对称排班（2人×3h）：
     日成本从 183 元降到 153 元（-17%）

  2. 万科欧泊（46单）：
     - 对称排班：{profit_sym_46:+.0f} 元/天
     - 非对称排班：{profit_asym_46:+.0f} 元/天
     - 改善：{profit_asym_46 - profit_sym_46:+.0f} 元/天
     → 但需确认 46 单是否超出非对称产能（≈31单）
     → 若产能不足，方案调整为：1人×3h + 1人×2.5h（成本165元，产能≈38单）

  3. 万菱广场（41单）：
     - 对称排班：{profit_sym_41:+.0f} 元/天
     - 非对称排班：{profit_asym_41:+.0f} 元/天
     - 改善：{profit_asym_41 - profit_sym_41:+.0f} 元/天
     → 推广期从打平变为日赚30+元，常规期也能打平或微利

  4. 风险点：
     - 产能判断是关键：如果 40+ 单集中在 2h 高峰窗口，2人能否处理？
       实测万菱 41单/3h ≈ 6.8单/人/h，高峰窗口可能需要 10+ 单/h 的效率
     - B 的时间窗口要对得准：来早了浪费、来晚了爆单
     - 建议先用万菱或万科做一周测试，对比对称vs非对称的人效数据
""")
    print("输出文件:", [
        "asymmetric_vs_symmetric_推广期.csv",
        "asymmetric_vs_symmetric_常规期.csv",
        "asymmetric_detail.csv",
        "point_asymmetric_apply.csv",
    ])


if __name__ == "__main__":
    main()
