# 阶段 P1-2：fsn.yaml 与 template.yaml

## 任务目标

把 FSN 专用规则迁移到 profile 配置文件 `config/profiles/fsn.yaml`，并提供新 IP 模板 `config/profiles/template.yaml`。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划（P1-2 部分）
3. `lib/profile.py` — P1-1 实现的 profile loader（理解 profile YAML 格式）
4. `lib/relevance.py` — 当前 DEFAULT_INCLUDE_KEYWORDS 和 DEFAULT_EXCLUDE_KEYWORDS（需要迁移到 fsn.yaml）
5. `lib/classifier.py` — 当前 CATEGORY_RULES（需要迁移到 fsn.yaml）
6. `config/fsn_crawl.yaml` — 当前 FSN 配置
7. `config/fsn_seeds.txt` — 当前种子列表
8. `config/fsn_include_keywords.txt` — 当前包含关键词
9. `config/fsn_exclude_keywords.txt` — 当前排除关键词

## 本阶段允许修改的范围

- 新增 `config/profiles/fsn.yaml` — FSN profile
- 新增 `config/profiles/template.yaml` — 新 IP 模板
- `lib/relevance.py` — 清理 DEFAULT_INCLUDE_KEYWORDS / DEFAULT_EXCLUDE_KEYWORDS（如果 P1-1 未完成）
- `lib/classifier.py` — 清理 CATEGORY_RULES（如果 P1-1 未完成）

## 本阶段不要做的事情

1. 不要修改 crawl_ip.py（P1-1）
2. 不要修改输出目录结构（P1-3）
3. 不要修改 crawl_fsn.py（P1-3）
4. 不要修改 README 或设计文档（P1-4）
5. 不要全局排除 FGO——FGO 排除只属于 fsn.yaml
6. 不要全局排除声优/歌曲/萌属性——它们是 profile 级别的 noise 配置

## 具体修改要求

### 1. 创建 `config/profiles/fsn.yaml`

根据完整改造计划和 FSN 评估报告，创建 FSN profile。

必须包含：

#### 1.1 基本信息

```yaml
id: fsn
name: Fate/stay night
description: Fate/stay night 设定爬取 profile
site:
  source: moegirl
```

#### 1.2 爬取默认值

```yaml
crawl:
  default_max_depth: 1
  default_max_pages: 50
  default_min_score: 12
```

注意：`default_min_score` 建议从 8 提高到 12，因为 source_relevance_bonus 从 +8 降到 +3。

#### 1.3 种子列表

种子至少包含以下页面（来自完整改造计划）：

- 作品主条目：Fate/stay night
- 核心角色：间桐樱、远坂凛、卫宫士郎、Saber、Archer、Lancer、Rider、Caster、Assassin、Berserker
- 真名：阿尔托莉雅·潘德拉贡、英灵卫宫、库·丘林、美杜莎、美狄亚、佐佐木小次郎、赫拉克勒斯、吉尔伽美什
- 配角：言峰绮礼、伊莉雅斯菲尔·冯·爱因兹贝伦、间桐慎二、间桐脏砚、藤村大河、柳洞一成、葛木宗一郎、美缀绫子
- 世界观：圣杯战争、第五次圣杯战争、令咒、从者、御主、英灵、宝具、固有结界、无限剑制、魔术回路、魔术刻印、小圣杯、大圣杯
- 地点：冬木市、穗群原学园、柳洞寺、冬木教会、远坂邸、间桐邸

#### 1.4 核心关键词

分组织：

- `characters`：核心角色名（不包含 "Fate"、"Class" 等泛化词）
- `world`：圣杯战争、令咒、从者、宝具、固有结界、魔术回路等
- `locations`：冬木市、穗群原学园、柳洞寺等
- `factions`：远坂家、间桐家、爱因兹贝伦等
- `items`：宝具名、武器名等
- `plot`：Fate 线、UBW 线、HF 线等

**关键原则**：
- "Fate" 不应作为普通 substring 高分词
- "Saber"、"Archer" 可以作为角色别名，但不能让所有 "(Fate)" 后缀页面自动高分
- "魔术" 可以保留为低权重或组合规则
- 不应包含 "Fate/Grand Order" 在 include 中

#### 1.5 related_ip_allowlist

```yaml
related_ip_allowlist:
  - Fate/Zero
  - Fate/hollow ataraxia
```

#### 1.6 related_ip_blocklist

```yaml
related_ip_blocklist:
  - Fate/Grand Order
  - FGO
  - Fate/kaleid
  - 魔法少女伊莉雅
  - Fate/Apocrypha
  - Fate/EXTRA
  - Fate/Prototype
  - Fate/strange Fake
```

**注意**：FGO 排除只属于 fsn.yaml。如果未来创建 fgo.yaml，FGO 应该变成核心目标。

#### 1.7 noise_keywords

分组织（参考评估报告中的建议）：

```yaml
noise_keywords:
  voice_actor:
    - 声优
    - 配音
    - 配音演员
    - CV
    - 日本声优
    - 中国声优
    - 台湾声优
  music:
    - 歌曲
    - 歌手
    - 作词
    - 作曲
    - 编曲
    - 演唱
    - OP
    - ED
    - 片头曲
    - 片尾曲
    - 主题曲
    - 角色歌
  moe_traits:
    - 萌属性
    - 萌点
    - 中长发
    - 大和抚子
    - 小恶魔系
    - 家务全能
    - 料理达人
    - 连衣裙
  staff_company:
    - 动画公司
    - 制作公司
    - 出版社
    - KADOKAWA
    - ufotable
    - SILVER LINK
```

#### 1.8 评分权重

参考评估报告的建议，调整评分权重：

```yaml
scoring:
  seed_bonus: 100
  title_keyword_bonus: 8
  alias_keyword_bonus: 6
  category_keyword_bonus: 4
  source_relevance_bonus: 3    # 从 +8 降到 +3（最关键改动）
  allowed_related_ip_bonus: 2
  blocked_related_ip_penalty: -20
  noise_keyword_penalty: -15
  short_generic_title_penalty: -8
```

#### 1.9 分类规则

从 classifier.py 迁移到 profile：

```yaml
classification:
  characters:
    label: 角色
    keywords: [...]
  world:
    label: 世界观/设定
    keywords: [...]
  locations:
    label: 地点
    keywords: [...]
  factions:
    label: 组织/阵营
    keywords: [...]
  items:
    label: 道具/宝具
    keywords: [...]
  plot-arcs:
    label: 剧情/路线
    keywords: [...]
```

### 2. 创建 `config/profiles/template.yaml`

提供新 IP 的模板，所有字段为空或示例值：

```yaml
id: example_ip
name: Example IP
description: 用于说明如何创建一个新的 IP profile

site:
  source: moegirl

crawl:
  default_max_depth: 1
  default_max_pages: 50
  default_min_score: 10

seeds: []

core_keywords:
  characters: []
  world: []
  locations: []
  factions: []
  items: []
  plot: []

aliases: {}

related_ip_allowlist: []
related_ip_blocklist: []

noise_keywords:
  voice_actor: []
  music: []
  moe_traits: []
  staff_company: []

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
    keywords: []
  world:
    label: 世界观/设定
    keywords: []
  locations:
    label: 地点
    keywords: []
  factions:
    label: 组织/阵营
    keywords: []
  items:
    label: 道具/宝具
    keywords: []
  plot-arcs:
    label: 剧情/路线
    keywords: []
```

### 3. 清理核心代码中的硬编码

如果 P1-1 未完成以下清理，本阶段必须完成：

- `relevance.py`：`DEFAULT_INCLUDE_KEYWORDS` 改为空列表 `[]`
- `relevance.py`：`DEFAULT_EXCLUDE_KEYWORDS` 改为基本 Wiki 命名空间过滤列表（不含 FSN 特定规则）
- `relevance.py`：`is_fsn_page` 重命名为 `is_relevant_page`
- `classifier.py`：`CATEGORY_RULES` 改为空 dict `{}`

### 4. 验证 profile 加载

确保 `crawl_ip.py --profile fsn --dry-run` 能正确加载 fsn.yaml 的所有字段。

## 验收标准

1. `config/profiles/fsn.yaml` 包含所有 FSN 专用规则
2. `config/profiles/template.yaml` 可作为新 IP 的模板
3. Python 核心代码中搜索不到 "圣杯战争"、"冬木市"、"间桐樱"、"FGO" 等硬编码
4. `python scripts/crawl_ip.py --profile fsn --dry-run` 能正确运行
5. FSN profile 的评分规则与评估报告中的建议一致（source_relevance_bonus=3）

## 建议验证命令

```bash
# 1. 检查 profile 文件
cat config/profiles/fsn.yaml
cat config/profiles/template.yaml

# 2. 检查核心代码是否有 FSN 硬编码
rg -i "圣杯战争|冬木市|间桐樱|FGO|远坂凛|卫宫士郎" lib/ --type py

# 3. 验证 profile 加载
python scripts/crawl_ip.py --profile fsn --dry-run --max-depth 1

# 4. 验证评分权重
python -c "
from lib.profile import ProfileLoader
from pathlib import Path
loader = ProfileLoader(Path('config/profiles'))
p = loader.load('fsn')
print('source_relevance_bonus:', p['scoring']['source_relevance_bonus'])
print('seeds count:', len(p['seeds']))
print('blocklist:', p['related_ip_blocklist'])
"

# 5. 列出可用 profile
python scripts/crawl_ip.py --list-profiles
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P1-2_report.md`，包含：

1. 新增了哪些文件
2. fsn.yaml 中各字段的数量（seeds 数、core_keywords 数、noise_keywords 数等）
3. 核心代码中是否还有 FSN 硬编码残留
4. source_relevance_bonus 的值（应该是 3 而不是 8）
5. 验证命令运行结果
6. 未完成项
7. 下一阶段（P1-3）需要注意的事项
