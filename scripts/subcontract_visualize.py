"""
接力送 · 分包分润可视化
======================
生成6张图表，展示分包五五分润方案的三阶段经济效果
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

# ═══════════════════════════════════════════════════════════
# 中文字体
# ═══════════════════════════════════════════════════════════
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# 全局参数
# ═══════════════════════════════════════════════════════════
LABOR_RATE = 30
MAT_MONTH = 100
MAT_DAILY = MAT_MONTH / 30
DAYS = 30
CAPACITY = 12
MIN_OPP = 20
ANCHOR_H = 3.0
SPLIT = 0.5

PHASES = {
    "Phase1": {"rider_fee": 1.0, "settlement": 2.5, "subsidy": True,  "label": "引流期",    "color": "#27ae60"},
    "Phase2": {"rider_fee": 2.0, "settlement": 2.5, "subsidy": True,  "label": "长期补贴",  "color": "#2980b9"},
    "Phase3": {"rider_fee": 2.0, "settlement": 2.0, "subsidy": False, "label": "补贴归零",  "color": "#e74c3c"},
}

PAC = ["#27ae60", "#2980b9", "#e74c3c", "#f39c12", "#8e44ad", "#1abc9c", "#2c3e50"]


def rider_vol_mult(fee):
    surplus = 3.0 - fee
    ratio = surplus / 3.0
    if ratio >= 0.7:   return 1.0
    elif ratio >= 0.5: return 0.95 - (0.7 - ratio) * 2.5
    elif ratio >= 0.3: return 0.50 - (0.5 - ratio) * 1.5
    elif ratio >= 0.15: return 0.25 - (0.3 - ratio) * 1.2
    else:              return max(0.05, ratio * 0.6)


def optimal_staffing(daily_orders):
    """搜索最优排班，返回 (总人数, 总工时, 人均单量, 达标补贴)"""
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
                best = (tp, total_h, round(opp, 1), opp >= MIN_OPP)
    if best is None:
        for n in range(0, 31):
            if 20 * n + 21 >= daily_orders:
                tp = 1 + n
                total_h = ANCHOR_H + n * 2.0
                opp = daily_orders / tp
                return tp, total_h, round(opp, 1), opp >= MIN_OPP
        tp, total_h = 31, ANCHOR_H + 60
        return tp, total_h, round(daily_orders / 31, 1), False
    return best


def calc_subcontract(daily_orders, phase_key):
    """计算分包分润，返回月度数据"""
    p = PHASES[phase_key]
    actual = max(5, int(daily_orders * rider_vol_mult(p["rider_fee"])))
    tp, th, opp, sub_ok = optimal_staffing(actual)
    daily_sub = (tp - 1) * 80 if (p["subsidy"] and sub_ok) else 0
    daily_rev = actual * (p["settlement"] + p["rider_fee"]) + daily_sub
    daily_labor = th * LABOR_RATE
    daily_profit = daily_rev - daily_labor - MAT_DAILY

    return {
        "actual": actual, "tp": tp, "th": th, "opp": opp,
        "monthly_rev": daily_rev * DAYS,
        "monthly_labor": daily_labor * DAYS,
        "monthly_sub": daily_sub * DAYS,
        "monthly_profit": daily_profit * DAYS,
        "operator_share": daily_profit * DAYS * SPLIT,
        "platform_share": daily_profit * DAYS * SPLIT,
        "per_order_op": (daily_profit * SPLIT / actual) if actual else 0,
    }


def fm(v):
    return f"¥{v:+,.0f}" if v >= 0 else f"-¥{abs(v):,.0f}"


# ═══════════════════════════════════════════════════════════
# 图1: 三阶段运营方月分成曲线
# ═══════════════════════════════════════════════════════════
def fig1_operator_share_curves():
    fig, ax = plt.subplots(figsize=(14, 7))
    orders_range = np.arange(30, 510, 5)
    all_data = {}

    for pk, p in PHASES.items():
        shares = []
        actuals = []
        for o in orders_range:
            d = calc_subcontract(o, pk)
            shares.append(d["operator_share"])
            actuals.append(d["actual"])
        all_data[pk] = {"shares": shares, "actuals": actuals}

        ax.plot(orders_range, shares, color=p["color"], linewidth=2.5,
                label=f'{p["label"]}（骑手付¥{p["rider_fee"]:.0f} | 结算¥{p["settlement"]:.1f}）',
                marker="", zorder=3)

    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)

    # 标注盈亏平衡点
    for pk, p in PHASES.items():
        for i, s in enumerate(all_data[pk]["shares"]):
            if s >= 0:
                o = orders_range[i]
                ax.annotate(f'BE={o}单',
                            xy=(o, 0), xytext=(o, 1500 if pk == "Phase1" else -2000),
                            fontsize=9, fontweight="bold", color=p["color"],
                            ha="center",
                            arrowprops=dict(arrowstyle="->", color=p["color"], alpha=0.7),
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85))
                break

    # Phase 1→Phase 2 断崖标注
    ax.annotate("", xy=(200, all_data["Phase2"]["shares"][(200-30)//5]),
                xytext=(200, all_data["Phase1"]["shares"][(200-30)//5]),
                arrowprops=dict(arrowstyle="<->", color="#2c3e50", lw=2.5))
    ax.text(215,
            (all_data["Phase1"]["shares"][(200-30)//5] + all_data["Phase2"]["shares"][(200-30)//5]) / 2,
            "200单点位\nPhase1→2断崖\n降幅68%", fontsize=9, fontweight="bold",
            color="#2c3e50", va="center",
            bbox=dict(boxstyle="round", facecolor="#fff3cd", alpha=0.9))

    ax.set_xlabel("基准日单量（单）", fontsize=12)
    ax.set_ylabel("运营方月分成（元）", fontsize=12)
    ax.set_title("运营方月度分成 · 三阶段对比（50% 分润）", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(30, 500)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("¥%d"))

    # 右上角信息框
    ax.text(0.98, 0.95,
            "平台:运营方 = 50:50\n"
            "平台垫付人力+物料\n"
            "补贴统一入池",
            transform=ax.transAxes, fontsize=9, va="top", ha="right",
            bbox=dict(boxstyle="round", facecolor="#eaf2f8", alpha=0.85))

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "subcontract_fig1_operator_share.png")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {os.path.basename(path)}")


# ═══════════════════════════════════════════════════════════
# 图2: 分润瀑布图 — 收入→成本→利润→分成
# ═══════════════════════════════════════════════════════════
def fig2_profit_waterfall():
    scenarios = [
        ("Phase1\n60单", "Phase1", 60),
        ("Phase1\n150单", "Phase1", 150),
        ("Phase1\n200单", "Phase1", 200),
        ("Phase2\n200单", "Phase2", 200),
        ("Phase3\n200单", "Phase3", 200),
    ]

    fig, ax = plt.subplots(figsize=(16, 7))
    x = np.arange(len(scenarios))
    bar_w = 0.55

    # 收集数据
    labels, settlements, rider_fees, subsidies, labors, materials, operator_shares, platform_shares, profits = (
        [], [], [], [], [], [], [], [], [])

    for label, pk, orders in scenarios:
        d = calc_subcontract(orders, pk)
        monthly = d["monthly_rev"]
        labels.append(label)
        settlements.append(d["actual"] * DAYS * PHASES[pk]["settlement"])
        rider_fees.append(d["actual"] * DAYS * PHASES[pk]["rider_fee"])
        subsidies.append(d["monthly_sub"])
        labors.append(-d["monthly_labor"])
        materials.append(-MAT_MONTH)
        operator_shares.append(d["operator_share"])
        platform_shares.append(d["platform_share"])
        profits.append(d["monthly_profit"])

    # 堆叠柱状图
    # 第1层: 结算收入(蓝色)
    bars_settle = ax.bar(x, settlements, bar_w, color="#3498db", alpha=0.9, label="美团结算", zorder=3)
    # 第2层: 骑手费(青色)
    bars_rider = ax.bar(x, rider_fees, bar_w, bottom=settlements, color="#1abc9c", alpha=0.85, label="骑手费收入", zorder=3)
    # 第3层: 补贴(绿色)
    bottom_after_rider = [s + r for s, r in zip(settlements, rider_fees)]
    bars_sub = ax.bar(x, subsidies, bar_w, bottom=bottom_after_rider,
                      color="#27ae60", alpha=0.7, label="人头补贴", zorder=3)

    # 总收入线
    total_revenues = [s + r + sub for s, r, sub in zip(settlements, rider_fees, subsidies)]
    for i, tr in enumerate(total_revenues):
        ax.plot([i - bar_w/2, i + bar_w/2], [tr, tr], color="#2c3e50", linewidth=2, zorder=5)

    # 成本箭头（红色向下）
    cost_bottoms = total_revenues.copy()
    for i, (labor, mat) in enumerate(zip(labors, materials)):
        # 人力成本
        ax.bar(i, labor, bar_w * 0.6, bottom=cost_bottoms[i],
               color="#e74c3c", alpha=0.7, label="人力成本" if i == 0 else "", zorder=3)
        cost_after_labor = cost_bottoms[i] + labor
        # 物料
        ax.bar(i, mat, bar_w * 0.6, bottom=cost_after_labor,
               color="#c0392b", alpha=0.6, label="物料摊销" if i == 0 else "", zorder=3)

    # 净利润线
    net_bottoms = [tr + l + m for tr, l, m in zip(total_revenues, labors, materials)]
    for i, nb in enumerate(net_bottoms):
        ax.plot([i - bar_w/2, i + bar_w/2], [nb, nb], color="#8e44ad", linewidth=2.5, linestyle="--", zorder=5)

    # 分成标注
    for i, (op, pf, nb) in enumerate(zip(operator_shares, platform_shares, net_bottoms)):
        color = "#27ae60" if op >= 0 else "#e74c3c"
        ax.annotate(f'净利{fm(nb)}\n平台得{fm(pf)}\n运营方得{fm(op)}',
                    xy=(i, nb), fontsize=8.5, fontweight="bold",
                    color=color, ha="center",
                    xytext=(i, nb - 3000 if nb > 0 else nb - 4000),
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor=color, alpha=0.9))

    ax.axhline(y=0, color="black", linewidth=0.8, zorder=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("月度金额（元）", fontsize=12)
    ax.set_title("分包分润月度拆解：收入 → 成本 → 净利 → 五五分", fontsize=14, fontweight="bold")

    # 去重 legend
    handles, labs = ax.get_legend_handles_labels()
    by_label = dict(zip(labs, handles))
    ax.legend(by_label.values(), by_label.keys(), fontsize=8, loc="upper right", ncol=2)

    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(-5000, 40000)

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "subcontract_fig2_waterfall.png")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {os.path.basename(path)}")


# ═══════════════════════════════════════════════════════════
# 图3: Phase 1→Phase 2 断崖对比
# ═══════════════════════════════════════════════════════════
def fig3_phase_cliff():
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    # ---- 左图：运营方月分成降幅 ----
    ax = axes[0]
    order_points = [60, 80, 100, 150, 200, 300, 500]
    x = np.arange(len(order_points))
    width = 0.3

    p1_shares = [calc_subcontract(o, "Phase1")["operator_share"] for o in order_points]
    p2_shares = [calc_subcontract(o, "Phase2")["operator_share"] for o in order_points]
    p3_shares = [calc_subcontract(o, "Phase3")["operator_share"] for o in order_points]

    bars1 = ax.bar(x - width, p1_shares, width, color=PHASES["Phase1"]["color"],
                   alpha=0.85, label="Phase 1 引流期", zorder=3)
    bars2 = ax.bar(x, p2_shares, width, color=PHASES["Phase2"]["color"],
                   alpha=0.85, label="Phase 2 长期补贴", zorder=3)
    bars3 = ax.bar(x + width, p3_shares, width, color=PHASES["Phase3"]["color"],
                   alpha=0.85, label="Phase 3 补贴归零", zorder=3)

    # 降幅标注
    for i, (p1, p2) in enumerate(zip(p1_shares, p2_shares)):
        if p1 > 0 and p2 < p1:
            drop = (1 - p2 / p1) * 100
            ax.annotate(f"↓{drop:.0f}%",
                        xy=(i, (p1 + p2) / 2),
                        fontsize=9, fontweight="bold", color="#c0392b", ha="center",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="#fadbd8", alpha=0.85))

    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{o}单" for o in order_points], fontsize=10)
    ax.set_ylabel("运营方月分成（元）", fontsize=11)
    ax.set_title("运营方月分成 · 三阶段对比", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("¥%d"))

    # ---- 右图：单均运营方分成 ----
    ax = axes[1]
    order_range = np.arange(30, 510, 5)

    for pk, p in PHASES.items():
        per_orders = [calc_subcontract(o, pk)["per_order_op"] for o in order_range]
        ax.plot(order_range, per_orders, color=p["color"], linewidth=2.2, label=p["label"])

    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("基准日单量（单）", fontsize=11)
    ax.set_ylabel("单均运营方分成（元/单）", fontsize=11)
    ax.set_title("运营方单均分成 · 三阶段对比", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(30, 500)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("¥%.2f"))

    # 标注
    ax.annotate("Phase 1: 规模效应\n单均分成递增",
                xy=(300, 1.6), fontsize=9,
                bbox=dict(boxstyle="round", facecolor="#d5f5e3", alpha=0.8))
    ax.annotate("Phase 2: 200+单才\n突破单均¥1",
                xy=(200, 1.0), fontsize=9,
                bbox=dict(boxstyle="round", facecolor="#d4e6f1", alpha=0.8))

    fig.suptitle("分包分润：Phase 1 → Phase 2 断崖 & 单均效益", fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "subcontract_fig3_phase_cliff.png")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {os.path.basename(path)}")


# ═══════════════════════════════════════════════════════════
# 图4: 收入构成 vs 成本结构（面积图）
# ═══════════════════════════════════════════════════════════
def fig4_revenue_cost_structure():
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    order_range = np.arange(30, 510, 10)

    # ---- 左图：Phase 1 收入构成面积图 ----
    ax = axes[0]
    for pk in ["Phase1", "Phase2"]:
        p = PHASES[pk]
        settlements_arr, rider_fees_arr, subsidies_arr = [], [], []
        for o in order_range:
            d = calc_subcontract(o, pk)
            settlements_arr.append(d["actual"] * DAYS * p["settlement"])
            rider_fees_arr.append(d["actual"] * DAYS * p["rider_fee"])
            subsidies_arr.append(d["monthly_sub"])

        alpha = 0.7 if pk == "Phase1" else 0.5
        ls = "-" if pk == "Phase1" else "--"
        ax.fill_between(order_range, 0, settlements_arr,
                        alpha=alpha, color="#3498db", label=f'{p["label"]} 结算')
        ax.fill_between(order_range, settlements_arr,
                        [s + r for s, r in zip(settlements_arr, rider_fees_arr)],
                        alpha=alpha, color="#1abc9c", label=f'{p["label"]} 骑手费')
        ax.fill_between(order_range,
                        [s + r for s, r in zip(settlements_arr, rider_fees_arr)],
                        [s + r + sub for s, r, sub in zip(settlements_arr, rider_fees_arr, subsidies_arr)],
                        alpha=alpha, color="#27ae60", label=f'{p["label"]} 补贴')

    ax.set_xlabel("基准日单量（单）", fontsize=11)
    ax.set_ylabel("月收入（元）", fontsize=11)
    ax.set_title("月收入构成 · Phase 1 vs Phase 2", fontsize=13, fontweight="bold")
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(30, 500)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("¥%d"))

    # ---- 右图：成本 vs 收入（Phase 1） ----
    ax = axes[1]
    p1_revs, p1_labors, p1_mats = [], [], []
    for o in order_range:
        d = calc_subcontract(o, "Phase1")
        p1_revs.append(d["monthly_rev"])
        p1_labors.append(d["monthly_labor"])
        p1_mats.append(MAT_MONTH)

    ax.fill_between(order_range, 0, p1_labors, alpha=0.5, color="#e74c3c", label="人力成本")
    ax.fill_between(order_range, p1_labors, [l + MAT_MONTH for l in p1_labors],
                    alpha=0.5, color="#c0392b", label="物料摊销")
    ax.fill_between(order_range, [l + MAT_MONTH for l in p1_labors], p1_revs,
                    alpha=0.4, color="#27ae60", label="净利（平台+运营方各半）")

    ax.plot(order_range, p1_revs, color="#2c3e50", linewidth=2, label="总收入")

    # 盈亏平衡点
    for i, (rev, lab) in enumerate(zip(p1_revs, p1_labors)):
        if rev >= lab + MAT_MONTH:
            ax.axvline(x=order_range[i], color="#27ae60", linestyle=":", alpha=0.6, linewidth=1.5)
            ax.annotate(f'盈亏平衡\n{order_range[i]}单',
                        xy=(order_range[i], lab + MAT_MONTH),
                        fontsize=9, fontweight="bold", color="#27ae60",
                        xytext=(order_range[i] + 40, lab + MAT_MONTH + 5000),
                        arrowprops=dict(arrowstyle="->", color="#27ae60"))
            break

    ax.set_xlabel("基准日单量（单）", fontsize=11)
    ax.set_ylabel("月金额（元）", fontsize=11)
    ax.set_title("Phase 1 成本结构 vs 总收入", fontsize=13, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(30, 500)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("¥%d"))

    fig.suptitle("收入构成 & 成本结构分析", fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "subcontract_fig4_structure.png")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {os.path.basename(path)}")


# ═══════════════════════════════════════════════════════════
# 图5: 多点打包收益 — 运营方管理 N 个点位
# ═══════════════════════════════════════════════════════════
def fig5_multi_point_portfolio():
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    # 假设的点位组合：1大2中2小
    portfolio = [
        ("大点\n200单", "Phase1", 200),
        ("中点A\n100单", "Phase1", 100),
        ("中点B\n80单", "Phase1", 80),
        ("小点A\n60单", "Phase1", 60),
        ("小点B\n40单", "Phase1", 40),
    ]

    # ---- 左图：Phase 1 多点收益堆叠 ----
    ax = axes[0]
    x = np.arange(len(portfolio))
    bar_w = 0.5

    names_p1, op_shares_p1, pf_shares_p1 = [], [], []
    for label, pk, orders in portfolio:
        d = calc_subcontract(orders, pk)
        names_p1.append(label)
        op_shares_p1.append(d["operator_share"])
        pf_shares_p1.append(d["platform_share"])

    bars_op = ax.bar(x, op_shares_p1, bar_w, color="#27ae60", alpha=0.8, label="运营方分成", zorder=3)
    bars_pf = ax.bar(x, pf_shares_p1, bar_w, bottom=op_shares_p1,
                     color="#3498db", alpha=0.7, label="平台方分成", zorder=3)

    # 标注
    for i, (op, pf) in enumerate(zip(op_shares_p1, pf_shares_p1)):
        total = op + pf
        ax.text(i, total + 300, f'{fm(total)}',
                ha="center", fontsize=9, fontweight="bold", color="#2c3e50")

    total_op = sum(op_shares_p1)
    total_pf = sum(pf_shares_p1)
    ax.annotate(f'运营方合计: {fm(total_op)}/月\n平台方合计: {fm(total_pf)}/月',
                xy=(0.02, 0.95), xycoords="axes fraction",
                fontsize=11, fontweight="bold", va="top",
                bbox=dict(boxstyle="round", facecolor="#fff3cd", alpha=0.9))

    ax.set_xticks(x)
    ax.set_xticklabels(names_p1, fontsize=10)
    ax.set_ylabel("月分成（元）", fontsize=11)
    ax.set_title("Phase 1 · 5个点位打包收益", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 12000)

    # ---- 右图：Phase 2 同一组点位 ----
    ax = axes[1]
    names_p2, op_shares_p2, pf_shares_p2 = [], [], []
    for label, pk, orders in portfolio:
        d = calc_subcontract(orders, "Phase2")
        names_p2.append(label)
        op_shares_p2.append(d["operator_share"])
        pf_shares_p2.append(d["platform_share"])

    ax.bar(x, op_shares_p2, bar_w, color="#e74c3c", alpha=0.8, label="运营方分成", zorder=3)
    ax.bar(x, pf_shares_p2, bar_w, bottom=op_shares_p2,
           color="#3498db", alpha=0.7, label="平台方分成", zorder=3)

    for i, (op, pf) in enumerate(zip(op_shares_p2, pf_shares_p2)):
        total = op + pf
        color = "#27ae60" if total >= 0 else "#e74c3c"
        ax.text(i, max(total, 0) + 200 if total >= 0 else total - 800,
                f'{fm(total)}',
                ha="center", fontsize=9, fontweight="bold", color=color)

    total_op2 = sum(op_shares_p2)
    total_pf2 = sum(pf_shares_p2)
    ax.annotate(f'运营方合计: {fm(total_op2)}/月\n平台方合计: {fm(total_pf2)}/月\n'
                f'Phase 1→2 运营方↓{(1-total_op2/total_op)*100:.0f}%' if total_op > 0 else '',
                xy=(0.02, 0.95), xycoords="axes fraction",
                fontsize=11, fontweight="bold", va="top",
                bbox=dict(boxstyle="round", facecolor="#fadbd8", alpha=0.9))

    ax.set_xticks(x)
    ax.set_xticklabels(names_p2, fontsize=10)
    ax.set_ylabel("月分成（元）", fontsize=11)
    ax.set_title("Phase 2 · 同一组点位（单量暴跌后）", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(-4000, 4000)

    # 新增盈亏平衡线
    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)

    fig.suptitle("多点打包运营收益 · Phase 1 vs Phase 2", fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "subcontract_fig5_portfolio.png")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {os.path.basename(path)}")


# ═══════════════════════════════════════════════════════════
# 图6: 分包 vs 直营对比 + 敏感性
# ═══════════════════════════════════════════════════════════
def fig6_direct_vs_subcontract():
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    order_range = np.arange(30, 510, 10)

    # ---- 左图：平台方到手（直营 vs 分包） ----
    ax = axes[0]

    # 直营：平台方得到全部净利
    direct_p1 = []
    for o in order_range:
        d = calc_subcontract(o, "Phase1")
        direct_p1.append(d["monthly_profit"])

    # 分包：平台方只得到一半
    sub_p1 = []
    for o in order_range:
        d = calc_subcontract(o, "Phase1")
        sub_p1.append(d["platform_share"])

    ax.fill_between(order_range, sub_p1, direct_p1, alpha=0.3, color="#f39c12")
    ax.plot(order_range, direct_p1, color="#27ae60", linewidth=2.5, label="直营（平台得全部净利）")
    ax.plot(order_range, sub_p1, color="#2980b9", linewidth=2.5, label="分包（平台仅得50%）")

    # 标注差距
    mid = len(order_range) // 2
    ax.annotate("差额 = 运营方分走的50%\n= 规模化代价",
                xy=(order_range[mid], (direct_p1[mid] + sub_p1[mid]) / 2),
                fontsize=10, fontweight="bold",
                color="#e67e22", ha="left",
                bbox=dict(boxstyle="round", facecolor="#fef9e7", alpha=0.9))

    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("基准日单量（单）", fontsize=11)
    ax.set_ylabel("平台方月到手（元）", fontsize=11)
    ax.set_title("Phase 1 · 直营 vs 分包（平台方视角）", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(30, 500)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("¥%d"))

    # ---- 右图：人效偏离敏感性（运营方多排人） ----
    ax = axes[1]

    # 以100单为例，看人为多排1人的影响
    base_orders = 100
    d_base = calc_subcontract(base_orders, "Phase1")
    base_people = d_base["tp"]
    base_hours = d_base["th"]

    extra_people = np.arange(0, 6)  # 多排0-5人
    operator_losses = []
    platform_losses = []

    for extra in extra_people:
        tp = base_people + extra
        # 多排的人每人3h
        th = base_hours + extra * 3.0
        opp = d_base["actual"] / tp
        daily_sub = (tp - 1) * 80 if (PHASES["Phase1"]["subsidy"] and opp >= MIN_OPP) else 0
        daily_rev = d_base["actual"] * (PHASES["Phase1"]["settlement"] + PHASES["Phase1"]["rider_fee"]) + daily_sub
        daily_labor = th * LABOR_RATE
        monthly_profit = (daily_rev - daily_labor - MAT_DAILY) * DAYS
        operator_losses.append(monthly_profit * SPLIT)
        platform_losses.append(monthly_profit * SPLIT)

    ax.bar(extra_people, operator_losses, 0.35, color="#e74c3c", alpha=0.8, label="运营方分成", zorder=3)
    ax.bar(extra_people + 0.35, platform_losses, 0.35, color="#3498db", alpha=0.7, label="平台方分成", zorder=3)

    # 标注基准
    ax.axhline(y=operator_losses[0], color="#27ae60", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.annotate(f'基准: 双方各得\n{fm(operator_losses[0])}/月',
                xy=(0, operator_losses[0]),
                fontsize=9, fontweight="bold", color="#27ae60",
                xytext=(1.5, operator_losses[0] + 1000),
                arrowprops=dict(arrowstyle="->", color="#27ae60"))

    # 标注补贴门槛
    for i, extra in enumerate(extra_people):
        tp = base_people + extra
        opp = d_base["actual"] / tp
        if opp < MIN_OPP:
            ax.axvline(x=extra - 0.2, color="#e74c3c", linestyle=":", alpha=0.5, linewidth=1.5)
            ax.annotate(f'人均{opp:.0f}<20\n补贴归零!',
                        xy=(extra, operator_losses[i]),
                        fontsize=8, fontweight="bold", color="#e74c3c",
                        xytext=(extra + 0.5, operator_losses[i] - 1000),
                        arrowprops=dict(arrowstyle="->", color="#e74c3c"))
            break

    ax.set_xlabel("多排的人数", fontsize=11)
    ax.set_ylabel("月分成（元）", fontsize=11)
    ax.set_title(f"100单点位 · 运营方多排1人的后果（Phase 1）", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xticks(extra_people + 0.175)
    ax.set_xticklabels([f"+{e}人" for e in extra_people])

    fig.suptitle("直营 vs 分包对比 & 人效偏离风险", fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "subcontract_fig6_direct_vs_sub.png")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {os.path.basename(path)}")


# ═══════════════════════════════════════════════════════════
def main():
    print("生成分包分润可视化图表...\n")
    print("  [1/6] 三阶段运营方分成曲线...")
    fig1_operator_share_curves()
    print("  [2/6] 分润瀑布图...")
    fig2_profit_waterfall()
    print("  [3/6] Phase断崖对比...")
    fig3_phase_cliff()
    print("  [4/6] 收入成本结构...")
    fig4_revenue_cost_structure()
    print("  [5/6] 多点打包收益...")
    fig5_multi_point_portfolio()
    print("  [6/6] 直营vs分包 + 人效敏感性...")
    fig6_direct_vs_subcontract()

    print(f"\n6张分包分润图表已保存到 {OUTPUT_DIR}/")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.startswith("subcontract_fig"):
            print(f"  ✓ {f}")


if __name__ == "__main__":
    main()
