# ruff: noqa: E501
"""Render an honest, self-contained academy conversion research report."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def render_report(
    summary_path: Path,
    outcomes_path: Path,
    rosters_path: Path,
    output_path: Path,
    *,
    primary_threshold: int = 15,
) -> None:
    summaries = list(csv.DictReader(summary_path.open(newline="")))
    outcomes = list(csv.DictReader(outcomes_path.open(newline="")))
    rosters = list(csv.DictReader(rosters_path.open(newline="")))
    by_threshold: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in outcomes:
        by_threshold[int(row["threshold"])].append(row)
    overall = []
    for threshold, rows in sorted(by_threshold.items()):
        total = len(rows)
        established = sum(row["status"] == "reached" for row in rows)
        sustained = sum(row["sustained_status"] == "reached" for row in rows)
        overall.append(
            {
                "threshold": threshold,
                "total": total,
                "established": established,
                "establishedLowerBound": established / total if total else 0,
                "sustained": sustained,
                "sustainedLowerBound": sustained / total if total else 0,
            }
        )
    cohort_rows = [
        {
            "exitSeason": int(row["exit_season_start"]),
            "threshold": int(row["threshold"]),
            "total": int(row["total_players"]),
            "established": int(row["established_players"]),
            "sustained": int(row["sustained_players"]),
            "unknown": int(row["unknown_players"]),
            "completeCoverage": int(row["complete_coverage_players"]),
        }
        for row in summaries
    ]
    if primary_threshold not in by_threshold:
        raise ValueError(f"primary threshold not found: {primary_threshold}")
    primary_rows = by_threshold[primary_threshold]
    tier_counts = Counter(
        row["established_tier"]
        for row in primary_rows
        if row["status"] == "reached" and row["established_tier"]
    )
    report_data = {
        "analysisComplete": bool(summaries)
        and all(row["analysis_complete"].lower() == "true" for row in summaries),
        "rosterListings": len(rosters),
        "primaryThreshold": primary_threshold,
        "rosterReports": len({row["source_url"] for row in rosters}),
        "uniqueRosterPlayers": len({row["player_id"] for row in rosters}),
        "exitPlayers": len(primary_rows),
        "completeCoveragePlayers": max(
            (int(row["complete_coverage_players"]) for row in summaries), default=0
        ),
        "overall": overall,
        "cohorts": cohort_rows,
        "tierCounts": dict(sorted(tier_counts.items())),
        "players": primary_rows,
    }
    encoded = json.dumps(report_data, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("<", "\\u003c")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_HTML.replace("__REPORT_DATA__", encoded))


_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>La Masia 青训转换研究</title>
  <style>
    :root{--ink:#152234;--muted:#637083;--paper:#f4f0e8;--card:#fffdf8;--blue:#123a63;--red:#bd2841;--gold:#dd9d28;--line:#dcd5c9;--unknown:#a8a39b}
    *{box-sizing:border-box} body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
    .shell{max-width:1180px;margin:auto;padding:36px 22px 70px}.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--red);font-weight:800}
    h1{font-family:Georgia,serif;font-size:clamp(38px,6vw,74px);line-height:.96;margin:16px 0 18px;max-width:900px}.dek{max-width:780px;font-size:18px;line-height:1.65;color:var(--muted)}
    .status{margin:28px 0;padding:18px 20px;border:1px solid #e1b2bb;background:#fff3f5;display:flex;gap:14px;align-items:flex-start}.status b{color:var(--red)}
    .grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px;margin-top:22px}.card{background:var(--card);border:1px solid var(--line);border-radius:3px;padding:22px;box-shadow:0 8px 30px rgba(30,35,45,.04)}
    .kpi{grid-column:span 3}.kpi .num{font-family:Georgia,serif;font-size:42px;margin:8px 0}.kpi small,.note{color:var(--muted);line-height:1.45}.wide{grid-column:span 8}.side{grid-column:span 4}.full{grid-column:1/-1}
    h2{font-family:Georgia,serif;font-size:28px;margin:0 0 16px}h3{font-size:14px;margin:0 0 10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
    .controls{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 22px}.controls button{border:1px solid var(--line);background:white;padding:8px 13px;cursor:pointer;border-radius:20px}.controls button.active{background:var(--blue);color:white;border-color:var(--blue)}
    .bar-row{display:grid;grid-template-columns:70px 1fr 64px;gap:10px;align-items:center;margin:13px 0}.track{height:18px;background:#e8e3da;position:relative;overflow:hidden}.fill{height:100%;background:var(--blue)}.fill.sustain{background:var(--gold)}
    .legend{display:flex;gap:18px;font-size:12px;color:var(--muted);margin-bottom:14px}.dot{width:10px;height:10px;display:inline-block;margin-right:6px}.method ol{padding-left:20px;line-height:1.7;color:var(--muted)}
    table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:11px 8px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600}.tag{padding:3px 7px;border-radius:10px;background:#e7edf3;color:var(--blue);font-size:11px}.tag.unknown{background:#ece9e3;color:#746f67}
    .table-wrap{overflow:auto;max-height:520px}.foot{margin-top:24px;color:var(--muted);font-size:12px;line-height:1.6}
    @media(max-width:850px){.kpi{grid-column:span 6}.wide,.side{grid-column:1/-1}} @media(max-width:520px){.kpi{grid-column:1/-1}.shell{padding:24px 14px 50px}}
  </style>
</head>
<body><main class="shell">
  <div class="eyebrow">Academy conversion · Barcelona Juvenil A</div>
  <h1>从最高青年梯队，到成年足球</h1>
  <p class="dek">2015–16 至 2019–20 离开 Juvenil A 的球员，观察随后五个完整赛季。主口径是单季成年国内联赛出场至少 15 次；10 与 20 次用于敏感性分析。</p>
  <div class="status"><b>覆盖受限的探索性下界</b><span>当前成年履历来自不完整的公开派生赛事包。观察到的成功是真实正例；未观察到不能解释为失败。完整 T0/T1/T2 成材率暂不成立。</span></div>
  <section class="grid">
    <article class="card kpi"><h3>Roster-season 行</h3><div class="num" id="listings">—</div><small><span id="report-count">—</span> 份官方年报名册</small></article>
    <article class="card kpi"><h3>唯一球员</h3><div class="num" id="unique">—</div><small>跨赛季身份去重后</small></article>
    <article class="card kpi"><h3>目标 exit cohort</h3><div class="num" id="exits">—</div><small>最终名单季 2015–19</small></article>
    <article class="card kpi"><h3>完整覆盖球员</h3><div class="num" id="complete">—</div><small>不足时只报告下界</small></article>
    <article class="card wide"><h2>按 exit cohort 的观察下界</h2><div class="controls" id="thresholds"></div><div class="legend"><span><i class="dot" style="background:var(--blue)"></i>Established</span><span><i class="dot" style="background:var(--gold)"></i>Sustained</span></div><div id="cohort-chart"></div></article>
    <aside class="card side"><h2>阈值敏感性</h2><div id="sensitivity"></div><p class="note">百分比以全部 <span id="denominator">—</span> 人为分母，是保守下界，不是完整估计。</p></aside>
    <article class="card full"><h2>球员级审计表 · N=<span id="primary-threshold">—</span></h2><div class="table-wrap"><table><thead><tr><th>球员</th><th>Exit</th><th>最高观察级别</th><th>Established</th><th>Sustained</th><th>状态</th></tr></thead><tbody id="players"></tbody></table></div></article>
    <article class="card full method"><h2>如何阅读</h2><ol><li>分母是官方年报列出的全部 Juvenil A 球员，不要求青年比赛出场。</li><li>每名球员归入最后一个 Juvenil A 名单赛季；读取到 2021–22 以识别继续留队者。</li><li>不同赛事级别不会相加跨过单季阈值；同级别跨俱乐部可以相加。</li><li>Established 为一个赛季达到阈值；Sustained 为至少两个赛季达到阈值。</li><li>当前 coverage 全为 partial 或 missing，因此蓝色数字只能作为已观察正例和下界。</li></ol></article>
  </section>
  <p class="foot">研究类型：描述性青训转换，不识别拉玛西亚的因果培养效果。原始 PDF 与受限派生包不随页面再分发；页面只含可审计的派生结果。</p>
</main>
<script>const D=__REPORT_DATA__;
const pct=x=>`${(100*x).toFixed(1)}%`;const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));document.querySelector('#listings').textContent=D.rosterListings;document.querySelector('#report-count').textContent=D.rosterReports;document.querySelector('#unique').textContent=D.uniqueRosterPlayers;document.querySelector('#exits').textContent=D.exitPlayers;document.querySelector('#denominator').textContent=D.exitPlayers;document.querySelector('#complete').textContent=D.completeCoveragePlayers;document.querySelector('#primary-threshold').textContent=D.primaryThreshold;
const controls=document.querySelector('#thresholds');const thresholds=D.overall.map(x=>x.threshold);let active=thresholds.includes(15)?15:thresholds[0];
function renderCohorts(){controls.innerHTML=thresholds.map(t=>`<button class="${t===active?'active':''}" data-t="${t}">≥ ${t} 场</button>`).join('');controls.querySelectorAll('button').forEach(b=>b.onclick=()=>{active=+b.dataset.t;renderCohorts()});const rows=D.cohorts.filter(x=>x.threshold===active);document.querySelector('#cohort-chart').innerHTML=rows.map(r=>`<div class="bar-row"><b>${r.exitSeason}</b><div><div class="track"><div class="fill" style="width:${100*r.established/r.total}%"></div></div><div class="track" style="margin-top:3px"><div class="fill sustain" style="width:${100*r.sustained/r.total}%"></div></div></div><span>${r.established}/${r.total}</span></div>`).join('')}
renderCohorts();document.querySelector('#sensitivity').innerHTML=D.overall.map(r=>`<div class="bar-row"><b>≥ ${r.threshold}</b><div class="track"><div class="fill" style="width:${100*r.establishedLowerBound}%"></div></div><span>${pct(r.establishedLowerBound)}</span></div>`).join('');
document.querySelector('#players').innerHTML=D.players.map(r=>`<tr><td>${esc(r.player_name)}</td><td>${r.exit_season_start}</td><td>${esc(r.highest_reached_tier||'—')}</td><td>${esc(r.established_tier||'—')}</td><td>${esc(r.sustained_tier||'—')}</td><td><span class="tag ${r.status==='unknown'?'unknown':''}">${esc(r.status)}</span></td></tr>`).join('');
</script></body></html>"""
