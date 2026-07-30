# 检查

## 当前数据范围

- 上游 commit：`b0bc9f22dd77c206ddedc1d742893b3bbe64baec`
- competition ID：`11`
- season ID：`90`
- match ID：`3773585`

## 数据完整性

- [x] competitions 与 matches 元数据能够定位所选比赛。
- [x] events、lineups 和 three-sixty 文件均已下载。
- [x] 两支球队都存在 lineup 记录。
- [x] event ID 在本场比赛内唯一。
- [x] 所有 360 `event_uuid` 都能关联到一个 event。
- [ ] 检查核心字段缺失及其含义。
- [ ] 检查坐标范围和进攻方向。

## 当前记录数

| 对象 | 记录数 | 当前检查 |
| --- | ---: | --- |
| lineup 球队 | 2 | Barcelona 23 名球员；Real Madrid 20 名球员 |
| event | 4,213 | 4,213 个唯一 event ID；26 种事件类型 |
| 360 frame | 3,858 | 3,858 个唯一 event_uuid，全部有 visible_area |

这些计数是源数据事实，不表示比赛表现或数据覆盖了比赛现实的全部方面。

## 进攻三区进入分析

- [x] 将一次进入定义为 `start_x < 80 <= end_x`。
- [x] Pass 只保留没有 `outcome` 的成功传球。
- [x] Carry 表示持球推进，不将 Dribble 当作持续移动。
- [x] 保留 `play_pattern` 和 `pass_type`，没有静默排除界外球或定位球来源。
- [x] 117 个进入事件 ID 唯一，且全部满足定义边界。

| 球队 | Pass | Carry | 合计 |
| --- | ---: | ---: | ---: |
| Barcelona | 40 | 23 | 63 |
| Real Madrid | 34 | 20 | 54 |

## 进入后的 possession 结果

- [x] 每次 possession 只保留第一次成功进入进攻三区。
- [x] 78 个进入三区的 possession ID 唯一。
- [x] 禁区到达检查同队后续事件起点及成功 Pass/Carry 终点。
- [x] 比分状态使用第一次进入发生前的比分。
- [x] 四个进球均已审计；三个来自定义内的进入控球，点球不要求此前成功进入。

| 球队 | 进入控球 | 到达禁区 | 形成射门 | 后续 xG | 后续进球 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Barcelona | 44 | 25 | 8 | 1.101 | 1 |
| Real Madrid | 34 | 16 | 9 | 1.500 | 2 |

## 四个进球的事件链

- [x] 四个 Goal Shot 的 event index、possession、play pattern 和 xG 已核对。
- [x] Valverde：`From Keeper`，约60秒 possession，Benzema 直塞助攻，单刀。
- [x] Fati：`From Free Kick`，Messi 直塞 Alba，Alba 低平球助攻，一脚完成。
- [x] Ramos：Kroos 高球任意球后，Lenglet/Ramos 的两个 foul 事件成对关联且
  均标记 `penalty=True`。
- [x] Modrić：`From Goal Kick`，长球未成功；Rodrygo 高位 Ball Recovery 后助攻，
  Modrić 完成 Dribble 后射门。
- [x] 两个 `From Counter` possession 均未产生本场进球；不自定义第二套反击标签。

| 进球 | possession 来源 | 直接得分链 | xG |
| --- | --- | --- | ---: |
| Valverde 5' | From Keeper | Benzema through ball → 单刀 | 0.312 |
| Fati 8' | From Free Kick | Messi through ball → Alba 低平球 → 一脚射门 | 0.396 |
| Ramos 63' | 任意球后形成点球 | Kroos 高球 → Lenglet foul → 点球 | 0.784 |
| Modrić 90' | From Goal Kick | Rodrygo 高位回收 → Modrić 过人 → 射门 | 0.294 |

## 后续验证

- [x] Notebook 从干净 kernel 自上而下执行。
- [x] 解释 Pass 与 Carry 的嵌套起终点字段和分析单位。
- [x] 解释进入事件与进入三区 possession 的分析单位差异。
- [x] 对球队结果率和比分状态图完成视觉检查。
- [x] 解释 event、360 frame 和 visible_area 的差异。
- [x] 对四球事件链图完成视觉检查。
- [x] 将当前图表结果按证据阶梯分类。
- [ ] 决定主结果展示全部 play pattern，还是单独展示 Regular Play。
