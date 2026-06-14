"""
生成接力送项目进度可视化图表，可直接分享。
输出: output/project_progress.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties
import numpy as np

# ── 字体 ──────────────────────────────────────────────
# 使用系统注册字体名，兼容性更好
font_cn = FontProperties(family="Microsoft YaHei", size=11)
font_cn_bold = FontProperties(family="Microsoft YaHei", weight="bold", size=11)
font_title = FontProperties(family="Microsoft YaHei", weight="bold", size=18)
font_num = FontProperties(family="Microsoft YaHei", weight="bold", size=28)

# ── 数据 ──────────────────────────────────────────────
# 点位分类
old_points = [
    ("万达广场", "番禺区"),
    ("汇德国际中心", "越秀区"),
    ("北京路广百", "越秀区"),
    ("金鹰大厦", "越秀区"),
]

relay_early = [
    ("和业广场", "荔湾区", "6月早期"),
]

relay_week2 = [
    ("华林国际C馆", "荔湾区"),
    ("万科欧泊", "番禺区"),
    ("绿地星玥", "海珠区"),
    ("万菱广场", "越秀区"),
    ("金鹰大厦", "越秀区"),
]

week3_must = [("珠江国际纺织城", "--")]  # 周一必开
week3_candidates = [
    ("中大附属第六医院", "天河区", "未踩点"),
    ("中大附属第三医院", "天河区", "未踩点"),
    ("中大附三岭南医院", "黄埔区", "未踩点"),
    ("云升科学园", "黄埔区", "未踩点"),
    ("丰兴广场", "天河区", "未踩点"),
    ("万达广场萝岗点", "黄埔区", "未踩点"),
    ("荔胜广场", "荔湾区", "未踩点"),
]

# ── 画布 ──────────────────────────────────────────────
fig = plt.figure(figsize=(16, 11), facecolor="#FAFAFA")
gs = fig.add_gridspec(3, 2, height_ratios=[1, 2.5, 1.8],
                      width_ratios=[2.8, 1], hspace=0.35, wspace=0.28)

# ── 配色 ──────────────────────────────────────────────
C_DONE    = "#2E7D32"  # 深绿 已完成
C_ACTIVE  = "#1565C0"  # 深蓝 进行中
C_OLD     = "#6D4C41"  # 棕   旧点位
C_CAND    = "#78909C"  # 灰蓝 候选
C_UNSCOUT = "#C62828"
C_BG_DONE = "#E8F5E9"
C_BG_ACT  = "#E3F2FD"
C_BG_OLD  = "#EFEBE9"
C_BG_CAND = "#ECEFF1"
C_BG_UNSCOUT = "#FFF0F0"

# ═══════════════════════════════════════════════════════
# 1. 顶部：标题 + 核心数字
# ═══════════════════════════════════════════════════════
ax_top = fig.add_subplot(gs[0, :])
ax_top.set_xlim(0, 10)
ax_top.set_ylim(0, 3)
ax_top.axis("off")

ax_top.text(0.1, 2.2, "接力送 · 6月点位开设进度",
            fontproperties=font_title, fontsize=20, color="#1a1a1a", va="center")
ax_top.text(0.1, 1.6, "美团末端配送 — 办公楼宇接力上楼",
            fontproperties=font_cn, fontsize=11, color="#666666", va="center")

# 三个核心数字
metrics = [
    ("12", "6月目标", "#37474F"),
    ("6", "已开设", C_DONE),
    ("6", "待开设", C_ACTIVE),
]
for i, (num, label, color) in enumerate(metrics):
    x = 7.2 + i * 0.95
    ax_top.text(x, 2.2, num, fontproperties=font_num, fontsize=32,
                color=color, ha="center", va="center")
    ax_top.text(x, 1.5, label, fontproperties=font_cn, fontsize=9,
                color="#888888", ha="center", va="center")

# 分割线
ax_top.axhline(y=0.5, xmin=0.02, xmax=0.98, color="#E0E0E0", linewidth=0.8)

# ═══════════════════════════════════════════════════════
# 2. 左下：点位时间线
# ═══════════════════════════════════════════════════════
ax = fig.add_subplot(gs[1, 0])
ax.set_xlim(-0.5, 6.5)
ax.set_ylim(-1, 15.5)
ax.axis("off")

y = 15  # 起始高度

def draw_section(title, subtitle, color, bg_color, count_text):
    """画出一个小节标题"""
    global y
    y -= 1.2
    ax.text(-0.3, y, title, fontproperties=font_cn_bold, fontsize=12,
            color=color, va="center")
    ax.text(1.5, y, subtitle, fontproperties=font_cn, fontsize=9,
            color="#999999", va="center")
    ax.text(6.3, y, count_text, fontproperties=font_cn_bold, fontsize=10,
            color=color, va="center", ha="right")
    y -= 0.7

def draw_row(label, district, color, bg_color, tag=None):
    """画出一行点位"""
    global y
    # 圆点
    ax.plot(0.2, y, "o", color=color, markersize=8, zorder=3)
    # 横线
    ax.plot([0.2, 5.8], [y, y], color="#E0E0E0", linewidth=0.6, zorder=1)
    # 名称
    ax.text(0.65, y, label, fontproperties=font_cn, fontsize=10.5,
            color="#333333", va="center")
    # 区域
    ax.text(3.6, y, district, fontproperties=font_cn, fontsize=8.5,
            color="#999999", va="center")
    # tag
    if tag:
        ax.text(5.1, y, tag, fontproperties=font_cn, fontsize=7.5,
                color=color, va="center",
                bbox=dict(boxstyle="round,pad=0.25", facecolor=bg_color,
                          edgecolor="none", alpha=0.8))
    y -= 0.52

# ── 旧点位 ──
draw_section("旧点位（小二帮送）", "已运营点位，其中金鹰大厦同时使用接力送", C_OLD, C_BG_OLD, f"{len(old_points)}个")
for name, dist in old_points:
    tag = "双模式" if "金鹰" in name else None
    draw_row(name, dist, C_OLD, C_BG_OLD, tag)

y -= 0.4

# ── 接力送：已开设 ──
draw_section("接力送 · 已开设", "6月起陆续上线", C_DONE, C_BG_DONE, "6个")

# 早期
ax.text(0.65, y, "早期", fontproperties=font_cn, fontsize=8.5, color="#999999", va="center")
y -= 0.45
for name, dist, _ in relay_early:
    draw_row(name, dist, C_DONE, C_BG_DONE)

# 第2周
ax.text(0.65, y, "第2周", fontproperties=font_cn, fontsize=8.5, color="#999999", va="center")
y -= 0.45
for name, dist in relay_week2:
    tag = "双模式" if "金鹰" in name else None
    draw_row(name, dist, C_DONE, C_BG_DONE, tag)

y -= 0.4

# ── 接力送：待开设 ──
draw_section("接力送 · 待开设", "第3周周中截止", C_ACTIVE, C_BG_ACT, f"{1 + len(week3_candidates)}个候选 -> 开4个")

ax.text(0.65, y, "周一必开", fontproperties=font_cn, fontsize=8.5, color="#E65100", va="center")
y -= 0.45
draw_row(week3_must[0][0], "已踩点", "#E65100", "#FFF3E0", "必开")

ax.text(0.65, y, "候选（7选3）", fontproperties=font_cn, fontsize=8.5, color="#999999", va="center")
y -= 0.45
for name, dist, tag in week3_candidates:
    draw_row(name, dist, C_CAND, C_BG_CAND, tag)

# ═══════════════════════════════════════════════════════
# 3. 右下：进度环
# ═══════════════════════════════════════════════════════
ax_ring = fig.add_subplot(gs[1, 1])
ax_ring.set_xlim(-1.5, 1.5)
ax_ring.set_ylim(-1.5, 1.5)
ax_ring.axis("off")

# 环形进度
from matplotlib.patches import Wedge
total = 12
done = 6
theta = 360 * done / total

# 背景环
wedge_bg = Wedge((0, 0), 1.1, 0, 360, width=0.3, color="#E0E0E0",
                 transform=ax_ring.transData)
ax_ring.add_patch(wedge_bg)
# 完成环
wedge_done = Wedge((0, 0), 1.1, 90, 90 + theta, width=0.3, color=C_DONE,
                   transform=ax_ring.transData)
ax_ring.add_patch(wedge_done)
# 中心文字
ax_ring.text(0, 0.15, f"{done}/{total}", fontproperties=font_num, fontsize=36,
             color=C_DONE, ha="center", va="center")
ax_ring.text(0, -0.35, "已开设点位", fontproperties=font_cn, fontsize=10,
             color="#888888", ha="center", va="center")

# 下方小字
ax_ring.text(0, -0.9, "6月目标12个", fontproperties=font_cn, fontsize=9,
             color="#AAAAAA", ha="center", va="center")

# ═══════════════════════════════════════════════════════
# 4. 底部：周进度条
# ═══════════════════════════════════════════════════════
ax_bar = fig.add_subplot(gs[2, :])
ax_bar.set_xlim(0, 6)
ax_bar.set_ylim(0, 1.5)
ax_bar.axis("off")

weeks_data = [
    ("第1周", "1", "1", C_DONE),
    ("第2周", "5", "5", C_DONE),
    ("第3周", "4", "进行中", C_ACTIVE),
    ("第4周", "2", "待定", C_CAND),
]

bar_y = 0.9
x_start = 0.5
width_per = 1.15
gap = 0.15

for i, (label, target, status, color) in enumerate(weeks_data):
    x = x_start + i * (width_per + gap)
    # 方块背景
    rect = mpatches.FancyBboxPatch((x, bar_y - 0.32), width_per, 0.58,
                                    boxstyle="round,pad=0.08",
                                    facecolor="#F5F5F5" if color == C_CAND else
                                              (C_BG_DONE if color == C_DONE else C_BG_ACT),
                                    edgecolor="none", zorder=1)
    ax_bar.add_patch(rect)
    # 状态色条
    if color != C_CAND:
        ax_bar.fill_between([x + 0.04, x + width_per - 0.04],
                           [bar_y - 0.32 + 0.05, bar_y - 0.32 + 0.05],
                           [bar_y + 0.26 - 0.05, bar_y + 0.26 - 0.05],
                           color=color, alpha=0.25, zorder=2)
    # 周标签
    ax_bar.text(x + width_per / 2, bar_y + 0.1, label,
                fontproperties=font_cn_bold, fontsize=11, color="#333333",
                ha="center", va="center")
    # 进度
    ax_bar.text(x + width_per / 2, bar_y - 0.15, status,
                fontproperties=font_cn_bold, fontsize=10, color=color,
                ha="center", va="center")
    # 小字
    ax_bar.text(x + width_per / 2, bar_y - 0.38, f"目标 {target}个",
                fontproperties=font_cn, fontsize=7.5, color="#AAAAAA",
                ha="center", va="center")

# 底部备注
ax_bar.text(3.0, -0.25, "数据截至 2026.06.14 | 接力送 UE 项目",
            fontproperties=font_cn, fontsize=8, color="#CCCCCC", ha="center")

# ── 保存 ──────────────────────────────────────────────
fig.savefig("output/project_progress.png", dpi=180, bbox_inches="tight",
            facecolor="#FAFAFA", edgecolor="none")
plt.close()
print("Done: output/project_progress.png")
