# 00-01 仓库、数据与证据边界

Status: review

## 足球问题

Hudl StatsBomb 开放数据实际包含什么？仅凭这些数据，哪些比赛问题可以回答，
哪些只能形成待视频或追踪数据验证的假设？

本课用一个具体问题作为入门主线：Barcelona 和 Real Madrid 怎样进入进攻三区？
一次控球首次进入后，有多大概率到达禁区、形成射门并产生 xG，这种差异是否随
比分状态改变？四个进球各自由什么事件链形成，possession 来源标签与直接得分
机制是否一致？

## 为什么从这里开始

如果不知道每种数据观察了什么，后续再准确的计算也可能产生错误的足球解释。
本课先建立数据地图和证据边界，不追求复杂图表。

## 学习目标

- 找到赛事、赛季、比赛、阵容、事件和 360 数据。
- 读取上游 README，并记录数据版本与归属要求。
- 选择一场同时具有所需数据的比赛。
- 解释 Pass、Carry、Shot 和 possession 的核心字段与分析单位。
- 定义进入进攻三区，并区分事件次数与进入三区的控球次数。
- 比较进入后到达禁区、形成射门和产生 xG 的结果。
- 区分进球 possession 的来源标签与最后直接得分事件链。
- 使用关联的 Foul Committed/Foul Won 解释点球的数据事实与证据边界。
- 使用证据阶梯评价一个足球结论。

## 分析单位

本课涉及赛事赛季、比赛、单个事件和一次 StatsBomb possession。事件级结果描述
进入方式；结果比较以每次控球第一次成功进入为单位。进球审计则以 Shot 为终点，
向前关联助攻、犯规、restart 和球权回收；不聚合球员能力或球队风格。

## 输入

- `data/competitions.json`
- 所选赛事的 match 文件
- 所选比赛的 events、lineups，以及可用时的 three-sixty 文件

## 已确认数据范围

- 赛事：La Liga 2020/2021（competition ID `11`，season ID `90`）
- 比赛：Barcelona 1–3 Real Madrid，2020-10-24（match ID `3773585`）
- 教练：Ronald Koeman、Zinédine Zidane
- 文件：
  - `data/external/statsbomb-open-data/data/matches/11/90.json`
  - `data/external/statsbomb-open-data/data/lineups/3773585.json`
  - `data/external/statsbomb-open-data/data/events/3773585.json`
  - `data/external/statsbomb-open-data/data/three-sixty/3773585.json`
- 上游 commit：`b0bc9f22dd77c206ddedc1d742893b3bbe64baec`

这场比赛同时具有 match、lineup、event 和 360 数据，且为常规 90 分钟比赛，
适合第一次建立数据地图。选择知名比赛有助于理解语境，但本课不会据此评价球队
赛季表现或推断教练战术原因。

## 产物

- `analysis.ipynb`：进入事件、possession 结果、比分状态和四球事件链的可视化分析
- `football_analytics.evidence` 与 `match-evidence`：可复用的单场比赛证据接口
- `findings.md`：数据地图、三类可回答问题、三类不可直接回答问题
- `checks.md`：路径、文件、比赛 ID、记录数和关键字段检查
- `exercises.md`：改变 play pattern 或比赛样本后复算指标

## 验收标准

- Notebook 从干净 kernel 执行。
- 记录上游 open-data commit。
- 能说明一次进入事件与一次进入三区的 possession 为什么不是同一分析单位。
- 审计四个进球是否满足此前存在成功三区进入的定义。
- 能为四球分别说明 possession 来源、直接助攻或犯规链和射门方式。
- 能说明为什么 `From Free Kick` 或 `From Goal Kick` 不等于直接定位球得分。
- 能说明 event data 对点球原因能确认到哪一步、哪些仍需视频。
- 能说明 event data 缺少哪些解释比分差异所需的空间或视频证据。
- 所有解释性结论标注证据层级。
- 不把事件数据描述为完整的比赛现实。

## 编码前讨论

选择第一场比赛时，优先考虑数据完整性和可解释性，不以知名球队为唯一标准。
