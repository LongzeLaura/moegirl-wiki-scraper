# 阶段 P1-1：profile loader 与通用入口

## 任务目标

实现 profile 加载机制和通用入口脚本 `crawl_ip.py`。这是从 FSN 专用爬虫到通用框架的关键转折。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景和目标结构
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划（P1-1 部分）
3. `scripts/crawl_fsn.py` — 当前入口（理解需要抽象什么）
4. `lib/relevance.py` — 当前硬编码的 DEFAULT_INCLUDE_KEYWORDS 和 DEFAULT_EXCLUDE_KEYWORDS
5. `lib/classifier.py` — 当前硬编码的 CATEGORY_RULES
6. `config/fsn_crawl.yaml` — 当前 FSN 配置
7. `config/fsn_seeds.txt` — 当前种子列表
8. `config/fsn_include_keywords.txt` — 当前包含关键词
9. `config/fsn_exclude_keywords.txt` — 当前排除关键词

## 本阶段允许修改的范围

- 新增 `lib/profile.py` — profile loader
- 新增 `scripts/crawl_ip.py` — 通用入口
- `lib/relevance.py` — 移除 DEFAULT_INCLUDE_KEYWORDS/DEFAULT_EXCLUDE_KEYWORDS 的硬编码默认值，改为从 profile 接收
- `lib/classifier.py` — 移除 CATEGORY_RULES 硬编码默认值，改为从 profile 接收
- `scripts/crawl_fsn.py` — 可微调以适配 profile（但不改核心逻辑）

## 本阶段不要做的事情

1. 不要创建 fsn.yaml 的最终内容（P1-2 的任务）
2. 不要创建 template.yaml（P1-2 的任务）
3. 不要修改输出目录结构（P1-3 的任务）
4. 不要修改 crawl_fsn.py 使其变成 wrapper（P1-3 的任务）
5. 不要修改 README 或设计文档（P1-4 的任务）

## 具体修改要求

### 1. 新增 `lib/profile.py`

实现 `ProfileLoader` 类：

```python
class ProfileLoader:
    """Load and validate a crawl profile from YAML."""

    def __init__(self, profiles_dir: Path = None):
        """
        Args:
            profiles_dir: Directory containing profile YAML files.
                         Default: config/profiles/
        """
        ...

    def load(self, profile_id: str) -> dict:
        """Load a profile by ID.

        Args:
            profile_id: e.g. "fsn"

        Returns:
            Profile dict with keys: id, name, description, site, crawl,
            seeds, core_keywords, aliases, related_ip_allowlist,
            related_ip_blocklist, noise_keywords, scoring, classification

        Raises:
            FileNotFoundError: if profile YAML doesn't exist
            ValueError: if profile is invalid
        """
        ...

    def list_profiles(self) -> list[str]:
        """List available profile IDs."""
        ...

    def validate(self, profile: dict) -> list[str]:
        """Validate a profile dict. Returns list of warning strings."""
        ...
```

### 2. Profile YAML 格式

Profile YAML 应包含以下顶层键：

```yaml
id: fsn
name: Fate/stay night
description: Fate/stay night 设定爬取 profile

site:
  source: moegirl

crawl:
  default_max_depth: 1
  default_max_pages: 50
  default_min_score: 8

seeds:
  - Fate/stay night
  - 间桐樱
  - ...

core_keywords:
  characters:
    - 卫宫士郎
    - 远坂凛
    - ...
  world:
    - 圣杯战争
    - 令咒
    - ...
  locations:
    - 冬木市
    - ...

aliases: {}  # 角色别名映射

related_ip_allowlist:
  - Fate/Zero
  - Fate/hollow ataraxia

related_ip_blocklist:
  - Fate/Grand Order
  - FGO
  - ...

noise_keywords:
  voice_actor:
    - 声优
    - 配音
    - ...
  music:
    - 歌曲
    - 歌手
    - ...
  moe_traits:
    - 萌属性
    - ...
  staff_company:
    - 动画公司
    - ...

scoring:
  seed_bonus: 100
  title_keyword_bonus: 8
  alias_keyword_bonus: 6
  category_keyword_bonus: 4
  source_relevance_bonus: 3
  allowed_related_ip_bonus: 2
  blocked_related_ip_penalty: -20
  noise_keyword_penalty: -15
  short_generic_title_penalty: -8

classification:
  characters:
    label: 角色
    keywords: [...]
  world:
    label: 世界观/设定
    keywords: [...]
  ...
```

### 3. Profile 加载与配置合并

`crawl_ip.py` 的配置加载流程：

1. 加载 profile YAML
2. 从 profile 中提取：
   - seeds
   - include_keywords（从 core_keywords 展开）
   - exclude_keywords（从 noise_keywords 展开 + related_ip_blocklist）
   - scoring weights
   - classification rules
3. 命令行参数覆盖 profile 默认值

### 4. 新增 `scripts/crawl_ip.py`

通用入口，核心参数：

```bash
python scripts/crawl_ip.py --profile fsn
python scripts/crawl_ip.py --profile fsn --max-depth 1 --max-pages 50 --min-score 10
python scripts/crawl_ip.py --profile fsn --seed "间桐樱"
python scripts/crawl_ip.py --profile fsn --force
python scripts/crawl_ip.py --profile fsn --resume
python scripts/crawl_ip.py --profile fsn --dry-run
```

参数列表：
- `--profile` — 必需，profile ID
- `--seed` — 覆盖 profile 中的种子（单种子）
- `--seeds` — 覆盖 profile 中的种子（文件）
- `--max-depth` — 覆盖 profile 中的 default_max_depth
- `--max-pages` — 覆盖 profile 中的 default_max_pages
- `--min-score` — 覆盖 profile 中的 default_min_score
- `--delay` — 请求间隔
- `--force` — 忽略缓存
- `--resume` — 断点续传
- `--dry-run` — 预演模式
- `--list-profiles` — 列出可用 profile

### 5. 核心代码不硬编码 FSN

关键：在 `crawl_ip.py` 和 `lib/` 中的代码不应包含 "FSN"、"间桐樱"、"圣杯战争" 等硬编码。

这些内容只应存在于 `config/profiles/fsn.yaml` 中。

**注意**：`relevance.py` 中的 `DEFAULT_INCLUDE_KEYWORDS` 和 `DEFAULT_EXCLUDE_KEYWORDS` 需要保留为空列表或移除。所有关键词应从 profile 传入。

**注意**：`classifier.py` 中的 `CATEGORY_RULES` 需要支持从 profile 传入。保留默认空规则，实际规则从 profile 的 `classification` 字段加载。

**注意**：`is_fsn_page` 函数名需要改为通用名如 `is_profile_page` 或 `is_relevant_page`。其逻辑不应硬编码 FSN 检测，而是基于 profile 配置判断。

### 6. profile_id 传递

profile_id 应贯穿整个爬取流程：
- checkpoint 中记录 profile_id
- crawl_log 中记录 profile_id
- crawl_report 中记录 profile_id
- pending_queue 中每个条目记录 profile_id

## 验收标准

1. `python scripts/crawl_ip.py --list-profiles` 能列出可用 profile
2. `python scripts/crawl_ip.py --profile fsn --dry-run` 能正确加载 profile 并运行
3. 核心代码（lib/*.py）中不含 FSN 硬编码关键词
4. `relevance.py` 的 `DEFAULT_INCLUDE_KEYWORDS` 变为空列表或被移除
5. `classifier.py` 的 `CATEGORY_RULES` 变为空 dict 或被移除
6. `is_fsn_page` 被重命名为通用名称
7. 不指定 `--profile` 时报清晰错误

## 建议验证命令

```bash
# 1. 列出 profile
python scripts/crawl_ip.py --list-profiles

# 2. dry-run 测试
python scripts/crawl_ip.py --profile fsn --dry-run --max-depth 1

# 3. 检查核心代码是否有 FSN 硬编码
rg -i "间桐樱|圣杯战争|冬木市|FGO" lib/ --type py

# 4. 检查 is_fsn_page 是否被重命名
rg "is_fsn_page" lib/ --type py
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P1-1_report.md`，包含：

1. 新增了哪些文件
2. 修改了哪些文件
3. Profile YAML 的完整格式说明
4. 验证命令运行结果
5. 核心代码中是否还有 FSN 硬编码残留
6. 未完成项
7. 下一阶段（P1-2）需要注意的事项
