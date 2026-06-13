"""
接力送项目 — 盈利模型可视化
===========================
生成6张核心图表，保存到 output/ 目录
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

# ============================================================
# 中文字体设置 (Windows)
# ============================================================
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 参数（与模型脚本一致）
# ============================================================
LABOR_RATE = 30
SUBSIDY = 80
MIN_ORDERS_PER_PERSON = 20
MATERIAL_DAILY = 100 / 30

PAC = ["#2c3e50", "#e74c3c", "#27ae60", "#2980b9", "#8e44ad", "#f39c12", "#1abc9c"]


def daily_cost(staff, hours):
    return staff * hours * LABOR_RATE + MATERIAL_DAILY


def subsidy_ok(staff, orders):
    return orders / staff > MIN_ORDERS_PER_PERSON


def profit(staff, hours, orders, settlement):
    rev = orders * settlement + (SUBSIDY if subsidy_ok(staff, orders) else 0)
    return rev - daily_cost(staff, hours)


# ============================================================
# 图1: 利润曲线 — 不同配置在不同单量下的日利润
# ============================================================
def fig1_profit_curves():
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    configs = [
        (2, 3.0, "2人×3h"),
        (2, 4.0, "2人×4h"),
        (2, 5.0, "2人×5h"),
        (3, 3.0, "3人×3h"),
        (3, 4.0, "3人×4h"),
    ]
    order_range = np.arange(10, 131)

    for ax, (settlement, title) in zip(axes, [(2.5, "推广期（结算 2.5 元/单）"), (2.0, "常规期（结算 2.0 元/单）")]):
        for i, (staff, hours, label) in enumerate(configs):
            profits = [profit(staff, hours, o, settlement) for o in order_range]
            ax.plot(order_range, profits, color=PAC[i], linewidth=1.8, label=label, alpha=0.9)

        ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.axvline(x=41, color="#e74c3c", linestyle=":", linewidth=0.8,
                   alpha=0.6, label="补贴门槛 41单")
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.set_xlabel("日单量（单）", fontsize=11)
        ax.set_ylabel("日利润（元）", fontsize=11)
        ax.legend(fontsize=8, ncol=2, loc="lower right")
        ax.set_xlim(10, 130)
        ax.set_ylim(-400, 150)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))
        ax.grid(True, alpha=0.3)

    fig.suptitle("不同人员配置下的日利润曲线", fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/fig1_profit_curves.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================
# 图2: 盈亏平衡热力图 — 人数 × 时长 × 结算价
# ============================================================
def fig2_breakeven_heatmap():
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    staff_range = range(2, 9)
    hours_range = np.arange(3.0, 8.5, 0.5)

    for ax, (settlement, title) in zip(axes, [(2.5, "推广期 2.5元/单"), (2.0, "常规期 2.0元/单")]):
        data = np.zeros((len(staff_range), len(hours_range)))
        for si, staff in enumerate(staff_range):
            for hi, hours in enumerate(hours_range):
                cost = daily_cost(staff, hours)
                # 有补贴的盈亏平衡
                be = (cost - SUBSIDY) / settlement
                data[si, hi] = be

        im = ax.imshow(data, aspect="auto", cmap="RdYlGn_r",
                       extent=[hours_range[0]-0.25, hours_range[-1]+0.25,
                               staff_range[-1]+0.5, staff_range[0]-0.5])
        for si, staff in enumerate(staff_range):
            for hi, hours in enumerate(hours_range):
                val = data[si, hi]
                color = "white" if val > 200 else "black"
                ax.text(hours, staff, f"{val:.0f}", ha="center", va="center",
                        fontsize=7, color=color, fontweight="bold")

        ax.set_title(f"{title}\n盈亏平衡单量（有补贴）", fontsize=12, fontweight="bold")
        ax.set_xlabel("营业时长（h）", fontsize=11)
        ax.set_ylabel("人数", fontsize=11)
        ax.set_yticks(list(staff_range))
        cbar = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
        cbar.set_label("盈亏平衡单量（单/天）", fontsize=10)

    fig.suptitle("盈亏平衡热力图：人员配置 vs 营业时长", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/fig2_breakeven_heatmap.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================
# 图3: 各点位盈亏瀑布图 — 当前单量下的收入/成本拆解
# ============================================================
def fig3_point_waterfall():
    points = {
        "万科欧泊\n46单": (46, 2.5),
        "万科欧泊\n46单(常规)": (46, 2.0),
        "万菱广场\n41单": (41, 2.5),
        "万菱广场\n41单(常规)": (41, 2.0),
        "和业广场\n36单": (36, 2.5),
        "金鹰大厦\n20单": (20, 2.5),
    }

    fig, ax = plt.subplots(figsize=(16, 7))
    x = np.arange(len(points))
    width = 0.25

    costs = []
    revenues = []
    subsidies = []
    profits = []

    for name, (orders, settlement) in points.items():
        staff, hours = 2, 3.0
        cost_val = daily_cost(staff, hours)
        rev_val = orders * settlement
        sub_val = SUBSIDY if subsidy_ok(staff, orders) else 0
        profit_val = rev_val + sub_val - cost_val

        costs.append(-cost_val)
        revenues.append(rev_val)
        subsidies.append(sub_val)
        profits.append(profit_val)

    # 画成本柱（红色在下）
    ax.bar(x, costs, width * 1.2, color="#e74c3c", alpha=0.85, label="人力+物料成本", zorder=3)
    # 订单收入在成本之上
    ax.bar(x, revenues, width, color="#3498db", alpha=0.85, bottom=costs, label="订单收入", zorder=3)
    # 补贴在订单收入之上
    sub_bottom = [c + r for c, r in zip(costs, revenues)]
    ax.bar(x, subsidies, width, color="#27ae60", alpha=0.85, bottom=sub_bottom, label="人头补贴", zorder=3)

    # 利润/亏损标注
    for i, p in enumerate(profits):
        total = revenues[i] + subsidies[i]
        color = "#27ae60" if p >= 0 else "#e74c3c"
        ax.annotate(f"{'盈利' if p>=0 else '亏损'}\n{p:+.0f}元",
                    xy=(i, total), fontsize=10, fontweight="bold",
                    color=color, ha="center",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor=color, alpha=0.9))

    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(list(points.keys()), fontsize=9)
    ax.set_ylabel("金额（元）", fontsize=11)
    ax.set_title("各点位日收入/成本拆解（2人×3h 配置）", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(-250, 250)

    # 添加补贴门槛标注
    ax.annotate("补贴门槛=\n人均>20单", xy=(0.3, 0.95), xycoords="axes fraction",
                fontsize=9, ha="left",
                bbox=dict(boxstyle="round", facecolor="#fff3cd", alpha=0.9))

    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/fig3_point_waterfall.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================
# 图4: 骑手费率敏感性 — 订单量与利润的权衡
# ============================================================
def fig4_rider_fee_sensitivity():
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    # 订单量衰减曲线
    fees = np.linspace(0.5, 2.5, 50)

    def volume_mult(fee):
        if fee <= 0.9:
            return 1.0
        elif fee <= 1.0:
            return 0.95
        elif fee <= 1.5:
            return 0.95 - (fee - 1.0) / 0.5 * 0.45
        else:
            return 0.50 - (fee - 1.5) / 0.5 * 0.25

    volumes = [volume_mult(f) for f in fees]

    # 左图：订单量衰减
    ax = axes[0]
    ax.plot(fees, [v * 100 for v in volumes], color="#2c3e50", linewidth=2.5, zorder=2)
    ax.fill_between(fees, [v * 100 for v in volumes], alpha=0.15, color="#2c3e50")

    # 标注已知数据点
    ax.scatter([0.9], [100], color="#27ae60", s=120, zorder=5)
    ax.annotate("0.9元\n意愿强烈\n100%单量", xy=(0.9, 100), xytext=(0.6, 110),
                fontsize=9, ha="center",
                arrowprops=dict(arrowstyle="->", color="#27ae60"),
                bbox=dict(boxstyle="round", facecolor="#d5f5e3"))
    ax.scatter([1.5], [50], color="#e74c3c", s=120, zorder=5)
    ax.annotate("1.5元\n掉量50%\n恢复后稳定", xy=(1.5, 50), xytext=(1.8, 65),
                fontsize=9, ha="center",
                arrowprops=dict(arrowstyle="->", color="#e74c3c"),
                bbox=dict(boxstyle="round", facecolor="#fadbd8"))
    ax.scatter([2.0], [volume_mult(2.0) * 100], color="#f39c12", s=120, zorder=5)
    ax.annotate(f"2.0元\n预计掉量\n至{volume_mult(2.0)*100:.0f}%", xy=(2.0, volume_mult(2.0)*100),
                xytext=(2.2, 40), fontsize=9, ha="center",
                arrowprops=dict(arrowstyle="->", color="#f39c12"),
                bbox=dict(boxstyle="round", facecolor="#fef9e7"))

    ax.set_xlabel("骑手每单付费（元）", fontsize=11)
    ax.set_ylabel("预估订单量（% 基准）", fontsize=11)
    ax.set_title("骑手费率 → 订单量衰减", fontsize=12, fontweight="bold")
    ax.set_xlim(0.4, 2.6)
    ax.set_ylim(0, 120)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%d%%"))

    # 右图：利润 vs 费率（2人×3h配置，基准31单）
    ax = axes[1]
    base_orders = 31
    rider_fees = [0.5, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0]

    for settlement, label, color, ls in [
        (2.5, "推广期（结算2.5元）", "#27ae60", "-"),
        (2.0, "常规期（结算2.0元）", "#e74c3c", "--")
    ]:
        est_orders = [base_orders * volume_mult(f) for f in rider_fees]
        profits_list = []
        for f, o in zip(rider_fees, est_orders):
            oi = int(round(o))
            if oi < 1:
                oi = 1
            staff, hours = 2, 3.0
            # 根据单量调整（如果单量低，保持2人3h）
            p = profit(staff, hours, oi, settlement)
            profits_list.append(max(p, -daily_cost(staff, hours)))  # 最差亏掉成本

        ax.plot(rider_fees, profits_list, color=color, linewidth=2.2,
                marker="o", markersize=8, linestyle=ls, label=label)

    ax.axhline(y=0, color="gray", linestyle=":", alpha=0.7, linewidth=0.8)
    ax.fill_between([0.5, 2.0], 0, -200, alpha=0.03, color="red", label="亏损区")
    ax.fill_between([0.5, 2.0], 0, 100, alpha=0.03, color="green", label="盈利区")

    ax.set_xlabel("骑手每单付费（元）", fontsize=11)
    ax.set_ylabel("预估日利润（元）", fontsize=11)
    ax.set_title(f"骑手费率 → 我方日利润（基准 {base_orders} 单/天）", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0.4, 2.2)

    fig.suptitle("骑手费率敏感性分析", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/fig4_rider_fee_sensitivity.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================
# 图5: 各点位盈亏距离 — 横向条形图
# ============================================================
def fig5_point_gap():
    points_data = [
        ("万科欧泊", 46, 3, 3.0),
        ("绿地星玥 (当前)", 151, 5, 6.5),
        ("绿地星玥 (优化)", 151, 3, 4.0),
        ("万菱广场", 41, 2, 3.0),
        ("和业广场", 36, 2, 3.0),
        ("金鹰大厦", 20, 2, 3.0),
        ("华林国际C馆", 3, 2, 3.0),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    for ax, (settlement, title) in zip(axes, [(2.5, "推广期（2.5元/单）"), (2.0, "常规期（2.0元/单）")]):
        names = []
        current_loss = []
        be_orders = []
        gap_pct = []
        colors = []

        for name, orders, staff, hours in points_data:
            cost = daily_cost(staff, hours)
            p = profit(staff, hours, orders, settlement)
            be = (cost - SUBSIDY) / settlement
            gap = be - orders

            names.append(name)
            current_loss.append(p)
            be_orders.append(be)
            gap_pct.append(max(0, gap))
            colors.append("#27ae60" if p >= 0 else ("#f39c12" if gap <= 10 else "#e74c3c"))

        y_pos = range(len(names))

        # 水平柱状图：当前单量 vs 盈亏平衡单量
        ax.barh(y_pos, [p["orders"] for p in [
            {"orders": 46}, {"orders": 151}, {"orders": 151}, {"orders": 41},
            {"orders": 36}, {"orders": 20}, {"orders": 3}
        ]], height=0.35, color="#3498db", alpha=0.7, label="当前单量")

        # 标注BE线
        for i, be in enumerate(be_orders):
            ax.axvline(x=be, ymin=(i-0.2)/len(names), ymax=(i+0.2)/len(names),
                       color="#e74c3c" if gap_pct[i] > 5 else "#27ae60",
                       linewidth=2, alpha=0.8)

        # 利润标注
        for i, p in enumerate(current_loss):
            sign = "+" if p >= 0 else ""
            ax.text(max(5, be_orders[i] + 5), i, f"日利{sign}{p:.0f}元 | BE={be_orders[i]:.0f}单",
                    va="center", fontsize=9, fontweight="bold",
                    color=colors[i])

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=10)
        ax.set_xlabel("单量（单/天）", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)
        ax.set_xlim(0, max(be_orders) + 80)

        # 红色竖线标注补贴门槛
        ax.axvline(x=41, color="gray", linestyle=":", alpha=0.5, linewidth=1)
        ax.text(42, len(names) - 0.3, "补贴门槛 41单", fontsize=7, color="gray", alpha=0.7)

    fig.suptitle("各点位当前单量 vs 盈亏平衡单量（2人×3h配置）", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/fig5_point_gap.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================
# 图6: 非对称 vs 对称排班对比
# ============================================================
def fig6_asymmetric_vs_symmetric():
    fig, ax = plt.subplots(figsize=(15, 7))

    orders = np.arange(10, 81, 2)

    # 对称2人×3h
    sym_profits_promo = [profit(2, 3.0, o, 2.5) for o in orders]
    sym_profits_regular = [profit(2, 3.0, o, 2.0) for o in orders]

    # 非对称：1人×3h + 1人×2h
    asym_cost = (3 + 2) * LABOR_RATE + MATERIAL_DAILY

    def asym_profit(orders, settlement):
        rev = orders * settlement + (SUBSIDY if orders / 2 > MIN_ORDERS_PER_PERSON else 0)
        return rev - asym_cost

    asym_profits_promo = [asym_profit(o, 2.5) for o in orders]
    asym_profits_regular = [asym_profit(o, 2.0) for o in orders]

    # 画利润差额（非对称 - 对称）
    diff_promo = [a - s for a, s in zip(asym_profits_promo, sym_profits_promo)]
    diff_regular = [a - s for a, s in zip(asym_profits_regular, sym_profits_regular)]

    ax.fill_between(orders, diff_promo, alpha=0.2, color="#27ae60")
    ax.plot(orders, diff_promo, color="#27ae60", linewidth=2.2, label="推广期（2.5元）")
    ax.plot(orders, diff_regular, color="#e74c3c", linewidth=2.2, label="常规期（2.0元）",
            linestyle="--")

    ax.axhline(y=0, color="gray", linewidth=0.8)
    ax.axvline(x=41, color="gray", linestyle=":", alpha=0.5)
    ax.annotate("补贴门槛 41单", xy=(41, 35), fontsize=9, color="gray", alpha=0.8)

    # 产能上限标注
    ax.axvline(x=30, color="#e74c3c", linestyle=":", alpha=0.5)
    ax.annotate("非对称产能上限\n≈30单", xy=(30, -5), fontsize=9, color="#e74c3c",
                ha="center", va="top",
                bbox=dict(boxstyle="round", facecolor="#fadbd8", alpha=0.8))

    ax.fill_between(orders, -5, 35, where=(np.array(orders) <= 30),
                    alpha=0.05, color="green")
    ax.text(15, 15, "可行区", fontsize=11, color="#27ae60", fontweight="bold", alpha=0.6)
    ax.fill_between(orders, -5, 35, where=(np.array(orders) > 30),
                    alpha=0.05, color="red")
    ax.text(50, 15, "超产能区\n需延长工时", fontsize=10, color="#e74c3c",
            fontweight="bold", alpha=0.6, ha="center")

    ax.set_xlabel("日单量（单）", fontsize=11)
    ax.set_ylabel("非对称排班日利润优势（元）", fontsize=11)
    ax.set_title("非对称排班（1人×3h + 1人×2h）vs 对称排班（2人×3h）的日利润差额",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(10, 80)
    ax.set_ylim(-10, 40)

    # 添加文字说明
    ax.text(0.98, 0.05,
            "非对称排班日省30元人力\n"
            "但产能上限约束于≈30单\n"
            "只适用于低单量点位",
            transform=ax.transAxes, fontsize=9,
            verticalalignment="bottom", horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="#fef9e7", alpha=0.9))

    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/fig6_asymmetric_vs_symmetric.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================
# 主函数
# ============================================================
def main():
    print("生成可视化图表...")

    print("  [1/6] 利润曲线...")
    fig1_profit_curves()

    print("  [2/6] 盈亏平衡热力图...")
    fig2_breakeven_heatmap()

    print("  [3/6] 点位收入成本拆解...")
    fig3_point_waterfall()

    print("  [4/6] 骑手费率敏感性...")
    fig4_rider_fee_sensitivity()

    print("  [5/6] 点位盈亏距离...")
    fig5_point_gap()

    print("  [6/6] 非对称vs对称排班...")
    fig6_asymmetric_vs_symmetric()

    print(f"\n6张图表已保存到 {OUTPUT_DIR}/")
    for f in ["fig1_profit_curves.png", "fig2_breakeven_heatmap.png",
              "fig3_point_waterfall.png", "fig4_rider_fee_sensitivity.png",
              "fig5_point_gap.png", "fig6_asymmetric_vs_symmetric.png"]:
        print(f"  ✓ {f}")


if __name__ == "__main__":
    main()
