# 00-02 一场比赛如何成为事件表

Status: completed

## 足球问题

在 Barcelona 1–3 Real Madrid（match ID `3773585`）中，两队记录到的传球距离与
空间分布、射门时机与 xG，以及首次换人前的传球连接有何不同；事件数据又能在
多大程度上描述 Messi 的接球和持球行为位置？

本课只做单场比赛的描述性比较，不据此评价赛季风格，也不从事件分布推断战术原因。

## 为什么值得研究

这组图把“事件表是一张稀疏宽表”的理解变成可检查的足球输出，同时迫使我们明确
每张图使用哪些事件、怎样处理结构性缺失，以及 event data 与连续追踪数据的边界。

## 学习目标

- 从嵌套 event JSON 构造 Pass、Shot、Substitution 与球员行为分析表。
- 区分结构性缺失与真正的数据质量问题，例如空 `pass.outcome` 表示成功传球。
- 为跨队比较固定筛选条件、时间窗口、分箱和视觉尺度。
- 复现原书 Chapter 3 的 `mplsoccer` KDE 与 hexbin 热图方法。
- 正确描述事件数据支持的 Messi 接球/持球位置，而不误称连续移动轨迹。

## 范围

- 分析单位：单次 Pass、Shot、Ball Receipt 或记录到的持球行为；passing network
  的边是球员对之间的成功传球。
- 包含的赛事、赛季、比赛或事件：La Liga 2020/2021，match ID `3773585` 的
  events 与 lineups。
- 排除项：赛季风格、因果战术解释、连续跑动距离、无球移动和 360 中无法识别身份的
  freeze-frame 球员。
- 比较基准：同场对手；相同事件口径、分箱和坐标尺度；network 使用开场至全场
  第一次换人之前的共同窗口。
- 结果：六组可视化及其样本量、计算口径、局限与下一步可信度检查。

## 定义与假设

| 术语 | 操作性定义 | 考虑过的替代定义 |
| --- | --- | --- |
| 成功传球 | `type.name == "Pass"` 且 `pass.outcome` 缺失 | 把缺失当未知；这与 StatsBomb schema 语义冲突 |
| 传球距离样本 | 成功且 `play_pattern.name == "Regular Play"` 的 Pass | 所有传球；会混入界外球、角球等重启方式 |
| 传球热区 | 所有具有起点坐标的 Pass 的事件密度 | 只画成功传球；回答的是不同问题 |
| 累计射门 | 按事件精确时间排序的 Shot 累计次数 | 只用整数分钟；会丢失同一分钟内的顺序 |
| 传球网络窗口 | 从开球到第一条 Substitution 事件之前 | 各队分别到自己的第一次换人；比较窗口不一致 |
| Messi 位置图 | Ball Receipt 与 Pass/Carry/Dribble/Shot 起点 | “移动热区”；事件数据没有连续轨迹，不能这样命名 |

## 所需数据

- 文件：
  - `data/external/statsbomb-open-data/data/events/3773585.json`
  - `data/external/statsbomb-open-data/data/lineups/3773585.json`
- 字段：`index`、`period`、`minute`、`second`、`timestamp`、`type`、`team`、
  `player`、`location`、`play_pattern`、`pass.*`、`shot.*`、`substitution.*`。
- 上游 open-data commit：`b0bc9f22dd77c206ddedc1d742893b3bbe64baec`
- 原书 companion notebook commit：`b146ad11248ceee9a04d1212e172a6728b579a61`

## 预期产物

- `visualization-lab.ipynb`：六组图、事件类型概览、显式筛选和数据质量断言；
  本轮经讨论后用它作为 00-02 的主 Notebook，不再另建 `analysis.ipynb`。
- `findings.md`：结果、证据层级、敏感性与限制。
- `checks.md`：数据、指标和可复现性检查。
- `exercises.md`：定义敏感性与迁移练习。

## 验收标准

- [x] Notebook 能从干净 kernel 自上而下执行。
- [x] 使用统一 1 米分箱比较两队成功 Regular Play 传球距离，并显示样本量。
- [x] 使用统一 0.1 xG 分箱比较全部射门，并标明点球与总 xG。
- [x] 用精确事件时间绘制 0–90 分钟累计射门阶梯图并标记进球。
- [x] 热图沿用原书 KDE/hexbin 样式，且说明 KDE 色阶不能直接比较绝对次数。
- [x] 两队 passing network 使用同一首次换人窗口和同一节点/边尺度。
- [x] Messi 图明确是接球与记录到的持球行为位置，不声称表示连续移动。
- [x] 每组输出说明问题、样本、算法、足球读法、不能证明什么和增强可信度的检查。
- [x] 学习者审阅图表口径与视觉结果，并接受本课在当前边界完成。

## 分析前预测

由学习者在看图前填写：哪队的常规比赛成功传球预计更长、哪队射门更早累积，
以及 Messi 的接球位置预计集中在哪些区域？
