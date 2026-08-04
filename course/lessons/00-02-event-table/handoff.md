---
lesson_id: 00-02-event-table
status: completed
checkpoint_id: CP-002
current_step: 学习者已接受 00-02 在 visualization lab 边界完成
next_action: 与学习者讨论下一波问题，再据新问题初始化后续课程单元
updated_at: 2026-08-04T16:45:09+08:00
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
- 已补齐 `findings.md`、`checks.md` 与 `exercises.md`，学习者接受本课完成。

## 当前工作

- 00-02 已在协商后的 visualization lab 边界完成；事件类型概览、射门时间线与
  本实验所需字段的缺失检查均包含在主 Notebook 中。
- 不自动切换到 00-03；下一课题由学习者的新一轮问题决定。

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
- `uv lock --check`：通过。
- `uv run ruff format --check .` 与 `uv run ruff check .`：38 个文件通过。
- `uv run pytest`：19 个测试通过。
- 课程模板 Notebook 也从干净 kernel 执行成功。

## 开放问题

- 多场样本、network 阈值敏感性和连续移动需要后续课程或不同数据源验证；它们不是
  本课未完成的交付项。
- 下一步先讨论新的足球问题，再决定是否按原顺序进入 00-03。
