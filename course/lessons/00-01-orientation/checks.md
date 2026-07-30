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

## 后续验证

- [x] Notebook 从干净 kernel 自上而下执行。
- [x] 解释 Pass 与 Carry 的嵌套起终点字段和分析单位。
- [ ] 解释 event、360 frame 和 visible_area 的差异。
- [x] 将当前图表结果按证据阶梯分类。
- [ ] 决定主结果展示全部 play pattern，还是单独展示 Regular Play。
