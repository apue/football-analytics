---
lesson_id: 00-02-event-table
status: paused
checkpoint_id: CP-001
current_step: visualization lab 已完成并暂停，等待学习者审阅六组图表
next_action: 学习者打开 visualization-lab.ipynb，逐图确认口径、可读性和解释边界
updated_at: 2026-08-04T16:36:02+08:00
---

# 课程交接

## 已完成

- 已从完成的 00-01 初始化 00-02，并切换全局课程指针。
- 已固定比赛、分析单位、比较口径、缺失值语义和六组图的验收标准。
- 已决定使用独立 `visualization-lab.ipynb`，不改动已完成的 00-01 Notebook。
- 已创建并执行 23-cell 的教程 Notebook，包含 7 张图，对应学习者提出的六组输出；
  传球热区同时保留 KDE 与共享尺度 hexbin。
- 已加入按事件类型的 missing-data 检查，并确认本场用于这些图的必要字段完整。
- 已逐张视觉检查传球距离、xG、累计射门、两类热图、passing network 和 Messi
  事件位置图，并修正标题、尺度、色条与累计图留白。

## 当前工作

- 本实验已经达到预定 review 边界；当前暂停等待学习者审阅。
- 00-02 的核心事件类型表、比赛时间线和完整缺失报告尚未开始，不会在本检查点自动推进。

## 决定

- 传球距离只比较成功 Regular Play Pass；热图则使用全部有坐标的 Pass 起点。
- Passing network 使用两队共同的开场至全场第一次换人之前窗口。
- Messi 图只描述接球和记录到的持球行为位置，不称为连续移动热区。
- 热图主图使用原书参数的 KDE；另加 `gridsize=25` hexbin 并固定两队共同的
  1–7 次颜色尺度，避免把每队归一化 KDE 颜色当作绝对次数。
- 1 米传球距离图使用双面板柱状直方图和各队自身百分比；0.1 xG 图使用全部射门。
- Network 节点位置取传球起点与接球终点平均，节点大小表示传出加接到次数，
  无向边表示球员对成功传球数，只显示至少 3 次的边。

## 检查

- 原始 events 共 4,213 条，展开 1,203 条 Pass、26 条 Shot、4,186 条带位置事件。
- Pass 起点/终点、成功传球 recipient、Shot xG 和坐标边界检查均为 0 个异常行。
- Network 共同窗口截止 Real Madrid 42:06 的第一次换人之前；样本为 Barcelona
  215 条、Real Madrid 289 条成功传球。
- Messi 样本为 85 条 Ball Receipt 和 164 条记录到的持球行为起点。
- `jupyter nbconvert --execute --inplace`：从干净 kernel 执行并写入输出成功。
- `scripts/validate_notebook.py visualization-lab.ipynb`：独立 clean-kernel 执行成功。
- `nbformat.validate`：schema 有效；23 cells、11 code cells、7 张存储图、0 个错误输出。
- `git diff --check`：通过。
- 已视觉检查 7 张图；最后的 hexbin 标题明确共享颜色尺度且不再遮挡球场。
- 未运行 pytest 或 ruff：本检查点没有修改 `src/` 或 Python 模块，相关不确定性由
  Notebook clean-kernel 执行和 schema/视觉检查覆盖。

## 开放问题

- 学习者需要确认：成功 Regular Play 是否是所需传球距离口径、network 的 3 次边阈值
  是否合适，以及 Messi 两面板是否比“移动热区”更符合想回答的问题。
- 学习者确认后，再决定是调整本实验，还是继续 00-02 的事件类型表、时间线与缺失报告。
