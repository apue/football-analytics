# 检查

## 数据完整性

- [x] 已记录 StatsBomb open-data commit。
- [x] events 与 lineups 文件存在且 match ID 一致。
- [x] Pass 与 Shot 分析表的 event ID 唯一，network 球员均能关联球衣号码。
- [x] 已按事件类型检查必要字段缺失，不对稀疏宽表统一填值。
- [x] 4,186 条带位置事件均在 StatsBomb `120 x 80` 坐标边界内；图中采用供应商
  统一的从左向右进攻方向。

## 指标完整性

- [x] 每张图的分析单位和筛选条件写在图前。
- [x] 传球距离与 xG 使用两队相同分箱，样本量和总量可核对。
- [x] 空 `pass.outcome` 按成功处理，点球单独标记，network 使用共同换人窗口。
- [x] KDE 旁增加共享计数尺度 hexbin，避免把归一化颜色当作绝对次数。
- [ ] 多场样本、KDE 带宽和 network 边阈值敏感性留作后续练习，不作为本课结论。

## 可复现性

- [x] Notebook 可以从干净 kernel 自上而下执行。
- [x] 本课没有新增 `src/` 逻辑；高风险定义由 Notebook 断言和真实比赛样本直接检查。
- [x] 本课没有随机过程。
- [x] 所有分析表和图都从原始 events 与 lineups 重新构建。

## 结果

| 检查 | 命令或方法 | 结果 | 后续动作 |
| --- | --- | --- | --- |
| Clean-kernel 执行 | `scripts/validate_notebook.py visualization-lab.ipynb` | 通过 | 无 |
| Notebook schema | `nbformat.validate` | 23 cells、11 code cells、7 图、0 错误 | 无 |
| 必要字段 | Notebook type-aware assertions | 0 个缺失或越界行 | 无 |
| 视觉检查 | 逐张检查 7 张图 | 标题、尺度、标记和布局可读 | 无 |
| 格式与 lint | `ruff format --check .`、`ruff check .` | 38 个文件通过 | 无 |
| 测试 | `pytest` | 19 个测试通过 | 无 |
| 模板 Notebook | `scripts/validate_notebook.py course/templates/analysis.ipynb` | 通过 | 无 |
| 文本与补丁 | `git diff --check` | 通过 | 无 |
