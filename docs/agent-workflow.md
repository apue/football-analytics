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

新 session 读取仓库说明和当前 lesson 后运行：

```bash
uv run python scripts/course_resume.py
```

Resume 是只读摘要：

- clean 表示可从当前 HEAD 可达的最近 checkpoint 继续；
- dirty 表示存在 checkpoint 后的工作，Agent 必须先检查 diff；
- checkpoint、分支或 handoff 不一致时只报告 warning；
- 无法读取 state、handoff 或 Git 仓库时才报告 fatal error。

Agent 向学习者展示摘要并等待确认，不自动丢弃、提交或修复文件。

## Lesson 生命周期

### Ready

`brief.md` 已明确问题、范围、分析单位、基准和验收标准。

### In progress

Agent 实现当前最小学习单元。可复用逻辑进入 `src/`，Notebook 负责编排、检查和
叙事。检查强度与该单元的分析风险相称。

### Paused 或 Blocked

Handoff 明确已完成和未完成的边界、未运行或失败的检查，以及恢复所需的唯一
下一步。

### Review

实际 lesson Notebook 从干净 kernel 执行；findings 区分证据层级；checks 记录
结果；学习者能够解释主要输出和限制。

### Completed

学习者确认验收后更新 handoff 和全局导航，形成 completed checkpoint，再进入
PR、CI 和明确确认后的 squash merge。

## Checkpoint

Checkpoint 是有意义学习单元的本地 Git commit，不是每个命令或 cell 的日志。
常见边界包括数据范围确定、可复用模块完成、Notebook 段落验证、主要图表完成、
findings/checks 更新或主动暂停。

提交格式为：

```text
checkpoint(<lesson-id>): CP-NNN <step>
```

Git 已经保存 checkpoint 历史，所以 handoff 只维护最新快照。课中不 push。

## 分工

编码前，学习者和 Agent 应明确足球问题、数据可见性、分析单位、分母、基准、
定义、替代定义和完成标准。

编码后，Agent 按三个层次解释：

1. 足球直觉：输出在比赛中代表什么；
2. 分析方法：数据、计算、比较与限制；
3. 代码实现：关键模块及其复用或修改方式。

每个重要输出都要说明可读结论、常见误读，以及能提高可信度的下一项检查。

## Notebook 边界

Resume 和普通 checkpoint 不执行实际 lesson Notebook。Notebook 的完整
clean-kernel 验证发生在 review；仓库 CI 只对模板做 smoke test。

## 课末交付

1. 进入 review，运行完整验证并向学习者讲解；
2. 学习者确认完成后创建 completed checkpoint；
3. push lesson 分支并创建单课 PR；
4. CI 通过且获得明确 merge 确认后 squash merge；
5. 合并后 handoff 的下一步为初始化下一课，真正开始时才移动全局指针。
