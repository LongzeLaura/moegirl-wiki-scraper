# 阶段 P0-5：crawl_report 生成

## 任务目标

每次正式爬取后自动生成 `crawl_report.md`，用于快速评估爬取质量。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划（P0-5 部分）
3. `docs/FSN_CRAWL_QUALITY_EVALUATION.md` — 质量评估报告（理解需要什么样的报告）
4. `scripts/crawl_fsn.py` — 当前爬虫主循环
5. `lib/checkpoint.py` — CrawlState（可获取统计数据）
6. `lib/archiver.py` — 当前归档逻辑

## 本阶段允许修改的范围

- 新增 `lib/report.py` — crawl_report 生成逻辑
- `scripts/crawl_fsn.py` — 在爬取完成后调用 report 生成
- `lib/checkpoint.py` — 可能需要增加一些统计方法

## 本阶段不要做的事情

1. 不要修改评分逻辑
2. 不要修改链接过滤逻辑
3. 不要修改 dry-run 模式
4. 不要实现 profile loader
5. 不要修改 archiver 的归档格式

## 具体修改要求

### 1. 新增 `lib/report.py`

实现一个 `generate_crawl_report()` 函数，接受爬取结果数据，生成 Markdown 报告。

输入参数：
- `state: CrawlState` 或等价 dict — 爬取状态
- `log_path: Path` — crawl_log.jsonl 路径
- `output_path: Path` — 报告输出路径
- `profile_id: str` — 当前 profile ID（暂用 "fsn"）
- `config: dict` — 爬取配置

### 2. 报告内容

```markdown
# Crawl Report

> Generated at: <timestamp>
> Profile: <profile_id>

## Profile Information
- Profile ID: fsn
- Seeds: 间桐樱, Fate/stay night, ...
- Crawl Config:
  - max_depth: 1
  - max_pages: 50
  - min_score: 8
  - delay: 4.0s

## Summary
| Metric | Value |
|--------|-------|
| Visited pages | 30 |
| Accepted pages | 25 |
| Rejected pages | 150 |
| Filtered pages | 50 |
| Error pages | 0 |
| Pending queue remaining | 200 |
| Stop reason | pages_crawled >= max_pages |

## Depth Distribution
| Depth | Count |
|-------|-------|
| 0 | 5 (seeds) |
| 1 | 25 |

## Category Distribution
| Category | Count |
|----------|-------|
| characters | 10 |
| world | 5 |
| locations | 3 |
| plot-arcs | 2 |
| uncategorized | 5 |

## Top Accepted Pages (by score)
| # | Title | Score | Depth | Source |
|---|-------|-------|-------|--------|
| 1 | 冬木市 | 26 | 1 | 间桐樱 |
| ... | | | | |

## Top Rejected Pages (by score)
| # | Title | Score | Reason |
|---|-------|-------|--------|
| 1 | 中长发 | 5 | score < threshold |
| ... | | | | |

## Filter Reason Statistics
| Reason | Count |
|--------|-------|
| redlink | 5 |
| action_edit | 3 |
| special_namespace | 12 |
| exclude_keyword | 30 |
| low_score | 150 |

## Suspicious Accepted Pages
(Pages with score close to threshold, may need review)
| Title | Score | Source |
|-------|-------|--------|
| ... | | |

## High-Score Pending Pages
(Pages in pending queue with high score that weren't crawled)
| Title | Score | Depth |
|-------|-------|-------|
| ... | | |

## Notes
- <any observations from the crawl>
```

### 3. 数据来源

报告数据从以下来源获取：

- **Summary**：从 `CrawlState` 获取 pages_crawled, visited, queue_size, errors
- **Accepted/Rejected/Filtered 统计**：从 `crawl_log.jsonl` 解析，汇总 `link_accepted`、`link_rejected`、`link_filtered` 事件
- **Depth/Category 分布**：从 crawl_log.jsonl 和已归档页面统计
- **Top pages**：从 crawl_log.jsonl 中的 score 排序

### 4. 报告输出路径

```
data/raw/moegirl/crawl_report.md
```

或者（如果 P1-3 已完成 profile 隔离）：

```
data/raw/moegirl/<profile_id>/crawl_report.md
```

当前阶段先用 `data/raw/moegirl/crawl_report.md`，后续 P1-3 会调整路径。

### 5. 自动生成时机

在 `crawl_fsn.py` 的 `_print_summary()` 之前（或之后），调用 `generate_crawl_report()`。

只在非 dry-run 模式下生成报告。dry-run 模式已有自己的 dry-run report（P0-4）。

### 6. 与 P0-3 score_detail 的集成

报告中的 "Filter Reason Statistics" 和 "Top Rejected Pages" 应使用 P0-3 的 score_detail 数据。

## 验收标准

1. 正式爬取完成后自动生成 `crawl_report.md`
2. 报告包含 Summary、Depth 分布、Category 分布、Top Accepted、Top Rejected、Filter Reason Stats
3. 报告中的数据与 crawl_state.json 和 crawl_log.jsonl 一致
4. dry-run 模式不生成此报告
5. 报告格式可读，便于人工快速评估

## 建议验证命令

```bash
# 1. 正式爬取
python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 10 --force

# 2. 检查报告是否生成
ls -la data/raw/moegirl/crawl_report.md

# 3. 查看报告内容
cat data/raw/moegirl/crawl_report.md

# 4. dry-run 不应生成报告
rm data/raw/moegirl/crawl_report.md 2>/dev/null
python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --dry-run
ls data/raw/moegirl/crawl_report.md 2>/dev/null || echo "No report (correct for dry-run)"
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P0-5_report.md`，包含：

1. 新增了哪些文件
2. 修改了哪些文件
3. crawl_report.md 的完整内容（附示例）
4. 数据一致性验证结果
5. 未完成项
6. 下一阶段（P1-1）需要注意的事项
