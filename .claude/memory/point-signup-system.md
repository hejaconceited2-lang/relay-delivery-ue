---
name: point-signup-system
description: 接力送点位认领系统完整状态 — 三批次66个点位，Firebase实时同步，2026-07-06终版
metadata:
  type: project
---

## 系统概述

接力送点位认领与评估系统，在 Firebase Realtime Database 上运行，GitHub Pages 托管静态页面。

- **URL**: https://hejaconceited2-lang.github.io/relay-delivery-ue/output/point_signup.html
- **Firebase DB**: relay-delivery-signup-default-rtdb.firebaseio.com
- **Repo**: hejaconceited2-lang/relay-delivery-ue (master)

## 点位结构

| 批次 | 编号 | 数量 | 状态 |
|------|------|------|------|
| BATCH1 | p01-p08 | 8 | 已开点运营中，全部认领 |
| BATCH2 | p09-p33 | 25 | 待踩点评估，部分认领 |
| BATCH3 | p34-p67 | 34 | 新增候选，仅p65认领 |
| **合计** | | **66** | |

三批次均按区域排序（天河→越秀→海珠→荔湾→白云→黄埔→番禺→花都→增城），区内午高峰降序。

## BATCH3 预设认领

- p65 广日物流 → 陈家瑞（initPoints 硬编码，首次加载自动创建）
- 其余 33 个默认为无人认领

## Firebase 安全规则（终版）

```json
{
  "rules": {
    ".read": true,
    "points": {
      "$pointId": {
        ".write": true,
        "claimed": {
          ".write": "!data.exists() || data.val() == false"
        },
        "name": {
          ".write": "data.parent().child('claimed').val() == true"
        }
      }
    }
  }
}
```

**约束**：claimed 只能 false→true（不可撤回），name 只能已认领后修改，scouting 和 timestamp 无额外限制。

## 关键设计决策

1. **认领用 Firebase transaction**：`runTransaction` 保证原子性，防止两人同时认领同一点位
2. **scouting 写入加重试**：网络抖动时自动重试 2 次
3. **实时同步**：`onValue` 监听整个 points 节点，任何修改即时广播到所有在线用户
4. **p65 跳过通用初始化**：`forEach` 循环中 `if (id === "p65") return`，单独处理避免路径冲突
5. **脏数据清理**：页面加载时扫描 p66-p75，自动重置被重编号污染的点位

## ⚠️ 红线规则

**绝对不要修改已发布的 p 编号！** BATCH3 曾因多次重编号导致 Firebase 数据漂移——同一个 p 号在不同版本对应不同点位名，造成陈家瑞名字挂在多个点位上。如需新增点位，只能在当前最大编号后追加；如需调整排序，只改变数组顺序不改 ID。

## 剔除记录

已剔除的点位及原因：
- 番禺万达：其他项目在做
- 新中国大厦：竞对占据
- 新亚洲国际数码电子城：竞对占据
- 万菱广场、和业广场、金鹰大厦、绿地越秀海玥、汇德国际大厦、万科欧泊：接力送日订单项目已覆盖
- 孙逸仙纪念医院（南北院）：竞对占据
- 广百百货(北京路店)：其他项目在做

## 联系人分配（第三批踩点，不走线上）

见 [[batch3-scout-assignment]]
