# Soccer Analytics with Machine Learning 参考索引

本索引只负责稳定导航。原书仓库保存在 `references/external/` 的忽略目录中，实际
内容、许可说明和作者归属以上游固定 commit 为准，不复制进本项目历史。

## 固定来源

- 仓库：`SoccerAnalyticsML/Soccer-Analytics-with-Machine-Learning`
- commit：`b146ad11248ceee9a04d1212e172a6728b579a61`
- 清单：`references/sources.toml`
- 默认本地目录：`references/external/soccer-analytics-ml/`

## 已确认导航

| 主题 | 上游路径 | 本课程对应内容 |
| --- | --- | --- |
| `mplsoccer` 高级可视化、KDE、hexbin | `extras/chapter-3/05-advanced-visualizations-mplsoccer.ipynb` | 00-02 传球起点热图 |
| Passing networks | `extras/chapter-3/06-passing-networks.ipynb` | 00-02 首次换人前传球网络 |
| Japan 2019 World Cup 案例热图 | `extras/chapter-3/07-case-study-japan-wwc2019.ipynb` | 00-02 KDE 参数对照 |

这张表是人工确认过的入口，不是假装完整的全书目录。发现会重复使用的新入口时，
在同一个变更中补充主题、准确路径和课程对应关系。

## 固定查询方式

```bash
uv run book-ref status
uv run book-ref search "kdeplot" --chapter 3
uv run book-ref search "passing network" --cell-type markdown
uv run book-ref show \
  extras/chapter-3/05-advanced-visualizations-mplsoccer.ipynb \
  --cell 17
```

`search` 只搜索 notebook 的 source cells 和文本文件，不搜索已存储输出。结果包含
上游相对路径、cell、cell 类型、cell 内行号和片段。`show` 不接受绝对路径或逃出
参考仓库的 `..` 路径。

## 初始化与更新

第一次使用时显式运行：

```bash
./scripts/sync_book_reference.sh
```

同步命令 checkout 清单中的准确 commit，不跟随默认分支。正常查询不会访问网络，
也不会隐式 pull。若要升级版本，应先检查上游差异，再修改 `sources.toml`、更新本
索引、重新执行受影响的课程 Notebook，并通过单独 PR 合入。

可以用环境变量覆盖默认本地目录：

```bash
export SOCCER_ANALYTICS_ML_REPO=/absolute/path/to/repository
```

## 引用约定

回答或课程实现对照原书时，至少记录：

- 固定 commit；
- 上游相对文件路径；
- notebook cell 编号或文本行号；
- 本项目采用、调整或没有采用的内容。

不要把“与原书实现一致”扩大成对分析定义或足球结论的背书。
