# FSN 爬取质量评估报告

> 评估日期：2026-06-02  
> 评估对象：从「间桐樱」页面起始的实际爬取结果  
> 评估者：基于 crawl_state.json / crawl_log.jsonl / wiki 目录 / data/raw 实际数据

---

## 1. 本次评估结论

本次爬取严重偏保守且误收录率极高。实际爬取仅 5 页（因 max_pages=5 的历史运行残留），其中 **3 页为声优页面（雷碧文、林美秀、闫夜桥）**，**2 页为不存在的 redlink 页面（须藤友德、陆小蔓）**，核心 FSN 页面仅间桐樱、卫宫士郎、Fate/stay night、HF 剧场版 4 页。

**核心问题排序**：

1. **误收录 > 漏爬**：声优页面和 redlink 页面占了 5/10 的已爬页面，误收录率约 50%
2. **漏爬严重**：远坂凛、Saber、言峰绮礼等核心角色完全未爬到，BFS 只展开了一层且被 max_pages=5 截断
3. **评分规则致命缺陷**：`source_is_fsn=+8` 导致间桐樱页面几乎所有链接都 ≥8 分，222 条链接入队，其中大量声优、萌属性、歌曲等无关页面
4. **redlink 未过滤**：`index.php?title=xxx&action=edit&redlink=1` 页面被实际爬取和归档，浪费 20% 的配额
5. 不适合作为 llmWikiRPG 的 FSN 设定输入，核心覆盖极不完整且混入大量噪声

---

## 2. 本次爬取概况

| 指标 | 值 |
|------|-----|
| 起始种子 | `["间桐樱"]` |
| max_depth | 1 |
| max_pages | 5（历史运行残留，非 YAML 默认值 50） |
| min_relevance_score | 8 |
| 实际爬取页数 | 5（visited 5） |
| depth 0 页面 | 1（间桐樱） |
| depth 1 页面 | 4（Fate/stay night、卫宫士郎、HF 剧场版、须藤友德 redlink） |
| 待爬队列剩余 | 217 条（因 max_pages 截断） |
| 停止原因 | `pages_crawled >= max_pages`（5 页即停） |
| 错误/重试次数 | 0 |
| FSN 页面标记 | 4 页（间桐樱、Fate/stay night、卫宫士郎、HF 剧场版） |

### 分类分布

| 分类 | 页面数 | 页面标题 |
|------|--------|----------|
| characters | 6 | 间桐樱、卫宫士郎、雷碧文、林美秀、闫夜桥、下屋则子 |
| plot-arcs | 2 | Fate/stay night、HF 剧场版 |
| uncategorized | 2 | 陆小蔓 redlink、须藤友德 redlink |
| world | 0 | — |
| locations | 0 | — |
| factions | 0 | — |
| items | 0 | — |

**注意**：6 个 characters 中有 4 个是声优页面（雷碧文、林美秀、闫夜桥、下屋则子），实际 FSN 角色 characters 仅 2 个。

---

## 3. 页面相关性评估

### 3.1 核心相关页面（4 页，40%）

| 页面标题 | 当前分类 | depth | 相关性判断 |
|----------|----------|-------|-----------|
| 间桐樱 | characters | 0 | 核心女主角，正确 |
| Fate/stay night | plot-arcs | 1 | 作品主条目，正确 |
| 卫宫士郎 | characters | 1 | 核心男主角，正确 |
| Fate/stay night/剧场版动画/Heaven's Feel | plot-arcs | 1 | HF 剧场版，正确 |

### 3.2 明显无关页面（4 页，40%）

| 页面标题 | 当前分类 | depth | 误收录原因 |
|----------|----------|-------|-----------|
| 雷碧文 | characters | 1 | 台配声优，间桐樱页"声优→雷碧文"链入，分类器因声优关键词命中 characters |
| 林美秀 | characters | 1 | 台配声优，同上 |
| 闫夜桥 | characters | 1 | 中配声优，同上 |
| 下屋则子 | characters | 1 | 日语声优，同上 |

### 3.3 垃圾页面（2 页，20%）

| 页面标题 | 当前分类 | depth | 误收录原因 |
|----------|----------|-------|-----------|
| index.php?title=陆小蔓&action=edit&redlink=1 | uncategorized | 1 | redlink 不存在页面，link_extractor 的 _should_skip_title 应过滤但未生效 |
| index.php?title=须藤友德&action=edit&redlink=1 | uncategorized | 1 | 同上，redlink 页面 |

### 3.4 待爬队列中的页面分析（217 条）

从 crawl_state.json 的 pending_queue 可以分析：

**核心 FSN 页面（应在队列中优先爬取）**：

| 页面 | score | 分析 |
|------|-------|------|
| 远坂凛 | 18 | 核心女主角，应优先 |
| 伊莉雅丝菲尔·冯·爱因兹贝伦 | 23 | 核心女主角，应优先 |
| 间桐慎二 | 18 | 核心角色 |
| 言峰绮礼 | 18 | 核心角色 |
| 冬木市 | 26 | 核心地点 |
| 圣杯战争 | 26 | 核心世界观 |
| 卫宫切嗣 | 18 | FZ/FSN 核心角色 |
| 英灵卫宫 | 18 | Archer 真名 |
| 美杜莎(Fate) | 23 | Rider 真名 |
| 吉尔伽美什(Fate) | 23 | 核心角色 |

**应排除的无关页面（但 score≥8 入队了）**：

| 页面 | score | 误入原因 |
|------|-------|----------|
| 中长发 | 10 | 萌属性，source_is_fsn=8 + source_page_bonus=2 |
| 大和抚子 | 10 | 萌属性，同上 |
| 小恶魔系 | 10 | 萌属性，同上 |
| 家务全能 | 10 | 萌属性，同上 |
| 料理达人 | 10 | 萌属性，同上 |
| 连衣裙 | 10 | 服装属性，同上 |
| 高町奈叶 | 10 | 魔法少女奈叶角色，完全无关 |
| 菲特·泰斯特罗莎·哈拉温 | 10 | 同上 |
| 死亡笔记 | 10 | 完全无关作品 |
| 高町奈叶 | 10 | 完全无关作品 |
| 一大堆魔法少女伊莉雅歌曲 | 10 | 歌曲页面 |
| Oath sign / To the beginning / MEMORIA 等 | 10 | FZ 动画歌曲 |
| 虚渊玄 | 10 | FZ 小说作者 |
| 奈须蘑菇 | 10 | TYPE-MOON 创始人 |
| 武内崇 | 10 | 角色设计 |
| KADOKAWA | 10 | 出版社 |
| SILVER LINK. | 10 | 动画公司 |
| 井上坚二 | 10 | 魔法少女伊莉雅原作 |
| 特里斯坦(Fate) | 15 | FGO 角色 |
| 斯卡哈(Fate) | 15 | FGO 角色 |
| 梅芙(Fate) | 15 | FGO 角色 |
| 贞德(Fate) | 15 | FGO/Apocrypha 角色 |
| 田中(Fate) | 15 | FHA 角色 |

**结论**：217 条待爬队列中，至少 50%+ 是无关页面（萌属性、声优、歌曲、FGO 角色、动画制作人员等），只有约 30% 是核心 FSN 页面。

---

## 4. 漏爬的关键 FSN 页面

### 4.1 已出现在候选链接但被截断未爬

以下页面在 pending_queue 中但因 max_pages=5 截断未能爬取：

| 页面 | 重要性 | 类别 | 队列中 score | 原因 |
|------|--------|------|-------------|------|
| 远坂凛 | 高 | 角色 | 18 | max_pages 截断 |
| 伊莉雅丝菲尔·冯·爱因兹贝伦 | 高 | 角色 | 23 | max_pages 截断 |
| 间桐慎二 | 高 | 角色 | 18 | max_pages 截断 |
| 言峰绮礼 | 高 | 角色 | 18 | max_pages 截断 |
| 藤村大河 | 高 | 角色 | 18 | max_pages 截断 |
| 美缀绫子 | 中 | 角色 | 18 | max_pages 截断 |
| 柳洞一成 | 中 | 角色 | 18 | max_pages 截断 |
| 葛木宗一郎 | 中 | 角色 | 18 | max_pages 截断 |
| 冬木市 | 高 | 地点 | 26 | max_pages 截断 |
| 圣杯战争 | 高 | 世界观 | 26 | max_pages 截断 |
| 魔术协会 | 高 | 组织 | 26 | max_pages 截断 |
| 卫宫切嗣 | 高 | 角色(FZ/FSN) | 18 | max_pages 截断 |
| 间桐脏砚 | 高 | 角色 | 18 | max_pages 截断 |
| 间桐雁夜 | 中 | 角色(FZ) | 18 | max_pages 截断 |
| 远坂时臣 | 中 | 角色(FZ) | 18 | max_pages 截断 |
| Fate/Zero | 中 | 外围作品 | 26 | max_pages 截断 |
| 美杜莎(Fate) | 高 | Servant | 23 | max_pages 截断 |
| 赫拉克勒斯(Fate) | 高 | Servant | 23 | max_pages 截断 |
| 吉尔伽美什(Fate) | 高 | 角色 | 23 | max_pages 截断 |
| 佐佐木小次郎(Fate) | 中 | Servant | 23 | max_pages 截断 |
| 英灵卫宫 | 高 | Servant | 18 | max_pages 截断 |
| 美狄亚(Fate) | 中 | Servant | 18 | max_pages 截断 |
| 库·丘林(Fate) | 中 | Servant | 18 | max_pages 截断 |
| 圣杯 | 高 | 道具/概念 | 18 | max_pages 截断 |
| 宝具 | 高 | 世界观 | 18 | max_pages 截断 |
| 职阶卡 | 中 | 世界观(FHA) | 18 | max_pages 截断 |

### 4.2 完全未出现在候选链接中的关键 FSN 页面

这些页面从未出现在间桐樱页面的链接中，属于链接结构盲区：

| 页面 | 重要性 | 类别 | 漏爬原因 |
|------|--------|------|----------|
| 阿尔托莉雅·潘德拉贡 (Saber 本体) | 高 | 角色 | 间桐樱页链接到的是"阿尔托莉雅·潘德拉贡Alter"，不是标准 Saber 页 |
| Saber (Fate/stay night) | 高 | 角色 | 间桐樱页直接用"Saber"作显示文本，但链接指向 Alter 版本 |
| 无限剑制 (概念页面) | 高 | 世界观 | 不在间桐樱直接链接中 |
| 令咒 | 高 | 世界观 | 不在间桐樱直接链接中 |
| 魔术回路 | 高 | 世界观 | 不在间桐樱直接链接中 |
| 固有结界 | 高 | 世界观 | 不在间桐樱直接链接中 |
| 远坂邸 | 中 | 地点 | 不在间桐樱直接链接中 |
| 间桐邸 | 中 | 地点 | 不在间桐樱直接链接中 |
| 柳洞寺 | 中 | 地点 | 不在间桐樱直接链接中 |
| 冬木教会 | 中 | 地点 | 不在间桐樱直接链接中 |
| 穗群原学园 (独立页面) | 中 | 地点 | 间桐樱链接的是"私立穗群原学园"，可能无独立条目 |
| Fate 线剧情 | 高 | 剧情 | 不在间桐樱直接链接中 |
| UBW 线剧情 | 高 | 剧情 | 不在间桐樱直接链接中 |
| HF 线剧情 (除剧场版外) | 高 | 剧情 | 不在间桐樱直接链接中 |
| 抑制力 | 中 | 世界观 | 不在间桐樱直接链接中 |
| 魔术刻印 | 中 | 世界观 | 不在间桐樱直接链接中 |
| 第五次圣杯战争 | 高 | 世界观 | 不在间桐樱直接链接中 |
| 卫宫切嗣 (可能存在独立 FSN 版本) | 高 | 角色 | 虽然链接中有但被截断 |

**根因**：单种子 + max_depth=1 只能覆盖间桐樱直接链接的页面。间桐樱的页面链接偏向角色关系和声优信息，对世界观、地点、魔术体系等条目的链接覆盖天然不足。这是 BFS 自然扩展的固有局限。

---

## 5. 误收录页面分析

### 5.1 声优页面（最严重的误收录来源）

**典型案例**：雷碧文、林美秀、闫夜桥、下屋则子

**原因链条**：
1. 间桐樱信息框中列出声优（下屋则子、陆小蔓、闫夜桥、林美秀→雷碧文）
2. 这些声优名字以链接形式出现在间桐樱页面中
3. 间桐樱被标记为 FSN 页面 → `source_is_fsn = True` → `+8` 分
4. 间桐樱标题包含"间桐" → 命中 include_keyword"间桐樱" → `source_page_bonus = +2`
5. 声优页面标题 ≥ 3 字符 → 无短标题惩罚
6. 最终 score = 0(title_kw) + 0(display_kw) + 0(cat_kw) + 8(source_is_fsn) + 2(source_page_bonus) = 10 ≥ 8

**根因**：`source_is_fsn=+8` 过强，任何来自 FSN 页面的链接都能轻松达到 8 分阈值。声优名字本身不含 FSN 关键词，但 +8+2 已经 10 分了。

### 5.2 萌属性页面（中长发、大和抚子、小恶魔系等）

**原因链条**：
1. 间桐樱信息框的"萌点"列出大量萌属性链接
2. source_is_fsn=+8, source_page_bonus=+2
3. 这些 2-4 字短标题本身不含 FSN 关键词，但 8+2=10 ≥ 8
4. **但**部分极短标题（黑发、紫发、银发、学妹、妹妹等）因 len≤2 触发 short_generic_penalty=-5，最终 score=5 < 8，被成功排除
5. 中长发（3字）、大和抚子（4字）等不触发短标题惩罚

**根因**：短标题惩罚只覆盖 ≤2 字的标题，3-4 字的泛萌属性页面无法被惩罚。

### 5.3 redlink 页面

**典型案例**：`index.php?title=陆小蔓&action=edit&redlink=1`、`index.php?title=须藤友德&action=edit&redlink=1`

**原因**：link_extractor.py 的 `_should_skip_title()` 中有 `if title.startswith('index.php')` 的过滤规则，但在 `_compile_score()` 的评分阶段，标题被 normalize_title 后不再是 `index.php?title=...` 的形式，而是 URL 解码后的结果。

实际查看 crawl_state.json，这些 redlink 页面的 title 仍然保留了 `index.php?title=xxx&action=edit&redlink=1` 格式，说明 normalize_title 没有将其转化。问题出在 is_allowed_page 的 exclude_keyword 检查——"redlink" 不在 exclude_keywords 列表中。

更精确地说：`_should_skip_title()` 在 extract_links 阶段应已过滤 `index.php` 开头的标题和含 `redlink=1` 的标题。但实际这些页面仍进入了队列，说明**之前的缓存运行中链接提取逻辑可能不同**，或者这些链接在更早版本中被提取并缓存。

**根因**：缓存中的链接可能是旧版代码提取的，当前代码的 _should_skip_title 过滤不会重新应用到缓存数据上。

### 5.4 FGO 角色页面

**典型案例**：特里斯坦(Fate)（score=15）、斯卡哈(Fate)（score=15）、梅芙(Fate)（score=15）

**原因**：
1. 间桐樱页面提到了 FGO 中帕尔瓦蒂凭依樱等内容，链接到 FGO 角色
2. source_is_fsn=+8
3. 这些角色的显示文本不含 FSN 关键词，但标题中的"(Fate)"与 include_keyword"Fate" 匹配 → title_keywords=+5
4. 8+5=13 或更高 ≥ 8

**根因**：include_keywords 中的"Fate"过于宽泛，匹配所有含"Fate"的标题，包括大量 FGO/Apocrypha 角色。

### 5.5 歌曲页面

**典型案例**：Oath sign（score=10）、To the beginning（score=10）、MEMORIA（score=10）、I beg you（score=10）、数十首魔法少女伊莉雅相关歌曲

**原因**：source_is_fsn=+8 + source_page_bonus=+2 = 10 ≥ 8。歌曲名本身不含任何 FSN 关键词。

**根因**：source_is_fsn 加分过强。

### 5.6 制作人员页面

**典型案例**：奈须蘑菇（score=10）、虚渊玄（score=10）、武内崇（score=10）、Ufotable（score=10）、KADOKAWA（score=10）

**原因**：同上，source_is_fsn=+8 + source_page_bonus=+2 = 10 ≥ 8。

---

## 6. 相关性评分规则问题

### 6.1 include_keywords 的问题

| 关键词 | 问题 | 误匹配示例 |
|--------|------|-----------|
| "Fate" | 过于宽泛，任何含"Fate"的标题都匹配 | 特里斯坦(Fate)、斯卡哈(Fate)、贞德(Fate)、所有 FGO 角色页 |
| "Archer" | 职阶名不是角色特指，且与弓道等概念冲突 | 弓道相关页面 |
| "Master" | 过于泛化 | 任何含"Master"的页面 |
| "Class" | 英语常见词 | 任何含"Class"的页面 |
| "士郎" | 单独出现时不一定指卫宫士郎 | 其他作品角色 |
| "魔术" | 可匹配非 FSN 的魔术相关条目 | 魔术相关泛概念 |
| "剑" | 单字，过于泛化 | 任何含"剑"的页面 |
| "Fate/Grand Order" | 不应出现在 FSN 专用 include 列表 | FGO 页面被加分 |
| "月姬"、"魔法使之夜"、"空之境界" | 非 FSN 作品 | 其他 TM 作品页面被加分 |
| "Notes"、"DDD"、"Canaan" | 与 FSN 无直接设定关系 | 代码中的 DEFAULT_INCLUDE_KEYWORDS |

### 6.2 exclude_keywords 的问题

| 缺失的排除规则 | 误匹配后果 |
|----------------|-----------|
| 无"声优"排除 | 声优页面入队 |
| 无"配音"排除 | 配音演员页面入队 |
| 无"歌手"排除 | 歌手/演唱者页面入队 |
| 无"歌曲"排除 | 动画歌曲页面入队 |
| 无"FGO"/"Grand Order"排除 | FGO 页面以高分入队 |
| 无"歌词"排除 | 歌词页面入队 |
| 无"作曲"/"编曲"排除 | 音乐制作页面入队 |
| 无"redlink"排除 | 不存在页面入队 |
| 无"动画公司"/"制作公司"排除 | 动画制作公司页面入队 |
| 无"出版社"排除 | KADOKAWA 等入队 |
| 无"Fate/kaleid"排除 | 魔法少女伊莉雅大量页面入队 |

### 6.3 高价值分类问题

`high_value_cats` 包含"Fate系列"、"TYPE-MOON作品"等，+10 分/次命中。

**问题**：萌娘百科的 categories 在本次爬取中全部为空数组（`"categories": []`），因为 fetcher.py 的 extract_meta 从 HTML 提取 categories 的正则匹配可能对萌娘百科的 HTML 结构不生效。因此高价值分类加分在本次爬取中**实际未生效**，但这不代表将来不会生效。

**如果 categories 能正确提取**，"Fate系列"分类将给 FGO 页面额外 +10，导致更多 FGO 内容入队。

### 6.4 来源页面加分问题

`source_is_fsn = +8` 是最严重的评分问题：

- **间桐樱被标记为 FSN 页**后，其所有 264 条链接中，222 条 score≥8 入队
- 去掉 +8 后，大量萌属性、声优、歌曲页面的 score 会降到 2（仅 source_page_bonus=2），远低于阈值 8
- **+8 太强了**：它使得"来源页面是否是 FSN"成为几乎唯一的准入条件，关键词评分变成了次要因素

**建议**：将 source_is_fsn 加分降低到 +3 或 +4，让关键词评分重新成为主要判据。

### 6.5 短标题惩罚问题

当前短标题惩罚条件：`len(title) <= 2 and not any(kw in title for kw in include_keywords)`

**问题**：
- 只惩罚 ≤2 字的标题，大量 3-4 字的泛概念标题不受惩罚（中长发、大和抚子、小恶魔系等）
- 对 CJK 标题，2 字限制太窄，中文 3-4 字也可以是极泛的萌属性
- 不考虑标题是否含有实际 FSN 语义

**建议**：将惩罚范围扩展到 ≤4 字且不命中任何 include_keyword 的 CJK 标题。

### 6.6 min_score=8 是否合理

**当前 min_score=8 过低**。由于 source_is_fsn=+8 的存在，几乎所有来自 FSN 页面的链接都能达到 8 分。min_score 需要至少提到 12-15 才能过滤掉"仅有来源加分"的页面。

但如果简单提高 min_score 而不改 source_is_fsn，会同时过滤掉一些真正相关但标题关键词不突出的页面。

---

## 7. BFS 策略问题

### 7.1 单种子 + depth=1 的局限

从间桐樱出发，depth=1 只能覆盖其直接链接。间桐樱页面的链接特征：
- 偏重角色关系和声优信息
- 大量萌属性链接（信息框"萌点"字段）
- 歌曲链接（动画相关音乐）
- 缺少世界观/魔术体系的直接链接

这是**种子选择偏见**，不是 BFS 算法本身的错。

### 7.2 max_depth=1 是否太浅

**是的**，max_depth=1 只能抓到种子的直接链接，无法通过间接链接到达核心 FSN 世界观页面。例如：
- 间桐樱 → Fate/stay night → 令咒、魔术回路、固有结界（需要 depth=2）
- 间桐樱 → 卫宫士郎 → Saber、远坂凛（需要 depth=2）

**但是**，如果 max_depth 提到 2 而不修改评分规则，从间桐樱的 222 条出链扩展到 depth=2，每条链接再产生 100+ 出链，队列将爆炸至数万条，其中大部分是无关页面。

### 7.3 是否应该改成"核心种子白名单 + 受控 BFS 扩展"

**强烈建议**。当前 BFS 自然扩展的问题是：
1. 从角色页出发，链接偏向声优/萌属性/歌曲
2. 无法控制扩展方向
3. 评分阈值无法有效区分"相关但不关键"和"完全不相关"

建议架构：

```
Tier 0: 核心种子白名单（必须爬取，跳过评分）
  - Fate/stay night、圣杯战争、所有主要角色
  
Tier 1: 核心种子的一跳链接（评分过滤 + 白名单优先）
  - 从 Tier 0 页面发现的链接，用更严格的评分规则筛选
  
Tier 2: 扩展种子（可选爬取）
  - 从 Tier 1 页面发现的链接，最高评分阈值
  
Blocked: 黑名单（永不爬取）
  - 声优、歌曲、萌属性、FGO 专属角色、动画制作人员
```

### 7.4 max_pages 和 max_depth 推荐设置

| 配置 | max_depth | max_pages | 说明 |
|------|-----------|-----------|------|
| 高精度测试 | 1 | 30 | 多种子，高 min_score |
| 中等召回 | 2 | 80 | 多种子，严格评分 |
| 充分覆盖 | 2 | 150 | 多种子 + 白名单 |

### 7.5 队列排序问题

当前 BFS 按入队顺序处理，不考虑 score 排序。高 score 页面（如圣杯战争 score=26、冬木市 score=26）可能排在低 score 页面（如连衣裙 score=10）后面，在 max_pages 截断时被浪费。

**建议**：优先队列（按 score 降序）代替 FIFO 队列，确保高相关页面优先爬取。

---

## 8. 分类质量问题

### 8.1 当前 6 类分类的不足

| 问题 | 示例 |
|------|------|
| 声优被分到 characters | 雷碧文、林美秀、闫夜桥、下屋则子 → characters（因"声优"关键词命中 characters 规则） |
| Fate/stay night 被分到 plot-arcs | 主条目不是"剧情/路线"，是"作品概述" |
| 缺少 servants 子分类 | Servant 角色和普通角色混在一起 |
| 缺少 magic-system 分类 | 魔术、令咒、圣杯战争全在 world 中 |
| 缺少 organizations 分类 | 远坂家、间桐家、爱因兹贝伦在 factions 但关键词覆盖不足 |
| 缺少 masters/servants 分类 | 无法区分 Master 和 Servant |
| 缺少 routes-plot 分类 | Fate 线、UBW 线、HF 线没有独立分类 |

### 8.2 具体错分案例

| 页面 | 当前分类 | 应有分类 | 原因 |
|------|----------|----------|------|
| 雷碧文 | characters | 不应收录 / seiyuu | 声优页 |
| 林美秀 | characters | 不应收录 / seiyuu | 声优页 |
| 闫夜桥 | characters | 不应收录 / seiyuu | 声优页 |
| 下屋则子 | characters | 不应收录 / seiyuu | 声优页 |
| Fate/stay night | plot-arcs | works / 根条目 | 主条目不是剧情路线 |

### 8.3 建议的新分类方案

```
characters/       — FSN 出场角色
  servants/       — 从者/Servant（可子目录或平级）
  masters/        — 御主/Master
  npcs/           — 非战斗角色
world/            — 世界观/设定
  magic-system/   — 魔术体系（魔术回路、魔术师、魔术刻印、根源等）
  holy-grail-war/ — 圣杯战争机制（令咒、职阶、从者系统、小圣杯等）
locations/        — 地点
factions/         — 组织/家族
  families/       — 御三家（远坂家、间桐家、爱因兹贝伦）
items/            — 道具/宝具
  noble-phantasms/ — 宝具
  weapons/        — 武器
  mystic-codes/   — 魔术礼装
plot-arcs/        — 剧情路线
  fate-route/     — Fate 线
  ubw-route/      — Unlimited Blade Works 线
  hf-route/       — Heaven's Feel 线
works/            — 作品概述（Fate/stay night 主条目、动画版、剧场版）
uncategorized/    — 未分类
```

同时建议：
- 支持**多标签**：一个页面可以同时属于 characters 和 masters（如远坂凛既是角色又是 Master）
- 增加 **seiyuu** 分类用于声优页（或直接排除声优页）

---

## 9. 文本质量问题

### 9.1 噪声问题

| 问题 | 示例 | 严重程度 |
|------|------|----------|
| JS 提示残留 | "This site requires JavaScript enabled. Please check your browser settings." | 低（首行固定，可脚本移除） |
| 编辑引导模板 | "欢迎您参与完善《Fate/stay night》系列条目——投影，开始。" | 低（信息框上方，可识别） |
| QQ 群号 | "萌娘百科型月编辑群『穗群原学园萌百分园』：571632697" | 低（可正则排除） |
| 剧透警告 | "以下内容含有剧透成分，可能影响观赏作品兴趣" | 低 |
| 消歧义/导航模板内容 | 分类页尾的声优导航列表 | 中（雷碧文页尾有完整声优目录列表） |
| 折叠内容 | 某些长列表被折叠但文本中仍抽取 | 中 |

### 9.2 信息框质量

**正面**：间桐樱的信息框被成功抽取，包含：
- 基本资料（本名、别号、身高、体重、三围、生日、星座、血型、魔术属性）
- 亲属关系（学姐、亲姐姐、亲生父母等）
- 从者信息（Saber、Rider、Berserker）

**负面**：
- 信息框的键值对没有结构化保留，全部变成"键 值"的纯文本格式
- 链接关系被平铺为文本，无法区分"信息框中的链接"和"正文中的链接"
- 没有 section heading 信息，无法区分"基本资料"段和"人物经历"段

### 9.3 丢失的信息

| 丢失内容 | 影响 | 建议 |
|----------|------|------|
| outgoing_links 结构化数据 | 无法重建页面间引用关系 | 保存 links 列表到元数据 |
| categories 分类标签 | 评分和分类都依赖此数据 | 修复 extract_meta 的 categories 提取 |
| section headings | 无法定位具体内容段落 | 保存 section 标题列表 |
| infobox 结构化数据 | 设定数据无法结构化提取 | 考虑保存 infobox 的 key-value 对 |
| 页面间链接的 display_text | 丢失了链接的语义上下文 | 已在 _extracted_links 中保存 |

### 9.4 是否适合作为 llmWikiRPG 输入

**当前不适合**，原因：
1. 噪声比过高：声优页、萌属性页、歌曲页等无关内容占 50%+
2. 核心覆盖不足：缺少远坂凛、Saber、言峰绮礼等核心角色
3. 缺少结构化信息：section headings、infobox、outgoing_links
4. 缺少世界观/魔术体系条目
5. 文本中混入编辑引导、QQ 群号等噪声

需要：扩大覆盖 → 清洗噪声 → 结构化抽取 → 才能作为 RPG 输入。

---

## 10. 日志与可调试性

### 10.1 当前日志评估

| 事件类型 | 是否记录 | 记录质量 |
|----------|----------|----------|
| init | 是 | 包含 seeds、config_summary |
| cache_hit | 是 | 仅 title |
| fetch | 是 | title、pageid、html_size、depth、links_found |
| fetch_error | 是 | title、attempt、error |
| link_excluded | 是 | title、source、reason、score、score_detail |
| links_processed | 是 | source、added、excluded |
| classified | 是 | title、category、reason（含全部分类得分） |
| skip_visited | 是 | 仅 title |
| complete | 是 | summary |

### 10.2 缺失的日志字段

| 缺失字段 | 影响 | 建议 |
|----------|------|------|
| link_enqueued 事件 | 不知道哪些链接入了队及原因 | 添加 `link_enqueued` 事件，包含 title、source、score、score_detail |
| 每条入队链接的 score_detail | 无法判断"为什么这个声优页面进了队列" | 在 add_to_queue 时记录 |
| FSN 页面标记原因 | 不知道 is_fsn_page 的评分细节 | 在 is_fsn_page 后记录具体评分 |
| 页面 categories 提取结果 | categories 始终为 []，无法判断是提取失败还是页面无分类 | 修复 extract_meta + 日志记录原始 categories |
| BFS 队列状态快照 | 不知道某时刻队列中高/低 score 页面分布 | 在每个 depth 结束时记录队列统计 |
| 爬取耗时 | 不知道实际网络耗时 | 记录每页的 fetch 开始/结束时间 |

### 10.3 是否需要 crawl_report

**需要**。建议每次爬取完成后自动生成 `crawl_report.json`/`crawl_report.md`，包含：
- 爬取摘要（页数、depth、耗时）
- 相关性分布（核心/外围/可疑/无关的比例估算）
- 分类分布统计
- 高分未爬页面列表
- 低分误爬页面列表
- 错误摘要
- 与上轮爬取的差异对比（如果有）

---

## 11. 下一步修改建议

### P0：必须先修

不修这些问题，继续扩大爬取会明显污染知识库。

#### P0-1：修复 redlink 页面过滤

| 项目 | 内容 |
|------|------|
| 问题 | `index.php?title=xxx&action=edit&redlink=1` 页面被入队和爬取 |
| 证据 | 陆小蔓 redlink、须藤友德 redlink 被实际爬取归档 |
| 修改方向 | 在 is_allowed_page 或 _should_skip_title 中增加 redlink 检测；清除缓存中已有的 redlink 链接数据 |
| 预期效果 | 消除 5-20% 的垃圾页面入队 |
| 风险 | 低 |

#### P0-2：降低 source_is_fsn 加分

| 项目 | 内容 |
|------|------|
| 问题 | source_is_fsn=+8 导致间桐樱所有 222/264 条链接入队 |
| 证据 | pending_queue 中大量 score=10 的萌属性/声优/歌曲页面 |
| 修改方向 | 将 source_is_fsn 从 +8 降为 +3 |
| 预期效果 | 萌属性页面 score 从 10 降到 5（<8 被排除），声优页面同降；但标题含 FSN 关键词的核心页面不受影响 |
| 风险 | 中：某些仅靠来源加分通过的合理页面可能需要提高其 include_keyword 覆盖来补偿 |

#### P0-3：增加声优/歌曲/萌属性 exclude 规则

| 项目 | 内容 |
|------|------|
| 问题 | 声优页面、歌曲页面、萌属性页面大量入队 |
| 证据 | 雷碧文、下屋则子、Oath sign、中长发 等全部 ≥8 分 |
| 修改方向 | exclude_keywords 增加：声优、配音、歌手、歌曲、作曲、编曲、作词、萌属性、属性(萌)、导航、动画公司、制作公司、出版社、FGO、Grand Order、kaleid liner、redlink |
| 预期效果 | 消除 60%+ 的无关页面入队 |
| 风险 | 低：这些关键词不会误排除 FSN 设定页面 |

#### P0-4：修复 categories 提取

| 项目 | 内容 |
|------|------|
| 问题 | 所有页面的 categories 均为 [] |
| 证据 | 间桐樱.json 的 categories: [] |
| 修改方向 | 检查 fetcher.py 的 extract_meta 正则是否匹配萌娘百科实际 HTML 结构；考虑从 mw.config 的 wgCategories 提取 |
| 预期效果 | categories 可用后，高价值分类评分生效，分类器精度提升 |
| 风险 | 低 |

### P1：建议修

这些问题会影响覆盖率和分类质量。

#### P1-1：使用多种子列表代替单种子

| 项目 | 内容 |
|------|------|
| 问题 | 单种子（间桐樱）的链接偏向角色/声优，缺少世界观/地点直接链接 |
| 证据 | 间桐樱 pending_queue 中无令咒、魔术回路、固有结界等 |
| 修改方向 | 使用 fsn_seeds.txt 中的 23 个种子，覆盖作品、角色、圣杯战争；增加世界观种子（令咒、魔术回路、圣杯战争）和地点种子（冬木市、穗群原学园、柳洞寺） |
| 预期效果 | 从多个入口覆盖 FSN 知识图谱不同区域 |
| 风险 | 中：更多种子 = 更多出链，需要配合更严格的评分和 exclude |

#### P1-2：将 include_keywords 中的泛 Fate 关键词改为精确匹配

| 项目 | 内容 |
|------|------|
| 问题 | "Fate" 命中所有含 Fate 的标题，包括 FGO 角色 |
| 证据 | 特里斯坦(Fate)、斯卡哈(Fate)、贞德(Fate) 因标题含"Fate"获得 title_keywords=+5 |
| 修改方向 | 移除"Fate"单字关键词，只保留精确作品名"Fate/stay night"、"Fate/Zero"等；对标题中"(Fate)"后缀单独处理 |
| 预期效果 | FGO 角色不再因"Fate"关键词加分 |
| 风险 | 低 |

#### P1-3：引入优先队列替代 FIFO

| 项目 | 内容 |
|------|------|
| 问题 | 低 score 无关页面和高 score 核心页面同等优先级 |
| 证据 | max_pages=5 时，间桐樱的 4 个 depth=1 页面是顺序取的，非按 score 排序 |
| 修改方向 | 在 CrawlState 中实现按 score 降序的优先队列 |
| 预期效果 | 高 score 核心页面优先爬取，max_pages 截断时不会浪费配额 |
| 风险 | 低 |

#### P1-4：扩展短标题惩罚范围

| 项目 | 内容 |
|------|------|
| 问题 | ≤2 字惩罚只过滤了"黑发""紫发"等，3-4 字的"中长发""大和抚子"不受惩罚 |
| 证据 | 中长发(score=10)、大和抚子(score=10) 入队 |
| 修改方向 | CJK 标题 ≤4 字且不命中 include_keyword 时，惩罚 -8 |
| 预期效果 | 3-4 字泛概念标题被排除 |
| 风险 | 低 |

### P2：可后续优化

#### P2-1：分类体系改造

| 项目 | 内容 |
|------|------|
| 问题 | 6 类不够精细，声优被分到 characters，作品主条目被分到 plot-arcs |
| 证据 | 雷碧文→characters、Fate/stay night→plot-arcs |
| 修改方向 | 增加 servants/masters/magic-system/holy-grail-war/works 子分类；支持多标签 |
| 预期效果 | 分类更精确，便于 RPG 系统按类型检索 |
| 风险 | 中：需要改 classifier.py 和 archiver.py |

#### P2-2：文本抽取增强

| 项目 | 内容 |
|------|------|
| 问题 | 纯文本丢失了 section headings、infobox 结构、outgoing_links |
| 证据 | 间桐樱.txt 中信息框键值对无结构，无法区分段落 |
| 修改方向 | 在 save_raw_page 中额外保存 structured_data.json，包含 sections、infobox_kvs、outgoing_links |
| 预期效果 | 后续 RPG 系统可结构化查询设定数据 |
| 风险 | 低 |

#### P2-3：crawl_report 自动生成

| 项目 | 内容 |
|------|------|
| 问题 | 无自动质量评估报告 |
| 证据 | 需要人工分析 crawl_state.json + crawl_log.jsonl |
| 修改方向 | 爬取完成后自动生成 crawl_report.md，包含核心统计、分类分布、高分未爬页面、低分误爬页面 |
| 预期效果 | 每轮爬取可快速评估质量 |
| 风险 | 低 |

#### P2-4：种子白名单 + 受控扩展

| 项目 | 内容 |
|------|------|
| 问题 | BFS 自然扩展方向不可控 |
| 证据 | 从间桐樱出发主要爬到声优和萌属性 |
| 修改方向 | Tier 0 核心种子（跳过评分）→ Tier 1 评分过滤 → Tier 2 可选扩展 → Blocked 黑名单 |
| 预期效果 | 扩展方向可控，覆盖率可预期 |
| 风险 | 中：需重构 BFS 核心逻辑 |

---

## 12. 建议的下一轮实验配置

### 实验 A：高精度小规模

**目标**：验证评分规则修复后能否精准收录核心 FSN 页面

```
seeds:
  - "Fate/stay night"
  - "间桐樱"
  - "远坂凛"
  - "卫宫士郎"
  - "圣杯战争"
  - "冬木市"
  - "言峰绮礼"
  - "伊莉雅斯菲尔·冯·爱因兹贝伦"

max_depth: 1
max_pages: 30
min_relevance_score: 12

include_keywords 调整:
  - 移除 "Fate"（单字）
  - 移除 "Class"（英语常见词）
  - 保留精确作品名和角色名

exclude_keywords 新增:
  - 声优、配音、歌手、歌曲、作曲、编曲、作词
  - 萌属性、属性(萌)
  - FGO、Grand Order
  - kaleid liner、魔法少女
  - 动画公司、制作公司、出版社
  - redlink

source_is_fsn: +3（从 +8 降低）

短标题惩罚: CJK ≤4 字 -8
```

**预期**：30 页中 >80% 是核心 FSN 页面

### 实验 B：中等召回

**目标**：覆盖 FSN 主要设定，验证 depth=2 + 多种子的可控扩展

```
seeds: fsn_seeds.txt（扩展至 30+ 条，含世界观/地点种子）

max_depth: 2
max_pages: 80
min_relevance_score: 10

评分调整: 同实验 A

优先队列: 按 score 降序

exclude_keywords: 同实验 A + 增加:
  - 梗、成句
  - Fate/EXTRA、Fate/Apocrypha（非 FSN 作品）
```

**预期**：80 页覆盖 FSN 主要角色、世界观概念、地点、组织、宝具

### 实验 C：诊断型 dry-run

**目标**：不实际爬取，仅分析链接和评分分布，确认评分规则有效性

```
seeds:
  - "间桐樱"
  - "Fate/stay night"
  - "远坂凛"

max_depth: 1
max_pages: 0（不爬取 depth>0 页面）
dry_run: true

手动检查:
  - 间桐樱/Fate/stay night/远坂凛 的 outlinks 评分分布
  - 哪些核心页面被过滤及原因
  - 哪些无关页面通过及原因
  - source_is_fsn 从 +8 改为 +3 后的变化
```

**预期**：确认评分规则调优方向正确后再大规模爬取

---

## 附录：核心结论

**下一步最应该改的是：评分规则（P0-2 + P0-3 + P1-2）**

1. **降低 source_is_fsn 加分**（+8 → +3）是最关键的单一修改
2. **增加 exclude 规则**（声优/歌曲/FGO/萌属性）是最立竿见影的过滤手段
3. **移除泛 Fate 关键词**（消除 FGO 角色的误加分）
4. **修复 redlink 过滤**（消除垃圾页面）
5. **使用多种子列表**（突破单种子的链接偏见）
6. **引入优先队列**（确保高相关页面优先爬取）

修改顺序建议：P0-1（redlink）→ P0-3（exclude）→ P0-2（source_is_fsn）→ P1-2（Fate 关键词）→ P1-1（多种子）→ 实验 C（验证）→ 实验 B（正式爬取）
