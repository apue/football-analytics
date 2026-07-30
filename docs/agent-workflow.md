# Agent Workflow

这份文档解释课程工作流的设计理由。必须执行的简短规则以
[`AGENTS.md`](../AGENTS.md) 为准。

## 事实来源

课程恢复只依赖三类仓库事实：

- `course/state.yaml`：当前 stage、当前 lesson 和已完成 lesson；
- 当前 lesson 的 `handoff.md`：最新状态、步骤、决定、验证和下一步；
- Git：checkpoint 历史及 checkpoint 后的未提交工作。

不维护第二套 Agent memory、journal 或 handoff。聊天记录可以补充背景，但不能
覆盖仓库中更新、更具体的状态。

## Session 恢复

新 session 读取仓库说明、当前 lesson 和 handoff，然后查看：

```bash
git status --short
git log --oneline -5
git diff
```

clean 表示从当前 `HEAD` 继续；dirty 表示有提交后的未完成工作，Agent 先解释
diff 和风险，不自动丢弃或提交。恢复不需要一套 Python 状态解析器：版本化文本与
Git 本身就是可审查接口。

## Lesson 生命周期

### Ready

`brief.md` 已明确问题、范围、分析单位、基准和验收标准。

### In progress

Agent 实现当前最小学习单元。可复用逻辑进入 `src/`，Notebook 负责编排、检查和
叙事。需要什么检查由当前分析风险决定，不由 checkpoint 机制决定。

### Paused 或 Blocked

Handoff 明确已完成和未完成的边界、未运行或失败的检查，以及恢复所需的唯一
下一步。

### Review

实际 lesson Notebook 从干净 kernel 执行；findings 区分证据层级；checks 记录
结果；学习者能够解释主要输出和限制。

### Completed

学习者确认验收后更新 handoff 和全局导航，形成 completed checkpoint，再进入
PR、CI 和明确确认后的 squash merge。

## Turn 结束判断

仓库的 `$course-turn-checkpoint` Skill 在 dirty turn 结束时处理四种情况：

| 可提交 | 学习进度前进 | 动作 |
| --- | --- | --- |
| 否 | 否 | 保留未提交 diff，说明尚未完成的边界 |
| 否 | 是 | 更新 handoff 说明进度与缺口，但不提交 |
| 是 | 否 | 必要时做最小检查，创建普通本地 commit |
| 是 | 是 | 更新 handoff，必要时做最小检查，创建 checkpoint |

是否可提交、是否需要检查、是否推进学习进度都依赖本轮上下文与 diff，不能由
文件名或固定规则替代。纯技术整理不修改学习 handoff。

Checkpoint 是有意义且可恢复的学习单元，不是验证门，也不是每个命令或 cell 的
日志。提交格式为：

```text
checkpoint(<lesson-id>): CP-NNN <step>
```

Git 已经保存 checkpoint 历史，所以 handoff 只维护最新快照。课中不 push。

`.codex/hooks.json` 只在 Stop 时运行一次 `git status --porcelain`。若发现 dirty，
它把判断任务交还给当前 Agent；不会运行测试、修改 handoff 或提交。hook 续跑后
允许结束，避免无限循环。

## 分工

编码前，学习者和 Agent 应明确足球问题、数据可见性、分析单位、分母、基准、
定义、替代定义和完成标准。

编码后，Agent 按三个层次解释：

1. 足球直觉：输出在比赛中代表什么；
2. 分析方法：数据、计算、比较与限制；
3. 代码实现：关键模块及其复用或修改方式。

每个重要输出都要说明可读结论、常见误读，以及能提高可信度的下一项检查。

## Notebook 边界

普通 checkpoint 不会因为“到了 checkpoint”而执行 lesson Notebook。分析段落在
实现时已经按问题做检查；完整 clean-kernel 执行发生在 review。仓库 CI 只对模板
做 smoke test。

## 课末交付

1. 进入 review，按课程产物和完整分支 diff 选择验证并向学习者讲解；
2. 学习者确认完成后创建 completed checkpoint；
3. push lesson 分支并创建单课 PR；
4. CI 通过且获得明确 merge 确认后 squash merge；
5. 合并后 handoff 的下一步为初始化下一课，真正开始时才移动全局指针。
