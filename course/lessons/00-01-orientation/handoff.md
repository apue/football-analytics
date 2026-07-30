---
lesson_id: 00-01-orientation
status: in_progress
checkpoint_id: CP-002
current_step: 已定义并可视化两队进入进攻三区的事件
next_action: 与学习者解读三张图，并决定全部进攻与 Regular Play 的主比较口径
updated_at: 2026-07-30T16:11:51+08:00
---

# 课程交接

## 已完成

- 已定义课程问题、输入、产物和验收标准。
- 学习者确认使用 Barcelona 1–3 Real Madrid（match ID `3773585`）。
- 已下载所选比赛的 events、lineups 和 three-sixty 文件。
- 已记录上游 commit、对象记录数及第一组 ID 关联检查。
- 已创建并执行 `analysis.ipynb`，得到方式/高度、球员贡献和进入路线三组图。
- 已将一次进入定义为成功 Pass 或 Carry 满足 `start_x < 80 <= end_x`。

## 当前工作

- 当前事件表包含 117 次进入：Barcelona 63 次，Real Madrid 54 次。
- 图表已经生成，正在等待学习者判断哪些比较最有解释力。
- 结果目前包含所有 `play_pattern`；Notebook 末尾提供了 Regular Play 对照。

## 决定

- 以一个小型 event-data 足球问题带出数据字段，不把目录关系本身当作主要产物。
- 先使用标准 events 完成筛选、汇总和可视化；360 留到确实需要空间语境的问题。
- 首场比赛优先采用四类数据齐全、没有加时赛复杂度的样本。
- Carry 表示持球推进；Dribble 表示过人尝试，不作为进入三区的持续移动事件。
- 保留 `play_pattern` 和 `pass_type`，避免把界外球来源误当作普通传球。

## 检查

- events：4,213 条，event ID 无重复。
- 进入事件：117 条，ID 唯一且全部满足 `start_x < 80 <= end_x`。
- Notebook 已使用分析依赖从干净 kernel 自上而下执行成功。
- 已视觉检查三张输出图，并统一球员分面横轴、修复球场图图例裁切。

## 开放问题

- 主比较应展示所有进入，还是把 Regular Play 与定位球/界外球来源分开？
- 原始进入次数需要怎样结合控球、比分和比赛阶段，才不会被解释成稳定风格？
- 何时引入 360 才能回答普通 events 无法回答的空间问题？
