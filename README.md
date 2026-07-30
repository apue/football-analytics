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

需要 Git、[uv](https://docs.astral.sh/uv/) 和 Python 3.12。安装全部课程依赖：

```bash
uv sync --all-groups
```

同步公开数据的 Git 元数据和顶层文件：

```bash
./scripts/sync_open_data.sh
```

启动 JupyterLab：

```bash
uv run jupyter lab
```

运行项目检查：

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python scripts/validate_course.py
uv run python scripts/validate_notebook.py course/templates/analysis.ipynb
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
不会立刻下载全部比赛文件。进入具体课程时，再按所选赛事和比赛扩展 sparse
checkout；具体选择会记录在 lesson 的 `brief.md` 和 `checks.md`。

发布分析时应记录数据源 commit：

```bash
git -C data/external/statsbomb-open-data rev-parse HEAD
```

StatsBomb 要求公开分析注明数据来源并使用其标识。具体使用前请阅读上游仓库的
README 和许可说明。本项目不重新分发上游数据。

## 如何恢复课程

新的学习或 Agent session 按以下顺序读取：

1. `README.md`
2. `AGENTS.md`
3. `course/syllabus.md`
4. `course/state.yaml`
5. 当前 lesson 的 `brief.md` 与 `handoff.md`

当前状态以仓库文件和 Git 历史为准，不依赖旧聊天记录。

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
