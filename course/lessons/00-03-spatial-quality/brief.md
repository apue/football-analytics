# 00-03 坐标、方向与 360 数据质量

Status: review

## 足球问题

在 Barcelona 1–3 Real Madrid（match ID `3773585`）中，StatsBomb events 与
360 freeze frames 能否被完整关联，并在明确的坐标、方向、可见区域和缺失边界下，
为后续研究门将出球时的“可见压力—选择—结果”提供可靠输入？

本课检查数据是否适合测量，不分析压力是否改变出球选择，也不定义 build-up 成败。

## 为什么值得研究

后续多场分析会重复使用同一数据管道。若事件与 360 错配、坐标越界、方向被错误
翻转，或者把视野外球员当成不存在，批量处理只会稳定地放大错误。

## 学习目标

- 理解 StatsBomb 的 `120 x 80` 球场坐标、统一由左向右进攻的事件表示，以及
  freeze-frame 球员可能出现线外值，不能直接套用 event 的删除规则。
- 将 event 与 360 frame 按事件 UUID 一对一关联。
- 区分没有 360 frame、画面中没有 actor、线外 freeze-frame 坐标，以及 visible
  area 之外无法观察的球员。
- 将加载、关联和验证逻辑写成 Notebook 外的可复用接口。
- 生成一份可核对的数据质量报告，而不是战术结论。

## 范围

- 分析单位：一条 event、一个与 event 关联的 360 frame，以及 frame 中一个可见球员。
- 包含的赛事、赛季、比赛或事件：La Liga 2020/2021，match ID `3773585` 的
  全部 events 和全部可用 360 frames。
- 排除项：战术压力分类、门将出球 episode、未选择路线、连续移动、因果解释、
  10 场探索集和 25 场验证集。
- 比较基准：供应商坐标边界；event UUID 集合；按球队和半场拆分的射门位置，
  用于检查两队是否都已经按进攻方向由左向右表示。
- 结果：标准化的 event–360 场景表、质量报告、方向检查图和可复用接口。

## 定义与假设

| 术语 | 操作性定义 | 考虑过的替代定义 |
| --- | --- | --- |
| event–360 匹配 | `event.id == frame.event_uuid` | 按时间或事件顺序匹配；不如稳定 ID 可靠 |
| 球场线内坐标 | `0 <= x <= 120` 且 `0 <= y <= 80` | 去掉边界点；会错误排除合法边界坐标 |
| 线外 freeze-frame 球员 | 保留并报告，不自动判为错误 | 强制裁剪或删除；会丢失界外位置等有效信息 |
| 可见球员 | `freeze_frame` 中的一条球员记录 | 场上全部球员；360 只记录该事件瞬间画面中可见球员 |
| 统一进攻方向 | StatsBomb event/360 坐标已将控球队表示为由左向右进攻 | 按球队或半场再次翻转；会破坏供应商标准化坐标 |
| 缺少 360 | event ID 不在 360 frame 集合中 | 当作数据错误；360 本来只覆盖部分事件 |

## 所需数据

- 文件：
  - `data/external/statsbomb-open-data/data/events/3773585.json`
  - `data/external/statsbomb-open-data/data/three-sixty/3773585.json`
- 字段：`id`、`index`、`period`、`minute`、`second`、`type`、`team`、`player`、
  `location`、各事件 `end_location`、`event_uuid`、`freeze_frame`、`visible_area`、
  `teammate`、`actor`、`keeper`。
- 上游 commit：`b0bc9f22dd77c206ddedc1d742893b3bbe64baec`

## 预期产物

- `analysis.ipynb`：教程式展示单场加载、关联、质量报告和方向检查。
- `src/football_analytics/spatial.py`：可复用加载、关联和验证接口。
- `docs/data-guide.md`：公开接口、坐标契约与批量调用示例。
- `findings.md`：数据事实、指标结果和后续测量边界。
- `checks.md`：单元测试、Notebook 与仓库检查。
- `exercises.md`：解释、迁移和定义质疑练习。

## 验收标准

- [x] `load_match_spatial_data(match_id)` 能读取并关联单场 events 与 360。
- [x] 场景表保留 `match_id` 和稳定 event UUID，可安全拼接多场结果。
- [x] 质量报告检查重复 ID、无法关联的 frame、球场边界、visible area 点对和
  freeze-frame 标记。
- [x] 方向检查按球队和半场展示射门起点，不对第二半场再次翻转坐标。
- [x] Notebook 明确解释结构性 360 缺失和 visible area 的观察边界。
- [x] 公开函数具有输入、输出、约定和异常说明的 docstring。
- [x] `docs/data-guide.md` 展示单场和多场复用模式。
- [x] 新增确定性逻辑有合成 fixture 单元测试。
- [x] Notebook 能从干净 kernel 自上而下执行。

## 分析前预测

本课不预测战术结果。运行前预期：360 只覆盖部分 events；能匹配的 frame 应全部
指向有效 event UUID；合法坐标应位于 `120 x 80` 边界内；两队各半场射门都应在
统一的由左向右进攻坐标中更靠近 `x=120` 的球门。
