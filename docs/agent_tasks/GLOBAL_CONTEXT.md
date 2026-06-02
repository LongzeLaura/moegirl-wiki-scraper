# Global Context — Profile 化爬虫改造任务

> 本文件是所有阶段的公共背景，避免在每个阶段 prompt 中重复粘贴。

---

## 1. 项目定位

本仓库 `moegirl-pwb-test` 是一个萌娘百科爬虫项目。当前状态是 FSN (Fate/stay night) 专用爬虫，需要改造为**可配置的萌娘百科 IP 设定爬虫框架**，通过不同 profile 支持不同 IP。

**核心原则**：
- 爬虫核心代码不硬编码任何 IP 专有规则
- 所有 IP 相关规则（种子、关键词、排除词、评分权重、分类规则）放在 profile 配置中
- FSN 只是第一个 profile，不是最终形态

---

## 2. 当前代码结构

```
moegirl-pwb-test/
  config/
    fsn_crawl.yaml            # 主配置
    fsn_seeds.txt              # 种子列表
    fsn_include_keywords.txt   # 包含关键词
    fsn_exclude_keywords.txt   # 排除关键词
  scripts/
    crawl_fsn.py               # FSN 爬虫入口（715 行）
    fetch_page.py              # 单页爬取
  lib/
    fetcher.py                 # HTTP 抓取 + HTML 解析（238 行）
    link_extractor.py          # 链接提取 + 命名空间过滤（220 行）
    relevance.py               # 相关性评分 + 关键词匹配（295 行）
    classifier.py              # 页面分类（156 行）
    archiver.py                # 原始数据 + Markdown 归档（199 行）
    checkpoint.py              # 爬取状态持久化（108 行）
    cache.py                   # 文件缓存（71 行）
  data/raw/moegirl/            # 爬取输出
  wiki/                        # Markdown 归档输出
  docs/
    FSN_CRAWL_QUALITY_EVALUATION.md   # FSN 爬取质量评估
    PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md  # 完整改造计划
```

---

## 3. 已知问题（来自 FSN 评估报告）

1. **redlink 页面入队**：`index.php?title=xxx&action=edit&redlink=1` 被爬取归档
2. **source_is_fsn=+8 过强**：间桐樱所有 222/264 条链接都达到 8 分阈值
3. **include_keywords 过宽**："Fate" 命中所有含 Fate 的标题包括 FGO 角色
4. **FIFO BFS 队列**：低价值页面可能先于高价值页面被爬取
5. **评分不可解释**：日志中缺少 score_detail 字段
6. **分类规则过粗**：声优被分到 characters，缺子分类
7. **categories 提取失败**：所有页面的 categories 均为 []
8. **单种子 + depth=1 覆盖不足**：缺少世界观/地点/魔术体系条目

---

## 4. 改造目标结构

```
moegirl-wiki-scraper/
  config/
    profiles/
      fsn.yaml          # FSN profile
      template.yaml     # 新 IP 模板
  scripts/
    crawl_ip.py         # 通用入口
    crawl_fsn.py        # 兼容 wrapper（调用 crawl_ip.py --profile fsn）
  lib/
    crawler.py           # 通用爬虫核心
    scoring.py           # 通用评分框架
    profile.py           # Profile loader
    link_extractor.py    # 链接提取（含通用过滤）
    fetcher.py           # HTTP 抓取
    classifier.py        # 分类器（规则来自 profile）
    archiver.py          # 归档
    report.py            # crawl_report 生成
    checkpoint.py        # checkpoint / resume
    cache.py             # 缓存
  data/raw/moegirl/<profile_id>/   # 按 profile 隔离
  wiki/<profile_id>/               # 按 profile 隔离
```

---

## 5. 阶段总览

| 阶段 ID | 名称 | 类型 | 依赖 |
|---------|------|------|------|
| P0-1 | 通用链接过滤 | 通用核心 | 无 |
| P0-2 | 优先队列与 checkpoint | 通用核心 | 无 |
| P0-3 | score_detail 可解释日志 | 通用核心 | 无 |
| P0-4 | dry-run / score-only 模式 | 通用核心 | P0-3 |
| P0-5 | crawl_report 生成 | 通用核心 | P0-3 |
| P1-1 | profile loader 与通用入口 | Profile 化 | P0-1, P0-2, P0-3 |
| P1-2 | fsn.yaml 与 template.yaml | Profile 化 | P1-1 |
| P1-3 | 输出目录隔离与旧命令兼容 | Profile 化 | P1-1 |
| P1-4 | 文档更新与最终验证 | 收尾 | P1-2, P1-3 |

---

## 6. 关键约束

1. **不要在核心 Python 代码中硬编码 FSN 关键词**
2. **不要全局排除 FGO**——FGO 排除只属于 fsn.yaml
3. **不要全局排除声优/歌曲/萌属性**——这些是 profile 级别的 noise 配置
4. **不要重写整个项目**——渐进式改造
5. **不要引入 LLM 判断相关性**
6. **保持向后兼容**：旧的 `python scripts/crawl_fsn.py` 命令仍能运行

---

## 7. 相关文档路径

- 完整改造计划：`docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md`
- FSN 质量评估：`docs/FSN_CRAWL_QUALITY_EVALUATION.md`
- 阶段 prompt 目录：`docs/agent_tasks/`
- 阶段执行日志：`docs/agent_runs/`

---

## 8. 阶段报告格式

每个阶段完成后，agent 必须写入报告：

```
docs/agent_runs/<run_id>/<stage_id>_report.md
```

报告必须包含：
- 修改文件列表
- 新增文件列表
- 验证命令
- 验证结果
- 未完成项
- 下一阶段注意事项
