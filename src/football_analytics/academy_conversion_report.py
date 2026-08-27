# ruff: noqa: E501
"""Render an editorial, evidence-aware academy conversion report."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

_TIER_LABELS = {
    "T0": "五大联赛顶级联赛",
    "T1-A": "其他选定欧洲职业联赛",
    "T1-B": "日韩顶级联赛",
    "T2": "其他选定顶级职业联赛",
}


def render_report(
    summary_path: Path,
    outcomes_path: Path,
    rosters_path: Path,
    output_path: Path,
    *,
    primary_threshold: int = 15,
) -> None:
    """Render one self-contained HTML report from validated analysis outputs."""

    with summary_path.open(newline="") as handle:
        summaries = list(csv.DictReader(handle))
    with outcomes_path.open(newline="") as handle:
        outcomes = list(csv.DictReader(handle))
    if not rosters_path.is_file():
        raise ValueError(f"roster input not found: {rosters_path}")

    by_threshold: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in outcomes:
        by_threshold[int(row["threshold"])].append(row)
    if primary_threshold not in by_threshold:
        raise ValueError(f"primary threshold not found: {primary_threshold}")

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
    primary_rows = by_threshold[primary_threshold]
    established_rows = [row for row in primary_rows if row["status"] == "reached"]
    sustained_rows = [
        row for row in primary_rows if row["sustained_status"] == "reached"
    ]
    reached_rows = [row for row in primary_rows if row["highest_reached_tier"]]
    tier_counts = Counter(row["established_tier"] for row in established_rows)
    tier_breakdown = [
        {
            "tier": tier,
            "label": _TIER_LABELS.get(tier, tier),
            "count": count,
            "lowerBound": count / len(primary_rows) if primary_rows else 0,
            "shareOfConfirmed": count / len(established_rows)
            if established_rows
            else 0,
        }
        for tier, count in sorted(tier_counts.items(), key=lambda item: item[0])
    ]
    report_data = {
        "analysisComplete": bool(summaries)
        and all(row["analysis_complete"].lower() == "true" for row in summaries),
        "primaryThreshold": primary_threshold,
        "exitPlayers": len(primary_rows),
        "observedReached": len(reached_rows),
        "establishedCount": len(established_rows),
        "sustainedCount": len(sustained_rows),
        "unknownCount": sum(row["status"] == "unknown" for row in primary_rows),
        "completeCoveragePlayers": max(
            (int(row["complete_coverage_players"]) for row in summaries), default=0
        ),
        "overall": overall,
        "cohorts": cohort_rows,
        "tierBreakdown": tier_breakdown,
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
  <meta name="description" content="从青训价值与职业风险两面，观察2015至2020年巴塞罗那Juvenil A球员进入成年足球后的五年。">
  <title>拉玛西亚之后｜青训产出的价值与代价</title>
  <style>
    :root{--ink:#101923;--muted:#596675;--paper:#f3efe7;--surface:#fffdf8;--navy:#0b3157;--blue:#1860a0;--wine:#8f1736;--red:#c3314d;--gold:#d59a2d;--sand:#e6ded0;--line:#d8d0c3;--unknown:#aaa49b}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.6}a{color:inherit}
    .shell{max-width:1180px;margin:auto;padding:0 24px 88px}.mast{display:flex;justify-content:space-between;align-items:center;padding:22px 0;border-bottom:1px solid var(--line);font-size:12px;letter-spacing:.12em;text-transform:uppercase}.mast b{color:var(--wine)}
    .hero{padding:72px 0 50px;display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.55fr);gap:54px;align-items:end}.eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--wine);font-weight:800}.hero h1{font-family:Georgia,"Noto Serif SC",serif;font-size:clamp(50px,7.6vw,102px);line-height:.9;letter-spacing:-.045em;margin:20px 0 28px}.hero h1 span{display:block;color:var(--wine)}.dek{max-width:760px;font-size:20px;line-height:1.75;color:var(--muted);margin:0}.hero-note{border-top:4px solid var(--gold);padding-top:20px;font-family:Georgia,"Noto Serif SC",serif;font-size:21px;line-height:1.55}.hero-note small{display:block;font-family:inherit;font-size:13px;color:var(--muted);margin-top:16px}
    .chapter{padding:64px 0;border-top:1px solid var(--line)}.chapter-head{display:grid;grid-template-columns:120px minmax(0,720px);gap:24px;margin-bottom:36px}.chapter-num{color:var(--wine);font-weight:800;letter-spacing:.14em}.chapter h2{font-family:Georgia,"Noto Serif SC",serif;font-size:clamp(34px,4.2vw,56px);line-height:1.08;margin:0 0 16px}.chapter-intro{font-size:17px;color:var(--muted);margin:0;max-width:760px}
    .dual{display:grid;grid-template-columns:1fr 1fr;gap:18px}.panel{background:var(--surface);border:1px solid var(--line);padding:30px;position:relative}.panel.value{border-top:5px solid var(--blue)}.panel.risk{border-top:5px solid var(--wine)}.panel-label{font-size:12px;letter-spacing:.13em;text-transform:uppercase;font-weight:800;color:var(--muted)}.panel h3{font-family:Georgia,"Noto Serif SC",serif;font-size:30px;line-height:1.18;margin:12px 0}.panel p{color:var(--muted);margin:0}.big-number{font-family:Georgia,serif;font-size:72px;line-height:1;color:var(--navy);margin:24px 0 8px}.risk .big-number{color:var(--wine)}
    .metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px}.metric{background:var(--surface);border:1px solid var(--line);padding:22px}.metric .num{font-family:Georgia,serif;font-size:42px;line-height:1}.metric b{display:block;font-size:14px;margin:8px 0 4px}.metric small,.small{font-size:12px;color:var(--muted)}
    .funnel{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;margin:30px 0}.funnel-step{padding:28px 22px;background:var(--navy);color:white;min-height:154px}.funnel-step:nth-child(2){background:#154b78}.funnel-step:nth-child(3){background:var(--wine)}.funnel-step .n{font-family:Georgia,serif;font-size:50px;line-height:1}.funnel-step b{display:block;margin:8px 0 2px}.funnel-step small{color:#dfe8ef}.evidence-warning{background:#fff4e0;border-left:5px solid var(--gold);padding:20px 22px;margin-top:16px;color:#604818}
    .chart-layout{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(260px,.65fr);gap:18px}.chart-card{background:var(--surface);border:1px solid var(--line);padding:28px}.chart-card h3{font-family:Georgia,"Noto Serif SC",serif;font-size:26px;margin:0 0 6px}.chart-card .sub{font-size:13px;color:var(--muted);margin-bottom:24px}.hbar{display:grid;grid-template-columns:minmax(150px,250px) 1fr 72px;gap:14px;align-items:center;margin:20px 0}.hbar-label b{display:block}.hbar-label small{color:var(--muted)}.track{height:25px;background:#e9e3d9;overflow:hidden}.fill{height:100%;background:var(--blue);min-width:2px}.fill.gold{background:var(--gold)}.fill.wine{background:var(--wine)}.bar-value{text-align:right;font-variant-numeric:tabular-nums}.bar-value b{display:block}.bar-value small{color:var(--muted)}
    .insight-list{display:grid;gap:1px;background:var(--line);border:1px solid var(--line)}.insight{background:var(--surface);padding:24px}.insight strong{font-family:Georgia,"Noto Serif SC",serif;font-size:22px;display:block;line-height:1.3;margin-bottom:8px}.insight p{margin:0;color:var(--muted);font-size:14px}
    .controls{display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 22px}.controls button{border:1px solid var(--line);background:white;padding:9px 14px;cursor:pointer;border-radius:20px}.controls button.active{background:var(--navy);color:white;border-color:var(--navy)}.cohort-row{display:grid;grid-template-columns:68px 1fr 78px;gap:12px;align-items:center;margin:18px 0}.cohort-bars{display:grid;gap:4px}.cohort-track{height:13px;background:#e9e3d9}.cohort-fill{height:100%;background:var(--blue)}.cohort-fill.sustain{background:var(--gold)}.legend{display:flex;gap:18px;font-size:12px;color:var(--muted)}.dot{display:inline-block;width:10px;height:10px;margin-right:6px}
    .method-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.definition{padding:22px;border-top:3px solid var(--navy);background:var(--surface)}.definition b{display:block;margin-bottom:8px}.definition p{font-size:13px;color:var(--muted);margin:0}.boundary{margin-top:18px;padding:26px;background:var(--navy);color:white}.boundary h3{font-family:Georgia,"Noto Serif SC",serif;font-size:26px;margin:0 0 8px}.boundary p{color:#dbe5ef;margin:0}
    .table-tools{display:flex;gap:10px;margin-bottom:16px}.table-tools input,.table-tools select{border:1px solid var(--line);background:white;padding:10px 12px;font:inherit}.table-tools input{flex:1;min-width:160px}.table-wrap{overflow:auto;max-height:560px;border:1px solid var(--line);background:var(--surface)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:12px 10px;border-bottom:1px solid var(--line);white-space:nowrap}th{position:sticky;top:0;background:#f8f4ec;color:var(--muted);z-index:1}.tag{padding:4px 8px;border-radius:12px;background:#e6eef5;color:var(--navy);font-size:11px}.tag.unknown{background:#eeeae3;color:#514d47}
    .closing{background:var(--wine);color:white;margin-top:64px;padding:48px}.closing h2{font-family:Georgia,"Noto Serif SC",serif;font-size:clamp(34px,4vw,52px);line-height:1.1;margin:0 0 18px}.closing p{font-size:18px;max-width:850px;color:#f6dfe5}.foot{margin-top:28px;color:var(--muted);font-size:12px;line-height:1.7}
    @media(max-width:850px){.hero,.chart-layout{grid-template-columns:1fr}.hero{padding-top:50px}.dual{grid-template-columns:1fr}.chapter-head{grid-template-columns:1fr;gap:8px}.metric-grid,.method-grid{grid-template-columns:1fr}.funnel{grid-template-columns:1fr}.hbar{grid-template-columns:minmax(120px,190px) 1fr 60px}}
    @media(max-width:540px){.shell{padding:0 14px 60px}.hero h1{font-size:52px}.hero{gap:30px}.chapter{padding:48px 0}.panel,.chart-card{padding:22px}.hbar{grid-template-columns:1fr 58px}.hbar .track{grid-column:1/-1;grid-row:2}.bar-value{grid-column:2;grid-row:1}.closing{padding:30px 24px;margin-top:40px}.mast span:last-child{display:none}.table-tools{flex-direction:column}}
  </style>
</head>
<body><main class="shell">
  <header class="mast"><b>La Masia / Academy Output Study</b><span>2015–2020 exit cohorts · five-year window</span></header>
  <section class="hero">
    <div><div class="eyebrow">以拉玛西亚五届最高青年队为例</div><h1>顶级青训的<span>两面</span></h1><p class="dek">它的价值，来自能把少数人送到职业足球的最高处；它的残酷，在于即使已经抵达最高青年梯队，成年比赛的位置仍要从零开始、反复赢得。</p></div>
    <aside class="hero-note">青训不是通往一线队的流水线，而是一项高上限、低确定性的人才投资。<small>证据来自85名在2015–16至2019–20赛季最后一次进入巴萨 Juvenil A 名单的球员，以及他们随后五个完整赛季的成年联赛记录。</small></aside>
  </section>

  <section class="chapter" id="summary">
    <div class="chapter-head"><div class="chapter-num">01 / 观点</div><div><h2>顶级青训同时生产顶级价值，也生产职业不确定性</h2><p class="chapter-intro">评价青训不能只数有多少人留在本队，也不能把一次成年队出场叫作成功。真正值得观察的是：球员走到了多高、是否站稳，以及这种位置能否被重复获得。</p></div></div>
    <div class="metric-grid">
      <div class="metric"><div class="num"><span id="top-established">—</span><small> / 85</small></div><b>在五大联赛单季站稳</b><small>顶级竞技产出的保守下界</small></div>
      <div class="metric"><div class="num"><span id="established">—</span><small> / 85</small></div><b>在纳入联赛单季站稳</b><small>一个赛季至少 <span class="primary-n">—</span> 场</small></div>
      <div class="metric"><div class="num"><span id="sustained">—</span><small> / 85</small></div><b>在至少两个赛季站稳</b><small>职业位置能够被重复赢得</small></div>
    </div>
    <div class="evidence-warning">三项结果都是现有公开数据至少能够确认的人数，而不是完整成材率。数据缺失只影响估计的完整性，不改变已经观察到的正例。</div>
  </section>

  <section class="chapter" id="value">
    <div class="chapter-head"><div class="chapter-num">02 / 价值</div><div><h2>青训价值首先体现在球员能走到多高，而不只是谁留了下来</h2><p class="chapter-intro">一名球员在其他俱乐部成为高水平职业球员，可能是巴萨未能内部捕获的价值，却仍然证明了青训能够向职业足球输出什么级别的人才。</p></div></div>
    <div class="chart-layout">
      <article class="chart-card"><h3>已确认站稳者的竞技层级</h3><div class="sub">以全部研究对象为分母的保守下界；分类互斥，按最高达标层级计。</div><div id="tier-bars"></div></article>
      <aside class="insight-list">
        <div class="insight"><strong><span id="elite-share">—</span> 的已确认站稳者达到五大联赛</strong><p>这显示了产出的上限，但当前数据本身更偏向覆盖高水平联赛，不能据此推断培养偏好。</p></div>
        <div class="insight"><strong><span id="durability-share">—</span> 的已确认站稳者多赛季达标</strong><p>一次突破和持续职业位置是两件事；多赛季指标把短暂机会与稳定角色分开。</p></div>
        <div class="insight"><strong>“外部成功”不是青训失败</strong><p>本版衡量球员产出。巴萨一线队分钟、转会收入和成本节省需要另一套价值捕获数据。</p></div>
      </aside>
    </div>
  </section>

  <section class="chapter" id="pressure">
    <div class="chapter-head"><div class="chapter-num">03 / 代价</div><div><h2>进入成年队、站稳一个赛季、形成持续生涯，是三件不同的事</h2><p class="chapter-intro">在现有记录中，35人获得过纳入联赛的出场，25人至少一个赛季达到15场，14人能在两个赛季重复做到。青年队履历不会自动兑换成稳定的成年位置。</p></div></div>
    <div class="chart-layout">
      <article class="chart-card"><h3>阈值敏感性</h3><div class="sub">切换“站稳”的场次要求，比较单赛季与多赛季下界。</div><div class="controls" id="thresholds"></div><div id="threshold-bars"></div></article>
      <article class="chart-card"><h3>三层职业转换</h3><div class="sub">主口径 N=<span class="primary-n">—</span>；数字都是现有数据至少确认的人数。</div><div id="ladder"></div><div class="evidence-warning"><b>这不是淘汰漏斗。</b> 未确认者可能在缺失联赛中完成了职业转换，因此只能陈述“至少有多少人做到”。</div></article>
    </div>
  </section>

  <section class="chapter" id="definitions">
    <div class="chapter-head"><div class="chapter-num">04 / 含义</div><div><h2>这组数据改变了我们如何理解“青训成功”</h2><p class="chapter-intro">同一批球员，对俱乐部、从业者和家庭意味着不同的价值与风险。一个单一的“成材率”无法容纳这些差异。</p></div></div>
    <div class="method-grid">
      <div class="definition"><b>对俱乐部：产出不等于捕获</b><p>球员在外部成为高水平职业球员仍是青训产出；一线队分钟与转会收入则衡量俱乐部最终留住了多少价值。</p></div>
      <div class="definition"><b>对球员与家庭：入选不是承诺</b><p>最高青年队代表已经非常接近职业足球，却不保证成年队角色。机会、站稳和持续需要分别赢得。</p></div>
      <div class="definition"><b>对从业者：评估一个人才组合</b><p>既看顶级球员的高度，也看稳定职业球员的宽度和持续性，而不是用一名明星或一个比例概括整个年届。</p></div>
    </div>
    <div class="boundary"><h3>研究边界</h3><p>样本是85名最后一次进入 Juvenil A 名单的赛季位于2015–16至2019–20的球员，并观察其后五个完整赛季。更晚名单只用于避免把继续留队者误判为离队，不属于研究样本。结果不能代表所有进入拉玛西亚的儿童，也不能识别培养的因果效果。</p></div>
  </section>

  <section class="chapter" id="players">
    <div class="chapter-head"><div class="chapter-num">05 / 附录</div><div><h2>85名球员，85条不同的职业路径</h2><p class="chapter-intro">总体数字不应该抹掉个体差异。这里可以查看每名球员在五年窗口内被观察到的最高层级、单赛季稳定性和多赛季持续性。</p></div></div>
    <div class="table-tools"><input id="player-search" type="search" placeholder="搜索球员姓名" aria-label="搜索球员姓名"><select id="status-filter" aria-label="筛选结果"><option value="all">全部结果</option><option value="reached">已确认站稳</option><option value="unknown">尚无法判断</option></select></div>
    <div class="table-wrap" role="region" tabindex="0" aria-label="可横向滚动的球员职业结果表"><table><thead><tr><th>球员</th><th>离开年届</th><th>最高观察层级</th><th>单赛季站稳</th><th>多赛季站稳</th><th>证据状态</th></tr></thead><tbody id="player-rows"></tbody></table></div>
  </section>

  <section class="closing"><h2>顶级青训的两面，并不互相矛盾。</h2><p>正因为极少数球员能够走到职业足球的最高处，青训拥有巨大的竞技价值；也正因为这样的高度稀缺，即使对最高青年梯队的球员而言，稳定职业生涯仍然不是体系自动交付的结果。</p></section>
  <p class="foot">数据范围：<a href="https://www.fcbarcelona.com/en/club/organisation-and-strategic-plan/commissions-and-bodies/annual-reports">FC Barcelona 官方年报</a> Juvenil A 名单；最终名单季 2015–16 至 2019–20；随后五个完整赛季。成人履历来自覆盖受限的 <a href="https://github.com/dcaribou/transfermarkt-datasets">公开派生赛事包</a>，当前所有球员均为 partial 或 missing coverage。页面只报告已观察正例与全体分母下界，不把缺失值转换为失败。研究类型：描述性青训产出分析，不作因果归因。</p>
</main>
<script>(()=>{const D=__REPORT_DATA__;
const $=s=>document.querySelector(s);const pct=x=>`${(100*x).toFixed(1)}%`;const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const tierLabel=t=>({T0:'五大联赛顶级联赛','T1-A':'其他选定欧洲职业联赛','T1-B':'日韩顶级联赛',T2:'其他选定顶级职业联赛'}[t]||t||'—');
document.querySelectorAll('.exit-total').forEach(x=>x.textContent=D.exitPlayers);document.querySelectorAll('.primary-n').forEach(x=>x.textContent=D.primaryThreshold);$('#established').textContent=D.establishedCount;$('#sustained').textContent=D.sustainedCount;
const topTier=D.tierBreakdown.find(x=>x.tier==='T0')||{count:0,shareOfConfirmed:0};$('#top-established').textContent=topTier.count;$('#elite-share').textContent=pct(topTier.shareOfConfirmed);$('#durability-share').textContent=pct(D.establishedCount?D.sustainedCount/D.establishedCount:0);
const makeBar=(label,detail,count,total,color='')=>`<div class="hbar"><div class="hbar-label"><b>${esc(label)}</b><small>${esc(detail)}</small></div><div class="track"><div class="fill ${color}" style="width:${100*count/total}%"></div></div><div class="bar-value"><b>${count}/${total}</b><small>${pct(count/total)}</small></div></div>`;
$('#tier-bars').innerHTML=D.tierBreakdown.map((r,i)=>makeBar(r.label,`最高达标层级 · 已确认者中 ${pct(r.shareOfConfirmed)}`,r.count,D.exitPlayers,i?'gold':'')).join('');
const controls=$('#thresholds');let active=D.primaryThreshold;function renderThreshold(){controls.innerHTML=D.overall.map(r=>`<button class="${r.threshold===active?'active':''}" data-n="${r.threshold}">≥ ${r.threshold} 场</button>`).join('');controls.querySelectorAll('button').forEach(b=>b.onclick=()=>{active=+b.dataset.n;renderThreshold()});const row=D.overall.find(r=>r.threshold===active);$('#threshold-bars').innerHTML=makeBar('单赛季站稳','至少一个赛季达到阈值',row.established,row.total)+makeBar('多赛季站稳','至少两个赛季达到阈值',row.sustained,row.total,'gold')}
renderThreshold();$('#ladder').innerHTML=makeBar('获得机会','至少一次选定联赛出场',D.observedReached,D.exitPlayers)+makeBar('单赛季站稳',`一个赛季至少 ${D.primaryThreshold} 场`,D.establishedCount,D.exitPlayers,'gold')+makeBar('多赛季站稳',`至少两个赛季达到 ${D.primaryThreshold} 场`,D.sustainedCount,D.exitPlayers,'wine');
function renderPlayers(){const query=$('#player-search').value.trim().toLocaleLowerCase();const status=$('#status-filter').value;const rows=D.players.filter(r=>(!query||r.player_name.toLocaleLowerCase().includes(query))&&(status==='all'||r.status===status));$('#player-rows').innerHTML=rows.map(r=>`<tr><td><b>${esc(r.player_name)}</b></td><td>${r.exit_season_start}</td><td>${esc(tierLabel(r.highest_reached_tier))}</td><td>${esc(tierLabel(r.established_tier))}</td><td>${esc(tierLabel(r.sustained_tier))}</td><td><span class="tag ${r.status==='unknown'?'unknown':''}">${r.status==='reached'?'已确认站稳':'尚无法判断'}</span></td></tr>`).join('')}
$('#player-search').addEventListener('input',renderPlayers);$('#status-filter').addEventListener('change',renderPlayers);renderPlayers();})();
</script></body></html>"""
