"""
接力送 — 基于renxiao实采数据的人效评估
=========================================
数据来源: D:\CC\26-06-13\renxiao\ 6个点位 571单
分析: 实际人效、产能上限、模型修正
"""

import pandas as pd
import glob
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 数据加载
# ============================================================
files = sorted(glob.glob(os.path.join(PROJECT_ROOT, "renxiao", "*.xls")))
data = pd.concat([pd.read_excel(f, engine="xlrd") for f in files], ignore_index=True)
data["点位"] = data["站点名称"].str.replace("分段履约广州", "")
data["日期_str"] = data["日期"].astype(str).str[:10]

# ============================================================
# 1. 各点位每日概况
# ============================================================
print("=" * 80)
print("1. 各点位每日单量与配送员")
print("=" * 80)

summary_rows = []
for site in sorted(data["点位"].unique()):
    s = data[data["点位"] == site]
    for date in sorted(s["日期_str"].unique()):
        sd = s[s["日期_str"] == date]
        riders = sd["经手骑手2"].dropna().nunique()
        orders = len(sd)

        # 时段
        sd_t = sd[sd["骑手2经手时间"].notna()].copy()
        sd_t["t2"] = pd.to_datetime(sd_t["骑手2经手时间"])
        span = (sd_t["t2"].max() - sd_t["t2"].min()).total_seconds() / 3600 if len(sd_t) > 1 else 0

        # 人均
        per_rider = orders / riders if riders > 0 else orders

        # 最大单人单量
        top_rider = sd["经手骑手2"].value_counts().iloc[0] if riders > 0 else 0

        # 峰值小时
        sd["小时"] = pd.to_datetime(sd["下单时间"]).dt.hour
        peak_h = sd["小时"].value_counts().idxmax()

        summary_rows.append({
            "点位": site, "日期": date,
            "单量": orders, "配送员": riders,
            "时段跨度h": round(span, 1),
            "人均单量": round(per_rider, 1),
            "单人最高": top_rider,
            "峰值时": f"{peak_h}时",
            "天数": 1,
        })

df_summary = pd.DataFrame(summary_rows)
print(df_summary.to_string(index=False))

# ============================================================
# 2. 关键人效统计
# ============================================================
print("\n" + "=" * 80)
print("2. 人均产能 = 单量 / 时段跨度")
print("=" * 80)

rider_stats = []
for site in sorted(data["点位"].unique()):
    s = data[data["点位"] == site]
    for date in sorted(s["日期_str"].unique()):
        sd = s[s["日期_str"] == date]
        for rider in sd["经手骑手2"].dropna().unique():
            ro = sd[sd["经手骑手2"] == rider].copy()
            ro["t2"] = pd.to_datetime(ro["骑手2经手时间"])
            span_h = (ro["t2"].max() - ro["t2"].min()).total_seconds() / 3600
            if span_h == 0:
                span_h = 0.3
            rider_stats.append({
                "点位": site, "日期": date, "骑手": rider,
                "单量": len(ro), "跨度h": round(span_h, 1),
                "单/h": round(len(ro) / span_h, 1),
            })

df_rs = pd.DataFrame(rider_stats)

# 按单量分段
print(f"\n全体 ({len(df_rs)}人次): 中位产能 {df_rs['单/h'].median():.1f}单/h, 中位跨度 {df_rs['跨度h'].median():.1f}h")
for lo, hi, label in [(1, 10, "1-10单"), (11, 20, "11-20单"), (21, 35, "21-35单"), (36, 80, "36-80单"), (80, 200, "80+单")]:
    sub = df_rs[(df_rs["单量"] >= lo) & (df_rs["单量"] <= hi)]
    if len(sub) > 0:
        print(f"  {label}: {len(sub)}人次, 中位产能 {sub['单/h'].median():.1f}单/h, "
              f"均值产能 {sub['单/h'].mean():.1f}单/h, 中位跨度 {sub['跨度h'].median():.1f}h")

# ============================================================
# 3. 有效产能（排除低单量新手点位）
# ============================================================
print("\n" + "=" * 80)
print("3. 成熟点位人效（排除单量<20的点位-天）")
print("=" * 80)

mature = df_rs[df_rs["单量"] >= 20]
if len(mature) > 0:
    print(f"  {len(mature)}人次, 中位产能 {mature['单/h'].median():.1f}单/h, "
          f"均值 {mature['单/h'].mean():.1f}单/h")
    for _, r in mature.iterrows():
        print(f"    {r['点位']:12s} {r['日期']} {r['骑手']:4s}: {r['单量']:3.0f}单/{r['跨度h']:.1f}h = {r['单/h']:.1f}单/h")

# ============================================================
# 4. 交接效率
# ============================================================
print("\n" + "=" * 80)
print("4. 交接耗时（骑手1到骑手2）")
print("=" * 80)

dv = data[(data["骑手1经手时间"].notna()) & (data["骑手2经手时间"].notna())].copy()
dv["t1"] = pd.to_datetime(dv["骑手1经手时间"])
dv["t2"] = pd.to_datetime(dv["骑手2经手时间"])
dv["交接min"] = (dv["t2"] - dv["t1"]).dt.total_seconds() / 60

print(f"  均值 {dv['交接min'].mean():.1f}分, 中位 {dv['交接min'].median():.1f}分, "
      f"P75={dv['交接min'].quantile(.75):.1f}分, P90={dv['交接min'].quantile(.9):.1f}分")

# 每个点位交接效率
print("\n  各点位:")
for site in sorted(dv["点位"].unique()):
    sd = dv[dv["点位"] == site]
    print(f"    {site:12s}: {len(sd):3d}单, 中位交接 {sd['交接min'].median():.1f}分, "
          f"P90={sd['交接min'].quantile(.9):.1f}分")

# ============================================================
# 5. UE模型参数修正建议
# ============================================================
print("\n" + "=" * 80)
print("5. UE模型参数修正建议")
print("=" * 80)

print(f"""
  原假设 vs 实测:

  | 参数 | 原模型假设 | 实测值 | 建议 |
  |------|----------|--------|------|
  | 人均产能 | 10单/h | {df_rs['单/h'].median():.1f}单/h(全体) / {mature['单/h'].median():.1f}单/h(≥20单) | 8-12单/h保守 |
  | 产能峰值 | 10单/h | 15+单/h(高单量骑手) | 12-15单/h高峰 |
  | 有效人数 | N-1配送员 | 实测2-3人即够 | 无需大量加人 |
  | 交接耗时 | 未建模 | 中位{df_rs['跨度h'].median():.1f}分 | 可忽略 |

  关键发现:
  1. 和业广场6/12: 1人2.3h处理36单 → 15.6单/h
  2. 万菱广场6/12: 1人2.7h处理40单 → 14.8单/h
  3. 绿地星玥6/12: 1人9.2h处理151单 → 16.4单/h (马拉松式)
  4. 新点位(1-2天)人效很低(5-6单/h)，随天数增长快速提升
  5. 实测人效支持: 1人×3h可处理36-45单（高峰期15单/h）

  对UE模型的影响:
  - 产能上限应上调至12-15单/人/h
  - 单量40-80时只需2人(1楼+1楼)，非模型估算的3-4人
  - 利润应重新估算（人力成本更低）
""")

# ============================================================
# 生成修正版UE
# ============================================================
print("\n" + "=" * 80)
print("6. 修正UE（基于实测人效12单/h）")
print("=" * 80)

RATE = 30
DAYS = 30
MIN_OPP = 20
CAP = 12  # 实测人均产能（保守值）

def best_cfg(orders, settlement, has_sub):
    best_p = -float("inf")
    best = None
    # 搜索: 1个3h + N个2-3h
    for n in range(0, 21):
        for h in [2.0, 2.5, 3.0]:
            # 产能: n个配送员 + 1个楼下(闲时协助)
            if n == 0:
                cap = 1.0 * 3 * CAP  # 1人全包
            else:
                # 重叠时段产能: n个纯配送 + 0.5个楼下
                cap = (n + 0.5) * h * CAP + 0.5 * (3 - h) * CAP

            if cap < orders:
                continue

            tp = n + 1
            th = 3 + n * h
            cost = th * RATE + 100 / DAYS
            sub = (tp - 1) * 80 if (has_sub and orders / tp >= MIN_OPP) else 0
            rev = orders * settlement + sub
            p = rev - cost
            if p > best_p:
                best_p = p
                best = (n, h, tp, th, cost, sub, p, orders / tp >= MIN_OPP and has_sub,
                        round(orders / tp, 1), cap)
    return best

for orders in [20, 30, 40, 50, 60, 80, 100, 120, 150, 200, 300, 500]:
    b = best_cfg(orders, 2.5, True)
    if b:
        n, h, tp, th, cost, sub, dp, ok, opp, cap = b
        h_str = f"{h:.0f}h" if h == int(h) else f"{h:.1f}h"
        cfg = f"3h×1人 + {h_str}×{n}人" if n > 0 else "3h×1人"
        print(f"  {orders:3d}单 | {cfg:20s} | {tp}人 人均{opp:.0f} | "
              f"日补贴¥{sub:.0f} | 月利 {dp*30:+9,.0f} | 产能{cap:.0f}单")

print()
df_summary.to_csv(f"{OUTPUT_DIR}/renxiao_summary.csv", index=False, encoding="utf-8-sig")
df_rs.to_csv(f"{OUTPUT_DIR}/renxiao_rider_stats.csv", index=False, encoding="utf-8-sig")
print("输出: renxiao_summary.csv, renxiao_rider_stats.csv")
