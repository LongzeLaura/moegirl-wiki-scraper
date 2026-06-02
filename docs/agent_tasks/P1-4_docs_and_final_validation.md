# 阶段 P1-4：文档更新与最终验证

## 任务目标

补齐 README 和设计文档，运行最终验证，确认整个 profile 化改造完成。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划
3. `docs/FSN_CRAWL_QUALITY_EVALUATION.md` — 原始质量评估
4. `README.md` — 当前 README（需要更新）
5. 所有前序阶段的报告：`docs/agent_runs/<run_id>/P0-1_report.md` 到 `P1-3_report.md`
6. `scripts/crawl_ip.py` — 通用入口
7. `scripts/crawl_fsn.py` — 兼容入口
8. `lib/profile.py` — Profile loader
9. `config/profiles/fsn.yaml` — FSN profile
10. `config/profiles/template.yaml` — 模板

## 本阶段允许修改的范围

- `README.md` — 大幅更新
- `docs/PROFILE_BASED_CRAWLER_DESIGN.md` — 新增设计文档
- `docs/FSN_PROFILE_FIX_REPORT.md` — 新增修复报告
- `docs/agent_tasks/GLOBAL_CONTEXT.md` — 可微调

## 本阶段不要做的事情

1. 不要修改核心爬虫代码
2. 不要修改评分逻辑
3. 不要修改 profile 内容
4. 不要自动 commit

## 具体修改要求

### 1. 更新 README.md

当前 README 以 FSN 爬虫为焦点。需要改为以通用框架为焦点。

至少包含以下内容：

#### 1.1 项目定位

- 项目是**可配置的萌娘百科 IP 设定爬虫框架**
- 不是 FSN 专用爬虫
- FSN 是第一个 profile 实例

#### 1.2 如何使用 profile

```bash
# 使用 fsn profile
python scripts/crawl_ip.py --profile fsn

# 使用 fsn profile，dry-run 模式
python scripts/crawl_ip.py --profile fsn --dry-run

# 覆盖 profile 默认值
python scripts/crawl_ip.py --profile fsn --max-depth 2 --max-pages 80 --min-score 12

# 使用指定种子
python scripts/crawl_ip.py --profile fsn --seed "间桐樱"

# 断点续传
python scripts/crawl_ip.py --profile fsn --resume
```

#### 1.3 如何新增 IP profile

1. 复制 `config/profiles/template.yaml` 到 `config/profiles/<new_ip>.yaml`
2. 修改 profile 内容（id、name、seeds、core_keywords、noise_keywords 等）
3. 运行 `python scripts/crawl_ip.py --profile <new_ip> --dry-run` 验证
4. 正式运行

#### 1.4 输出目录结构

```
data/raw/moegirl/<profile_id>/
  pages/          # 原始 JSON 元数据
  text/           # 纯文本正文
  crawl_state.json
  crawl_log.jsonl
  crawl_report.md

wiki/<profile_id>/
  sources/moegirl/  # 来源页 Markdown
  characters/        # 角色分类
  world/             # 世界观分类
  ...
```

#### 1.5 旧命令兼容说明

```bash
# 旧命令仍可用（内部调用 crawl_ip.py --profile fsn）
python scripts/crawl_fsn.py --max-depth 1 --max-pages 50
```

#### 1.6 全局规则 vs Profile 规则

**全局规则**（核心代码中）：
- redlink / action=edit 过滤
- 特殊命名空间过滤
- 优先队列排序
- score_detail 日志
- crawl_report 生成
- dry-run 模式

**Profile 规则**（YAML 配置中）：
- 种子页面
- 核心关键词
- 噪声关键词
- 相关 IP 允许/屏蔽列表
- 评分权重
- 分类规则

### 2. 新增 docs/PROFILE_BASED_CRAWLER_DESIGN.md

设计文档，至少包含：

1. 为什么要做 profile 化
2. 核心爬虫和 profile 的边界
3. Profile 加载机制
4. 新增 profile 的步骤
5. 评分系统说明
6. 过滤机制说明

### 3. 新增 docs/FSN_PROFILE_FIX_REPORT.md

修复报告，至少包含：

1. 本次根据 FSN 评估报告修复了什么
2. 哪些问题是通用爬虫问题
3. 哪些问题是 FSN profile 问题
4. 实验结果
5. 仍存在的问题
6. 下一轮建议

### 4. 运行最终验证

#### 实验 1：profile 加载验证

```bash
python scripts/crawl_ip.py --profile fsn --dry-run --max-depth 1
```

#### 实验 2：redlink 通用过滤验证

```bash
python scripts/crawl_ip.py --profile fsn --seed "间桐樱" --max-depth 1 --max-pages 20 --force
```

#### 实验 3：FSN 高精度验证

```bash
python scripts/crawl_ip.py --profile fsn --max-depth 1 --max-pages 30 --min-score 12 --force
```

#### 实验 4：旧命令兼容验证

```bash
python scripts/crawl_fsn.py --max-depth 1 --max-pages 20 --force
```

#### 实验 5：检查 FSN 硬编码残留

```bash
rg -i "圣杯战争|冬木市|间桐樱|FGO|远坂凛|卫宫士郎|source_is_fsn|is_fsn_page" lib/ --type py
```

## 验收标准

1. README 已更新，说明项目是通用框架而非 FSN 专用
2. PROFILE_BASED_CRAWLER_DESIGN.md 已创建
3. FSN_PROFILE_FIX_REPORT.md 已创建
4. 4 个验证实验全部通过
5. lib/ 中无 FSN 硬编码残留
6. 旧命令仍可用
7. 文档中说明了如何新增 profile

## 建议验证命令

```bash
# 1. 全部验证实验
python scripts/crawl_ip.py --profile fsn --dry-run --max-depth 1
python scripts/crawl_ip.py --profile fsn --seed "间桐樱" --max-depth 1 --max-pages 20 --force
python scripts/crawl_ip.py --profile fsn --max-depth 1 --max-pages 30 --min-score 12 --force
python scripts/crawl_fsn.py --max-depth 1 --max-pages 20 --force

# 2. 检查硬编码残留
rg -i "圣杯战争|冬木市|间桐樱|FGO|远坂凛|卫宫士郎|source_is_fsn|is_fsn_page" lib/ --type py
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P1-4_report.md`，包含：

1. 新增了哪些文件
2. 修改了哪些文件
3. 4 个验证实验的结果摘要
4. 硬编码残留检查结果
5. 旧命令兼容验证结果
6. 整体改造完成度评估
7. 仍存在的问题
8. 下一轮建议
