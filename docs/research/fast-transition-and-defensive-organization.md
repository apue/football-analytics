# 快速转换与防守未落位的可操作定义

## 结论

足球行业对概念有大致共识：快速转换始于开放比赛中的夺回球权，进攻方随即快速、
直接地向前推进，目的是利用对手尚未恢复的防守结构。但行业并没有统一的秒数、
传球数、推进距离或防守人数阈值；研究综述也明确指出，文献对转换何时开始、何时
结束仍无共识
（[系统综述](https://link.springer.com/article/10.1007/s12662-024-00951-9)）。

数据供应商因此使用各自的采集定义：

- StatsBomb 在 event data 中提供 `play_pattern = "From Counter"`，但开放数据文档
  没有公开把这个标签还原成固定秒数或空间阈值。StatsBomb 的一项公开 phase-of-play
  方法直接把该标签映射为 `Counterattack`，把对手同时标为 `Regroup`
  （[Match Phases in Practice](https://statsbomb.com/wp-content/uploads/2024/10/Match-Phases-In-Practice-Ghezzi-and-Sotudeh.pdf)）。
- Opta 把 fast break 描述为从本方半场夺回球权、快速由守转攻后产生的射门；其公开
  定义没有给出固定秒数
  （[Opta event definitions](https://www.statsperform.com/es/opta-event-definitions/)）。
- Wyscout 把 counterattack 定义为夺取对手球权后快速由守转攻，试图抓住对手脱离
  防守形态的过程；这同样是供应商定义，不是数值公式
  （[Wyscout glossary](https://dataglossary.wyscout.com/counterattack/)）。

因此，本课不应宣称发现了一个行业通用的“真正反击”。更可靠的做法是并行保留
StatsBomb 原始标签与一个透明、可调参数的数据代理，然后用代表性回合检查两者。

## 数据里现成的线索

### 普通 event data

- `play_pattern.name == "From Counter"`：StatsBomb 对反击阶段的原始分类，可作为
  供应商基线，而不是我们自定义算法的训练答案。
- `possession`、`possession_team`、时间戳和事件顺序：重建从夺回球权到进入三区、
  射门或失去球权的序列。
- `location`、Pass/Carry 的终点：计算净向前推进、进入三区用时和推进速度。
- `counterpress`：说明某个防守动作属于丢球后的反抢语境。StatsBomb 公开分析通常
  用丢球后五秒作为反抢窗口
  （[StatsBomb counter-pressing analysis](https://blogarchive.statsbomb.com/articles/soccer/how-statsbomb-data-helps-measure-counter-pressing/)）。
- `under_pressure`、Pressure 事件：可以描述持球方是否被立即施压，但不能单独证明
  整条防线已经或尚未落位。

### StatsBomb 360

360 为事件发生时提供画面内队友和对手的位置；官方将其描述为 event 周围的 contextual
freeze frame，并明确用它观察转换、反抢和防守空隙
（[360 Freeze Frame Viewer](https://blogarchive.statsbomb.com/news/statsbomb-360-freeze-frame-viewer-a-new-release-in-statsbomb-iq/)）。
开放文件中的 `freeze_frame` 可区分 `teammate`、`actor`、`keeper` 并提供
`location`；`visible_area` 则限定该帧实际可观察的区域
（[StatsBomb open-data repository](https://github.com/hudl/open-data)）。

官方已有的 360 派生量说明了适合的建模方向：防守者与接球队员的距离、球门侧
防守者人数，以及传球是否穿过或越过防线
（[StatsBomb 360 metrics](https://www.hudl.com/blog/hudl-statsbomb-launch-new-360-metrics-line-breaking-passes-and-ball-receipts-in-space)）。
但开放数据没有一个名为“defence set”的字段。

## 推荐给本课的两层口径

### 第一层：供应商基线

先列出所有 `From Counter` possession，画出其时间线，并检查是否进入三区、射门、
产生 xG 或进球。这回答的是：

> StatsBomb 的采集定义认为哪些回合属于反击？

### 第二层：透明的快速转换候选

对所有开放比赛 possession 计算连续特征，而不是先强行二分：

1. possession 的起点、终点和总时长；
2. 从起点到首次进入进攻三区的用时；
3. 该阶段的净 x 推进和净 x 推进速度；
4. 动作数、传球数和 Carry 数；
5. 是否形成射门、xG 或进球；
6. 是否与 `From Counter` 重合。

可视化时先展示这些 possession 在“进入三区用时 × 净推进距离/速度”上的分布，
再把候选阈值作为可调参考线，例如分别观察 5、10、15 秒，而不要预先把 10 秒写成
行业标准。文献的共同特征是快速、直接、利用防守失衡，研究者采用的实际操作化则
依具体研究而异；近期 WSL 研究甚至通过文献、专家和视频共同校验分类，而非只用
单一阈值
（[PLOS One operational definitions](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0318929)）。

## “防守未落位”的 360 代理

在 possession 开始和首次进入三区两个节点，若存在 360 frame，可以计算：

- 球门侧防守者人数；
- 防守方落在本方半场、本方防守三区和禁区内的人数；
- 最深与次深防守者的位置，用于近似防线深度；
- 防守球员纵向跨度和横向跨度，用于近似阵型紧凑度；
- 持球者一定半径内的防守者人数和最近防守者距离；
- 进攻方位于球前的人数，以及局部攻守人数差；
- 从 possession 起点到进入三区，上述量恢复了多少。

“未落位”不应由其中一项直接命名。更稳妥的是先展示一个 defensive-recovery
profile，例如“球门侧人数较少、阵型纵向拉长、球前进攻者较多”，再查看
`From Counter` 和最终进球是否集中在这样的区域。

这里有两个重要限制：

1. 360 是事件时刻的离散快照，不是连续 tracking data，无法看到两个事件之间的
   完整回防轨迹。
2. `freeze_frame` 只包含 `visible_area` 内的球员；看不到某名防守者不等于他不在
   场上或没有回位。因此人数与阵型指标必须同时报告可见范围和可见球员数，边界不足
   的 frame 应标记为缺失或低置信度。

## 对本场比赛的建议

最合适的下一张图不是直接画“反击次数”，而是：

1. 每个开放比赛 possession 一个点；
2. 横轴为夺回球权到首次进入三区的时间；
3. 纵轴为净向前推进速度；
4. 颜色区分球队；
5. 形状标出 `From Counter`；
6. 大小或描边标出射门和进球。

这张图先让数据呈现“快”的结构。随后只对位于快速、直接区域且有 360 coverage 的
回合绘制防守恢复指标和球场快照，最后再把双方进球叠加进去。这样可以分别检验：

- StatsBomb 标签是否捕捉到我们肉眼认为的快速转换；
- 快速推进是否真的对应较少的球门侧防守者或更松散的防守形态；
- 本场三粒开放比赛进球是否位于同一类转换环境。
