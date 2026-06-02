# 阶段 P0-1：通用链接过滤

## 任务目标

实现 redlink / action=edit / 特殊命名空间等通用过滤机制。这些过滤规则是所有 IP 都适用的全局规则，不属于 FSN 专用。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景和改造目标
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划（P0-1 部分）
3. `docs/FSN_CRAWL_QUALITY_EVALUATION.md` — 质量评估报告（redlink 问题）
4. `lib/link_extractor.py` — 当前链接提取逻辑（重点看 `_should_skip_title` 和 `extract_links`）
5. `lib/relevance.py` — 当前 `is_allowed_page` 函数
6. `lib/checkpoint.py` — checkpoint 数据结构（理解 pending_queue 中条目的格式）
7. `scripts/crawl_fsn.py` — 当前爬虫主循环（看入队逻辑）

## 本阶段允许修改的范围

- `lib/link_extractor.py` — 增强 `_should_skip_title`、`extract_links`
- `lib/relevance.py` — 增强 `is_allowed_page`
- `lib/checkpoint.py` — 在 `load()` 中添加旧队列清洗逻辑
- `scripts/crawl_fsn.py` — 在入队前增加二次过滤调用

## 本阶段不要做的事情

1. 不要实现优先队列（那是 P0-2 的任务）
2. 不要实现 score_detail 日志（那是 P0-3 的任务）
3. 不要实现 profile loader（那是 P1-1 的任务）
4. 不要修改评分权重或关键词列表
5. 不要创建 fsn.yaml
6. 不要修改分类规则

## 具体修改要求

### 1. 增强 `_should_skip_title`（link_extractor.py）

当前已有过滤：index.php 开头、redlink=1、action=、特殊命名空间。

需要增强：

- 确保 `redlink=1` 检测覆盖 `&amp;redlink=1`（HTML 实体编码）
- 确保 `action=edit` 和 `action=raw` 被过滤
- 确保所有 MediaWiki 特殊命名空间被过滤（当前 `DEFAULT_SKIP_NAMESPACES` 已较全，检查是否有遗漏）
- 增加 `oldid=` 过滤（已有，确认生效）
- 增加 `diff=` 过滤
- 增加 `printable=yes` 过滤
- 增加 `disambiguation` 检测（消歧义页面标记）

### 2. 入队前二次过滤（crawl_fsn.py）

在 `_process_page` 中，链接入队前除了调用 `is_allowed_page`，还需要：

- 再次调用 `_should_skip_title` 检查
- 检查 URL 中是否包含 `redlink=1` 或 `action=edit`
- 检查标题 normalize 后是否属于特殊命名空间

### 3. checkpoint 加载时清洗旧队列（checkpoint.py）

在 `load()` 成功后，自动清洗 pending_queue：

- 移除 title 包含 `redlink=1` 的条目
- 移除 title 包含 `action=edit` 的条目
- 移除 title 属于特殊命名空间的条目
- 记录被移除的条目数量到日志

### 4. 过滤日志记录

每当一个链接被过滤时，在 crawl_log.jsonl 中记录：

```json
{
  "event": "link_filtered",
  "title": "...",
  "source": "...",
  "filter_reason": "redlink",
  "filter_stage": "extract|enqueue|checkpoint_resume"
}
```

`filter_reason` 应该是具体原因：`redlink`、`action_edit`、`special_namespace`、`oldid` 等。
`filter_stage` 应该区分是链接提取阶段、入队阶段、还是 checkpoint resume 阶段。

### 5. 缓存中旧 redlink 链接的处理

当前缓存中如果已存储了 redlink 页面的数据，不会重新过滤。

- 在 `PageCache.get()` 返回数据时，检查 meta 中的 `_extracted_links`，过滤掉 redlink
- 或者：在 link_extractor 的 `extract_links` 调用处，始终过滤返回结果

## 验收标准

1. 运行 `python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 10 --dry-run` 后：
   - pending_queue 中不包含任何 `redlink=1` 条目
   - pending_queue 中不包含任何 `action=edit` 条目
   - pending_queue 中不包含任何特殊命名空间条目
2. 使用 `--resume` 恢复旧的 crawl_state.json 时，旧队列中的 redlink 条目被自动移除
3. crawl_log.jsonl 中有 `link_filtered` 事件记录，包含 filter_reason 和 filter_stage
4. 不会误过滤正常的主命名空间条目

## 建议验证命令

```bash
# 1. 基本功能测试
python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 5 --dry-run

# 2. 检查 crawl_log 中是否有 link_filtered 事件
python -c "import json; [print(json.dumps(l)) for l in (json.loads(x) for x in open('data/raw/moegirl/crawl_log.jsonl')) if l.get('event')=='link_filtered']"

# 3. 检查 crawl_state 中是否有 redlink 残留
python -c "import json; s=json.loads(open('data/raw/moegirl/crawl_state.json').read()); redlinks=[x for x in s['pending_queue'] if 'redlink' in x.get('title','').lower() or 'action=edit' in x.get('title','').lower()]; print(f'redlink entries: {len(redlinks)}'); [print(x['title']) for x in redlinks]"
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P0-1_report.md`，包含：

1. 修改了哪些文件，每个文件改了什么
2. 新增了哪些函数/类
3. 验证命令运行结果
4. 过滤了多少 redlink / action=edit / 特殊命名空间条目（如果可以从日志统计）
5. 是否有误过滤正常条目的情况
6. 未完成项
7. 下一阶段（P0-2）需要注意的事项
