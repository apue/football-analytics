# Agent Workflow

这份协议使课程可以在新的 Codex session 或其他 Coding Agent 中继续。

## 恢复协议

Agent 开始工作时：

1. 读取 `AGENTS.md`。
2. 读取 `course/syllabus.md` 和 `course/state.yaml`。
3. 读取当前 lesson 的 `brief.md`、`handoff.md` 及已有产物。
4. 运行 `uv run python scripts/course_resume.py`。
5. 检查 Git 状态及 checkpoint 后的未提交 diff。
6. 向学习者展示当前课程、checkpoint、分支、工作区状态和下一步，并等待确认。

聊天记录可以提供背景，但不能覆盖仓库中更新、更具体的状态。

工作区 clean 时从最新 checkpoint 恢复。工作区 dirty 时，这些改动属于
checkpoint 后尚未完成的工作；Agent 先读 diff 并运行针对性检查，不得自动丢弃
或提交。

## 状态所有权

同时只允许一个活动 lesson：

- `course/state.yaml` schema v2 只保存全局导航：stage、lesson、已完成 lesson
  和更新时间。
- 当前 lesson 唯一的 `handoff.md` 保存 status、checkpoint、当前步骤、下一步、
  决策、验证和简短历史。
- 允许状态为 `ready`、`in_progress`、`paused`、`review`、`completed` 和
  `blocked`。
- 合并完成后，全局指针仍指向已完成 lesson；handoff 的下一步写“初始化下一课”。
  真正开始下一课时才切换全局指针。

## Lesson 生命周期

### Ready

- `brief.md` 已明确问题、范围、分析单位和验收标准。
- 学习者知道本课为什么值得研究。

### In progress

- Agent 实现最小可验证分析。
- 通用逻辑进入 `src/`，叙事和探索留在 Notebook。
- 中间结果接受数据质量和简单基线检查。

### Paused

- 当前小单元可以未完成，但 handoff 明确完成与未完成边界。
- 未运行或失败的验证必须写入 `Validation`。

### Review

- Notebook 能从干净 kernel 执行。
- `findings.md` 已区分证据层级。
- `checks.md` 记录验证结果，而不是只列检查名称。
- 学习者能够解释主要输出。

### Completed

- `exercises.md` 至少包含一个换球队、换比赛或换参数的迁移练习。
- `handoff.md` 和全局导航已更新。
- 必需验证通过并形成 `completed` checkpoint。

## Checkpoint 协议

开始一课时创建 `lesson/<lesson-id>` 分支和 `CP-000`。下列里程碑应形成新的
checkpoint：

- 数据范围确定；
- 一个可复用模块完成；
- 一个 Notebook 分析段落从干净 kernel 验证；
- 主要图表完成；
- findings/checks 更新；
- 等待学习者决策、主动暂停或明确 blocked。

checkpoint 固定顺序：

1. 更新 handoff 最新快照并追加历史；
2. 运行当前小单元的针对性检查；
3. 检查 diff；
4. 创建本地提交：
   `checkpoint(<lesson-id>): CP-NNN <step>`。

课中不 push。checkpoint 是教学里程碑，不是每个命令、cell 或微小改动。

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

`handoff.md` YAML frontmatter 必须写入：

- `lesson_id`、`stage`、`status`；
- `checkpoint_id`、`current_step`、`next_action`、`updated_at`。

正文必须写入：

- 已完成内容与文件
- 当前进行中的边界
- 新增定义和关键决定
- 运行过的验证命令及结果
- 未解决问题和数据限制
- 简短 checkpoint 历史

`course/state.yaml` 只保存全局导航信息；详细上下文留在当前 lesson 的
`handoff.md`。不要把大段日志塞进状态文件。

## 课末交付

1. 进入 `review` checkpoint，运行完整验证并向学习者讲解产物、定义和限制。
2. 学习者确认完成后，进入 `completed` checkpoint，并更新全局 state。
3. push lesson 分支，创建单课 PR，等待 CI。
4. 获得明确 merge 确认后 squash merge，使主分支每课保留一个整洁提交。

## Skills 策略

仓库规则以 `AGENTS.md` 为准，因为不同 Agent 对 Skills 的支持不同。当前 Codex
环境安装了 Jupyter Notebook Skill，用于 Notebook 创建和验证；其他机器应按
自己的 Agent 平台安装等价能力。课程不依赖该 Skill 才能运行。

新增第三方 Skill 时应记录来源和用途，不将未审查的 Skill 仓库作为课程代码
提交。稳定且项目特有的流程应先进入本文件，再考虑制作适配 Skill。
