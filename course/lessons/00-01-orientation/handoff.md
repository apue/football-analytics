---
lesson_id: 00-01-orientation
status: in_progress
checkpoint_id: CP-004
current_step: 已定义快速转换代理，并用 360 审计四个进球的最终序列
next_action: 与学习者解读 Modrić 回合，并选择非进球快速回合做空间对照
updated_at: 2026-07-30T18:53:44+08:00
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
- 已查证行业没有统一的快速转换数值定义，并记录 StatsBomb、Opta 与 Wyscout 口径。
- 已把 StatsBomb possession 进一步分为同队连续控制的 control spell。
- 已可视化进入用时/推进速度、360 防守恢复代理和 5/10/15 秒敏感性。
- 已用最终 control spell 重新审计四球，并绘制 Modrić 进球前后的 360 快照。

## 当前工作

- Barcelona 有44个进入控球，25个到达禁区、8个形成射门、产生1.101 xG。
- Real Madrid 有34个进入控球，16个到达禁区、9个形成射门、产生1.500 xG。
- StatsBomb 只标记两个 `From Counter`，均属于 Barcelona 且没有形成射门。
- 开放比赛夺回后从三区外进入的 control spell 有50个；10秒窗内有24个。
- 四球中只有 Modrić 的最终 spell 是开放比赛重新夺回后12秒内进球。
- Modrić 在 `x=106.3` 高位 Ball Recovery 后3.342秒射门；360 两帧均只观察到
  7名 Barcelona 防守者，其中3名位于球门侧。
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
- 快速转换没有行业统一阈值；并列展示供应商 `From Counter` 与连续时间/速度代理。
- control spell 是分析代理，不覆盖所有足球意义上的控制权判断。
- “防守未落位”不作为直接标签；360 只展示 visible_area 内的防守恢复代理。
- 阈值先于进球对照确定，并展示5/10/15秒敏感性，避免用进球反向调参。

## 检查

- events：4,213 条，event ID 无重复。
- 进入事件：117 条，ID 唯一且全部满足 `start_x < 80 <= end_x`。
- 进入控球：78个 possession ID 唯一；后续41个到达禁区、17个形成射门。
- Notebook 已使用分析依赖从干净 kernel 自上而下执行成功。
- 共有36个 cells、8张输出图、0个存储错误。
- 已视觉检查转换散点图、进球时间图和 Modrić 360 对照图。
- `scripts/validate_course.py` 在当前仓库中不存在；旧 AGENTS 命令无法执行，
  已改为直接检查 lesson ID、handoff frontmatter 与 checkpoint 字段。

## 开放问题

- 主比较应展示所有进入，还是把 Regular Play 与定位球/界外球来源分开？
- 两个在12秒内形成射门但没有进球的快速进入回合，与 Modrić 高位夺回有何差异？
- 球门侧防守人数、最近防守者距离和阵型跨度中，哪种代理最符合视频读法？
- Modrić 回合应被称为高位夺回后的快速进攻，还是宽泛的快速转换？
