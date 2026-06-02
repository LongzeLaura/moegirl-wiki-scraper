# 阶段 P0-2：优先队列与 checkpoint

## 任务目标

用优先队列替代当前 FIFO BFS，并保证 checkpoint / resume 可用。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划（P0-2 部分）
3. `docs/FSN_CRAWL_QUALITY_EVALUATION.md` — 质量评估报告（FIFO 队列问题）
4. `lib/checkpoint.py` — 当前 CrawlState 实现（重点看 `pending_queue`、`pop_next_batch`、`add_to_queue`）
5. `scripts/crawl_fsn.py` — 当前 BFS 循环（看队列消费逻辑）

## 本阶段允许修改的范围

- `lib/checkpoint.py` — 重构队列数据结构和排序逻辑
- `scripts/crawl_fsn.py` — 修改队列消费逻辑，适配优先队列
- `lib/relevance.py` — 确保评分结果可传递到队列条目

## 本阶段不要做的事情

1. 不要修改链接过滤逻辑（P0-1 的任务）
2. 不要实现 score_detail 日志（P0-3 的任务）
3. 不要实现 profile loader（P1-1 的任务）
4. 不要修改评分权重
5. 不要修改 archiver 或 classifier

## 具体修改要求

### 1. 队列条目数据结构

当前 pending_queue 中的条目格式：

```python
{
  "title": "...",
  "source_page": "...",
  "depth": 1,
  "display_text": "...",
  "score": 10
}
```

需要扩展为：

```python
{
  "title": "...",
  "url": "...",           # 可选，留空
  "source_page": "...",
  "depth": 1,
  "display_text": "...",
  "score": 10,
  "score_detail": {},      # 评分明细，P0-3 阶段会填充
  "enqueue_order": 0,      # 全局递增计数器
  "profile_id": "",        # 预留，P1-1 阶段会使用
  "is_seed": false         # 种子页面标记
}
```

### 2. 优先队列排序

`pop_next_batch` 不再简单取前 N 个，而是按以下排序取前 N 个：

```
1. is_seed desc（种子页面优先）
2. score desc（高分页面优先）
3. depth asc（浅层页面优先）
4. enqueue_order asc（同等条件下先入队优先，保证可复现）
```

实现方式：在 `pop_next_batch` 调用前对 `pending_queue` 排序，或维护一个排序数据结构。

推荐实现：每次 `pop_next_batch` 时对 `pending_queue` 排序后取前 N 个。这样 checkpoint 文件仍然是 JSON 数组，便于调试和手动编辑。

### 3. 全局 enqueue_order 计数器

在 CrawlState 中维护一个 `_next_enqueue_order` 计数器：

- 每次调用 `add_to_queue` 时，给每个条目分配递增的 `enqueue_order`
- 这个计数器也需要保存到 checkpoint

### 4. 种子页面标记

种子页面（depth=0 且由种子初始化的条目）需要标记 `is_seed: true`，并在排序中获得最高优先级。

当前种子添加逻辑在 `crawl_fsn.py` 的 `run()` 方法中：

```python
seed_items = [
    {"title": s, "source_page": "", "depth": 0, "display_text": s}
    for s in cfg["seeds"]
]
self.state.add_to_queue(seed_items)
```

需要给种子条目添加 `"is_seed": True` 和高 score（如 100）。

### 5. checkpoint 兼容性

旧 checkpoint 格式没有 `enqueue_order`、`score_detail`、`profile_id`、`is_seed` 字段。

处理方式：
- 加载旧 checkpoint 时，如果条目缺少 `enqueue_order`，自动分配（基于数组索引）
- 如果条目缺少 `score`，默认 0
- 如果条目缺少 `is_seed`，默认 false（但 depth=0 的条目可视为 seed）
- 在 load 日志中记录兼容处理情况

**不要**直接拒绝旧 checkpoint，给出清晰兼容。

### 6. resume 后队列排序一致性

resume 时，加载 pending_queue 后应能产生与中断前一致的排序结果。

关键：`enqueue_order` 必须被保存到 checkpoint 且在 resume 后不重复。

### 7. crawl_log 记录入队事件

在 `add_to_queue` 成功入队时，记录日志：

```json
{
  "event": "link_enqueued",
  "title": "...",
  "source": "...",
  "score": 10,
  "depth": 1,
  "enqueue_order": 42,
  "is_seed": false
}
```

## 验收标准

1. 运行爬虫后，pending_queue 中的条目按 score 降序排列
2. 种子页面（is_seed=true）始终排在队列最前
3. 同分同深度的条目按 enqueue_order 排序
4. checkpoint 保存后重新加载，队列排序一致
5. 旧 checkpoint 格式可以加载，不会崩溃
6. max_pages 较小时，高 score 页面优先被爬取，低 score 页面排在后面

## 建议验证命令

```bash
# 1. 小规模测试
python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 5 --force

# 2. 检查 pending_queue 排序
python -c "
import json
s = json.loads(open('data/raw/moegirl/crawl_state.json').read())
queue = s['pending_queue']
print(f'Queue size: {len(queue)}')
if queue:
    scores = [x.get('score', 0) for x in queue]
    print(f'Top 5 scores: {scores[:5]}')
    print(f'Sorted descending: {sorted(scores, reverse=True)[:5]}')
    print(f'Is sorted: {scores == sorted(scores, reverse=True)}')
    # Check enqueue_order
    orders = [x.get('enqueue_order', -1) for x in queue]
    print(f'Enqueue orders present: {any(o >= 0 for o in orders)}')
"

# 3. Test resume
python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 3 --resume
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P0-2_report.md`，包含：

1. 修改了哪些文件
2. 队列排序逻辑实现方式
3. enqueue_order 计数器实现方式
4. 旧 checkpoint 兼容性处理方式
5. 验证命令运行结果
6. 队列排序是否正确（附队列前 10 条 score 分布）
7. 未完成项
8. 下一阶段（P0-3）需要注意的事项
