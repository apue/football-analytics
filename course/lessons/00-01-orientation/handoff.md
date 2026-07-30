---
lesson_id: 00-01-orientation
status: in_progress
checkpoint_id: CP-001
current_step: 已确认比赛并取得 match、lineup、event 和 360 数据
next_action: 创建 analysis.ipynb，绘制数据目录地图并读取一个 event 及其 360 frame
updated_at: 2026-07-30T15:26:47+08:00
---

# 课程交接

## 已完成

- 已定义课程问题、输入、产物和验收标准。
- 学习者确认使用 Barcelona 1–3 Real Madrid（match ID `3773585`）。
- 已下载所选比赛的 events、lineups 和 three-sixty 文件。
- 已记录上游 commit、对象记录数及第一组 ID 关联检查。

## 当前工作

- 数据范围已经固定；尚未创建或执行本课 Notebook。
- 下一步从一个 event 与对应 360 frame 建立数据目录和观察边界。

## 决定

- 本课先建立数据地图，再进行足球表现分析。
- 首场比赛优先采用四类数据齐全、没有加时赛复杂度的样本。
- 单场目录与记录数是数据事实，不用于评价赛季表现或推断战术原因。

## 检查

- events：4,213 条，event ID 无重复。
- lineups：2 支球队，Barcelona 23 人、Real Madrid 20 人。
- 360：3,858 帧，全部关联到 event 且具有 visible_area。
- 尚未检查核心字段缺失、坐标方向或干净 kernel Notebook 执行。

## 开放问题

- 一个 event 对象哪些字段属于所有事件共有，哪些只属于特定事件类型？
- 360 frame 相比 event 增加了什么，又仍然缺少什么？
