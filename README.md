# moegirl-pwb-test

从**萌娘百科**（zh.moegirl.org.cn）抓取单页 HTML 源码并提取纯文本的最小项目。

---

## 抓取原理

萌娘百科的 API 禁用了内容读取（`prop=revisions` 返回 `action-notallowed`，即使登录也不行）。
本项目使用 `curl_cffi` 模拟 Edge 浏览器 TLS 指纹，绕过 Cloudflare WAF，直接抓取渲染后的 HTML 页面。

```
浏览器 → Cloudflare → Moegirlpedia → 渲染后的 HTML
                                    ↑
curl_cffi (Edge TLS 指纹) ──────────┘
```

---

## 项目结构

```
moegirl-pwb-test/
├── pywikibot/              # Python 虚拟环境
├── requirements.txt        # 依赖
├── scripts/
│   └── fetch_page.py       # 抓取脚本
├── data/
│   ├── raw_wikitext/       # *.html  +  *.txt（--text 模式）
│   ├── raw_json/           # *.json  元信息
│   └── markdown/           # 预留
└── README.md
```

---

## 快速开始（Windows PowerShell）

```powershell
# 1. 创建虚拟环境
cd moegirl-pwb-test
python -m venv pywikibot

# 2. 激活
.\pywikibot\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 抓取页面
python scripts\fetch_page.py "远坂凛"

# 5. 抓取并提取纯文本
python scripts\fetch_page.py "远坂凛" --text

# 6. 在其他 Wiki 上尝试 API 模式
python scripts\fetch_page.py "Albert Einstein" --api
```

---

## 命令行选项

| 选项 | 作用 |
|------|------|
| *(默认)* | 抓取 HTML 页面源码，保存为 `.html` |
| `--text` | 额外从 HTML 中提取纯文本，保存为 `.txt` |
| `--api` | 尝试通过 Pywikibot API 获取 wikitext（仅在允许 API 读取的 Wiki 上有效） |

---

## 输出文件

| 文件 | 触发条件 | 内容 |
|------|----------|------|
| `raw_wikitext/*.html` | 默认 | 完整 HTML 页面源码（~200 KB） |
| `raw_wikitext/*.txt` | `--text` | 提取的纯文本内容（~18 KB） |
| `raw_json/*.json` | 默认 | 元信息 |

### JSON 示例

```json
{
  "title": "远坂凛",
  "pageid": 6179,
  "namespace": 0,
  "revision": 8427374,
  "redirect": false,
  "exists": true,
  "source_title": "远坂凛",
  "url": "https://zh.moegirl.org.cn/%E8%BF%9C%E5%9D%82%E5%87%9B",
  "html_size": 202362,
  "method": "http_scrape"
}
```

不存在页面的 JSON：
```json
{
  "title": "不存在的页面xyz123",
  "pageid": 0,
  "exists": false,
  ...
}
```

---

## 依赖

| 包 | 用途 |
|----|------|
| `curl_cffi` | 模拟浏览器 TLS 指纹，绕过 Cloudflare |
| `pywikibot` | MediaWiki API 客户端（`--api` 模式使用） |
| `wikitextparser` | 预留：wikitext 解析 |

---

## 常见问题

### 为什么不用 API 获取 wikitext？

萌娘百科在服务器层面禁用了内容读取 API。即使使用 Bot 密码登录成功，
`action=query&prop=revisions` 仍然返回 `action-notallowed`。
这是站点策略，非脚本缺陷。

### HTML vs wikitext 的区别？

- **HTML**：渲染后的网页，包含导航栏、CSS、JS、已展开的模板。~200 KB。
- **Wikitext**：MediaWiki 标记源码，含 `{{模板}}`、`[[链接]]`。~30 KB。萌娘百科不提供。

### 纯文本提取质量如何？

`--text` 模式提取 `mw-parser-output` 区域中的可见文本。
能获取到：标题、正文、信息框数据、列表等。
会丢失：模板结构、分类标记、Wiki 链接语法。

---

---

## FSN 爬虫（crawl_fsn.py）

围绕 Fate/stay night 相关设定的**有边界、低风险、可恢复**爬虫。

### 快速开始

```powershell
# 1. 安装依赖（含 PyYAML）
pip install -r requirements.txt

# 2. 预演模式：查看会爬哪些页面，不实际大量请求
python scripts\crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 10 --delay 5 --dry-run

# 3. 正式爬取
python scripts\crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 10 --delay 5

# 4. 从文件读取种子列表
python scripts\crawl_fsn.py --seeds config\fsn_seeds.txt --max-depth 2 --max-pages 80

# 5. 断点续传
python scripts\crawl_fsn.py --seed "间桐樱" --resume
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--seed` | 单个起始页面标题 | 无 |
| `--seeds` | 起始页面列表文件路径 | 无 |
| `--max-depth` | 最大链接扩展深度 | YAML 配置: 1 |
| `--max-pages` | 最大爬取页面数 | YAML 配置: 50 |
| `--delay` | 请求间隔（秒） | YAML 配置: 4.0 |
| `--jitter` | 间隔随机抖动比例 (0.0-1.0) | YAML 配置: 0.3 |
| `--max-retries` | 请求失败最大重试次数 | YAML 配置: 3 |
| `--min-score` | 链接相关性最低分数 | YAML 配置: 8 |
| `--dry-run` | 预演模式，只爬取种子页并分析链接 | False |
| `--resume` | 从上次中断处继续 | False |
| `--force` | 忽略缓存重新抓取 | False |
| `--config` | YAML 配置文件路径 | `config/fsn_crawl.yaml` |
| `--output-dir` | 输出根目录（覆盖 YAML 配置） | 无 |
| `--include-keywords` | 包含关键词文件路径 | 无 |
| `--exclude-keywords` | 排除关键词文件路径 | 无 |

### 爬取边界控制

1. **种子页面**：从 `--seed`、`--seeds` 或 YAML 配置指定的起始页面开始
2. **max_depth**：BFS 层级限制，默认 1（只爬种子页和其直接链接）
3. **max_pages**：绝对上限，达到后立即停止
4. **相关性评分**：每个候选链接通过规则评分，低于 `min_relevance_score` 的不进入队列
5. **include/exclude keywords**：基于关键词的包含/排除过滤
6. **命名空间过滤**：默认只爬取主命名空间（普通条目），排除 User、Template、File、Help 等
7. **visited 去重**：同页面只爬一次，基于规范化标题去重
8. **index.php/redlink 过滤**：自动排除编辑页、历史页、不存在的页面

### 请求速度控制（安全优先）

- 默认单线程爬取
- 每请求间隔 4.0 秒，带 ±30% 随机抖动
- 遇到 429/5xx/网络错误时指数退避重试（10s → 30s → 60s）
- 已抓取页面优先读本地缓存，避免重复请求
- 不进行任何写入操作（纯读取）

### 输出结构

```
data/raw/moegirl/
  pages/<title>.json        # 原始元数据 + 提取的链接
  text/<title>.txt           # 纯文本正文
  crawl_state.json           # 爬取状态（checkpoint）
  crawl_log.jsonl            # 事件日志（JSON Lines）

wiki/
  sources/moegirl/<title>.md # 来源页 Markdown
  characters/<title>.md      # 角色分类
  world/<title>.md           # 世界观/设定分类
  locations/<title>.md       # 地点分类
  factions/<title>.md        # 组织/阵营分类
  items/<title>.md           # 道具/宝具分类
  plot-arcs/<title>.md       # 剧情/路线分类
  uncategorized/<title>.md   # 未分类
```

### Markdown 文件格式

每个归档文件包含 YAML frontmatter：

```yaml
---
title: 间桐樱
source: moegirl
source_page: 间桐樱
fetched_at: 2026-06-02T02:43:49Z
category: characters
crawl_depth: 0
related_pages:
  - Fate/stay night
  - 卫宫士郎
category_reason: {"scores": {...}, "best_category": "characters"}
---
```

### 分类规则

分类基于可解释的关键词启发式规则（不依赖大模型）：

| 分类 | 触发关键词示例 |
|------|---------------|
| characters | 角色、人物、声优、身高、从者、Master、萌点 |
| world | 圣杯战争、魔术、令咒、职阶、根源、魔力 |
| locations | 地点、城市、学校、冬木、教会、宅邸 |
| factions | 组织、阵营、协会、家族、魔术协会 |
| items | 宝具、道具、武器、剑、礼装、Noble Phantasm |
| plot-arcs | 路线、剧情、结局、Unlimited Blade Works、Heaven's Feel |

### 相关性评分规则

链接进入待爬队列前通过以下规则评分（不依赖大模型）：

- 标题命中 FSN 角色名/关键词：+5 分/关键词
- 显示文本命中关键词：+3 分/关键词
- 页面分类（categories）命中关键词：+6 分/关键词
- 高价值分类命中（如"Fate系列""TYPE-MOON作品"）：+10 分
- 来源页面是 FSN 相关页面：+8 分
- 短泛标题惩罚：-5 分
- 排除关键词命中：直接 -100 分（排除）

默认阈值为 8 分，可在 YAML 配置中调整。

### 配置文件

```
config/
  fsn_crawl.yaml            # 主配置（爬取边界、延迟、分类规则、输出路径）
  fsn_seeds.txt              # 种子页面列表
  fsn_include_keywords.txt   # 包含关键词（FSN 角色名、概念等）
  fsn_exclude_keywords.txt   # 排除关键词（帮助、模板、消歧义等）
```

### 避免过度爬取指南

1. **始终从 --dry-run 开始**：先预览会爬哪些页面
2. **max-depth 设小**：默认 1，最多 2
3. **max-pages 设小**：先用 10-30 页测试
4. **提高 min-score 阈值**：默认 8，调到 12-15 可更严格
5. **检查日志**：`data/raw/moegirl/crawl_log.jsonl` 中可以看到每个被排除链接的原因
6. **使用 --resume**：中断后可以继续，不会重复请求

### 新增依赖

| 包 | 用途 |
|----|------|
| `pyyaml>=6.0` | 读取 YAML 配置文件（`fsn_crawl.yaml`） |

选择原因：PyYAML 是 Python 生态最常用的 YAML 解析库（每月 ~1.5 亿次下载），
体积极小（~150KB），无外部依赖，是最低风险的配置解析方案。

### 与 fetch_page.py 的关系

`fetch_page.py` 保持不变，仍然可以独立使用进行单页爬取。
`crawl_fsn.py` 使用 `lib/` 中的共享模块（`fetcher.py` 等），两者互不干扰。

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1 | 2026-06-02 | 初始版本：单页爬取（fetch_page.py）+ FSN 专题爬虫（crawl_fsn.py），含相关性评分、分类归档、断点续传 |

---

## License

仅用于学习和测试目的。萌娘百科内容适用 CC BY-NC-SA 3.0。