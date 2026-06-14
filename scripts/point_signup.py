"""
接力送 · 点位认领 + 踩点确认页面
===============================
公开页面，认领点位 + 踩点四项确认同步协作。
Firebase Realtime Database 后端。
"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_html():
    html = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接力送 · 点位认领</title>
<style>
  :root{--g:#27ae60;--gb:#d5f5e3;--b:#2980b9;--bb:#d4e6f1;--r:#e74c3c;--rb:#fadbd8;--y:#f39c12;--yb:#fef9e7;--t:#2c3e50;--l:#7f8c8d;--br:#e0e0e0;--bg:#fafafa}
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--t);background:#fff;max-width:1060px;margin:0 auto;padding:28px 32px;line-height:1.65}
  h1{font-size:1.6rem;font-weight:800;margin-bottom:2px}
  h1 .sub{font-size:.78rem;color:var(--l);font-weight:400;margin-left:8px}
  h2{font-size:1.1rem;font-weight:700;margin:28px 0 10px}
  hr{border:none;border-top:2px solid #eee;margin:14px 0}

  .status-bar{display:flex;gap:20px;flex-wrap:wrap;margin:12px 0;font-size:.84rem}
  .stat{display:flex;align-items:center;gap:6px}
  .dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
  .dot.avail{background:var(--g)} .dot.taken{background:var(--r)} .dot.warn{background:var(--y)} .dot.gray{background:var(--l)}

  table{width:100%;border-collapse:collapse;font-size:.84rem;margin:10px 0}
  thead th{background:#2c3e50;color:#fff;padding:9px 8px;font-weight:600;text-align:center;white-space:nowrap}
  thead th:first-child{border-radius:8px 0 0 0} thead th:last-child{border-radius:0 8px 0 0}
  tbody td{padding:9px 8px;text-align:center;border-bottom:1px solid var(--br);transition:background .15s}
  tbody tr.main-row{cursor:pointer}
  tbody tr.main-row:hover{background:var(--bb)!important}
  tbody tr.taken-row{background:#fafafa;cursor:pointer}
  tbody tr.taken-row:hover{background:#f0f0f0!important}
  tbody tr.expanded{background:var(--bg)}
  tbody tr.expanded td{padding:0}

  .badge{display:inline-block;border-radius:12px;padding:3px 10px;font-size:.74rem;font-weight:700}
  .badge.go{background:var(--gb);color:#1e8449}
  .badge.tk{background:var(--rb);color:#922b21}
  .badge.ok{background:var(--gb);color:#1e8449}
  .badge.pr{background:var(--yb);color:#b7950b}

  .scout-count{display:inline-block;border-radius:12px;padding:3px 10px;font-size:.74rem;font-weight:700;min-width:36px}
  .scout-count.done{background:var(--gb);color:#1e8449}
  .scout-count.half{background:var(--yb);color:#b7950b}
  .scout-count.none{background:#f0f0f0;color:var(--l)}

  .detail-panel{padding:14px 20px;display:flex;flex-wrap:wrap;gap:14px;align-items:center}
  .detail-panel .chk-group{display:flex;gap:18px;flex-wrap:wrap;flex:1}
  .detail-panel .chk-item{display:flex;align-items:center;gap:6px;font-size:.8rem;cursor:pointer;user-select:none;padding:4px 0}
  .detail-panel .chk-box{width:20px;height:20px;border-radius:4px;border:2px solid var(--br);flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all .15s;font-size:.7rem}
  .detail-panel .chk-box.on{background:var(--g);border-color:var(--g);color:#fff}
  .detail-panel .chk-box.off{background:#fff}
  .detail-panel .chk-item:hover .chk-box.off{border-color:var(--g)}
  .detail-panel .scout-note{font-size:.76rem;color:var(--l);min-width:180px;text-align:right}
  .detail-panel .scout-note strong{color:var(--g)}
  .detail-panel .scout-note b{color:var(--r)}

  .arrow-expand{display:inline-block;transition:transform .2s;font-size:.7rem;margin-right:2px}
  .arrow-expand.open{transform:rotate(90deg)}

  .loading{text-align:center;padding:40px;color:var(--l);font-size:.9rem}

  .legend{display:flex;gap:14px;flex-wrap:wrap;font-size:.76rem;color:var(--l);margin:8px 0}
  .legend span{display:flex;align-items:center;gap:4px}

  .tips-toggle{display:inline-block;color:var(--b);cursor:pointer;font-size:.88rem;font-weight:700;margin:8px 0;user-select:none}
  .tips-toggle:hover{text-decoration:underline}
  .tips{display:none;background:var(--bb);border-radius:10px;padding:18px 22px;margin:10px 0;border:1px solid var(--b)}
  .tips.show{display:block}
  .tips h3{font-size:.92rem;margin-bottom:8px;color:var(--b)}
  .tips .tip-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px 20px;font-size:.8rem}
  @media(max-width:600px){.tips .tip-grid{grid-template-columns:1fr}}
  .tips .tip-item{display:flex;gap:6px;align-items:flex-start}
  .tips .tip-item .ico{flex-shrink:0}
  .tips .warn{font-size:.76rem;color:var(--r);margin-top:8px;background:#fff;border-radius:6px;padding:8px 12px}

  .modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.45);z-index:100;align-items:center;justify-content:center}
  .modal-overlay.show{display:flex}
  .modal{background:#fff;border-radius:12px;padding:24px 28px;width:90%;max-width:400px;text-align:center;box-shadow:0 8px 30px rgba(0,0,0,.15)}
  .modal h3{margin-bottom:12px}
  .modal input{width:100%;padding:10px 14px;border:2px solid var(--b);border-radius:8px;font-size:1rem;text-align:center;margin:12px 0;outline:none}
  .modal input:focus{border-color:var(--g)}
  .modal .btn-row{display:flex;gap:10px;justify-content:center;margin-top:14px}
  .modal button{padding:10px 28px;border:none;border-radius:8px;font-size:.9rem;font-weight:700;cursor:pointer}
  .modal .btn-go{background:var(--g);color:#fff} .modal .btn-go:hover{filter:brightness(.9)}
  .modal .btn-cancel{background:#eee;color:var(--t)} .modal .btn-cancel:hover{background:#ddd}
  .modal .err{color:var(--r);font-size:.8rem;margin-top:6px;display:none}

  .footer{margin-top:32px;padding-top:12px;border-top:2px solid #eee;color:var(--l);font-size:.72rem}
</style>
</head>
<body>

<h1>📍 接力送 · 点位认领<span class="sub">点击行展开踩点详情 · 点击「可认领」行认领点位</span></h1>
<hr>

<div class="status-bar" id="statusBar">
  <div class="stat"><div class="dot gray"></div> 总计 <strong id="cntTotal">—</strong></div>
  <div class="stat"><div class="dot avail"></div> 可选 <strong id="cntAvail" style="color:var(--g)">—</strong></div>
  <div class="stat"><div class="dot taken"></div> 已占 <strong id="cntTaken" style="color:var(--r)">—</strong></div>
  <div class="stat"><div class="dot warn"></div> 踩点进行中 <strong id="cntScouting" style="color:var(--y)">—</strong></div>
  <div class="stat"><div class="dot avail"></div> 踩点完成 <strong id="cntScoutDone" style="color:var(--g)">—</strong></div>
</div>

<div class="legend">
  <span><span style="background:var(--gb);width:14px;height:14px;border-radius:3px"></span> 点击行展开踩点详情</span>
  <span>⬜ 未踩 = 该点位还没有人实地看过</span>
</div>

<div class="loading" id="loading">加载中…</div>

<table id="table" style="display:none">
<thead><tr>
  <th style="width:30px"></th><th>序号</th><th>点位名称</th><th>区域</th><th>踩点进度</th><th>认领状态</th><th>认领人</th>
</tr></thead>
<tbody id="tbody"></tbody>
</table>

<!-- ═══════ 流程提示 ═══════ -->
<div style="margin-top:20px">
  <div class="tips-toggle" onclick="document.getElementById('tips').classList.toggle('show');this.textContent=document.getElementById('tips').classList.contains('show')?'▼ 隐藏开点流程':'▶ 查看开点流程'">▶ 查看开点流程</div>
  <div class="tips" id="tips">
    <h3>🗓 从认领到开点完整流程</h3>
    <div class="tip-grid">
      <div class="tip-item"><span class="ico">📦</span><span><strong>① 踩点确认四项</strong><br><small>外卖柜 → 骑手路线（高峰期看）→ 物业严格度 → 摆放位置。全部打勾才算踩点完成。</small></span></div>
      <div class="tip-item"><span class="ico">🪪</span><span><strong>② 提交人员信息</strong><br><small>开点前一天提供：身份证 + 电话 + 名字，缺一不可</small></span></div>
      <div class="tip-item"><span class="ico">🔥</span><span><strong>③ 美团火炬认证</strong><br><small>开点前一天 24:00 前完成认证，否则账号无法使用</small></span></div>
      <div class="tip-item"><span class="ico">🪧</span><span><strong>④ 物料准备</strong><br><small>KT板（物业严则用小号）+ 放餐篮子 + 马甲</small></span></div>
    </div>
    <div class="warn">⚠ 物业严格的地方尽量小号KT板。踩点时务必确认物业态度，决定正常摆还是隐蔽摆。</div>
  </div>
</div>

<div class="footer"><p>数据实时同步 · 踩点可多人协作 · 已占点位不可覆盖 · 有问题联系管理员</p></div>

<!-- ═══════ 认领弹窗 ═══════ -->
<div class="modal-overlay" id="modal">
  <div class="modal">
    <h3 id="modalTitle">认领点位</h3>
    <p style="font-size:.88rem;color:var(--l)" id="modalPoint">—</p>
    <input type="text" id="modalInput" placeholder="请输入你的姓名" maxlength="20" autocomplete="off">
    <div class="err" id="modalErr">点位刚刚被别人占了，请选择其他点位。</div>
    <div class="btn-row">
      <button class="btn-cancel" onclick="closeModal()">取消</button>
      <button class="btn-go" id="modalBtn" onclick="claimPoint()">确认认领</button>
    </div>
  </div>
</div>

<!-- ═══════ Firebase SDK ═══════ -->
<script type="module">
  import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-app.js";
  import { getDatabase, ref, get, set, update, onValue } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-database.js";

  const firebaseConfig = {
    apiKey: "AIzaSyA0BVosjdj5SQQIRW_n4BPPUy21dZJW8EI",
    authDomain: "relay-delivery-signup.firebaseapp.com",
    databaseURL: "https://relay-delivery-signup-default-rtdb.firebaseio.com",
    projectId: "relay-delivery-signup",
    storageBucket: "relay-delivery-signup.firebasestorage.app",
    messagingSenderId: "769448303567",
    appId: "1:769448303567:web:707701e31bc1b3cd2010ba",
    measurementId: "G-7DECQPG4NT"
  };

  const app = initializeApp(firebaseConfig);
  const db = getDatabase(app);
  const pointsRef = ref(db, "points");

  const POINTS = [
    ["p01", "珠江国际纺织城",     "海珠区"],
    ["p02", "中大附属第六医院",    "天河区"],
    ["p03", "中大附属第三医院",    "天河区"],
    ["p04", "中大附三岭南医院",    "黄埔区"],
    ["p05", "云升科学园",         "黄埔区"],
    ["p06", "丰兴广场",           "天河区"],
    ["p07", "万达广场萝岗点",     "黄埔区"],
    ["p08", "荔胜广场",           "荔湾区"],
  ];

  const SCOUT_ITEMS = [
    { key: "locker",      label: "外卖柜",   icon: "📦" },
    { key: "rider_route", label: "骑手路线", icon: "🏍️" },
    { key: "property",    label: "物业态度", icon: "🏢" },
    { key: "position",    label: "摆放位置", icon: "📍" },
  ];

  let currentData = {};
  let expandedId = null;
  let selectedPointId = null;

  function scoutCount(entry) {
    if (!entry?.scouting) return 0;
    let c = 0;
    SCOUT_ITEMS.forEach(si => { if (entry.scouting[si.key]) c++; });
    return c;
  }

  function scoutDone(entry) { return scoutCount(entry) === 4; }

  async function initPoints() {
    const snap = await get(pointsRef);
    const defaultScout = { locker: false, rider_route: false, property: false, position: false };
    if (!snap.exists()) {
      // 首次：创建所有点位，p01 预标记为赵金荣已认领
      const init = {};
      POINTS.forEach(([id]) => {
        init[id] = { claimed: false, name: "", timestamp: 0, scouting: { ...defaultScout } };
      });
      init.p01 = { claimed: true, name: "赵金荣", timestamp: Date.now(), scouting: { ...defaultScout } };
      await set(pointsRef, init);
    } else {
      // 已有数据：补足缺失字段 + 确保 p01 认领状态
      const data = snap.val();
      const updates = {};
      POINTS.forEach(([id]) => {
        if (!data[id]) {
          updates[id] = { claimed: false, name: "", timestamp: 0, scouting: { ...defaultScout } };
        } else {
          if (!data[id].scouting) updates[id + "/scouting"] = { ...defaultScout };
        }
      });
      if (data.p01 && !data.p01.claimed) {
        updates["p01/claimed"] = true;
        updates["p01/name"] = "赵金荣";
        updates["p01/timestamp"] = Date.now();
      }
      if (Object.keys(updates).length > 0) await update(ref(db, "points"), updates);
    }
  }

  function renderTable(snapshot) {
    const data = snapshot?.val() || {};
    currentData = data;

    let html = "";
    let avail = 0, taken = 0, scouting = 0, scoutDoneAll = 0;
    const wasExpanded = expandedId;

    POINTS.forEach(([id, name, district], i) => {
      const entry = data[id] || {};
      const claimed = entry.claimed === true;
      const claimer = entry.name || "";
      const sc = scoutCount(entry);
      const sd = scoutDone(entry);

      if (claimed) taken++; else avail++;
      if (sc > 0 && sc < 4) scouting++;
      if (sd) scoutDoneAll++;

      const scCls = sd ? "done" : (sc > 0 ? "half" : "none");
      const scText = sd ? "✅ 4/4" : `${sc}/4`;
      const isExpanded = (expandedId === id);

      // 主行
      html += `<tr class="${claimed ? 'taken-row' : 'main-row'}" onclick="window.toggleExpand('${id}')" id="row-${id}">
        <td><span class="arrow-expand${isExpanded ? ' open' : ''}" id="arrow-${id}">▶</span></td>
        <td>${i + 1}</td>
        <td style="text-align:left;font-weight:700">${name}</td>
        <td>${district}</td>
        <td><span class="scout-count ${scCls}">${scText}</span></td>
        <td>${claimed ? '<span class="badge tk">已认领</span>' : '<span class="badge go">可认领</span>'}</td>
        <td style="${claimed ? 'font-weight:700' : 'color:var(--l)'}">${claimed ? claimer : (claimed ? '' : '—')}</td>
      </tr>`;

      // 展开详情行
      if (isExpanded) {
        html += `<tr class="expanded" id="detail-${id}"><td colspan="7"><div class="detail-panel">`;
        html += `<div class="chk-group">`;
        SCOUT_ITEMS.forEach(si => {
          const on = entry?.scouting?.[si.key] === true;
          html += `<div class="chk-item" onclick="event.stopPropagation();window.toggleScout('${id}','${si.key}')">
            <span class="chk-box ${on ? 'on' : 'off'}">${on ? '✓' : ''}</span>
            <span>${si.icon} ${si.label}</span>
          </div>`;
        });
        html += `</div>`;
        html += `<div class="scout-note">${sd ? '<strong>✅ 踩点完成 — 可以开点</strong>' : (sc > 0 ? `还差 <b>${4-sc}</b> 项` : '⬜ 尚未踩点，点击上方勾选')}</div>`;
        html += `</div></td></tr>`;
      }
    });

    document.getElementById("tbody").innerHTML = html;
    document.getElementById("cntTotal").textContent = POINTS.length;
    document.getElementById("cntAvail").textContent = avail;
    document.getElementById("cntTaken").textContent = taken;
    document.getElementById("cntScouting").textContent = scouting;
    document.getElementById("cntScoutDone").textContent = scoutDoneAll;
    document.getElementById("loading").style.display = "none";
    document.getElementById("table").style.display = "";
  }

  // ═══════ 展开/收起 ═══════
  window.toggleExpand = function(id) {
    if (expandedId === id) {
      expandedId = null;
    } else {
      expandedId = id;
    }
    renderTable({ val: () => currentData });
  };

  // ═══════ 踩点项切换 ═══════
  window.toggleScout = async function(id, key) {
    const entry = currentData[id];
    if (!entry) return;
    const current = entry?.scouting?.[key] === true;
    try {
      await set(ref(db, `points/${id}/scouting/${key}`), !current);
    } catch (e) {
      alert("更新失败: " + e.message);
    }
  };

  // ═══════ 认领 ═══════
  window.openClaimModal = function(id, name) {
    if (currentData[id]?.claimed === true) {
      alert(`「${name}」已被认领。`);
      return;
    }
    selectedPointId = id;
    document.getElementById("modalPoint").textContent = name;
    document.getElementById("modalTitle").textContent = "📝 认领 " + name;
    document.getElementById("modalInput").value = "";
    document.getElementById("modalErr").style.display = "none";
    document.getElementById("modal").classList.add("show");
    document.getElementById("modalInput").focus();
  };

  window.closeModal = function() {
    document.getElementById("modal").classList.remove("show");
    selectedPointId = null;
  };

  window.claimPoint = async function() {
    const name = document.getElementById("modalInput").value.trim();
    if (!name) { document.getElementById("modalInput").focus(); return; }
    document.getElementById("modalBtn").disabled = true;
    document.getElementById("modalBtn").textContent = "提交中…";

    const snap = await get(ref(db, "points/" + selectedPointId));
    if (snap.exists() && snap.val().claimed === true) {
      document.getElementById("modalErr").style.display = "block";
      document.getElementById("modalBtn").disabled = false;
      document.getElementById("modalBtn").textContent = "确认认领";
      return;
    }

    try {
      const existing = snap.val() || {};
      await set(ref(db, "points/" + selectedPointId), {
        claimed: true, name: name, timestamp: Date.now(),
        scouting: existing.scouting || { locker: false, rider_route: false, property: false, position: false }
      });
      closeModal();
    } catch (e) {
      alert("提交失败: " + e.message);
      document.getElementById("modalBtn").disabled = false;
      document.getElementById("modalBtn").textContent = "确认认领";
    }
  };

  document.getElementById("modalInput").addEventListener("keydown", function(e) {
    if (e.key === "Enter") window.claimPoint();
  });

  // 点击弹窗外关闭
  document.getElementById("modal").addEventListener("click", function(e) {
    if (e.target === this) closeModal();
  });

  // ═══════ 启动 ═══════
  try {
    await initPoints();
    onValue(pointsRef, renderTable);
  } catch (e) {
    document.getElementById("loading").innerHTML = `<span style="color:var(--r)">加载失败: ${e.message}<br><small>请检查 Firebase 安全规则是否已发布</small></span>`;
    console.error(e);
  }
</script>
</body></html>'''
    return html


def main():
    print("生成点位认领页面…")
    html = build_html()
    path = os.path.join(OUTPUT_DIR, "point_signup.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已保存: {path} ({len(html):,} 字节)")


if __name__ == "__main__":
    main()
