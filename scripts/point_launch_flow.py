"""
美团接力送 · 点位开设流程图
===========================
生成静态 HTML 流程页面，面向内部/合作方使用。
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
<title>接力送 · 点位开设流程</title>
<style>
  :root{--g:#27ae60;--gb:#d5f5e3;--b:#2980b9;--bb:#d4e6f1;--r:#e74c3c;--rb:#fadbd8;--y:#f39c12;--yb:#fef9e7;--t:#2c3e50;--l:#7f8c8d;--br:#e0e0e0;--bg:#fafafa}
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--t);background:#fff;max-width:1000px;margin:0 auto;padding:36px 40px;line-height:1.7}
  h1{font-size:1.7rem;font-weight:800;margin-bottom:4px}
  h1 .sub{font-size:.8rem;color:var(--l);font-weight:400;margin-left:10px}
  hr{border:none;border-top:2px solid #eee;margin:18px 0}

  .flow{display:flex;flex-direction:column;gap:0;margin:20px 0}
  .phase{display:flex;gap:0;min-height:180px}
  .phase-num{width:72px;flex-shrink:0;display:flex;flex-direction:column;align-items:center;position:relative}
  .phase-num .circle{width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:800;color:#fff;z-index:2;flex-shrink:0}
  .phase-num::after{content:'';width:3px;flex:1;min-height:20px;margin:4px 0}
  .phase:last-child .phase-num::after{display:none}
  .c1{background:var(--g)} .phase-num.l1::after{background:var(--g)}
  .c2{background:var(--b)} .phase-num.l2::after{background:var(--b)}
  .c3{background:var(--y)} .phase-num.l3::after{background:#d4ac0d}
  .c4{background:var(--r)} .phase-num.l4::after{background:var(--r)}

  .phase-body{flex:1;background:var(--bg);border-radius:10px;padding:18px 22px;margin-bottom:16px;border:1px solid var(--br)}
  .phase-body h2{font-size:1.05rem;font-weight:700;margin-bottom:2px}
  .phase-body .dur{font-size:.8rem;color:var(--l);margin-bottom:12px}
  .phase-body .checklist{display:grid;grid-template-columns:1fr 1fr;gap:8px 20px}
  @media(max-width:600px){.phase-body .checklist{grid-template-columns:1fr}}
  .phase-body .item{display:flex;align-items:flex-start;gap:8px;font-size:.84rem;padding:6px 0;border-bottom:1px solid #f0f0f0}
  .phase-body .item .icon{flex-shrink:0;font-size:1rem;margin-top:1px}
  .phase-body .item .txt strong{display:block;font-size:.82rem;line-height:1.45}
  .phase-body .item .txt small{color:var(--l);font-size:.76rem}
  .phase-body .warn{font-size:.78rem;color:var(--r);background:var(--rb);border-radius:6px;padding:8px 12px;margin-top:10px}

  .phase-body .item-full{grid-column:1/-1}

  .summary{background:var(--bb);border-radius:10px;padding:20px 24px;margin:20px 0;border:1px solid var(--b)}
  .summary h3{font-size:.95rem;margin-bottom:8px}
  .summary .timeline{display:flex;align-items:center;gap:8px;font-size:.84rem;flex-wrap:wrap}
  .summary .timeline .step{background:#fff;border-radius:6px;padding:8px 14px;border:1px solid var(--br);text-align:center;font-weight:600;white-space:nowrap}
  .summary .timeline .arrow{color:var(--l);font-size:1.1rem}

  .footer{margin-top:36px;padding-top:12px;border-top:2px solid #eee;color:var(--l);font-size:.74rem}
</style>
</head>
<body>

<h1>🏗️ 接力送 · 点位开设流程<span class="sub">从确认点位到正式运营</span></h1>
<hr>

<div class="flow">

  <!-- ═══════ ① 踩点 ═══════ -->
  <div class="phase">
    <div class="phase-num l1"><div class="circle c1">①</div></div>
    <div class="phase-body">
      <h2>踩点阶段</h2>
      <div class="dur">⏱ 点位确认前 1-3 天 · 高峰期实地勘察</div>
      <div class="checklist">
        <div class="item">
          <span class="icon">📦</span>
          <span class="txt">
            <strong>确认外卖柜情况</strong>
            <small>楼下是否有美团外卖柜？如有，骑手可能直接把餐放柜子，不走接力送。</small>
          </span>
        </div>
        <div class="item">
          <span class="icon">🏍️</span>
          <span class="txt">
            <strong>骑手路线勘察</strong>
            <small>尽量高峰期（11:00-13:00）去查看，了解骑手到达后停车位置、进入楼宇的动线。</small>
          </span>
        </div>
        <div class="item">
          <span class="icon">🏢</span>
          <span class="txt">
            <strong>物业管控程度</strong>
            <small>物业是否严格？决定了点位正常摆放还是隐蔽摆放。</small>
          </span>
        </div>
        <div class="item">
          <span class="icon">📍</span>
          <span class="txt">
            <strong>确定摆放位置</strong>
            <small>选在大堂内骑手必经之处，靠近电梯口为佳，同时考虑物业容忍度。</small>
          </span>
        </div>
      </div>
      <div class="warn">⚠ 踩点结论直接影响后续物料选择（KT板大小）和运营方式（正常摆 vs 隐蔽摆）。物业严格的地方优先选小号物料。</div>
    </div>
  </div>

  <!-- ═══════ ② 招聘 ═══════ -->
  <div class="phase">
    <div class="phase-num l2"><div class="circle c2">②</div></div>
    <div class="phase-body">
      <h2>人员招聘阶段</h2>
      <div class="dur">⏱ 开点前至少 1 天完成信息收集</div>
      <div class="checklist">
        <div class="item">
          <span class="icon">🪪</span>
          <span class="txt">
            <strong>收集兼职信息</strong>
            <small>需提供：身份证 + 电话 + 名字。缺一不可。</small>
          </span>
        </div>
        <div class="item">
          <span class="icon">📅</span>
          <span class="txt">
            <strong>至少提前一天提交</strong>
            <small>开点前一天必须把人员信息提供给我方，由我方上传后台。</small>
          </span>
        </div>
        <div class="item item-full">
          <span class="icon">🔥</span>
          <span class="txt">
            <strong>美团火炬实名认证（关键步骤）</strong>
            <small>兼职人员须在收到后台信息后的<strong>当天 24:00 前</strong>，通过"美团火炬"完成实名认证。认证通过后<strong>第二天</strong>账号才能正常使用。未认证或超时认证，开点当天无法上岗。</small>
          </span>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══════ ③ 物料 ═══════ -->
  <div class="phase">
    <div class="phase-num l3"><div class="circle c3">③</div></div>
    <div class="phase-body">
      <h2>物料准备</h2>
      <div class="dur">⏱ 开点前 1-2 天备齐</div>
      <div class="checklist">
        <div class="item">
          <span class="icon">🪧</span>
          <span class="txt">
            <strong>接力送 KT 板</strong>
            <small>上面贴有骑手交接二维码，骑手扫码后完成单号绑定。物业严格的地方尽量用小的，降低存在感。</small>
          </span>
        </div>
        <div class="item">
          <span class="icon">🧺</span>
          <span class="txt">
            <strong>小号放餐 / 送餐篮子</strong>
            <small>用来分类摆放待配送的餐品，方便骑手放置和配送员取走。</small>
          </span>
        </div>
        <div class="item item-full">
          <span class="icon">🦺</span>
          <span class="txt">
            <strong>接力送马甲</strong>
            <small>配送员穿戴，便于骑手和物业识别。同时也是品牌露出。</small>
          </span>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══════ ④ 开点 ═══════ -->
  <div class="phase">
    <div class="phase-num l4"><div class="circle c4">④</div></div>
    <div class="phase-body">
      <h2>开点当天</h2>
      <div class="dur">⏱ 正式运营首日</div>
      <div class="checklist">
        <div class="item">
          <span class="icon">✅</span>
          <span class="txt">
            <strong>确认账号全部可用</strong>
            <small>开点前 1 小时检查所有兼职账号状态，确保火炬认证已通过。</small>
          </span>
        </div>
        <div class="item">
          <span class="icon">📸</span>
          <span class="txt">
            <strong>物料布置 + 拍照</strong>
            <small>KT板摆好、篮子就位、马甲穿上。拍照记录点位实际摆放状态。</small>
          </span>
        </div>
        <div class="item">
          <span class="icon">📋</span>
          <span class="txt">
            <strong>首日跟点</strong>
            <small>第一个午高峰全程在场，观察骑手动线是否顺畅、摆位是否需要调整。</small>
          </span>
        </div>
        <div class="item">
          <span class="icon">📊</span>
          <span class="txt">
            <strong>记录首日数据</strong>
            <small>当天单量、骑手配合情况、物业反应，作为后续优化依据。</small>
          </span>
        </div>
      </div>
    </div>
  </div>

</div>

<!-- ═══════ 时间线总览 ═══════ -->
<div class="summary">
  <h3>🗓 标准开点时间线</h3>
  <div class="timeline">
    <div class="step">D−3<br><small>踩点勘察</small></div>
    <div class="arrow">→</div>
    <div class="step">D−2<br><small>确认点位<br>准备物料</small></div>
    <div class="arrow">→</div>
    <div class="step">D−1<br><small>收集人员信息<br>上传后台</small></div>
    <div class="arrow">→</div>
    <div class="step" style="border-color:var(--r);border-width:2px">D−1 24:00<br><small>火炬认证<br>截止</small></div>
    <div class="arrow">→</div>
    <div class="step" style="background:var(--gb);border-color:var(--g);border-width:2px">D-Day<br><small>正式开点 🎉</small></div>
  </div>
</div>

<div class="footer">
  <p>美团接力送 · 点位开设流程 · 2026-06-14</p>
</div>
</body></html>'''
    return html


def main():
    print("生成点位开设流程图...")
    html = build_html()
    path = os.path.join(OUTPUT_DIR, "point_launch_flow.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已保存: {path} ({len(html):,} 字节)")


if __name__ == "__main__":
    main()
