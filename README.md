# Football Analytics Learning Lab

一个以真实足球问题为主线的公开学习项目。项目使用
[Hudl StatsBomb Open Data](https://github.com/hudl/open-data)，从事件数据理解、
比赛分析和可视化出发，逐步进入统计推断、指标设计与机器学习建模。

Coding Agent 负责实现、测试和解释代码；学习者负责问题、假设、足球解释和证据
审查。我们的目标不是让复杂模型替代足球理解，而是学习什么时候数据能够回答
问题、结论有多可靠，以及哪些部分仍需要视频或追踪数据。

## 学习路线

课程按足球问题而不是 Python 库组织：

1. 事件数据素养与证据边界
2. 单场比赛的推进、创造和终结
3. 赛季级球队与球员比较
4. 统计推断、稳定性与验证
5. xG、控球结果分类、xT 和风格建模
6. 独立研究与完整赛季报告

完整先修关系和产物定义见 [course/syllabus.md](course/syllabus.md)。

## 本地启动

需要 Git、[uv](https://docs.astral.sh/uv/) 和 Python 3.12。安装基础开发和
Notebook 环境：

```bash
uv sync --group notebook
```

进入需要 pandas 和绘图的分析课时再运行：

```bash
uv sync --group notebook --group analysis
```

同步公开数据的赛事与比赛目录：

```bash
./scripts/sync_open_data.sh
```

启动 JupyterLab：

```bash
uv run jupyter lab
```

## 数据约定

公开数据被独立克隆到：

```text
data/external/statsbomb-open-data/
```

该目录不会进入本仓库。更新时运行 `./scripts/sync_open_data.sh`，或直接执行：

```bash
git -C data/external/statsbomb-open-data pull --ff-only
```

上游仓库体积较大，因此首次同步采用 shallow partial clone 和 sparse checkout，
只下载赛事与比赛元数据，不会立刻下载大型事件文件。可用本地目录搜索比赛：

```bash
uv run catalog resolve team "巴塞罗那"
uv run catalog seasons --competition-id 11 --team-id 217
```

确认比赛后再用 `uv run catalog fetch --match-id <id>` 按需取得 events、lineups
和可用的 360；具体选择会记录在 lesson 的 `brief.md` 和 `checks.md`。完整命令和
覆盖范围约定见 [docs/data-guide.md](docs/data-guide.md)。

发布分析时应记录数据源 commit：

```bash
git -C data/external/statsbomb-open-data rev-parse HEAD
```

StatsBomb 要求公开分析注明数据来源并使用其标识。具体使用前请阅读上游仓库的
README 和许可说明。本项目不重新分发上游数据。

## 继续课程

`course/state.yaml` 指向当前课程。对应 lesson 的 `brief.md` 定义问题、范围和
验收标准，`handoff.md` 记录已经完成的内容、当前步骤和下一步。新 session 从这些
文件和现有 Git 改动继续。

## 计算资源

核心课程全部以本机 CPU 为目标，包括常规可视化、回归、树模型、聚类、xG 和
xT。只有后期可选的深度序列或大规模追踪数据实验才考虑 GPU；云端环境不会成为
完成主课程的前提。

## 证据边界

事件数据记录球上动作，但通常不能连续观察整体阵型、无球跑动和传球线路为何
没有被选择。所有分析应区分：

```text
数据事实 -> 指标结果 -> 足球解释 -> 未验证假设
```

参见 [docs/methodology.md](docs/methodology.md)。

## 许可证

本仓库的代码和课程材料采用 [MIT License](LICENSE)。Hudl StatsBomb Open
Data 不包含在该许可证中，仍适用上游仓库自己的许可与归属要求。
