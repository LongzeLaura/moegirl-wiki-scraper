你现在要根据已有的 FSN 爬取质量评估结果，改进当前萌娘百科爬虫项目。

项目地址：
https://github.com/LongzeLaura/moegirl-wiki-scraper/tree/master

重要前提：
这个爬虫项目不能被改成 Fate/stay night 专用爬虫。FSN 只是当前第一个实验目标。未来还要支持其他 IP / 作品 / 世界观，例如其他 Fate 作品、其他动漫、游戏、小说、Galgame 等。

因此，本次改造的核心目标不是“把 FSN 规则写死进代码”，而是：

1. 把爬虫核心能力做成通用机制。
2. 把 FSN 相关的种子、关键词、排除词、分类规则、评分权重放到独立 profile 配置中。
3. 用 FSN 这次评估报告中的问题作为第一个 profile 的回归测试案例。
4. 保证未来可以新增其他 IP profile，而不需要改核心代码。

请严格注意：
不要把“FGO 排除”“圣杯战争加分”“冬木市加分”“FSN 来源页加分”等写死进 Python 代码。
这些只能属于 config/profiles/fsn.yaml 或类似配置文件。

---

# 一、请先阅读项目和评估报告

请先阅读：

1. 当前项目结构。
2. 当前爬虫相关代码，尤其是：
   - scripts/crawl_fsn.py
   - scraper/link_extractor.py
   - scraper/fetcher.py
   - scraper/classifier.py
   - scraper/archiver.py
   - 配置文件
3. 已有评估报告：
   - docs/FSN_CRAWL_QUALITY_EVALUATION.md
   - 如果路径不同，请自行定位。

评估报告中的核心问题包括：

1. 从「间桐樱」单种子出发，实际覆盖面严重不足。
2. redlink、action=edit 页面进入队列和归档。
3. 声优、歌曲、萌属性、制作人员等页面被误收录。
4. source_is_fsn = +8 过强，导致只要来自 FSN 页面就容易入队。
5. include_keywords 过宽，例如 Fate、魔术、Saber、Archer 等词容易误伤。
6. BFS FIFO 队列导致高分核心页面可能排在低价值页面之后。
7. 日志不足以解释每个链接为什么被收录或排除。
8. 分类规则过粗，且不适合长期支持多个 IP。

这些问题要修，但修法必须是“通用框架 + FSN profile”，不能是“FSN 专用爬虫”。

---

# 二、总体改造目标

请把项目改造成如下结构方向：

```text
moegirl-wiki-scraper/
  config/
    profiles/
      fsn.yaml
      template.yaml
  scripts/
    crawl_ip.py
    crawl_fsn.py          # 可选：兼容旧命令的 wrapper
  scraper/
    crawler.py
    scoring.py
    profile.py
    link_extractor.py
    fetcher.py
    classifier.py
    archiver.py
    report.py
````

不要求文件名完全一致，但要实现类似分层：

## 1. 通用核心层

负责：

* 页面抓取
* 链接提取
* redlink / 特殊命名空间过滤
* checkpoint / resume
* 缓存
* 优先队列
* 评分框架
* 日志
* 报告生成
* 文本归档

这一层不应该知道“FSN”“圣杯战争”“冬木市”“FGO”等具体 IP 内容。

## 2. Profile 配置层

负责：

* 当前要爬哪个 IP
* 种子页面
* 核心关键词
* 别名
* 允许扩展的相关作品
* 默认排除的相关作品
* 噪声类型
* 分类规则
* 评分权重
* 输出目录命名

例如：

```yaml
id: fsn
name: Fate/stay night
description: Fate/stay night 设定爬取 profile

site:
  source: moegirl

crawl:
  default_max_depth: 1
  default_max_pages: 50
  default_min_score: 10

seeds:
  - Fate/stay night
  - 间桐樱
  - 远坂凛
  - 卫宫士郎
  - Saber
  - 阿尔托莉雅·潘德拉贡
  - 言峰绮礼
  - 伊莉雅斯菲尔·冯·爱因兹贝伦
  - 圣杯战争
  - 第五次圣杯战争
  - 令咒
  - 从者
  - 御主
  - 英灵
  - 宝具
  - 固有结界
  - 无限剑制
  - 魔术回路
  - 冬木市
  - 穗群原学园
  - 柳洞寺
  - 冬木教会

core_keywords:
  characters:
    - 卫宫士郎
    - 远坂凛
    - 间桐樱
    - Saber
    - Archer
    - Lancer
    - Rider
    - Caster
    - Assassin
    - Berserker
    - 吉尔伽美什
    - 言峰绮礼
    - 伊莉雅斯菲尔
    - 间桐慎二
    - 间桐脏砚
  world:
    - 圣杯战争
    - 第五次圣杯战争
    - 令咒
    - 从者
    - 御主
    - 英灵
    - 宝具
    - 固有结界
    - 无限剑制
    - 魔术回路
    - 魔术刻印
    - 小圣杯
    - 大圣杯
  locations:
    - 冬木市
    - 穗群原学园
    - 远坂邸
    - 间桐邸
    - 柳洞寺
    - 冬木教会

related_ip_allowlist:
  - Fate/Zero
  - Fate/hollow ataraxia

related_ip_blocklist:
  - Fate/Grand Order
  - FGO
  - Fate/kaleid
  - 魔法少女伊莉雅
  - Fate/Apocrypha
  - Fate/EXTRA
  - Fate/Prototype
  - Fate/strange Fake

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
```

以上只是参考结构。你可以根据项目实际情况调整字段名，但必须满足：

* FSN 规则在 profile 中。
* 核心代码不硬编码 FSN。
* 新增其他 IP 时可以复制 template.yaml 后修改配置。

---

# 三、必须完成的通用修复

以下规则应该是所有 IP 都适用的全局修复。

---

## P0-1：全局过滤 redlink / 编辑页 / 特殊命名空间

这是通用规则，不属于 FSN。

必须过滤：

```text
redlink=1
action=edit
index.php?title=xxx&action=edit
Special:
File:
Category:
Template:
Help:
User:
Talk:
萌娘百科:
MediaWiki:
```

要求：

1. 链接提取阶段过滤一次。
2. 入队前再过滤一次。
3. resume checkpoint 时也过滤一次旧数据。
4. 缓存中如果存在旧 redlink，也不能重新污染队列。
5. 日志记录过滤原因。

验收标准：

* redlink 页面不会进入 pending queue。
* redlink 页面不会进入 visited。
* redlink 页面不会被保存到 data/raw 或 wiki。
* 使用 --resume 也不会继续爬旧 redlink。

---

## P0-2：通用优先队列替代 FIFO BFS

这是通用能力，不属于 FSN。

当前 FIFO BFS 的问题是：
低价值页面可能先于高价值页面被爬取，max_pages 较小时浪费配额。

请改为优先队列：

排序建议：

```text
seed_priority desc
score desc
depth asc
enqueue_order asc
```

checkpoint 中保存：

```yaml
title
url
depth
score
score_detail
source_title
enqueue_order
profile_id
```

要求：

1. seed 页面最高优先级。
2. 高分页面优先。
3. depth 小的页面优先。
4. 同分时按 enqueue_order 保持可复现。
5. resume 后优先队列顺序应保持一致。

验收标准：

* max_pages 较小时，高价值页面不会被低价值页面挤掉。
* checkpoint / resume 仍然可用。
* 旧 checkpoint 格式要么兼容，要么给出清晰错误提示。

---

## P0-3：通用 score_detail 日志

评分系统必须可解释。

每个候选链接都应该记录：

```yaml
title
url
source_title
depth
profile_id
score
decision: accepted / rejected / filtered
filter_reason
score_detail:
  seed_bonus
  title_keyword_hits
  alias_hits
  category_hits
  source_relevance_bonus
  allowed_related_ip_hits
  blocked_related_ip_hits
  noise_keyword_hits
  short_generic_title_penalty
  final_score
```

不要求字段完全一致，但必须能回答：

1. 为什么这个页面被收录？
2. 为什么这个页面被排除？
3. 它命中了哪些关键词？
4. 它受到了哪些惩罚？
5. 它来自哪个页面？
6. 它属于哪个 profile？

验收标准：

* crawl_log.jsonl 能直接用于分析误收录和漏爬。
* 不需要人工读代码才能知道 score 为什么是这个值。

---

## P0-4：通用 dry-run / score-only 模式

新增 dry-run 模式，用于调试 profile。

示例命令：

```bash
python scripts/crawl_ip.py --profile fsn --dry-run --max-depth 1
```

dry-run 要求：

1. 可以读取种子。
2. 可以抓取种子页面并提取出链。
3. 可以对候选链接评分。
4. 可以输出 accepted / rejected / filtered 列表。
5. 不正式归档页面。
6. 不污染正式输出目录。

输出内容至少包括：

```text
- seeds 数量
- 每个 seed 的出链数量
- accepted 候选页面 Top N
- rejected 候选页面 Top N
- filtered 原因统计
- 高风险通过页面
- 低分但疑似核心页面
```

验收标准：

* 新增 profile 时，可以先用 dry-run 检查评分规则。
* 不需要真正爬几十页才能知道 profile 是否过宽。

---

## P0-5：通用 crawl_report

每次正式爬取后生成报告：

```text
data/raw/moegirl/<profile_id>/crawl_report.md
```

或者类似路径。

报告至少包含：

```markdown
# Crawl Report

## Profile

## Seeds

## Crawl Config

## Summary
- visited 数
- accepted 数
- rejected 数
- filtered 数
- error 数
- pending_queue 剩余数
- stop reason

## Depth Distribution

## Category Distribution

## Top Accepted Pages

## Top Rejected Pages

## Filter Reason Stats

## Suspicious Accepted Pages

## High-score Pending Pages

## Notes
```

验收标准：

* 每次实验后可以快速判断质量。
* 报告中必须包含 profile_id，避免不同 IP 的数据混淆。

---

# 四、必须完成的 Profile 化改造

---

## P1-1：新增 profile 加载机制

新增一个 profile loader，用来读取：

```text
config/profiles/<profile_id>.yaml
```

命令行示例：

```bash
python scripts/crawl_ip.py --profile fsn
```

需要支持：

```bash
python scripts/crawl_ip.py --profile fsn --max-depth 1 --max-pages 50 --min-score 10
python scripts/crawl_ip.py --profile fsn --seed 间桐樱
python scripts/crawl_ip.py --profile fsn --seeds config/profiles/fsn.yaml
python scripts/crawl_ip.py --profile fsn --force
python scripts/crawl_ip.py --profile fsn --resume
python scripts/crawl_ip.py --profile fsn --dry-run
```

具体参数可根据当前项目实际调整，但必须实现：

1. 指定 profile。
2. 使用 profile 默认 seeds。
3. 支持命令行临时覆盖 max_depth / max_pages / min_score。
4. 支持单独指定 seed。
5. 支持 force / resume。
6. 输出目录按 profile 隔离。

验收标准：

* 可以运行 `--profile fsn`。
* 未来新增 `config/profiles/example.yaml` 后，不需要改 Python 代码就能跑新 IP。

---

## P1-2：新增 fsn.yaml，作为第一个 profile

把所有 FSN 专用内容放进：

```text
config/profiles/fsn.yaml
```

包括：

1. FSN 种子。
2. FSN 核心角色。
3. FSN 世界观关键词。
4. FSN 地点关键词。
5. FSN 允许的相关作品。
6. FSN 默认排除的相关作品。
7. FSN 噪声词。
8. FSN 分类规则。
9. FSN 默认评分权重。

注意：

* “FGO 默认排除”只能在 fsn.yaml 中。
* 未来如果创建 fgo.yaml，FGO 应该变成核心目标，而不是全局排除。
* “声优 / 歌曲 / 萌属性”也不应绝对全局排除，而应作为 profile 中的默认 noise 类型。某些 profile 如果要爬歌曲或声优，应该能关闭这些 noise 规则。

验收标准：

* Python 代码中不应出现大量 FSN 专有词。
* 搜索代码时，不应该在核心逻辑里看到大量“圣杯战争 / 冬木市 / FGO / 间桐樱”等硬编码。
* 这些词应主要存在于 fsn.yaml 中。

---

## P1-3：新增 template.yaml

新增：

```text
config/profiles/template.yaml
```

用于指导未来添加其他 IP。

template.yaml 应包括注释或示例字段：

```yaml
id: example_ip
name: Example IP
description: 用于说明如何创建一个新的 IP profile

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
  staff_company: []
  moe_traits: []

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
  characters: []
  world: []
  locations: []
  factions: []
  items: []
  plot: []
```

验收标准：

* 未来新增一个 IP 时，可以复制 template.yaml。
* README 中要说明如何新增 profile。

---

# 五、FSN profile 的具体修复要求

以下是 FSN profile 的配置要求，不要写死进核心代码。

---

## FSN seeds

fsn.yaml 默认 seeds 至少包含：

```text
Fate/stay night
间桐樱
远坂凛
卫宫士郎
Saber
阿尔托莉雅·潘德拉贡
Archer
英灵卫宫
Lancer
库·丘林
Rider
美杜莎
Caster
美狄亚
Assassin
佐佐木小次郎
Berserker
赫拉克勒斯
吉尔伽美什
言峰绮礼
伊莉雅斯菲尔·冯·爱因兹贝伦
间桐慎二
间桐脏砚
藤村大河
柳洞一成
葛木宗一郎
美缀绫子
圣杯战争
第五次圣杯战争
令咒
从者
御主
英灵
宝具
固有结界
无限剑制
魔术回路
魔术刻印
小圣杯
大圣杯
冬木市
穗群原学园
柳洞寺
冬木教会
远坂邸
间桐邸
```

如果其中某些页面在萌娘百科不存在，请记录 missing seed，但不要导致整个任务失败。

---

## FSN 不应使用过宽关键词

避免以下词作为普通高权重 substring：

```text
Fate
Class
Master
Archer
Saber
剑
魔术
月姬
魔法使之夜
空之境界
Notes
DDD
Canaan
Fate/Grand Order
```

处理原则：

1. Fate 不能作为普通 substring 高分词。
2. Saber / Archer 可以作为 FSN 角色别名，但不能让所有 “xxx(Fate)” 自动高分。
3. 魔术可以保留为低权重或组合规则，不应单独导致入队。
4. Fate/Grand Order 在 fsn.yaml 中应属于 related_ip_blocklist，而不是 include_keywords。
5. Fate/Zero、Fate/hollow ataraxia 可作为 related_ip_allowlist，但权重不宜过高。

---

## FSN 默认噪声

以下内容对于 FSN 设定库默认视为噪声：

1. 声优页面。
2. 歌曲页面。
3. 萌属性页面。
4. 动画制作人员页面。
5. 出版社 / 制作公司页面。
6. FGO 专属角色。
7. 其他 Fate 衍生作品中与 FSN 无直接关系的页面。

但注意：
这些只是在 fsn.yaml 中默认排除，不是全局规则。

---

# 六、输出目录隔离

当前如果所有 IP 都输出到同一个目录，将来会混乱。

请调整为按 profile 隔离，例如：

```text
data/raw/moegirl/fsn/
  pages/
  text/
  crawl_state.json
  crawl_log.jsonl
  crawl_report.md

wiki/fsn/
  sources/
  characters/
  world/
  locations/
  factions/
  items/
  plot-arcs/
  uncategorized/
```

或者类似结构。

要求：

1. 不同 profile 的 raw 数据不要混在一起。
2. 不同 profile 的 wiki 输出不要混在一起。
3. README 说明新路径。
4. 如果保留旧路径，需要说明兼容策略。

验收标准：

* `--profile fsn` 的输出不会污染未来其他 IP。
* 未来 `--profile another_ip` 可以输出到独立目录。

---

# 七、兼容旧命令

如果当前已有：

```bash
python scripts/crawl_fsn.py
```

请尽量保留兼容。

可以把它改成 wrapper：

```python
# scripts/crawl_fsn.py
# internally calls crawl_ip.py --profile fsn
```

验收标准：

* 旧命令还能跑。
* 新命令 `python scripts/crawl_ip.py --profile fsn` 是推荐入口。
* README 中明确说明旧命令只是兼容入口。

---

# 八、验证实验

修改完成后，请至少运行以下验证。

---

## 实验 1：profile 加载验证

```bash
python scripts/crawl_ip.py --profile fsn --dry-run --max-depth 1
```

检查：

* 能正确加载 fsn.yaml。
* 能读取 seeds。
* 能输出 accepted / rejected / filtered。
* 不产生正式归档污染。

---

## 实验 2：redlink 通用过滤验证

```bash
python scripts/crawl_ip.py --profile fsn --seed 间桐樱 --max-depth 1 --max-pages 20 --force
```

检查：

* redlink 不进入 pending queue。
* redlink 不进入 visited。
* redlink 不进入 raw / wiki 输出。
* crawl_log 中有 redlink 过滤记录。

---

## 实验 3：FSN 高精度验证

```bash
python scripts/crawl_ip.py --profile fsn --max-depth 1 --max-pages 30 --min-score 10 --force
```

检查：

* 输出页面大部分应为 FSN 核心页面。
* 远坂凛、卫宫士郎、间桐樱、圣杯战争、冬木市等核心页面应优先出现。
* 声优、歌曲、萌属性、FGO 专属角色不应默认出现。
* 如果某些核心页面没有爬到，请在报告中说明原因。

---

## 实验 4：旧命令兼容验证

```bash
python scripts/crawl_fsn.py --max-depth 1 --max-pages 20 --force
```

检查：

* 旧命令仍可运行。
* 实际使用 fsn profile。
* 输出路径与新 profile 机制一致。

---

# 九、文档更新

请更新 README.md，并新增：

```text
docs/PROFILE_BASED_CRAWLER_DESIGN.md
docs/FSN_PROFILE_FIX_REPORT.md
```

## README.md 至少说明：

1. 项目不是 FSN 专用爬虫。
2. 如何使用 profile：

   ```bash
   python scripts/crawl_ip.py --profile fsn
   ```
3. 如何新增新的 IP profile。
4. 如何运行 dry-run。
5. 输出目录在哪里。
6. 如何使用 --resume / --force。
7. 旧的 crawl_fsn.py 是否仍可用。

## PROFILE_BASED_CRAWLER_DESIGN.md 至少说明：

1. 为什么要做 profile 化。
2. 核心爬虫和 profile 的边界。
3. 哪些规则是全局规则。
4. 哪些规则必须放在 profile 中。
5. 如何避免把某个 IP 的规则写死进代码。
6. 新增 profile 的步骤。

## FSN_PROFILE_FIX_REPORT.md 至少说明：

1. 本次根据 FSN 评估报告修复了什么。
2. 哪些问题是通用爬虫问题。
3. 哪些问题是 FSN profile 问题。
4. 实验结果。
5. 仍存在的问题。
6. 下一轮建议。

---

# 十、不要做的事情

本次不要做以下事情：

1. 不要把爬虫改成 FSN 专用。
2. 不要在核心 Python 代码中硬编码大量 FSN 关键词。
3. 不要全局排除 FGO。
4. 不要全局排除声优、歌曲、萌属性，因为未来可能有 profile 需要这些内容。
5. 不要引入 LLM 判断相关性。
6. 不要重写整个项目。
7. 不要一次性做复杂知识图谱。
8. 不要一次性设计多标签知识库系统。
9. 不要把所有 TYPE-MOON 作品都混入 FSN。
10. 不要牺牲当前 FSN 实验的可验证性。

---

# 十一、最终交付要求

请最终输出：

1. 修改了哪些文件。
2. 新增了哪些文件。
3. 哪些逻辑属于通用核心。
4. 哪些逻辑属于 fsn profile。
5. 是否还存在 FSN 专用硬编码。
6. 运行了哪些验证命令。
7. 每个验证命令的结果摘要。
8. 是否保留了旧命令兼容。
9. 如何新增下一个 IP profile。
10. 仍未完成的问题。

最终目标：

* 当前可以通过 fsn profile 高质量爬取 FSN 设定。
* 未来可以通过新增 profile 支持其他 IP。
* 核心爬虫不绑定 FSN。
* FSN 评估报告中的 redlink、误收录、漏爬、队列优先级、日志不可解释等问题得到修复。
* 项目从“FSN 实验脚本”升级为“可配置的萌娘百科 IP 设定爬虫框架”。

```
