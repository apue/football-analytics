# 练习

## 1. 阅读证据包

运行：

```bash
uv run match-evidence --match-id 3773585 --format markdown
```

任选一队，说明表中 Entries、Reached box、Shots 和 xG 的分析单位与分母。解释
为什么 Reached box 与 Shots 不是严格漏斗。

## 2. 从接口回到原始事件

使用 JSON 输出任选一个 `final_third_entries` 记录，根据 `event_id` 在原始 events
文件中找到它。核对 Pass/Carry 的起点、终点、结果和 `play_pattern`，说明工具箱
做了哪些标准化、没有添加哪些足球解释。

## 3. 来源标签与直接机制

不看 Notebook 的结论，分别写出四球的：

- possession 来源标签；
- 直接助攻或点球犯规链；
- event data 没有记录的一个关键机制。

比较 `From Free Kick`、`From Goal Kick` 和“直接定位球得分”为何不是同义词。

## 4. 质疑主样本

把 `entry_possessions` 按 `play_pattern` 分组，再只保留 Regular Play。运行前先
预测两队的进入次数和射门率会朝哪个方向变化；运行后记录结果，并说明它是否改变
本课结论。

## 5. 迁移到另一场比赛

使用 `catalog` 查找并下载另一场有 events 的比赛，再运行 `match-evidence`。不要
直接比较绝对数量；先提出一个包含研究对象、足球行为、结果、比较基准和场景范围
的问题，并指出需要哪些额外语境才能比较两场比赛。
