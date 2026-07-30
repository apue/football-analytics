---
lesson_id: 00-01-orientation
status: completed
checkpoint_id: CP-007
current_step: 00-01 已由学习者确认完成，等待合并课程分支
next_action: 合并后初始化 00-02 事件表课程，再切换全局 current_lesson
updated_at: 2026-07-30T21:36:09+08:00
---

# 课程交接

## 已完成

- 已定义课程问题、输入、产物和验收标准。
- 学习者确认使用 Barcelona 1–3 Real Madrid（match ID `3773585`）。
- 已下载所选比赛的 events、lineups 和 three-sixty 文件。
- 已记录上游 commit、对象记录数及第一组 ID 关联检查。
- 已创建并执行 `analysis.ipynb`，得到方式/高度、球员贡献和进入路线三组图。
- 已将一次进入定义为成功 Pass 或 Carry 满足 `start_x < 80 <= end_x`。
- 已将117次进入归并为78个首次进入三区的 possession。
- 已可视化两队后续到达禁区、形成射门、产生 xG 及比分状态差异。
- 已审计四个进球；点球没有此前的成功三区进入，按定义不纳入转化样本。
- 已为四球分别核对 possession 来源、最后助攻/犯规链、射门方式和 xG。
- 已绘制四球关键事件链，并明确关键链不是完整战术过程。
- 已放弃自定义快速转换分类，直接接受 StatsBomb `From Counter` 标签。
- 已新增 `build_match_evidence(events)`，统一抽取进入事件、首次进入 possession
  结果、供应商反击标签和可审计进球上下文。
- 已新增薄命令 `match-evidence`，可从本地 match ID 输出 JSON 或 Markdown
  证据包。
- 已将 Notebook 的重复抽取逻辑替换为工具箱调用，保留现有图表和叙事。
- 已新增 `findings.md` 与 `exercises.md`，总结数据地图、证据边界和迁移练习。

## 当前工作

- 学习者已确认合入，本课状态为 completed。
- 主结果仍包含所有 `play_pattern`；来源字段保留在证据包，Regular Play 作为
  敏感性拆分。

## 决定

- 以一个小型 event-data 足球问题带出数据字段，不把目录关系本身当作主要产物。
- 先使用标准 events 完成筛选、汇总和可视化；360 留到确实需要空间语境的问题。
- 首场比赛优先采用四类数据齐全、没有加时赛复杂度的样本。
- Carry 表示持球推进；Dribble 表示过人尝试，不作为进入三区的持续移动事件。
- 保留 `play_pattern` 和 `pass_type`，避免把界外球来源误当作普通传球。
- 结果比较以 possession 为单位，每次只使用第一次成功进入，避免重复进入被当成独立机会。
- 禁区到达与形成射门是并列结果；禁区外射门使二者不构成严格漏斗。
- 进球样本太少，主要比较 shot rate 与 xG per entry possession。
- `From Counter` 直接采用 StatsBomb 标签，不维护自定义反击分类。
- 进球模式必须区分 possession 来源与直接得分机制。
- 点球事件可以确认 foul 双方、位置和 penalty 标签，不能确认接触方式或判罚正确性。
- 工具箱采用一个深接口而非为漏斗、反击和进球各建脚本；CLI 只处理文件加载和
  输出格式，Notebook 负责问题、可视化与解释。
- 测试只覆盖高风险的定义与 ID 关联，不为课程叙事机械制造 expected output。

## 检查

- events：4,213 条，event ID 无重复。
- 进入事件：117 条，ID 唯一且全部满足 `start_x < 80 <= end_x`。
- 进入控球：78个 possession ID 唯一；后续41个到达禁区、17个形成射门。
- Notebook 已使用分析依赖从干净 kernel 自上而下执行成功。
- Notebook 已从干净 kernel 执行：32个 cells、6张输出图、0个存储错误。
- 四球事件 ID、关键助攻和 Ramos 成对 foul 关系已有断言。
- 已视觉检查四球事件链图，确认来源 restart、助攻、回收、犯规和射门标记可读。
- 真实比赛 `match-evidence` 输出：117次进入、78个进入控球、2个
  `From Counter` possession、4个进球；球队汇总与 Notebook 一致。
- `uv lock --check`：通过。
- `uv run ruff format --check .`：通过。
- `uv run ruff check .`：通过。
- `uv run pytest`：19个测试通过。
- `uv run --group notebook python scripts/validate_notebook.py
  course/templates/analysis.ipynb`：通过。
- `uv run --group notebook --group analysis python scripts/validate_notebook.py
  course/lessons/00-01-orientation/analysis.ipynb`：从干净 kernel 通过。
- `scripts/validate_course.py` 在当前仓库中不存在；旧 AGENTS 命令无法执行，
  已改为直接检查 lesson ID、handoff frontmatter 与 checkpoint 字段。

## 开放问题

- 00-02 尚未初始化；开始下一课时再创建 lesson 分支并切换全局课程指针。
- 坐标方向和系统性缺失检查分别留给 00-03 与 00-02。
