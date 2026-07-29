# Agent Workflow

这份协议使课程可以在新的 Codex session 或其他 Coding Agent 中继续。

## 恢复协议

Agent 开始工作时：

1. 读取 `AGENTS.md`。
2. 读取 `course/syllabus.md` 和 `course/state.yaml`。
3. 读取当前 lesson 的 `brief.md`、`handoff.md` 及已有产物。
4. 检查 Git 状态，不覆盖学习者或其他 Agent 的未提交工作。
5. 用一句话复述当前问题、状态和下一步，然后开始有边界的工作。

聊天记录可以提供背景，但不能覆盖仓库中更新、更具体的状态。

## Lesson 生命周期

### Ready

- `brief.md` 已明确问题、范围、分析单位和验收标准。
- 学习者知道本课为什么值得研究。

### In progress

- Agent 实现最小可验证分析。
- 通用逻辑进入 `src/`，叙事和探索留在 Notebook。
- 中间结果接受数据质量和简单基线检查。

### Review

- Notebook 能从干净 kernel 执行。
- `findings.md` 已区分证据层级。
- `checks.md` 记录验证结果，而不是只列检查名称。
- 学习者能够解释主要输出。

### Completed

- `exercises.md` 至少包含一个换球队、换比赛或换参数的迁移练习。
- `handoff.md` 和 `course/state.yaml` 已更新。
- 必需验证通过并形成 Git checkpoint。

## 编码前输出

Agent 在写代码前应确认：

- 本课问题和足球意义
- 数据是否能观察目标现象
- 分析单位和分母
- 比较基准
- 主要定义及替代定义
- 预期产物
- 完成标准

重要选择不明确时，先与学习者讨论。实现细节可以由 Agent 自主决定。

## 编码后讲解

Agent 不逐行朗读代码，而按三个层级解释：

1. **足球直觉**：这个结果在比赛中代表什么。
2. **分析方法**：数据、定义、比较和限制是什么。
3. **代码实现**：关键模块在哪里，如何修改或复用。

每个图表或模型输出还需说明：

- 如何阅读
- 合理结论
- 常见误读
- 下一项验证

## Handoff 协议

`handoff.md` 必须写入：

- 当前状态和最后更新时间
- 已完成内容与文件
- 新增定义和关键决定
- 运行过的验证命令及结果
- 未解决问题和数据限制
- 唯一明确的下一步

`course/state.yaml` 只保存全局导航信息；详细上下文留在当前 lesson 的
`handoff.md`。不要把大段日志塞进状态文件。

## Skills 策略

仓库规则以 `AGENTS.md` 为准，因为不同 Agent 对 Skills 的支持不同。当前 Codex
环境安装了 Jupyter Notebook Skill，用于 Notebook 创建和验证；其他机器应按
自己的 Agent 平台安装等价能力。课程不依赖该 Skill 才能运行。

新增第三方 Skill 时应记录来源和用途，不将未审查的 Skill 仓库作为课程代码
提交。稳定且项目特有的流程应先进入本文件，再考虑制作适配 Skill。
