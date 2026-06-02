# 阶段 P0-3：score_detail 与可解释日志

## 任务目标

让评分和入队决策可解释。每个候选链接都应该记录详细的评分明细和决策原因。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划（P0-3 部分）
3. `docs/FSN_CRAWL_QUALITY_EVALUATION.md` — 质量评估报告（评分不可解释问题）
4. `lib/relevance.py` — 当前评分逻辑（重点看 `_compile_score` 和 `score_page_relevance`）
5. `scripts/crawl_fsn.py` — 当前日志记录方式

## 本阶段允许修改的范围

- `lib/relevance.py` — 重构 `_compile_score` 返回更详细的 score_detail
- `scripts/crawl_fsn.py` — 增强 crawl_log 中的评分日志
- `lib/checkpoint.py` — 确保 score_detail 可以保存到 pending_queue 条目

## 本阶段不要做的事情

1. 不要修改链接过滤逻辑（P0-1）
2. 不要修改队列排序逻辑（P0-2）
3. 不要修改评分权重（那是 P1-2 中 profile 的任务）
4. 不要实现 dry-run 模式（P0-4）
5. 不要实现 crawl_report（P0-5）
6. 不要修改 DEFAULT_INCLUDE_KEYWORDS 或 DEFAULT_EXCLUDE_KEYWORDS 的内容

## 具体修改要求

### 1. 增强 `_compile_score` 返回值

当前 `_compile_score` 返回 `(score, reasons)`，其中 reasons 是简单 dict：

```python
{
  "title_keywords": 3,
  "display_text_keywords": 1,
  "source_is_fsn": 8,
  "short_generic_penalty": -5,
  "_total": 15
}
```

需要重构为更详细的结构：

```python
{
  "decision": "accepted",           # accepted / rejected / filtered
  "filter_reason": null,             # 如果被过滤，原因是什么
  "final_score": 15,
  "seed_bonus": 0,                   # 种子加分（预留）
  "title_keyword_hits": ["卫宫士郎", "Fate"],   # 命中了哪些标题关键词
  "title_keyword_score": 10,          # 标题关键词得分
  "alias_hits": [],                   # 命中了哪些别名（预留）
  "alias_keyword_score": 0,
  "category_hits": ["Fate系列"],       # 命中了哪些分类关键词
  "category_keyword_score": 6,
  "source_relevance_bonus": 8,         # 来源页面加分
  "source_title": "间桐樱",            # 来源页面标题
  "noise_keyword_hits": [],            # 命中了哪些噪声关键词（预留）
  "noise_keyword_penalty": 0,
  "blocked_related_ip_hits": [],       # 命中了哪些屏蔽 IP（预留）
  "blocked_related_ip_penalty": 0,
  "allowed_related_ip_hits": [],       # 命中了哪些允许 IP（预留）
  "allowed_related_ip_bonus": 0,
  "short_generic_title_penalty": 0,
  "min_score_threshold": 8,            # 当前阈值
  "profile_id": "",                    # 当前 profile（预留）
}
```

### 2. 修改 `score_page_relevance` 的返回值

当前返回 `(score, reasons)`，需要改为返回 `(score, score_detail)`，其中 score_detail 是上面的详细结构。

同时保持向后兼容：如果其他代码只使用 `score`，不应该受影响。

### 3. 在 crawl_log.jsonl 中记录完整评分

当前 `link_excluded` 事件记录了 `score` 和 `score_detail`，但 `score_detail` 不够详细。

需要：
- 对每个被评分的链接（无论 accepted 还是 rejected），都记录完整的 score_detail
- 入队时记录 `link_accepted` 事件（而不是只记录 `link_enqueued`）
- 被拒绝时记录 `link_rejected` 事件
- 被过滤时记录 `link_filtered` 事件（与 P0-1 的过滤事件统一）

### 4. 标记决策类型

每个候选链接必须标记为以下三种之一：

- **accepted**：score >= min_relevance_score，进入 pending_queue
- **rejected**：score < min_relevance_score，不入队
- **filtered**：被排除规则或命名空间过滤，不评分

### 5. 确保 score_detail 可保存到 checkpoint

pending_queue 中的条目现在包含 score_detail 字段（P0-2 已预留）。确保 score_detail dict 可以被 JSON 序列化。

### 6. 关键词命中列表

在 `_keyword_score` 之外，新增一个辅助函数 `_keyword_hits(text, keywords)` 返回命中的关键词列表（而不只是计数）。

这样 score_detail 中可以记录具体命中了哪些关键词，而不只是一个数字。

## 验收标准

1. crawl_log.jsonl 中每个候选链接都有完整的 score_detail
2. 可以直接从日志回答：为什么这个页面被收录？为什么被排除？
3. score_detail 包含具体命中的关键词列表（不只是计数）
4. 可以从日志统计：哪些关键词导致了最多误收录？
5. 可以从日志统计：哪些来源页面产生了最多被拒绝的链接？

## 建议验证命令

```bash
# 1. 运行小规模爬取
python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 3 --force

# 2. 检查日志中是否有 score_detail
python -c "
import json
for line in open('data/raw/moegirl/crawl_log.jsonl'):
    entry = json.loads(line)
    if entry.get('event') in ('link_accepted', 'link_rejected', 'link_filtered'):
        sd = entry.get('score_detail', {})
        decision = sd.get('decision', 'N/A')
        title_kw = sd.get('title_keyword_hits', [])
        print(f'{entry[\"event\"]:20s} {sd.get(\"final_score\", 0):5d} {entry.get(\"title\", \"\")[:30]:30s} title_hits={title_kw}')
        break
"

# 3. 统计 accepted 和 rejected 数量
python -c "
import json
from collections import Counter
decisions = Counter()
for line in open('data/raw/moegirl/crawl_log.jsonl'):
    entry = json.loads(line)
    if 'score_detail' in entry:
        decisions[entry['score_detail'].get('decision', 'unknown')] += 1
for d, c in decisions.most_common():
    print(f'{d}: {c}')
"
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P0-3_report.md`，包含：

1. 修改了哪些文件
2. score_detail 的新结构（附完整字段列表）
3. 验证命令运行结果
4. 从日志中能回答的关键问题示例
5. 未完成项
6. 下一阶段（P0-4）需要注意的事项
