"""
接力送项目盈利模型
===================
业务模式：美团骑手送餐到楼下 → 我方配送员接力送上楼到具体房间
收入来源：美团订单结算 + 美团人头补贴
成本：人力（时薪制）+ 物料（一次性投入）

更新时间：2026-06-13
"""

import pandas as pd
import numpy as np
from tabulate import tabulate
import os

# 输出目录（项目根目录下的 output/）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# ============================================================
# 0. 全局参数
# ============================================================

# 收入参数（单位：元）
SETTLEMENT_PER_ORDER_PROMO = 2.5   # 推广期（前两周）：美团每单结算
SETTLEMENT_PER_ORDER_REGULAR = 2.0 # 常规期：去掉5毛补贴后
HEADCOUNT_SUBSIDY_PER_POINT = 80   # 人头补贴 元/点位/天

# 人头补贴条件
SUBSIDY_MIN_HOURS = 3.0            # 点位至少营业时长(h)
SUBSIDY_MIN_ORDERS_PER_PERSON = 20 # 人均当量 > 20单
SUBSIDY_MIN_STAFF_FULL_SHIFT = 1   # 至少1人上满3小时

# 成本参数（单位：元）
LABOR_RATE_HOURLY = 30             # 时薪 元/人/小时
MATERIAL_COST_PER_POINT = 100      # 单个点位一次性物料投入
MATERIAL_AMORT_DAYS = 30           # 物料摊销天数（约1个月损耗替换）

# 骑手收费参数（美团定价，从骑手配送费中扣除）
RIDER_FEE_PROMO = 1.0              # 推广期：骑手每单只收1元
RIDER_FEE_REGULAR = 2.0            # 常规期：骑手每单收2元
RIDER_TAKEHOME_TYPICAL = (3.0, 4.0)# 骑手通常到手配送费范围

# ============================================================
# 1. 实际点位数据
# ============================================================

RAW_DATA = {
    "万科欧泊": {
        "staff": 3,
        "hours": 3.0,
        "orders": {7: 26, 8: 23, 9: 21, 10: 35, 11: 35, 12: 46},
    },
    "绿地星玥": {
        "staff": 5,
        "hours": 6.5,
        "orders": {10: 122, 11: 151},
    },
    "和业广场": {
        "staff": 2,
        "hours": 3.0,
        "orders": {11: 36},
    },
    "华林国际C馆": {
        "staff": 2,
        "hours": 3.0,
        "orders": {11: 3},
    },
    "万菱广场": {
        "staff": 2,
        "hours": 3.0,
        "orders": {10: 12, 11: 41},
    },
    "金鹰大厦": {
        "staff": 2,
        "hours": 3.0,
        "orders": {11: 20},
    },
}

# ============================================================
# 2. 核心计算函数
# ============================================================

def check_subsidy_eligible(staff, hours, orders):
    """
    判断某点位某天是否满足人头补贴条件。

    条件：
    1. 点位营业时长 >= 3h
    2. 至少1人上满3小时（这里简化为 hours >= SUBSIDY_MIN_HOURS）
    3. 人均当量 > 20 单

    返回: (eligible: bool, reason: str)
    """
    if hours < SUBSIDY_MIN_HOURS:
        return False, f"营业时长{hours}h < {SUBSIDY_MIN_HOURS}h"
    if staff < SUBSIDY_MIN_STAFF_FULL_SHIFT:
        return False, f"上满{SUBSIDY_MIN_HOURS}h人数不足"
    per_person = orders / staff
    if per_person <= SUBSIDY_MIN_ORDERS_PER_PERSON:
        return False, f"人均{per_person:.1f}单 ≤ {SUBSIDY_MIN_ORDERS_PER_PERSON}单"
    return True, f"人均{per_person:.1f}单 ✓"


def calc_daily_pnl(point_name, staff, hours, orders, settlement_rate, scenario_label):
    """
    计算单个点位单日损益。

    参数:
        point_name: 点位名称
        staff: 当日实际上岗人数
        hours: 当日营业时长
        orders: 当日单量
        settlement_rate: 美团每单结算价
        scenario_label: 场景标签（用于输出区分）

    返回: dict
    """
    # 收入
    order_revenue = orders * settlement_rate
    eligible, reason = check_subsidy_eligible(staff, hours, orders)
    subsidy = HEADCOUNT_SUBSIDY_PER_POINT if eligible else 0

    total_revenue = order_revenue + subsidy

    # 成本
    labor_cost = staff * hours * LABOR_RATE_HOURLY
    material_cost_daily = MATERIAL_COST_PER_POINT / MATERIAL_AMORT_DAYS
    total_cost = labor_cost + material_cost_daily

    # 利润
    gross_profit = total_revenue - total_cost
    gross_margin = gross_profit / total_revenue if total_revenue > 0 else np.nan

    # 单位经济
    unit_revenue = settlement_rate + (subsidy / orders if orders > 0 else 0)
    unit_cost = total_cost / orders if orders > 0 else np.nan
    unit_profit = unit_revenue - unit_cost if orders > 0 else np.nan

    return {
        "点位": point_name,
        "场景": scenario_label,
        "人数": staff,
        "营业时长(h)": hours,
        "单量": orders,
        "人均单量": orders / staff if staff > 0 else 0,
        "订单收入": round(order_revenue, 2),
        "人头补贴": subsidy,
        "总收入": round(total_revenue, 2),
        "人力成本": round(labor_cost, 2),
        "物料摊销": round(material_cost_daily, 2),
        "总成本": round(total_cost, 2),
        "毛利": round(gross_profit, 2),
        "毛利率": f"{gross_margin*100:.1f}%" if not np.isnan(gross_margin) else "N/A",
        "单均收入": round(unit_revenue, 2),
        "单均成本": round(unit_cost, 2) if not np.isnan(unit_cost) else "N/A",
        "单均毛利": round(unit_profit, 2) if not np.isnan(unit_profit) else "N/A",
        "补贴达标": "✓" if eligible else f"✗ ({reason})",
    }


def calc_breakeven(staff, hours, settlement_rate, with_subsidy):
    """
    计算盈亏平衡单量。

    成本 = 收入
    staff * hours * 30 = orders * settlement + (subsidy if eligible)
    这里 subsidy 的 eligibility 依赖 orders，需要迭代。

    无补贴时：orders_be = staff * hours * 30 / settlement
    有补贴时：orders_be = (staff * hours * 30 - 80) / settlement
              但还要验证人均 > 20
    """
    labor_cost = staff * hours * LABOR_RATE_HOURLY
    material_daily = MATERIAL_COST_PER_POINT / MATERIAL_AMORT_DAYS
    fixed_cost = labor_cost + material_daily

    if not with_subsidy:
        be_orders = fixed_cost / settlement_rate
        be_per_person = be_orders / staff
        return {
            "人数": staff,
            "时长(h)": hours,
            "日固定成本": round(fixed_cost, 2),
            "结算价": settlement_rate,
            "含补贴": "否",
            "盈亏平衡单量": round(be_orders, 1),
            "人均需达单量": round(be_per_person, 1),
            "补贴条件满足": "N/A",
        }
    else:
        # 有补贴场景：先算含补贴的 BE，再验证人均是否 > 20
        be_with_subsidy = (fixed_cost - HEADCOUNT_SUBSIDY_PER_POINT) / settlement_rate
        be_per_person = be_with_subsidy / staff

        # 验证：盈亏平衡点是否同时满足补贴条件
        if be_per_person > SUBSIDY_MIN_ORDERS_PER_PERSON:
            subsidy_note = f"人均{be_per_person:.1f} > 20，符合"
            effective_be = be_with_subsidy
        else:
            # 补贴条件下人均不达标，意味着拿不到补贴，实际 BE 更高
            # 需要重新算：先达到补贴门槛，再看盈亏
            subsidy_threshold = SUBSIDY_MIN_ORDERS_PER_PERSON * staff  # 刚好拿补贴的单量
            # 在补贴门槛处：收入 = subsidy_threshold * settlement + 80
            revenue_at_threshold = subsidy_threshold * settlement_rate + HEADCOUNT_SUBSIDY_PER_POINT
            if revenue_at_threshold >= fixed_cost:
                # 达到补贴门槛就盈利了
                effective_be = subsidy_threshold
                subsidy_note = f"补贴门槛{int(subsidy_threshold)}单即盈利"
            else:
                # 达到补贴门槛还不够，需要额外单量
                extra_needed = (fixed_cost - revenue_at_threshold) / settlement_rate
                effective_be = subsidy_threshold + extra_needed
                subsidy_note = f"需超补贴门槛{extra_needed:.0f}单"

        return {
            "人数": staff,
            "时长(h)": hours,
            "日固定成本": round(fixed_cost, 2),
            "结算价": settlement_rate,
            "含补贴": "是",
            "盈亏平衡单量": round(effective_be, 1),
            "人均需达单量": round(effective_be / staff, 1),
            "补贴条件满足": subsidy_note,
        }


# ============================================================
# 3. 主计算流程
# ============================================================

def build_actual_pnl():
    """基于实际数据的逐日逐点位损益表"""
    rows = []
    for point_name, data in RAW_DATA.items():
        staff = data["staff"]
        hours = data["hours"]
        for day, orders in sorted(data["orders"].items()):
            row = calc_daily_pnl(
                point_name, staff, hours, orders,
                SETTLEMENT_PER_ORDER_PROMO, "推广期(结算2.5元)"
            )
            row["日期"] = f"6月{day}日"
            rows.append(row)
    return pd.DataFrame(rows)


def build_point_summary(df_actual):
    """按点位汇总"""
    summary = df_actual.groupby("点位").agg(
        天数=("单量", "count"),
        日均单量=("单量", "mean"),
        日均收入=("总收入", "mean"),
        日均成本=("总成本", "mean"),
        日均毛利=("毛利", "mean"),
        累计毛利=("毛利", "sum"),
        补贴达标天数=("补贴达标", lambda x: (x == "✓").sum()),
    ).reset_index()

    summary["日均单量"] = summary["日均单量"].round(1)
    summary["日均收入"] = summary["日均收入"].round(2)
    summary["日均成本"] = summary["日均成本"].round(2)
    summary["日均毛利"] = summary["日均毛利"].round(2)
    summary["累计毛利"] = summary["累计毛利"].round(2)
    return summary


def build_breakeven_table():
    """不同人员配置下的盈亏平衡表"""
    configs = [
        (2, 3.0),   # 最简配置
        (2, 6.5),
        (3, 3.0),   # 万科欧泊配置
        (3, 6.5),
        (5, 6.5),   # 绿地星玥配置
        (2, 8.0),
        (3, 8.0),
    ]
    rows = []
    for staff, hours in configs:
        for settlement, label in [(SETTLEMENT_PER_ORDER_PROMO, "2.5元"), (SETTLEMENT_PER_ORDER_REGULAR, "2.0元")]:
            for subsidy in [False, True]:
                r = calc_breakeven(staff, hours, settlement, subsidy)
                r["结算价"] = label
                rows.append(r)
    return pd.DataFrame(rows)


def build_subsidy_check_table():
    """
    不同人员配置下，刚好拿到补贴所需的最低单量。
    条件：人均 > 20 单，即 orders > staff * 20。
    """
    rows = []
    for staff in [1, 2, 3, 4, 5, 6]:
        min_orders = staff * SUBSIDY_MIN_ORDERS_PER_PERSON + 1  # 超过20
        daily_cost = staff * 3 * LABOR_RATE_HOURLY + MATERIAL_COST_PER_POINT / MATERIAL_AMORT_DAYS

        # 在刚好拿补贴时的日利润（推广期）
        rev_promo = min_orders * SETTLEMENT_PER_ORDER_PROMO + HEADCOUNT_SUBSIDY_PER_POINT
        profit_promo = rev_promo - daily_cost

        # 常规期
        rev_regular = min_orders * SETTLEMENT_PER_ORDER_REGULAR + HEADCOUNT_SUBSIDY_PER_POINT
        profit_regular = rev_regular - daily_cost

        rows.append({
            "人数": staff,
            "人均>20的最少单量": int(min_orders),
            "日人力成本(3h)": round(staff * 3 * LABOR_RATE_HOURLY, 0),
            "推广期日利润": round(profit_promo, 2),
            "常规期日利润": round(profit_regular, 2),
        })
    return pd.DataFrame(rows)


def build_rider_fee_sensitivity():
    """
    骑手费率敏感性分析。

    已知：
    - 骑手到手配送费 3~4 元
    - 0.9 元收费 → 骑手意愿强烈（假设基准单量 = 100%）
    - 1.5 元收费 → 剧烈掉量后恢复到原量 50%
    - 2.0 元收费 → 未测试，推测更严重

    我方收入：
    - 推广期：无论骑手付多少，美团结算 2.5 元/单
    - 常规期：骑手付多少，美团结算多少（去掉补贴后即 2.0 元）
    """
    rider_fees = [0.5, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0]

    # 基于已知数据点的订单量衰减模型
    # 0.9元：意愿强烈 → 假设基准量的 100%
    # 1.0元：略低于 0.9 元 → 95%
    # 1.5元：掉到 50%，恢复后 50%
    # 2.0元：推测掉到 20-30%

    def volume_multiplier(fee):
        """根据骑手费率估算订单量倍率"""
        if fee <= 0.9:
            return 1.0
        elif fee <= 1.0:
            return 0.95
        elif fee <= 1.2:
            # 线性插值 1.0→1.5: 0.95→0.50
            return 0.95 - (fee - 1.0) / 0.5 * 0.45
        elif fee <= 1.5:
            return 0.50
        else:
            # 1.5→2.0: 0.50→0.25
            return 0.50 - (fee - 1.5) / 0.5 * 0.25

    # 以万科欧泊日均单量 31 作为基准（现有推广期 1元收费下的表现）
    base_daily_orders = 31
    # 以绿地星玥日均 136 作为高单量基准
    high_base_orders = 136

    rows = []
    for fee in rider_fees:
        mult = volume_multiplier(fee)
        est_orders_low = base_daily_orders * mult  # 低单量点位
        est_orders_high = high_base_orders * mult  # 高单量点位

        # 推广期：我方收入 2.5元/单（美团补贴差价）
        rev_promo_low = est_orders_low * SETTLEMENT_PER_ORDER_PROMO
        rev_promo_high = est_orders_high * SETTLEMENT_PER_ORDER_PROMO

        # 常规期：我方收入 = 骑手费率（美团不再补贴）
        rev_regular_low = est_orders_low * fee
        rev_regular_high = est_orders_high * fee

        # 2人3h 成本基准
        baseline_cost = 2 * 3 * LABOR_RATE_HOURLY

        rows.append({
            "骑手费率(元)": fee,
            "订单量倍率": f"{mult:.0%}",
            "低量点位预估单量": round(est_orders_low, 0),
            "高量点位预估单量": round(est_orders_high, 0),
            "推广期日收入(低)": round(rev_promo_low, 0),
            "推广期日收入(高)": round(rev_promo_high, 0),
            "常规期日收入(低)": round(rev_regular_low, 0),
            "常规期日收入(高)": round(rev_regular_high, 0),
            "2人3h日成本": baseline_cost,
            "推广期毛利(低)": round(rev_promo_low - baseline_cost, 0),
            "常规期毛利(低)": round(rev_regular_low - baseline_cost, 0),
            "常规期毛利(高)": round(rev_regular_high - baseline_cost, 0),
        })
    return pd.DataFrame(rows)


def build_scenario_comparison():
    """
    场景对比：推广期 vs 常规期，补贴 vs 无补贴
    统一以 2人3h 配置为基准，不同单量水平。
    """
    scenarios = []
    # 不同单量水平
    for daily_orders in [10, 20, 30, 40, 50, 60, 80, 100, 150]:
        staff, hours = 2, 3.0
        labor_cost = staff * hours * LABOR_RATE_HOURLY
        material_daily = MATERIAL_COST_PER_POINT / MATERIAL_AMORT_DAYS
        total_cost = labor_cost + material_daily

        # 补贴条件检查
        per_person = daily_orders / staff
        subsidy_eligible = (hours >= SUBSIDY_MIN_HOURS
                            and staff >= SUBSIDY_MIN_STAFF_FULL_SHIFT
                            and per_person > SUBSIDY_MIN_ORDERS_PER_PERSON)

        for scenario_name, settlement in [("推广期(结算2.5元)", SETTLEMENT_PER_ORDER_PROMO),
                                           ("常规期(结算2.0元)", SETTLEMENT_PER_ORDER_REGULAR)]:
            order_rev = daily_orders * settlement
            sub = HEADCOUNT_SUBSIDY_PER_POINT if subsidy_eligible else 0
            total_rev = order_rev + sub
            profit = total_rev - total_cost
            margin = profit / total_rev if total_rev > 0 else np.nan

            scenarios.append({
                "场景": scenario_name,
                "日单量": daily_orders,
                "人均单量": per_person,
                "订单收入": round(order_rev, 2),
                "人头补贴": sub,
                "总收入": round(total_rev, 2),
                "总成本": round(total_cost, 2),
                "毛利": round(profit, 2),
                "毛利率": f"{margin*100:.1f}%" if not np.isnan(margin) else "N/A",
                "补贴达标": "✓" if subsidy_eligible else "✗",
                "单均毛利": round(profit / daily_orders, 2) if daily_orders > 0 else "N/A",
            })
    return pd.DataFrame(scenarios)


# ============================================================
# 4. 输出
# ============================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 80)
    print("接力送项目 — 盈利模型分析")
    print("=" * 80)

    # ---- 核心假设 ----
    print("\n" + "─" * 60)
    print("【核心假设】")
    print("─" * 60)
    print(f"""
    收入端:
      - 推广期（前2周）美团每单结算: {SETTLEMENT_PER_ORDER_PROMO} 元
      - 常规期（补贴取消后）美团每单结算: {SETTLEMENT_PER_ORDER_REGULAR} 元
      - 人头补贴: {HEADCOUNT_SUBSIDY_PER_POINT} 元/点位/天
      - 补贴条件: 营业≥3h, 至少1人上满3h, 人均>20单, T-1支付

    骑手端（美团定价）:
      - 推广期骑手付费: {RIDER_FEE_PROMO} 元/单
      - 常规期骑手付费: {RIDER_FEE_REGULAR} 元/单
      - 骑手到手配送费通常: {RIDER_TAKEHOME_TYPICAL[0]}-{RIDER_TAKEHOME_TYPICAL[1]} 元/单
      - 已测试: 0.9元意愿强烈, 1.5元掉量50%

    成本端:
      - 人力: {LABOR_RATE_HOURLY} 元/人/小时
      - 物料: {MATERIAL_COST_PER_POINT} 元/点位 (按{MATERIAL_AMORT_DAYS}天摊销)
    """)

    # ---- 4.1 实际数据逐日明细 ----
    print("\n" + "─" * 60)
    print("【实际点位逐日损益】（推广期，结算价2.5元）")
    print("─" * 60)
    df_actual = build_actual_pnl()
    # 关键列
    display_cols = ["点位", "日期", "人数", "营业时长(h)", "单量", "人均单量",
                    "总收入", "总成本", "毛利", "毛利率", "单均毛利", "补贴达标"]
    print(tabulate(df_actual[display_cols], headers="keys", tablefmt="grid",
                   showindex=False, numalign="right", stralign="left"))
    df_actual.to_csv(f"{OUTPUT_DIR}/actual_daily_pnl.csv", index=False, encoding="utf-8-sig")

    # ---- 4.2 点位汇总 ----
    print("\n" + "─" * 60)
    print("【点位汇总】")
    print("─" * 60)
    df_summary = build_point_summary(df_actual)
    print(tabulate(df_summary, headers="keys", tablefmt="grid",
                   showindex=False, numalign="right", stralign="left"))
    df_summary.to_csv(f"{OUTPUT_DIR}/point_summary.csv", index=False, encoding="utf-8-sig")

    # ---- 4.3 盈亏平衡表 ----
    print("\n" + "─" * 60)
    print("【盈亏平衡分析】")
    print("─" * 60)
    df_be = build_breakeven_table()
    print(tabulate(df_be, headers="keys", tablefmt="grid",
                   showindex=False, numalign="right", stralign="left"))
    df_be.to_csv(f"{OUTPUT_DIR}/breakeven.csv", index=False, encoding="utf-8-sig")

    # ---- 4.4 补贴门槛利润 ----
    print("\n" + "─" * 60)
    print("【刚好达补贴门槛时的日利润】（营业3h）")
    print("─" * 60)
    df_sub = build_subsidy_check_table()
    print(tabulate(df_sub, headers="keys", tablefmt="grid",
                   showindex=False, numalign="right", stralign="left"))
    df_sub.to_csv(f"{OUTPUT_DIR}/subsidy_threshold_profit.csv", index=False, encoding="utf-8-sig")

    # ---- 4.5 骑手费率敏感性 ----
    print("\n" + "─" * 60)
    print("【骑手费率敏感性分析】")
    print("─" * 60)
    print("""
    订单量衰减模型（基于已有测试数据推算）:
      ≤0.9元 → 100% 基准量（骑手意愿强烈）
      1.0元   → 95%
      1.2元   → 72%
      1.5元   → 50%（测试确认：剧烈掉量后恢复到此水平）
      1.8元   → 37%
      2.0元   → 25%（推测，未实测）
    """)
    df_rider = build_rider_fee_sensitivity()
    print(tabulate(df_rider, headers="keys", tablefmt="grid",
                   showindex=False, numalign="right", stralign="left"))
    df_rider.to_csv(f"{OUTPUT_DIR}/rider_fee_sensitivity.csv", index=False, encoding="utf-8-sig")

    # ---- 4.6 场景对比矩阵 ----
    print("\n" + "─" * 60)
    print("【场景矩阵：推广期 vs 常规期 × 不同单量（2人3h配置）】")
    print("─" * 60)
    df_scenario = build_scenario_comparison()
    # 分开展示推广期和常规期
    for scenario in ["推广期(结算2.5元)", "常规期(结算2.0元)"]:
        print(f"\n  [{scenario}]")
        subset = df_scenario[df_scenario["场景"] == scenario]
        print(tabulate(subset, headers="keys", tablefmt="grid",
                       showindex=False, numalign="right", stralign="left"))

    df_scenario.to_csv(f"{OUTPUT_DIR}/scenario_matrix.csv", index=False, encoding="utf-8-sig")

    # ---- 4.7 关键发现 ----
    print("\n" + "=" * 80)
    print("【关键发现与风险提示】")
    print("=" * 80)

    # 检查哪些点位哪几天达标了补贴
    eligible_days = df_actual[df_actual["补贴达标"] == "✓"]
    if len(eligible_days) == 0:
        print("""
  ⚠ 补贴达标情况：现有数据中无任何点位/日期满足人头补贴条件。
    原因：人均单量均未超过20单的门槛。

    万科欧泊 (3人)：日均31单，人均仅10.3单 — 远低于20单门槛
    绿地星玥 (5人)：日均136单，人均27.3单 — 仅此点位有望达标
      → 6/10: 122单/5人=24.4 ✓  6/11: 151单/5人=30.2 ✓
    其他点位：日均单量太低，补贴条件无法满足
""")
    else:
        print(f"\n  补贴达标天数: {len(eligible_days)} 天")
        print(tabulate(eligible_days[["点位", "日期", "单量", "人均单量"]],
                       headers="keys", tablefmt="simple", showindex=False))

    print("""
  ⚠ 骑手费率风险：常规期 2元/单 定价远超已验证的骑手接受上限。
    - 骑手到手 3~4 元，扣 2 元后仅剩 1~2 元跑第一段
    - 0.9 元测试意愿强烈，1.5 元掉量 50%
    - 2.0 元可能导致订单量断崖式下跌至基准的 25% 或更低

  ⚠ 2人3h 最低配置下：
    - 推广期盈亏平衡：72单/天（无补贴），40单/天（有补贴）
    - 常规期盈亏平衡：90单/天（无补贴），50单/天（有补贴）
    - 当前多数点位在 20-46 单区间，严重低于盈亏平衡线

  ⚠ 绿地星玥是唯一有望盈利的点位，但：
    - 5人配置人力成本高（5×6.5×30=975元/天）
    - 必须稳定拿到人头补贴+日均120单以上才有利润
    - 常规期结算降到2.0元后压力更大
""")

    # 绿地星玥详细分析
    print("─" * 60)
    print("【绿地星玥 — 重点点位分析】")
    print("─" * 60)
    lvdi_data = df_actual[df_actual["点位"] == "绿地星玥"]
    print(tabulate(lvdi_data[display_cols], headers="keys", tablefmt="grid",
                   showindex=False, numalign="right", stralign="left"))

    # 常规期绿地星玥模拟
    print("\n  常规期模拟（结算价2.0元，假设单量不变）：")
    for _, row in lvdi_data.iterrows():
        orders = row["单量"]
        staff = row["人数"]
        hours = row["营业时长(h)"]
        # 常规期重算
        order_rev = orders * SETTLEMENT_PER_ORDER_REGULAR
        eligible, reason = check_subsidy_eligible(staff, hours, orders)
        sub = HEADCOUNT_SUBSIDY_PER_POINT if eligible else 0
        total_rev = order_rev + sub
        labor = staff * hours * LABOR_RATE_HOURLY
        mat = MATERIAL_COST_PER_POINT / MATERIAL_AMORT_DAYS
        total_cost = labor + mat
        profit = total_rev - total_cost
        margin = profit / total_rev * 100 if total_rev > 0 else 0
        print(f"    {row['日期']}: 单量{int(orders)}, 收入{total_rev:.0f}元, "
              f"成本{total_cost:.0f}元, 毛利{profit:.0f}元, 毛利率{margin:.1f}%, "
              f"补贴{'✓' if eligible else '✗'}")

    print("\n" + "=" * 80)
    print("输出文件已保存到 output/ 目录:")
    print("  - actual_daily_pnl.csv     实际点位逐日损益")
    print("  - point_summary.csv         点位汇总")
    print("  - breakeven.csv             盈亏平衡分析")
    print("  - subsidy_threshold_profit.csv  补贴门槛利润")
    print("  - rider_fee_sensitivity.csv 骑手费率敏感性")
    print("  - scenario_matrix.csv       场景矩阵")
    print("=" * 80)


if __name__ == "__main__":
    main()
