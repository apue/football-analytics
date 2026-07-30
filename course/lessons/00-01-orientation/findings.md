# 发现

## 研究问题

Hudl StatsBomb 开放数据能让我们确认 Barcelona 1–3 Real Madrid 这场比赛中的
哪些球上事实？两队如何进入进攻三区、进入后发生了什么，四个进球能回溯到哪些
直接事件链？哪些战术原因仍不能仅凭 event data 判断？

## 数据范围

- 赛事：La Liga 2020/2021（competition ID `11`，season ID `90`）。
- 比赛：Barcelona 1–3 Real Madrid，2020-10-24（match ID `3773585`）。
- 文件：competition、match、lineup、event 和可用的 three-sixty。
- 上游 commit：`b0bc9f22dd77c206ddedc1d742893b3bbe64baec`。
- 排除项：不从单场推断稳定球队风格，不用 event data 判断无球跑位、整体阵型、
  犯规接触方式或裁判判罚是否正确。

## 数据地图

| 数据 | 分析单位 | 主要连接键 | 本课能回答什么 |
| --- | --- | --- | --- |
| competitions | 赛事赛季 | `competition_id`、`season_id` | 有哪些公开赛事和赛季 |
| matches | 一场比赛 | `match_id` | 对阵、日期、比分、教练和比赛元数据 |
| lineups | 一队在一场比赛的名单 | `match_id`、`player_id` | 名单、出场时段、位置、换人和纪律记录 |
| events | 一次供应商记录的事件 | `match_id`、event `id`、`possession` | 球上动作、位置、结果和事件关联 |
| three-sixty | 一个被采样 event 的冻结帧 | `event_uuid` | 该瞬间可见球员位置和可见区域 |

lineups 不是“首发名单”：它覆盖整场比赛的球队名单，并在 position periods、
cards 等字段中记录首发、替补和位置变化。

## 结果

### 进入进攻三区

- 证据层级：指标结果。
- 定义：成功 Pass 或 Carry 满足 `start_x < 80 <= end_x`。
- 结果：共117次进入事件，归属于78个首次进入三区的 possession。Barcelona
  有44个进入控球，其中25个后续到达禁区、8个形成射门、产生1.101 xG；
  Real Madrid 有34个，其中16个到达禁区、9个形成射门、产生1.500 xG。
- 足球读法：这场比赛里 Barcelona 更频繁进入三区，Real Madrid 的进入控球形成
  射门的比例和每次进入产生的 xG 更高。
- 不能确认：单场差异不能证明稳定球队风格，也不能单独说明空间为何出现。

### 反击标签

- 证据层级：数据事实。
- 结果：StatsBomb 只把两个 possession 标记为 `From Counter`，均属于
  Barcelona，且都没有形成射门。
- 足球读法：本场四个进球不应被统一解释为供应商定义下的反击进球。
- 不能确认：本课没有另建“快速转换”分类；事件序列看起来快，不等于已满足一个
  可复现的战术反击定义。

### 四个进球

- 证据层级：数据事实与事件链分类。
- Valverde：`From Keeper` 来源，最后由 Benzema 直塞形成单刀。
- Fati：`From Free Kick` 来源，最后由 Messi 直塞、Alba 低平球助攻完成。
- Ramos：Kroos 任意球后记录 Lenglet `Foul Committed` 与 Ramos
  `Foul Won`，两者均标记 `penalty=True`，随后点球得分。
- Modrić：`From Goal Kick` 来源，最后由 Rodrygo 高位 Ball Recovery 后助攻。
- 足球读法：possession 来源标签与直接得分机制是两件事，四球没有共同的单一
  直接模式。
- 不能确认：event data 不能连续显示防守落位、进攻跑位、点球接触过程或判罚
  正确性。

## 可以与不可以直接回答的问题

可以直接回答：

1. 一场比赛记录了哪些事件类型、球员、位置、结果和关联 ID？
2. 按明确阈值，两队以 Pass 或 Carry 进入三区多少次，首次进入后产生什么结果？
3. 每个进球的 play pattern、直接助攻、射门方式以及被记录的点球犯规链是什么？

不可以直接回答：

1. 某次无球跑位或教练指令为什么让传球线路打开？
2. 防线在事件之间是否已经落位，整体压迫和空间结构如何连续变化？
3. 点球的身体接触具体如何发生，裁判判罚是否正确？

## 可复用工具箱

`football_analytics.evidence.build_match_evidence(events)` 将一场原始 events JSON
转成 JSON 可序列化的证据包，统一返回：

- 成功进入三区的 Pass/Carry 事件；
- 每个 possession 的第一次进入及后续禁区、射门、xG 和进球结果；
- StatsBomb `From Counter` possessions；
- 进球、key pass、最后 Ball Recovery 和点球犯规关联。

薄命令行用于加载本地数据和呈现：

```bash
uv run match-evidence --match-id 3773585 --format markdown
uv run match-evidence --match-id 3773585 --format json
```

它沉淀确定性的抽取与定义，不自动生成战术结论。Notebook 继续负责选择问题、
绘图、解释和证据边界。

## 敏感性与限制

- 主结果保留所有 `play_pattern`，并保留来源字段以便拆分；只看 Regular Play
  是敏感性分析，不是默认静默过滤。
- 禁区到达和形成射门是并列结果，不是严格漏斗：禁区外射门可能没有先到达禁区。
- 本课使用一个比赛样本；球队能力和稳定风格需要赛季样本及比较基准。
- 坐标方向和系统性缺失检查分别进入 00-03 和 00-02，不在本课重复展开。

## 结论

本课最重要的收获不是“哪队踢得更好”，而是建立可审查的证据接口：event data
能够定位和重建球上事实，明确计算进入与后续结果，并沿 ID 关联审计助攻和犯规；
它不能仅凭事件记录解释这些空间和机会为什么产生。后续课程可以复用同一证据包，
把精力放在新的足球问题与比较设计上。
