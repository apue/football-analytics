---
lesson_id: 00-03-spatial-quality
status: review
checkpoint_id: CP-003
current_step: 实现与验证完成，等待学习者审阅 00-03 的结果和边界
next_action: 学习者解释结构性 360 缺失与线外 freeze-frame 坐标，再决定是否接受本课
updated_at: 2026-08-05T16:18:22+08:00
---

# 课程交接

## 已完成

- 已与学习者确定 00-03 使用单场 events + 360 练习坐标、方向和数据质量。
- 已确定可复用逻辑进入 `src/`，Notebook 只负责调用、展示与解释。
- 已冻结本课边界，不进入 10 场探索、25 场验证或战术 classifier。
- 已新增 `spatial.py`，提供单场加载、UUID 关联、质量报告、关键断言、360 场景行和
  射门方向摘要接口；公开接口由包根导出。
- 已创建并执行 22-cell 教程 Notebook，生成 3,858 行场景表和两队两半场方向图。
- 已在 `docs/data-guide.md` 记录接口契约及单场、多场调用模式。
- 已用 12 个合成 fixture 测试覆盖结构性缺失、重复/错配 ID、坐标、frame 标记、
  visible area、线外球员和方向分组。

## 当前工作

- 代码、文档和验证已完成，lesson 状态为 review；尚未由学习者接受完成。

## 决定

- 后续“压力—选择—结果”只作为数据检查的应用背景。
- 不在本课定义压力、出球路线或 build-up 结果阈值。
- 多场复用通过稳定的 `match_id` 接口和可拼接场景行完成。
- 真实数据推翻了“所有 360 球员坐标必须在线内”的初始假定：377/65,283 个
  freeze-frame 球员在线外。它们被保留并报告，不作为关键断言失败。
- 没有 360 的 event 和 actor 不可见属于允许但必须报告的观察边界；重复/错配 ID、
  畸形坐标、缺失 visible area、多 actor 等会令关键断言失败。
- StatsBomb 已将控球队表示成朝 `x=120` 进攻，本课不按半场再次翻转坐标。

## 检查

- 本场 4,213 events、3,858 frames；全部 frame 唯一匹配，355 events 无 360，覆盖率
  91.6%。场景表 3,858 行且 event UUID 唯一。
- event 起点 4,186、事件终点 2,226、visible-area 顶点 22,457，均无畸形或线外值；
  freeze-frame 球员位置 65,283 条，无畸形值，377 条在线外。
- 四组射门均在 `x >= 60`：Barcelona period 1/2 为 5/5，Real Madrid 为 6/10，
  方向图已视觉检查。
- `tests/test_spatial.py`：12 passed；全量 `pytest`：42 passed。
- Notebook 原地 clean-kernel 执行和独立 `validate_notebook.py` 执行均通过；22 cells、
  10 code cells、1 张 PNG、0 errors。
- `uv lock --check`、全仓库 Ruff format/check 和 `git diff --check` 均通过。

## 开放问题

- 学习者尚未解释结构性 360 缺失、visible area 和线外球员坐标的区别。
- 本课只证明单场数据管道可运行；目标门将事件的覆盖率和多场稳定性尚未检查。
- 压力、选择、episode 终止和结果窗口仍未定义，不能从本课输出提出战术结论。
