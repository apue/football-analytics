# ruff: noqa: E501
"""Render an editorial, evidence-aware academy conversion report."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path

from .academy_conversion import (
    AppearanceRow,
    CompetitionRule,
    select_representative_competitions,
)
from .academy_conversion_io import load_appearances, load_competition_rules
from .academy_study import AcademyStudyConfig, load_academy_study_config


def render_report(
    summary_path: Path,
    outcomes_path: Path,
    appearances_path: Path,
    competitions_path: Path,
    study_config_path: Path,
) -> Path:
    """Render one self-contained HTML report from validated analysis outputs."""

    with summary_path.open(newline="") as handle:
        summaries = list(csv.DictReader(handle))
    with outcomes_path.open(newline="") as handle:
        outcomes = list(csv.DictReader(handle))
    study = load_academy_study_config(study_config_path, require_approved=True)
    competition_policy = _load_competition_policy(Path(study.competition_policy_path))
    appearances = load_appearances(appearances_path)
    rules = load_competition_rules(competitions_path)
    expected_policy_version = str(competition_policy.get("policy_version", ""))
    actual_policy_versions = {row.policy_version for row in rules}
    if actual_policy_versions != {expected_policy_version}:
        raise ValueError(
            "competition facts do not match study policy: "
            f"expected={expected_policy_version}, actual={sorted(actual_policy_versions)}"
        )

    by_threshold: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in outcomes:
        by_threshold[int(row["threshold"])].append(row)
    expected_thresholds = set(study.sensitivity_thresholds)
    if set(by_threshold) != expected_thresholds:
        raise ValueError(
            "outcome thresholds do not match study config: "
            f"expected={sorted(expected_thresholds)}, actual={sorted(by_threshold)}"
        )
    primary_threshold = study.primary_appearance_threshold
    if primary_threshold not in by_threshold:
        raise ValueError(f"primary threshold not found: {primary_threshold}")
    if not summaries:
        raise ValueError("summary input is empty")

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
                "sustained": sustained,
            }
        )

    summary_totals: dict[int, Counter[str]] = defaultdict(Counter)
    for row in summaries:
        threshold = int(row["threshold"])
        summary_totals[threshold].update(
            total=int(row["total_players"]),
            established=int(row["established_players"]),
            sustained=int(row["sustained_players"]),
        )
    for row in overall:
        expected = summary_totals[row["threshold"]]
        actual = {
            "total": row["total"],
            "established": row["established"],
            "sustained": row["sustained"],
        }
        if dict(expected) != actual:
            raise ValueError(
                "summary does not reconcile to player outcomes for threshold "
                f"{row['threshold']}: summary={dict(expected)}, outcomes={actual}"
            )

    primary_rows = by_threshold[primary_threshold]
    actual_exit_seasons = {int(row["exit_season_start"]) for row in primary_rows}
    expected_exit_seasons = set(
        range(study.exit_season_start, study.exit_season_end + 1)
    )
    if not actual_exit_seasons.issubset(expected_exit_seasons):
        raise ValueError("outcomes contain exit seasons outside the study config")
    established_rows = [row for row in primary_rows if row["status"] == "reached"]
    sustained_rows = [
        row for row in primary_rows if row["sustained_status"] == "reached"
    ]
    tier_counts = Counter(row["established_tier"] for row in established_rows)
    tier_labels = competition_policy.get("tier_labels_zh", {})
    tier_ranks = competition_policy.get("tier_ranks", {})
    if not isinstance(tier_labels, dict):
        raise ValueError("competition policy tier_labels_zh must be an object")
    if not isinstance(tier_ranks, dict):
        raise ValueError("competition policy tier_ranks must be an object")
    tier_breakdown = [
        {
            "tier": tier,
            "label": str(tier_labels.get(tier, tier)),
            "count": count,
            "shareOfConfirmed": count / len(established_rows)
            if established_rows
            else 0,
        }
        for tier, count in sorted(
            tier_counts.items(), key=lambda item: int(tier_ranks.get(item[0], 99))
        )
    ]
    level_matrix = _build_level_matrix(primary_rows, competition_policy)
    player_rows = _add_representative_leagues(
        primary_rows,
        appearances,
        rules,
        competition_policy,
        study,
        threshold=primary_threshold,
    )
    coverage_complete = all(
        row["coverage_complete"].lower() == "true" for row in primary_rows
    ) and all(row["analysis_complete"].lower() == "true" for row in summaries)
    report_data = {
        "study": {
            "academyName": study.academy_display_name,
            "squadName": study.squad_name,
            "cohortLabel": _cohort_label(study),
            "observationSeasons": study.observation_season_count,
            "sustainedSeasons": study.sustained_qualifying_seasons,
            "rosterSourceUrl": study.roster_source_public_url,
            "adultSourceUrl": study.adult_source_public_url,
            "coverageNote": study.adult_source_coverage_note,
        },
        "primaryThreshold": primary_threshold,
        "coverageComplete": coverage_complete,
        "exitPlayers": len(primary_rows),
        "establishedCount": len(established_rows),
        "sustainedCount": len(sustained_rows),
        "overall": overall,
        "tierBreakdown": tier_breakdown,
        "levelMatrix": level_matrix,
        "players": player_rows,
    }
    encoded = json.dumps(report_data, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("<", "\\u003c")
    output_path = Path(study.report_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_HTML.replace("__REPORT_DATA__", encoded))
    return output_path


def _load_competition_policy(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"competition policy not found: {path}")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("competition policy must be a JSON object")
    return value


def _build_level_matrix(
    rows: list[dict[str, str]], policy: Mapping[str, object]
) -> list[dict[str, object]]:
    bands = policy.get("reporting_bands")
    if not isinstance(bands, list) or not bands:
        raise ValueError("competition policy requires reporting_bands")
    result = []
    for value in bands:
        if not isinstance(value, dict):
            raise ValueError("each reporting band must be an object")
        tiers_value = value.get("tiers")
        tiers = None if tiers_value is None else set(tiers_value)
        if tiers is None:
            established = sum(row["status"] == "reached" for row in rows)
            sustained = sum(row["sustained_status"] == "reached" for row in rows)
        else:
            established = sum(row["established_tier"] in tiers for row in rows)
            sustained = sum(row["sustained_tier"] in tiers for row in rows)
        result.append(
            {
                "id": str(value.get("id", "")),
                "label": str(value.get("label_zh", "")),
                "detail": str(value.get("detail_zh", "")),
                "established": established,
                "sustained": sustained,
            }
        )
    by_id = {str(row["id"]): row for row in result}
    required = {"professional", "higher-level", "big-five"}
    if len(result) != 3 or set(by_id) != required:
        raise ValueError(
            "reporting bands must be exactly professional, higher-level, and big-five"
        )
    professional_source = next(
        value for value in bands if value.get("id") == "professional"
    )
    if professional_source.get("tiers") is not None:
        raise ValueError("professional reporting band must use tiers: null")
    for field in ("established", "sustained"):
        values = [
            int(by_id[band_id][field])
            for band_id in ("professional", "higher-level", "big-five")
        ]
        if values != sorted(values, reverse=True):
            raise ValueError(f"reporting bands are not nested for {field}: {values}")
    return result


def _add_representative_leagues(
    outcomes: list[dict[str, str]],
    appearances: list[AppearanceRow],
    rules: list[CompetitionRule],
    policy: Mapping[str, object],
    study: AcademyStudyConfig,
    *,
    threshold: int,
) -> list[dict[str, str]]:
    metadata = policy.get("competition_metadata", {})
    names = (
        {
            competition_id: str(value.get("name_zh", competition_id))
            for competition_id, value in metadata.items()
            if isinstance(value, dict)
        }
        if isinstance(metadata, dict)
        else {}
    )
    selected = select_representative_competitions(
        {row["player_id"]: int(row["exit_season_start"]) for row in outcomes},
        appearances,
        rules,
        threshold=threshold,
        observation_season_count=study.observation_season_count,
    )
    return [
        dict(
            outcome,
            representative_leagues="、".join(
                names.get(value, value) for value in selected[outcome["player_id"]]
            ),
        )
        for outcome in outcomes
    ]


def _cohort_label(study: AcademyStudyConfig) -> str:
    start = f"{study.exit_season_start}–{str(study.exit_season_start + 1)[-2:]}"
    end = f"{study.exit_season_end}–{str(study.exit_season_end + 1)[-2:]}"
    return start if start == end else f"{start} 至 {end}"


_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="从竞技高度与职业持续性两面，观察最高青年队球员进入成年足球后的发展。">
  <title>青训之后｜青训产出的价值与代价</title>
  <style>
    :root{--ink:#101923;--muted:#596675;--paper:#f3efe7;--surface:#fffdf8;--navy:#0b3157;--blue:#1860a0;--wine:#8f1736;--gold:#d59a2d;--line:#d8d0c3}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.6}a{color:inherit}
    .shell{max-width:1180px;margin:auto;padding:0 24px 88px}.mast{display:flex;justify-content:space-between;align-items:center;padding:22px 0;border-bottom:1px solid var(--line);font-size:12px;letter-spacing:.12em;text-transform:uppercase}.mast b{color:var(--wine)}
    .hero{padding:72px 0 50px;display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.55fr);gap:54px;align-items:end}.eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--wine);font-weight:800}.hero h1{font-family:Georgia,"Noto Serif SC",serif;font-size:clamp(50px,7.6vw,102px);line-height:.9;letter-spacing:-.045em;margin:20px 0 28px}.hero h1 span{display:block;color:var(--wine)}.dek{max-width:760px;font-size:20px;line-height:1.75;color:var(--muted);margin:0}.hero-note{border-top:4px solid var(--gold);padding-top:20px;font-family:Georgia,"Noto Serif SC",serif;font-size:21px;line-height:1.55}.hero-note small{display:block;font-family:inherit;font-size:13px;color:var(--muted);margin-top:16px}
    .chapter{padding:64px 0;border-top:1px solid var(--line)}.chapter-head{display:grid;grid-template-columns:120px minmax(0,720px);gap:24px;margin-bottom:36px}.chapter-num{color:var(--wine);font-weight:800;letter-spacing:.14em}.chapter h2{font-family:Georgia,"Noto Serif SC",serif;font-size:clamp(34px,4.2vw,56px);line-height:1.08;margin:0 0 16px}.chapter-intro{font-size:17px;color:var(--muted);margin:0;max-width:760px}
    .metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px}.metric{background:var(--surface);border:1px solid var(--line);padding:22px}.metric .num{font-family:Georgia,serif;font-size:42px;line-height:1}.metric b{display:block;font-size:14px;margin:8px 0 4px}.metric small{font-size:12px;color:var(--muted)}
    .evidence-warning{background:#fff4e0;border-left:5px solid var(--gold);padding:20px 22px;margin-top:16px;color:#604818}.evidence-kind{display:inline-block;margin-bottom:12px;padding:4px 8px;background:#ece5da;color:var(--muted);font-size:11px;font-weight:800;letter-spacing:.08em}
    .chart-layout{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(260px,.65fr);gap:18px}.chart-card{background:var(--surface);border:1px solid var(--line);padding:28px}.chart-card h3{font-family:Georgia,"Noto Serif SC",serif;font-size:26px;margin:0 0 6px}.chart-card .sub{font-size:13px;color:var(--muted);margin-bottom:24px}.hbar{display:grid;grid-template-columns:minmax(150px,250px) 1fr 72px;gap:14px;align-items:center;margin:20px 0}.hbar-label b{display:block}.hbar-label small{color:var(--muted)}.track{height:25px;background:#e9e3d9;overflow:hidden}.fill{height:100%;background:var(--blue);min-width:2px}.fill.gold{background:var(--gold)}.bar-value{text-align:right;font-variant-numeric:tabular-nums}.bar-value b{display:block}.bar-value small{color:var(--muted)}
    .level-group{padding:22px 0;border-top:1px solid var(--line)}.level-group:first-child{padding-top:0;border-top:0}.level-head{display:flex;justify-content:space-between;gap:18px;align-items:baseline}.level-head b{font-family:Georgia,"Noto Serif SC",serif;font-size:21px}.level-head small{color:var(--muted);text-align:right}.level-group .hbar{margin:12px 0}.level-group .hbar-label b{font-family:inherit;font-size:13px}
    .insight-list{display:grid;gap:1px;background:var(--line);border:1px solid var(--line)}.insight{background:var(--surface);padding:24px}.insight strong{font-family:Georgia,"Noto Serif SC",serif;font-size:22px;display:block;line-height:1.3;margin-bottom:8px}.insight p{margin:0;color:var(--muted);font-size:14px}
    .controls{display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 22px}.controls button{border:1px solid var(--line);background:white;padding:9px 14px;cursor:pointer;border-radius:20px}.controls button.active{background:var(--navy);color:white;border-color:var(--navy)}
    .method-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.definition{padding:22px;border-top:3px solid var(--navy);background:var(--surface)}.definition b{display:block;margin-bottom:8px}.definition p{font-size:13px;color:var(--muted);margin:0}.boundary{margin-top:18px;padding:26px;background:var(--navy);color:white}.boundary h3{font-family:Georgia,"Noto Serif SC",serif;font-size:26px;margin:0 0 8px}.boundary p{color:#dbe5ef;margin:0}
    .table-tools{display:flex;gap:10px;margin-bottom:16px}.table-tools input,.table-tools select{border:1px solid var(--line);background:white;padding:10px 12px;font:inherit}.table-tools input{flex:1;min-width:160px}.table-wrap{overflow:auto;max-height:560px;border:1px solid var(--line);background:var(--surface)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:12px 10px;border-bottom:1px solid var(--line);white-space:nowrap}th{position:sticky;top:0;background:#f8f4ec;color:var(--muted);z-index:1}.tag{padding:4px 8px;border-radius:12px;background:#e6eef5;color:var(--navy);font-size:11px}.tag.unknown{background:#eeeae3;color:#514d47}
    .closing{background:var(--wine);color:white;margin-top:64px;padding:48px}.closing h2{font-family:Georgia,"Noto Serif SC",serif;font-size:clamp(34px,4vw,52px);line-height:1.1;margin:0 0 18px}.closing p{font-size:18px;max-width:850px;color:#f6dfe5}.foot{margin-top:28px;color:var(--muted);font-size:12px;line-height:1.7}
    @media(max-width:850px){.hero,.chart-layout{grid-template-columns:1fr}.hero{padding-top:50px}.chapter-head{grid-template-columns:1fr;gap:8px}.metric-grid,.method-grid{grid-template-columns:1fr}.hbar{grid-template-columns:minmax(120px,190px) 1fr 60px}}
    @media(max-width:540px){.shell{padding:0 14px 60px}.hero h1{font-size:52px}.hero{gap:30px}.chapter{padding:48px 0}.chart-card{padding:22px}.hbar{grid-template-columns:1fr 58px}.hbar .track{grid-column:1/-1;grid-row:2}.bar-value{grid-column:2;grid-row:1}.closing{padding:30px 24px;margin-top:40px}.mast span:last-child{display:none}.table-tools{flex-direction:column}}
  </style>
</head>
<body><main class="shell">
  <header class="mast"><b id="study-brand">Academy Output Study</b><span id="study-range">—</span></header>
  <section class="hero">
    <div><div class="eyebrow">以 <span class="academy-name">—</span> <span class="squad-name">—</span> 为例</div><h1>顶级青训的<span>两面</span></h1><p class="dek">它的价值，来自能把少数人送到职业足球的最高处；它的残酷，在于即使已经抵达最高青年梯队，成年比赛的位置仍要从零开始、反复赢得。</p></div>
    <aside class="hero-note"><span class="evidence-kind">足球解释</span><br>青训不是通往一线队的流水线，而是一项高上限、低确定性的人才投资。<small>证据来自 <span class="exit-total">—</span> 名在 <span class="cohort-label">—</span> 最后一次进入 <span class="squad-name">—</span> 名单的球员，以及他们随后 <span class="observation-count">—</span> 个完整赛季的成年联赛记录。</small></aside>
  </section>

  <section class="chapter" id="summary">
    <div class="chapter-head"><div class="chapter-num">01 / 观点</div><div><span class="evidence-kind">足球解释</span><h2>顶级青训同时生产顶级价值，也生产职业不确定性</h2><p class="chapter-intro">评价青训不能只数有多少人留在本队，也不能把一次成年队出场叫作成功。真正值得观察的是：球员走到了多高、是否站稳，以及这种位置能否被重复获得。</p></div></div>
    <div class="metric-grid">
      <div class="metric"><span class="evidence-kind">指标结果</span><div class="num"><span id="top-established">—</span><small> / <span class="exit-total">—</span></small></div><b>在五大联赛单季站稳</b><small>顶级竞技产出的<span class="result-kind">—</span></small></div>
      <div class="metric"><span class="evidence-kind">指标结果</span><div class="num"><span id="established">—</span><small> / <span class="exit-total">—</span></small></div><b>已确认在职业联赛单季立足</b><small>一个赛季至少 <span class="primary-n">—</span> 场</small></div>
      <div class="metric"><span class="evidence-kind">指标结果</span><div class="num"><span id="sustained">—</span><small> / <span class="exit-total">—</span></small></div><b>已确认持续立足职业联赛</b><small>至少 <span class="sustained-n">—</span> 个赛季达到同一门槛</small></div>
    </div>
    <div class="evidence-warning" id="result-scope">—</div>
  </section>

  <section class="chapter" id="value">
    <div class="chapter-head"><div class="chapter-num">02 / 价值</div><div><span class="evidence-kind">足球解释</span><h2>青训价值首先体现在球员能走到多高，而不只是谁留了下来</h2><p class="chapter-intro">一名球员在其他俱乐部成为高水平职业球员，可能是母队未能内部捕获的价值，却仍然证明了青训能够向职业足球输出什么级别的人才。</p></div></div>
    <div class="chart-layout">
      <article class="chart-card"><h3>已确认站稳者的竞技层级</h3><div class="sub" id="tier-scope">—</div><div id="tier-bars"></div></article>
      <aside class="insight-list">
        <div class="insight"><strong><span id="elite-share">—</span> 的已确认站稳者达到五大联赛</strong><p id="coverage-interpretation">—</p></div>
        <div class="insight"><strong><span id="durability-share">—</span> 的已确认站稳者多赛季达标</strong><p>一次突破和持续职业位置是两件事；多赛季指标把短暂机会与稳定角色分开。</p></div>
        <div class="insight"><strong>“外部成功”不是青训失败</strong><p>本版衡量球员产出。母队一线队分钟、转会收入和成本节省需要另一套价值捕获数据。</p></div>
      </aside>
    </div>
  </section>

  <section class="chapter" id="career">
    <div class="chapter-head"><div class="chapter-num">03 / 出路</div><div><span class="evidence-kind">足球解释</span><h2>对家庭，真正的问题不只是能否成为明星，而是能否留在职业足球</h2><p class="chapter-intro">“达到多高”和“能否持续”是两个维度。我们把联赛水平分成职业联赛、较高水平职业联赛和五大联赛，再分别观察球员是否至少一个赛季、或至少 <span class="sustained-n">—</span> 个赛季达到 <span class="primary-n">—</span> 场。</p></div></div>
    <div class="chart-layout">
      <article class="chart-card"><span class="evidence-kind">指标结果</span><h3>联赛水平 × 职业持续性</h3><div class="sub">浅蓝为单季立足，金色为至少 <span class="sustained-n">—</span> 个赛季立足；所有比例均以 <span class="exit-total">—</span> 名球员为分母。</div><div id="level-matrix"></div></article>
      <article class="chart-card"><span class="evidence-kind">指标结果</span><h3>结论会随门槛改变多少？</h3><div class="sub">切换单赛季出场要求，比较单季与多年立足的<span class="result-kind">—</span>。</div><div class="controls" id="thresholds"></div><div id="threshold-bars"></div><div class="evidence-warning"><b>先读覆盖边界。</b> <span class="coverage-note"></span></div></article>
    </div>
  </section>

  <section class="chapter" id="definitions">
    <div class="chapter-head"><div class="chapter-num">04 / 含义</div><div><span class="evidence-kind">足球解释</span><h2>这组数据改变了我们如何理解“青训成功”</h2><p class="chapter-intro">同一批球员，对俱乐部、从业者和家庭意味着不同的价值与风险。一个单一的“成材率”无法容纳这些差异。</p></div></div>
    <div class="method-grid">
      <div class="definition"><b>对俱乐部：产出不等于捕获</b><p>球员在外部成为高水平职业球员仍是青训产出；一线队分钟与转会收入则衡量俱乐部最终留住了多少价值。</p></div>
      <div class="definition"><b>对球员与家庭：入选不是承诺</b><p>最高青年队代表已经非常接近职业足球，却不保证成年队角色。机会、站稳和持续需要分别赢得。</p></div>
      <div class="definition"><b>对从业者：评估一个人才组合</b><p>既看顶级球员的高度，也看稳定职业球员的宽度和持续性，而不是用一名明星或一个比例概括整个年届。</p></div>
    </div>
    <div class="boundary"><h3>研究边界</h3><p>样本是 <span class="exit-total">—</span> 名最后一次进入 <span class="academy-name">—</span> <span class="squad-name">—</span> 名单的赛季位于 <span class="cohort-label">—</span> 的球员，并观察其后 <span class="observation-count">—</span> 个完整赛季。更晚名单只用于避免把继续留队者误判为离队，不属于研究样本。结果不能代表所有进入该青训体系的儿童，也不能识别培养的因果效果。</p></div>
  </section>

  <section class="chapter" id="players">
    <div class="chapter-head"><div class="chapter-num">05 / 球员</div><div><span class="evidence-kind">指标结果</span><h2>抽象层级最终要落回真实的职业路径</h2><p class="chapter-intro">每名球员最多展示两个在达标赛季中具有代表性的真实联赛，优先显示竞技级别更高、出场更多的联赛。多个同级联赛的出场可能共同构成一个达标赛季。没有列出联赛不等于没有职业生涯，也可能只是当前数据尚未覆盖。</p></div></div>
    <div class="table-tools"><input id="player-search" type="search" placeholder="搜索球员姓名" aria-label="搜索球员姓名"><select id="status-filter" aria-label="筛选结果"><option value="all">全部结果</option><option value="reached">已确认站稳</option><option value="not_reached">完整观察下未达标</option><option value="unknown">尚无法判断</option></select></div>
    <div class="table-wrap" role="region" tabindex="0" aria-label="可横向滚动的球员职业结果表"><table><thead><tr><th>球员</th><th>离开年届</th><th>达标赛季涉及的代表联赛</th><th>单季立足</th><th>多年立足</th><th>数据状态</th></tr></thead><tbody id="player-rows"></tbody></table></div>
  </section>

  <section class="closing"><span class="evidence-kind">足球解释</span><h2>顶级青训的两面，并不互相矛盾。</h2><p>正因为极少数球员能够走到职业足球的最高处，青训拥有巨大的竞技价值；也正因为这样的高度稀缺，即使对最高青年梯队的球员而言，稳定职业生涯仍然不是体系自动交付的结果。</p></section>
  <p class="foot"><span class="evidence-kind">数据事实</span><br>数据范围：<a id="roster-source" href="#">名单来源</a>记录的 <span class="academy-name">—</span> <span class="squad-name">—</span> 名单；最终名单季 <span class="cohort-label">—</span>；随后 <span class="observation-count">—</span> 个完整赛季。成人履历来自<a id="adult-source" href="#">成年履历来源</a>。<span class="coverage-note"></span> 页面不把缺失值转换为失败。研究类型：描述性青训产出分析，不作因果归因。</p>
</main>
<script>(()=>{const D=__REPORT_DATA__;
const $=s=>document.querySelector(s);const pct=x=>`${(100*x).toFixed(1)}%`;const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const statusLabel=s=>({reached:'已确认',not_reached:'完整观察下未达标',unknown:'尚无法判断'}[s]||s);
document.title=`${D.study.academyName}之后｜青训产出的价值与代价`;$('#study-brand').textContent=`${D.study.academyName} / Academy Output Study`;$('#study-range').textContent=`${D.study.cohortLabel} · ${D.study.observationSeasons}赛季观察窗`;document.querySelectorAll('.academy-name').forEach(x=>x.textContent=D.study.academyName);document.querySelectorAll('.squad-name').forEach(x=>x.textContent=D.study.squadName);document.querySelectorAll('.cohort-label').forEach(x=>x.textContent=D.study.cohortLabel);document.querySelectorAll('.observation-count').forEach(x=>x.textContent=D.study.observationSeasons);document.querySelectorAll('.sustained-n').forEach(x=>x.textContent=D.study.sustainedSeasons);document.querySelectorAll('.exit-total').forEach(x=>x.textContent=D.exitPlayers);document.querySelectorAll('.primary-n').forEach(x=>x.textContent=D.primaryThreshold);document.querySelectorAll('.coverage-note').forEach(x=>x.textContent=D.study.coverageNote);$('#roster-source').href=D.study.rosterSourceUrl;$('#adult-source').href=D.study.adultSourceUrl;$('#established').textContent=D.establishedCount;$('#sustained').textContent=D.sustainedCount;
document.querySelectorAll('.result-kind').forEach(x=>x.textContent=D.coverageComplete?'完整比例':'保守下界');$('#result-scope').textContent=D.coverageComplete?'所有研究对象的声明范围均已完整检查，未达标者可以与缺失数据区分。':'页面只报告现有数据至少能够确认的人数；未知结果不是失败，已观察到的正例仍然成立。';
$('#tier-scope').textContent=D.coverageComplete?'以全部研究对象为分母的完整比例；分类互斥，按最高达标层级计。':'以全部研究对象为分母的保守下界；分类互斥，按最高达标层级计。';$('#coverage-interpretation').textContent=D.coverageComplete?'这显示了已确认职业产出的竞技上限；描述性结果不能单独识别青训的培养偏好或因果贡献。':'这显示了已观察到产出的上限，但当前数据更偏向覆盖高水平联赛，不能据此推断培养偏好。';
const bigFive=D.levelMatrix.find(x=>x.id==='big-five')||{established:0};$('#top-established').textContent=bigFive.established;$('#elite-share').textContent=pct(D.establishedCount?bigFive.established/D.establishedCount:0);$('#durability-share').textContent=pct(D.establishedCount?D.sustainedCount/D.establishedCount:0);
const makeBar=(label,detail,count,total,color='')=>`<div class="hbar"><div class="hbar-label"><b>${esc(label)}</b><small>${esc(detail)}</small></div><div class="track"><div class="fill ${color}" style="width:${100*count/total}%"></div></div><div class="bar-value"><b>${count}/${total}</b><small>${pct(count/total)}</small></div></div>`;
$('#tier-bars').innerHTML=D.tierBreakdown.map((r,i)=>makeBar(r.label,`最高达标层级 · 已确认者中 ${pct(r.shareOfConfirmed)}`,r.count,D.exitPlayers,i?'gold':'')).join('');
$('#level-matrix').innerHTML=D.levelMatrix.map(r=>`<div class="level-group"><div class="level-head"><b>${esc(r.label)}</b><small>${esc(r.detail)}</small></div>${makeBar('单季立足',`至少一个赛季达到 ${D.primaryThreshold} 场`,r.established,D.exitPlayers)}${makeBar('多年立足',`至少 ${D.study.sustainedSeasons} 个赛季达到 ${D.primaryThreshold} 场`,r.sustained,D.exitPlayers,'gold')}</div>`).join('');
const controls=$('#thresholds');let active=D.primaryThreshold;function renderThreshold(){controls.innerHTML=D.overall.map(r=>`<button class="${r.threshold===active?'active':''}" data-n="${r.threshold}">≥ ${r.threshold} 场</button>`).join('');controls.querySelectorAll('button').forEach(b=>b.onclick=()=>{active=+b.dataset.n;renderThreshold()});const row=D.overall.find(r=>r.threshold===active);$('#threshold-bars').innerHTML=makeBar('单赛季站稳','至少一个赛季达到阈值',row.established,row.total)+makeBar('多赛季站稳',`至少 ${D.study.sustainedSeasons} 个赛季达到阈值`,row.sustained,row.total,'gold')}
renderThreshold();
function renderPlayers(){const query=$('#player-search').value.trim().toLocaleLowerCase();const status=$('#status-filter').value;const rows=D.players.filter(r=>(!query||r.player_name.toLocaleLowerCase().includes(query))&&(status==='all'||r.status===status));$('#player-rows').innerHTML=rows.map(r=>`<tr><td><b>${esc(r.player_name)}</b></td><td>${r.exit_season_start}</td><td>${esc(r.representative_leagues||'尚无已确认达标联赛')}</td><td><span class="tag ${r.status==='reached'?'':'unknown'}">${esc(statusLabel(r.status))}</span></td><td><span class="tag ${r.sustained_status==='reached'?'':'unknown'}">${esc(statusLabel(r.sustained_status))}</span></td><td>${r.coverage_complete==='True'?'覆盖完整':'覆盖不完整'}</td></tr>`).join('')}
$('#player-search').addEventListener('input',renderPlayers);$('#status-filter').addEventListener('change',renderPlayers);renderPlayers();})();
</script></body></html>"""
