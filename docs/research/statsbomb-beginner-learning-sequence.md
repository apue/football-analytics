# StatsBomb 开放数据的常见入门顺序

## 结论

一手教学材料并不把“认识四类文件并画出它们的关系”当作主要学习成果，也不把
“随机取一脚传球并叠加 360”作为标准的第一项分析。更常见的顺序是：

1. 先提出一个范围很小、可以由普通 event data 回答的足球问题。
2. 从 competition、match 逐层取得一场比赛的 events。
3. 查看字段，把坐标等嵌套值整理成可筛选的列。
4. 筛选一种或几种事件，做简单计数或汇总。
5. 先用表格确认结果，再画普通图和球场图。
6. 掌握 event data 后，再为一个确实需要场上空间背景的问题引入 360。

因此，“画一脚传球”可以作为几分钟的坐标和绘图练习，但它本身不是很好的课程
问题；同时叠加 360 会一次引入事件关联、可见区域、可见球员和证据缺口，更适合
普通事件分析之后，而不是第一项任务。

## 一手材料中的实际顺序

### Hudl Statsbomb 的初学者 Python webinar

Hudl 把该 webinar 明确描述为面向完全初学者，覆盖工作区设置、载入数据、第一行
代码和第一次分析；文章列出的顺序是安装包、导入数据、操作数据、Matplotlib
可视化、球场可视化（[官方说明](https://www.hudl.com/blog/using-hudl-statsbomb-free-data-in-python)）。

官方提供的
[`python_webinar.ipynb`](https://drive.google.com/file/d/12DbjowXTq2Ua9TKyOKDtbd--58EBb9qD/view?usp=drive_link)
实际上按下面的顺序展开：

- 取得 competitions；
- 用 competition ID 和 season ID 取得 matches；
- 按球队筛选比赛并选择最近一场；
- 取得该场 events，查看前几行和字段；
- 拆出事件起点、传球终点和带球终点坐标；
- 回答“哪些球员最常把球推进到进攻三区”：
  - 筛选进入进攻三区的成功传球和带球；
  - 按球员计数并合并结果；
  - 先画条形图，再把某名球员的这些动作画在球场上；
- 第二个问题才比较两名球员的触球位置，bonus 才进入整届赛事的射门和 xG。

这个入门 Notebook 没有使用 lineups 或 360。它的主线是
“小问题 → 事件筛选 → 汇总 → 可视化”，而不是先完整讲解数据模型。

### statsbombpy 与 mplsoccer

`statsbombpy` 的官方 README 也沿着 competitions、matches、lineups、events 的
可调用接口逐项给出表格示例；event 的默认返回值是一张包含各类事件及其属性的
DataFrame（[statsbombpy README](https://github.com/statsbomb/statsbombpy)）。
这更像数据访问参考，但与 webinar 的逐层取得比赛再分析 events 的顺序一致。

`mplsoccer` 的官方 StatsBomb 示例先分别展示 competition、match、lineup 和 event
DataFrame 的结构，360 则作为独立部分读取为 frames 与 visible-area 数据
（[StatsBomb 数据示例](https://mplsoccer.readthedocs.io/en/latest/gallery/statsbomb/plot_statsbomb_data.html)）。
其基础球场文档先教画球场；StatsBomb 坐标范围为 `x=0..120`，`y=80..0`
（[Pitch Types](https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_setup/plot_pitch_types.html)）。

### 官方 360 入门材料

StatsBomb 发布首批开放 360 数据时，明确建议不熟悉 StatsBomb 数据的学习者先完成
普通数据指南，并说明 360 案例面向更有经验的使用者。案例不是随机展示一个 frame，
而是提出“传中发生时禁区里有多少进攻与防守球员”：

1. 分别取得 360 frames 和标准 events；
2. 用 `event_uuid` 与 event `id` 连接；
3. 筛选传中并计算禁区内攻守人数；
4. 排序找出值得观察的传中；
5. 最后才画其中一个 360 frame。

详见[官方 Euro 2020 360 教程](https://blogarchive.statsbomb.com/news/statsbomb-announce-the-release-of-free-statsbomb-360-data-euro-2020-available-now/)。
这说明 360 在教学中承担的是“给已有 event 问题增加空间语境”，不是认识数据的
第一步。`mplsoccer` 的独立 360 示例虽然只需读取 frame、区分队友/对手并绘制
`visible_area`，但它是绘图库的功能示例，不等于完整的初学分析流程
（[mplsoccer 360 示例](https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_plots/plot_sb360_frame.html)）。

## 对本课的具体建议

第一课不必把 match、lineup、event、360 四者都设成同等重要的学习对象。推荐把
主任务改成一个只依赖标准 events 的小问题，例如：

> Barcelona 和 Real Madrid 各通过多少次成功传球或带球把球推进到进攻三区，
> 哪些球员完成得最多，这些动作从哪里开始？

学习顺序可以是：

1. 用已选比赛确认 match 背景，只解释取得 event 文件所需的 ID。
2. 读取 events，查看事件类型、通用字段和 Pass/Carry 特有字段。
3. 先定义“进入进攻三区”及“成功传球”，再筛选和计数。
4. 用一张小表回答问题，再画所选球队或球员的推进动作。
5. 讨论单场计数、比赛状态、事件定义和缺少无球信息等限制。

Lineups 只在球员身份、出场时间或换人边界影响当前问题时引入。360 可以作为后续
扩展：先提出“这脚推进为什么在空间上值得看”或“传球时攻守人数/传球路线是什么”
之类的问题，再连接并绘制相应 frame。

这样保留了“画传球很容易、能快速获得反馈”的优点，但图是回答足球问题的结果，
而不是为了展示数据结构而画。
