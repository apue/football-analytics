# 检查

## 数据完整性

- [x] 已记录数据源 commit。
- [x] events 与 three-sixty 文件存在。
- [x] 360 frame UUID 关联没有意外损失。
- [x] 已检查 event/frame ID 重复与结构性缺失。
- [x] 已检查 event、end location、freeze frame 和 visible area 球场边界。
- [x] 已按球队与半场检查供应商统一进攻方向。

## 接口完整性

- [x] 分析单位和返回字段明确。
- [x] 公开函数 docstring 说明输入、输出、坐标约定和异常。
- [x] 场景行保留 `match_id` 和 `event_uuid`。
- [x] 多场调用复用同一单场函数，不复制 Notebook 逻辑。

## 可复现性

- [x] Notebook 可以从干净 kernel 自上而下执行。
- [x] 新增确定性逻辑有合成 fixture 单元测试。
- [x] Notebook 只编排和展示，加载与验证逻辑位于 `src/`。

## 结果

| 检查 | 命令或方法 | 结果 | 后续动作 |
| --- | --- | --- | --- |
| 上游版本 | `git -C data/external/statsbomb-open-data rev-parse HEAD` 与 Notebook 断言 | `b0bc9f22...`，通过 | 版本改变后重跑本课 |
| 真实数据关联 | `build_spatial_quality_report` | 4,213 events；3,858 frames 全部唯一匹配；355 events 无 360 | 多场时逐场报告覆盖率 |
| 坐标质量 | 同一报告的四类坐标检查 | event 起终点和 visible-area 顶点 0 异常；65,283 个 freeze-frame 球员中 377 个在线外并保留 | 多场检查线外比例与事件类型 |
| 容器质量 | freeze-frame 标记和 visible-area 检查 | 畸形、缺失、空 frame、多 actor 与 actor 不可见均为 0 | 门将子样本需单独报告 |
| 新增单元测试 | `uv run pytest tests/test_spatial.py` | 12 passed | 无 |
| 全量测试 | `uv run pytest` | 42 passed | 无 |
| Notebook 原地执行 | `jupyter nbconvert --execute --inplace` | 通过 | 无 |
| Notebook 独立执行 | `scripts/validate_notebook.py analysis.ipynb` | clean kernel 通过 | 无 |
| Notebook schema/输出 | `nbformat.validate` 与输出检查 | 22 cells、10 code cells、1 张 PNG、0 errors | 无 |
| 方向图视觉检查 | 检查两队两半场四面板 | 标题、球场、点位与样本数清晰；未见翻转 | 无 |
| 格式与静态检查 | `uv run ruff format --check .`、`uv run ruff check .` | 51 files 通过 | 无 |
| 锁文件 | `uv lock --check` | 通过 | 无 |
| Diff 空白 | `git diff --check` | 通过 | 无 |
