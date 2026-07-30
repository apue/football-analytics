---
lesson_id: 00-01-orientation
status: in_progress
checkpoint_id: CP-005
current_step: 已区分四个进球的 possession 来源与直接得分事件链
next_action: 与学习者确认四球事实分类，再选择一个得分机制继续追问
updated_at: 2026-07-30T19:18:35+08:00
---

# 课程交接

## 已完成

- 已定义课程问题、输入、产物和验收标准。
- 学习者确认使用 Barcelona 1–3 Real Madrid（match ID `3773585`）。
- 已下载所选比赛的 events、lineups 和 three-sixty 文件。
- 已记录上游 commit、对象记录数及第一组 ID 关联检查。
- 已创建并执行 `analysis.ipynb`，得到方式/高度、球员贡献和进入路线三组图。
- 已将一次进入定义为成功 Pass 或 Carry 满足 `start_x < 80 <= end_x`。
- 已将117次进入归并为78个首次进入三区的 possession。
- 已可视化两队后续到达禁区、形成射门、产生 xG 及比分状态差异。
- 已审计四个进球；点球没有此前的成功三区进入，按定义不纳入转化样本。
- 已为四球分别核对 possession 来源、最后助攻/犯规链、射门方式和 xG。
- 已绘制四球关键事件链，并明确关键链不是完整战术过程。
- 已放弃自定义快速转换分类，直接接受 StatsBomb `From Counter` 标签。

## 当前工作

- Barcelona 有44个进入控球，25个到达禁区、8个形成射门、产生1.101 xG。
- Real Madrid 有34个进入控球，16个到达禁区、9个形成射门、产生1.500 xG。
- StatsBomb 只标记两个 `From Counter`，均属于 Barcelona 且没有形成射门。
- Valverde 是持续控球后的 Benzema 直塞单刀；Fati 是任意球来源的开放式组合。
- Ramos 点球由 Kroos 任意球后 Lenglet 对 Ramos 的成对 foul 事件产生。
- Modrić 的 possession 来源是球门球，但直接机制是 Rodrygo 高位回收后的助攻。
- 结果仍包含所有 `play_pattern`；Notebook 末尾保留 Regular Play 对照练习。

## 决定

- 以一个小型 event-data 足球问题带出数据字段，不把目录关系本身当作主要产物。
- 先使用标准 events 完成筛选、汇总和可视化；360 留到确实需要空间语境的问题。
- 首场比赛优先采用四类数据齐全、没有加时赛复杂度的样本。
- Carry 表示持球推进；Dribble 表示过人尝试，不作为进入三区的持续移动事件。
- 保留 `play_pattern` 和 `pass_type`，避免把界外球来源误当作普通传球。
- 结果比较以 possession 为单位，每次只使用第一次成功进入，避免重复进入被当成独立机会。
- 禁区到达与形成射门是并列结果；禁区外射门使二者不构成严格漏斗。
- 进球样本太少，主要比较 shot rate 与 xG per entry possession。
- `From Counter` 直接采用 StatsBomb 标签，不维护自定义反击分类。
- 进球模式必须区分 possession 来源与直接得分机制。
- 点球事件可以确认 foul 双方、位置和 penalty 标签，不能确认接触方式或判罚正确性。

## 检查

- events：4,213 条，event ID 无重复。
- 进入事件：117 条，ID 唯一且全部满足 `start_x < 80 <= end_x`。
- 进入控球：78个 possession ID 唯一；后续41个到达禁区、17个形成射门。
- Notebook 已使用分析依赖从干净 kernel 自上而下执行成功。
- Notebook 已从干净 kernel 执行：31个 cells、6张输出图、0个存储错误。
- 四球事件 ID、关键助攻和 Ramos 成对 foul 关系已有断言。
- 已视觉检查四球事件链图，确认来源 restart、助攻、回收、犯规和射门标记可读。
- `scripts/validate_course.py` 在当前仓库中不存在；旧 AGENTS 命令无法执行，
  已改为直接检查 lesson ID、handoff frontmatter 与 checkpoint 字段。

## 开放问题

- 主比较应展示所有进入，还是把 Regular Play 与定位球/界外球来源分开？
- 四球事实分类是否符合学习者对“模式”的理解？
- 下一步应比较机会质量、定位球制造，还是最后一传与射门方式？
- 在不看视频的前提下，哪条事件链最值得继续下钻？
