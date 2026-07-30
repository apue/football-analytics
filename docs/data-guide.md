# 数据指南

## 上游数据

项目使用 [Hudl StatsBomb Open Data](https://github.com/hudl/open-data)。
上游仓库通常包含：

- `data/competitions.json`：可用赛事和赛季
- `matches/`：赛事赛季下的比赛列表
- `events/`：逐场事件
- `lineups/`：阵容信息
- `three-sixty/`：部分比赛的事件瞬间周边球员位置

具体字段和可用范围以上游当前仓库为准。

## 本地位置

默认路径：

```text
data/external/statsbomb-open-data/
```

也可以设置环境变量：

```bash
export STATSBOMB_OPEN_DATA=/absolute/path/to/open-data
```

Python 代码通过 `football_analytics.get_open_data_root()` 取得路径，避免在
Notebook 中散布机器相关的绝对路径。

## 同步与溯源

首次克隆或后续更新：

```bash
./scripts/sync_open_data.sh
```

脚本使用 shallow partial clone 和 sparse checkout，初始取得赛事与全部比赛
元数据，但不下载大型 events、lineups 和 three-sixty 文件。元数据会构建为本地
SQLite 目录：

```text
data/processed/open_data_catalog.sqlite
```

该文件可以从上游 JSON 重建，不进入 Git。第一次查询会创建目录；最近一次成功
检查超过七天时，查询命令会尝试 fast-forward 上游。有变化时原子重建，无变化
时只更新检查时间；网络失败时保留旧目录并报告其状态。

## 查找与选择比赛

先把人类名称解析为稳定的上游 ID：

```bash
uv run catalog resolve competition "西甲"
uv run catalog resolve team "巴萨"
uv run catalog resolve manager "Guadiola"
```

规范名称和配置在 `config/open_data_aliases.json` 中的别名可以直接解析。重音和
大小写会规范化；错拼或多个匹配只返回候选，必须确认后才能用于比赛查询。修改
别名配置后运行 `uv run catalog refresh` 重建本地目录。

常见查询使用结构化命令：

```bash
uv run catalog seasons --competition-id 11 --team-id 220 --limit 5

uv run catalog matches \
  --competition-id 11 \
  --season-id 90 \
  --team-id 220 \
  --has-360
```

赛季按实际 `last_match_date` 从新到旧排列，不能使用不具备时间语义的 season ID
或赛季名称字符串判断最新。结果中的 `available_match_count` 只表示上游开放库
包含的比赛，不自动表示完整赛季。

确认范围后按需下载：

```bash
uv run catalog fetch --match-id 3773497 --match-id 3773526
```

`fetch` 不会隐式更新数据源，并会确认目录与上游 checkout 指向同一 commit。

长尾筛选可以查询以下稳定只读视图：

- `catalog_competition_seasons`
- `catalog_team_seasons`
- `catalog_matches`
- `catalog_match_managers`

例如：

```bash
uv run catalog sql \
  "SELECT * FROM catalog_team_seasons
   WHERE competition_id = 11 AND team_id = 220
   ORDER BY last_match_date DESC LIMIT 1"
```

接口只允许一条 `SELECT` 或 `WITH` 查询，数据库以只读模式打开。查看同步状态或
强制检查上游：

```bash
uv run catalog status
uv run catalog refresh
```

查看用于某次分析的数据版本：

```bash
git -C data/external/statsbomb-open-data rev-parse HEAD
```

已完成 lesson 的 `findings.md` 应记录该 commit。更新上游数据后，如果指标发生
变化，应重新执行数据检查和 Notebook。目录查询负责选择样本，不负责定义“表现”
或其他足球指标；研究问题和比较基准仍在 lesson 中确定。

## 不可变原则

- 不修改 `data/external/` 中的上游文件。
- 清洗结果写入 `data/processed/`，并保证可由代码重新生成。
- 小型测试 fixture 可以进入 `tests/fixtures/`，但必须注明来源并最小化。
- 不把完整上游数据复制进 Notebook、报告或 Git 历史。

## 归属与许可

公开输出必须遵守上游 README 中的数据使用和归属要求。发布图表或报告时注明
数据来自 StatsBomb，并按其要求使用标识。本项目不是上游数据的再分发渠道。
