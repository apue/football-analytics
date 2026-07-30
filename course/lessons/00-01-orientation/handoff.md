---
lesson_id: 00-01-orientation
status: in_progress
checkpoint_id: CP-003
current_step: 已比较进入三区的控球在禁区、射门和 xG 方面的结果
next_action: 与学习者解读 possession 和比分状态图，并选择代表性序列回看
updated_at: 2026-07-30T16:43:30+08:00
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

## 当前工作

- Barcelona 有44个进入控球，25个到达禁区、8个形成射门、产生1.101 xG。
- Real Madrid 有34个进入控球，16个到达禁区、9个形成射门、产生1.500 xG。
- 新增结果图已经生成，正在等待学习者解释并选择代表性 possession 回看。
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

## 检查

- events：4,213 条，event ID 无重复。
- 进入事件：117 条，ID 唯一且全部满足 `start_x < 80 <= end_x`。
- 进入控球：78个 possession ID 唯一；后续41个到达禁区、17个形成射门。
- Notebook 已使用分析依赖从干净 kernel 自上而下执行成功。
- 已视觉检查五张输出图，并修正两张新增比例图的单位标签。

## 开放问题

- 主比较应展示所有进入，还是把 Regular Play 与定位球/界外球来源分开？
- 哪些具体 possession 最能解释 Barcelona 的数量优势与 Real Madrid 的结果优势？
- 比分状态差异是比赛过程描述，还是需要视频与更多比赛验证的战术假设？
- 何时引入 360 才能回答普通 events 无法回答的空间问题？
