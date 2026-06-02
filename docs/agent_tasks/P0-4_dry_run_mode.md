# 阶段 P0-4：dry-run / score-only 模式

## 任务目标

支持只抓种子、提取出链、评分、输出候选结果，不正式归档。用于调试 profile 评分规则。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划（P0-4 部分）
3. `scripts/crawl_fsn.py` — 当前 dry-run 实现（已有基础，需增强）
4. `lib/checkpoint.py` — checkpoint 逻辑
5. `lib/archiver.py` — 归档逻辑（dry-run 不应触发）

## 本阶段允许修改的范围

- `scripts/crawl_fsn.py` — 重构 dry-run 逻辑
- `lib/checkpoint.py` — dry-run 模式下不保存正式 checkpoint

## 本阶段不要做的事情

1. 不要修改评分逻辑（P0-3）
2. 不要修改链接过滤逻辑（P0-1）
3. 不要实现 crawl_report（P0-5）
4. 不要实现 profile loader（P1-1）
5. 不要修改 archiver 或 classifier 的核心逻辑

## 具体修改要求

### 1. 增强当前 dry-run 实现

当前 `crawl_fsn.py` 的 dry-run 逻辑：
- depth=0（种子）：正常抓取
- depth>0：只打印 "Would fetch this page"，不做任何处理

这不够。dry-run 模式应该：

1. 抓取种子页面
2. 提取种子页面的出链
3. 对候选链接评分（使用 P0-3 的 score_detail）
4. 输出所有候选链接的评分结果
5. **不**正式归档页面
6. **不**写入正式输出目录
7. **不**保存正式 checkpoint
8. **不**继续爬取 depth>0 的页面

### 2. dry-run 输出内容

dry-run 完成后，输出以下内容到 stdout 和一个独立的 dry-run 报告文件：

```markdown
# Dry-Run Report

## Profile: <profile_id>  (暂用 "fsn")

## Seeds
- 间桐樱 (depth=0)
- Fate/stay night (depth=0)
- ...

## Seed Link Counts
| Seed | Outgoing Links | After Filtering |
|------|---------------|-----------------|
| 间桐樱 | 264 | 42 |
| Fate/stay night | 180 | 35 |

## Accepted Candidates (score >= threshold)
| # | Title | Score | Source | Title Keyword Hits |
|---|-------|-------|--------|-------------------|
| 1 | 远坂凛 | 18 | 间桐樱 | 远坂凛 |
| 2 | 冬木市 | 26 | 间桐樱 | 冬木市 |
| ... | | | | |

## Rejected Candidates (score < threshold)
| # | Title | Score | Source | Reason |
|---|-------|-------|--------|--------|
| 1 | 中长发 | 5 | 间桐樱 | noise: 萌属性 |
| ... | | | | |

## Filtered Candidates (namespace/exclude rule)
| # | Title | Source | Filter Reason |
|---|-------|--------|--------------|
| 1 | Template:XXX | 间桐樱 | special_namespace |
| ... | | | | |

## Top N Accepted Candidates
(默认 Top 30)

## High-Risk Accepted Pages
(score 刚好过阈值，可能需要人工审查)

## Low-Score but Potentially Core Pages
(score 低于阈值但可能是核心内容，需要关注)

## Filter Reason Statistics
| Reason | Count |
|--------|-------|
| redlink | 5 |
| action_edit | 3 |
| special_namespace | 12 |
| exclude_keyword | 8 |
| low_score | 200 |
```

### 3. dry-run 输出路径

dry-run 报告输出到临时目录，不污染正式输出：

```
data/raw/moegirl/dry_run_<timestamp>/
  dry_run_report.md
  dry_run_state.json       # 包含所有候选链接的评分结果
```

或者更简单：直接输出到 stdout，同时写入 `data/raw/moegirl/dry_run_report.md`。

### 4. dry-run 不保存 checkpoint

dry-run 模式下：
- 不修改 `crawl_state.json`
- 不写入 `crawl_log.jsonl`（或写入独立的 dry-run log）
- 不调用 `save_raw_page` 和 `save_markdown_page`

### 5. 命令行参数

当前已有 `--dry-run` 参数，保持不变。

可以新增：
- `--dry-run-top-n 30` — Top N 候选展示数量（默认 30）

### 6. 与 P0-3 的 score_detail 集成

dry-run 报告中应使用 P0-3 阶段实现的 score_detail 数据：
- 每个 accepted/rejected 候选都显示命中的关键词
- 每个 filtered 候选都显示过滤原因
- 统计各过滤原因的数量

## 验收标准

1. `--dry-run` 只抓取种子页面，不抓取 depth>0 页面
2. dry-run 报告包含 accepted / rejected / filtered 分类
3. dry-run 报告包含 Top N 候选和高风险页面
4. dry-run 不污染正式输出目录（不修改 crawl_state.json、不写入 wiki/ 目录）
5. dry-run 报告中有 filter reason 统计
6. 可以用 dry-run 快速验证评分规则是否合理

## 建议验证命令

```bash
# 1. dry-run 测试
python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --dry-run

# 2. 检查 dry-run 报告是否存在
ls data/raw/moegirl/dry_run_report.md

# 3. 检查正式输出是否被污染
python -c "
import json, os
if os.path.exists('data/raw/moegirl/crawl_state.json'):
    s = json.loads(open('data/raw/moegirl/crawl_state.json').read())
    print(f'Visited: {len(s.get(\"visited\", []))}')
else:
    print('No crawl_state.json (good: dry-run did not pollute)')
"

# 4. 多种子 dry-run
python scripts/crawl_fsn.py --seeds config/fsn_seeds.txt --max-depth 1 --dry-run
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P0-4_report.md`，包含：

1. 修改了哪些文件
2. dry-run 报告的完整输出（至少一个种子的结果）
3. dry-run 是否污染了正式输出目录
4. Top N accepted 候选列表
5. Filter reason 统计
6. 未完成项
7. 下一阶段（P0-5）需要注意的事项
