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

脚本使用 shallow partial clone 和 sparse checkout，初始只取 Git 元数据和顶层
文件。这样能够检查可用赛事并保留正常的 Git 同步能力，而不在课程开始前下载
数 GB 的全部比赛数据。选定赛事后再为该 lesson 获取所需的 matches、events、
lineups 和 three-sixty 文件，并在 `checks.md` 记录选择范围。

查看用于某次分析的数据版本：

```bash
git -C data/external/statsbomb-open-data rev-parse HEAD
```

已完成 lesson 的 `findings.md` 应记录该 commit。更新上游数据后，如果指标发生
变化，应重新执行数据检查和 Notebook。

## 不可变原则

- 不修改 `data/external/` 中的上游文件。
- 清洗结果写入 `data/processed/`，并保证可由代码重新生成。
- 小型测试 fixture 可以进入 `tests/fixtures/`，但必须注明来源并最小化。
- 不把完整上游数据复制进 Notebook、报告或 Git 历史。

## 归属与许可

公开输出必须遵守上游 README 中的数据使用和归属要求。发布图表或报告时注明
数据来自 StatsBomb，并按其要求使用标识。本项目不是上游数据的再分发渠道。
