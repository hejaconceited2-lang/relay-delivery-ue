"""
接力送 · 分包分润模型
====================
平台方出资（物料+系统），运营方出力（人员+管理），利润五五分。
基于现有三阶段参数，测算不同单量下的分润结果。
"""

import pandas as pd
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# 全局参数（与 relay_delivery_model / three_phase_model 一致）
# ═══════════════════════════════════════════════════════════
LABOR_RATE = 30       # 元/h/人
MAT_MONTH = 100       # 元/点位/月
MAT_DAILY = MAT_MONTH / 30
DAYS = 30
CAPACITY = 12         # 单/h/人（实测基准）
MIN_OPP = 20          # 人均最低单量（补贴门槛）
ANCHOR_H = 3.0        # 锚定人员固定工时
SPLIT_RATIO = 0.5     # 分润比例（50:50）

# 三阶段参数
PHASES = {
    "Phase1": {"rider_fee": 1.0, "settlement": 2.5, "subsidy": True,  "label": "引流期"},
    "Phase2": {"rider_fee": 2.0, "settlement": 2.5, "subsidy": True,  "label": "长期补贴"},
    "Phase3": {"rider_fee": 2.0, "settlement": 2.0, "subsidy": False, "label": "补贴归零"},
}


def rider_vol_mult(fee):
    """骑手费率 → 单量保留率"""
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


def optimal_staffing(daily_orders):
    """搜索最优排班（1锚 + N峰），返回 (总人数, 总工时, 人均单量, 是否达标补贴)"""
    best = None
    best_profit = -float("inf")

    for n in range(0, 21):  # 0-20 个峰期人员
        for h in [2.0, 2.5, 3.0]:
            total_h = ANCHOR_H + n * h
            capacity = CAPACITY * total_h
            if capacity < daily_orders:
                continue
            total_people = 1 + n  # 锚定 + 峰期
            opp = daily_orders / total_people
            labor_cost = total_h * LABOR_RATE + MAT_DAILY
            # 此处只比总成本最低，不涉及收入
            if labor_cost < best_profit or best is None:
                # 用人力成本做初筛，选成本最低的可行方案
                if best is None or labor_cost < best_profit:
                    best_profit = labor_cost
                    best = {
                        "n_peak": n, "peak_h": h,
                        "total_people": total_people,
                        "total_hours": total_h,
                        "opp": round(opp, 1),
                        "subsidy_ok": opp >= MIN_OPP,
                    }
    if best is None:
        # fallback: 用简化产能公式
        for n in range(0, 31):
            if 20 * n + 21 >= daily_orders:
                best = {
                    "n_peak": n, "peak_h": 2.0,
                    "total_people": 1 + n,
                    "total_hours": ANCHOR_H + n * 2.0,
                    "opp": round(daily_orders / (1 + n), 1),
                    "subsidy_ok": daily_orders / (1 + n) >= MIN_OPP,
                }
                break
        else:
            best = {
                "n_peak": 30, "peak_h": 2.0,
                "total_people": 31,
                "total_hours": ANCHOR_H + 60,
                "opp": round(daily_orders / 31, 1),
                "subsidy_ok": False,
            }
    return best


def calc_point(daily_orders, phase_key):
    """计算单个点位在指定阶段的月度分润"""
    p = PHASES[phase_key]

    # 单量衰减
    vol_mult = rider_vol_mult(p["rider_fee"])
    actual_orders = max(5, int(daily_orders * vol_mult))

    # 排班
    staff = optimal_staffing(actual_orders)

    # 日收入
    daily_settlement = actual_orders * p["settlement"]
    daily_rider_fee = actual_orders * p["rider_fee"]
    daily_subsidy = (staff["total_people"] - 1) * 80 if (p["subsidy"] and staff["subsidy_ok"]) else 0
    daily_revenue = daily_settlement + daily_rider_fee + daily_subsidy

    # 日成本
    daily_labor = staff["total_hours"] * LABOR_RATE
    daily_cost = daily_labor + MAT_DAILY

    # 日利润
    daily_profit = daily_revenue - daily_cost

    # 月度
    monthly_revenue = daily_revenue * DAYS
    monthly_labor = daily_labor * DAYS
    monthly_subsidy = daily_subsidy * DAYS
    monthly_cost = daily_cost * DAYS
    monthly_profit = daily_profit * DAYS

    # 分润
    platform_share = monthly_profit * SPLIT_RATIO
    operator_share = monthly_profit * SPLIT_RATIO

    return {
        "阶段": p["label"],
        "基准单量": daily_orders,
        "实际单量": actual_orders,
        "骑手费率": p["rider_fee"],
        "结算价": p["settlement"],
        "补贴": "有" if (p["subsidy"] and staff["subsidy_ok"]) else "无",
        "排班": f"1锚+{staff['n_peak']}峰×{staff['peak_h']}h",
        "人数": staff["total_people"],
        "总工时_h": round(staff["total_hours"], 1),
        "人均单量": staff["opp"],
        "日收入": round(daily_revenue, 0),
        "其中_结算": round(daily_settlement, 0),
        "其中_骑手费": round(daily_rider_fee, 0),
        "其中_补贴": round(daily_subsidy, 0),
        "日人力成本": round(daily_labor, 0),
        "日利润": round(daily_profit, 0),
        "月收入": round(monthly_revenue, 0),
        "月人力": round(monthly_labor, 0),
        "月人头补贴": round(monthly_subsidy, 0),
        "月物料": MAT_MONTH,
        "月净利": round(monthly_profit, 0),
        "月净利率": f"{monthly_profit/monthly_revenue*100:+.1f}%" if monthly_revenue > 0 else "N/A",
        "平台月分成": round(platform_share, 0),
        "运营方月分成": round(operator_share, 0),
        "单均利润": round(daily_profit / actual_orders, 2) if actual_orders else 0,
        "单均运营方分成": round(operator_share / (actual_orders * DAYS), 2) if actual_orders else 0,
    }


def fm(v):
    """金额格式化"""
    if v >= 0:
        return f"¥{v:+,.0f}"
    return f"-¥{abs(v):,.0f}"


def print_summary_table(results):
    """终端输出分润汇总表"""
    print(f"\n{'='*120}")
    print("接力送 · 分包分润测算（平台:运营 = 50:50）")
    print(f"{'='*120}")

    for phase_label, data in results.items():
        print(f"\n{'─'*100}")
        print(f"  {phase_label}")
        print(f"{'─'*100}")
        header = (
            f"{'基准':>5s} | {'实际':>4s} | {'排班':>14s} | {'人数':>3s} | "
            f"{'月收入':>10s} | {'月人力':>10s} | {'月补贴':>10s} | "
            f"{'月净利':>10s} | {'平台':>10s} | {'运营方':>10s} | {'单均':>6s}"
        )
        print(header)
        print("-" * len(header))

        for r in data:
            print(
                f"{r['基准单量']:5d} | {r['实际单量']:4d} | {r['排班']:>14s} | {r['人数']:3d} | "
                f"{fm(r['月收入']):>10s} | {fm(r['月人力']):>10s} | {fm(r['月人头补贴']):>10s} | "
                f"{fm(r['月净利']):>10s} | {fm(r['平台月分成']):>10s} | {fm(r['运营方月分成']):>10s} | "
                f"{r['单均运营方分成']:>+6.2f}"
            )


def export_csv(results):
    """导出 CSV"""
    for phase_key, data in results.items():
        df = pd.DataFrame(data)
        path = os.path.join(OUTPUT_DIR, f"subcontract_{phase_key}.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"已保存: {path}")


def main():
    # 基准单量梯度
    levels = [30, 40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 400, 500]

    results = {}
    for phase_key in PHASES:
        results[PHASES[phase_key]["label"]] = [
            calc_point(o, phase_key) for o in levels
        ]

    print_summary_table(results)
    export_csv(results)

    # ═══════════════════════════════════════════════════════════
    # 关键发现
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*100}")
    print("关键发现")
    print(f"{'='*100}")

    # Phase 1 盈亏平衡点
    p1 = results["引流期"]
    be1 = next((r for r in p1 if r["月净利"] >= 0), None)
    if be1:
        print(f"Phase 1 盈亏平衡: {be1['基准单量']}单/天 "
              f"(实际{be1['实际单量']}单, 双方各得{fm(be1['运营方月分成'])}/月)")

    # Phase 2 盈亏平衡点
    p2 = results["长期补贴"]
    be2 = next((r for r in p2 if r["月净利"] >= 0), None)
    if be2:
        print(f"Phase 2 盈亏平衡: {be2['基准单量']}单/天 "
              f"(实际{be2['实际单量']}单, 双方各得{fm(be2['运营方月分成'])}/月)")
    else:
        # 找最小亏损点
        best_p2 = min(p2, key=lambda r: abs(r["月净利"]))
        print(f"Phase 2 无法盈亏平衡。最优点: {best_p2['基准单量']}单/天, "
              f"月净利 {fm(best_p2['月净利'])}")

    # Phase 3
    best_p3 = max(p3 := results["补贴归零"], key=lambda r: r["月净利"])
    print(f"Phase 3 全线亏损。最优: {best_p3['基准单量']}单/天, 月净利 {fm(best_p3['月净利'])}")

    # 200单 → Phase 2 的对比
    d200_p1 = next(r for r in p1 if r["基准单量"] == 200)
    d200_p2 = next(r for r in p2 if r["基准单量"] == 200)
    print(f"\n200单点位 Phase 1→Phase 2 分润变化:")
    print(f"  运营方月分成: {fm(d200_p1['运营方月分成'])} → {fm(d200_p2['运营方月分成'])}")
    print(f"  降幅: {(1 - d200_p2['运营方月分成']/d200_p1['运营方月分成'])*100:.0f}%")


if __name__ == "__main__":
    main()
