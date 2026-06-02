# 阶段 P1-3：输出目录隔离与旧命令兼容

## 任务目标

按 profile 隔离输出目录，并保留旧 `crawl_fsn.py` 命令的兼容入口。

## 你必须先阅读的文件

1. `docs/agent_tasks/GLOBAL_CONTEXT.md` — 项目背景
2. `docs/PROFILE_BASED_CRAWLER_REFACTOR_PLAN.md` — 完整改造计划（P1-3 兼容部分）
3. `scripts/crawl_fsn.py` — 当前 FSN 入口（需要改为 wrapper）
4. `scripts/crawl_ip.py` — P1-1 实现的通用入口
5. `lib/archiver.py` — 当前归档路径逻辑
6. `lib/cache.py` — 当前缓存路径逻辑
7. `lib/checkpoint.py` — 当前 checkpoint 路径逻辑
8. `scripts/crawl_fsn.py` — 当前 `load_config` 中的 `output_paths` 配置

## 本阶段允许修改的范围

- `scripts/crawl_fsn.py` — 改为调用 `crawl_ip.py --profile fsn` 的 wrapper
- `scripts/crawl_ip.py` — 输出路径按 profile_id 隔离
- `lib/archiver.py` — 接受 profile_id 参数，输出到 `data/raw/moegirl/<profile_id>/`
- `lib/cache.py` — 接受 profile_id 参数
- `lib/checkpoint.py` — 接受 profile_id 参数
- `scripts/crawl_fsn.py` — 配置路径改为按 profile_id

## 本阶段不要做的事情

1. 不要修改 profile YAML 内容（P1-2）
2. 不要修改评分逻辑
3. 不要修改链接过滤逻辑
4. 不要修改 README（P1-4）
5. 不要删除旧的 `data/raw/moegirl/` 中的数据

## 具体修改要求

### 1. 输出目录按 profile 隔离

当前输出路径：

```
data/raw/moegirl/
  pages/<title>.json
  text/<title>.txt
  crawl_state.json
  crawl_log.jsonl

wiki/
  sources/moegirl/<title>.md
  characters/<title>.md
  world/<title>.md
  ...
```

改为：

```
data/raw/moegirl/fsn/
  pages/<title>.json
  text/<title>.txt
  crawl_state.json
  crawl_log.jsonl
  crawl_report.md

wiki/fsn/
  sources/moegirl/<title>.md
  characters/<title>.md
  world/<title>.md
  ...
```

未来其他 IP：

```
data/raw/moegirl/fgo/
  ...

wiki/fgo/
  ...
```

### 2. crawl_ip.py 路径构建

在 `crawl_ip.py` 中，基于 profile_id 构建输出路径：

```python
raw_base = Path(f"data/raw/moegirl/{profile_id}")
wiki_base = Path(f"wiki/{profile_id}")
state_file = raw_base / "crawl_state.json"
log_file = raw_base / "crawl_log.jsonl"
```

### 3. crawl_fsn.py 改为 wrapper

当前 `crawl_fsn.py` 是一个独立的完整爬虫（715 行）。改为：

```python
#!/usr/bin/env python3
"""
crawl_fsn.py — Backward-compatible wrapper for FSN crawl.

This script now delegates to the generic entry point:
    python scripts/crawl_ip.py --profile fsn <args>

The old --seed, --seeds, --max-depth, etc. arguments are
forwarded to crawl_ip.py.

Usage:
    python scripts/crawl_fsn.py --max-depth 1 --max-pages 50
    python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1
"""

import sys
import subprocess
from pathlib import Path

def main():
    # Map old args to new crawl_ip.py args
    args = [sys.executable, str(Path(__file__).parent / "crawl_ip.py"), "--profile", "fsn"]

    # Forward all arguments
    args.extend(sys.argv[1:])

    sys.exit(subprocess.call(args))

if __name__ == "__main__":
    main()
```

或者更简单：保留 `crawl_fsn.py` 的 argparser，但在内部调用 `crawl_ip.py --profile fsn` 的核心逻辑。

**注意**：两种方式都可以。关键是旧命令 `python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1` 仍然能运行，且使用 fsn profile。

### 4. README 说明

在 crawl_fsn.py 的 docstring 中说明：

- 旧命令仍可用
- 实际调用的是 `crawl_ip.py --profile fsn`
- 推荐使用 `crawl_ip.py --profile fsn`

（完整的 README 更新在 P1-4，这里只需在脚本注释中说明）

### 5. 旧数据兼容

旧的 `data/raw/moegirl/` 中的数据不应被自动删除或移动。

但需要注意：
- 如果旧的 `crawl_state.json` 存在且没有 profile_id，resume 时应该能处理
- 可以在 resume 检测时，如果发现旧路径有 state 文件，提示用户手动迁移

### 6. profile_id 贯穿所有输出

确保以下文件/路径中包含 profile_id：
- `data/raw/moegirl/<profile_id>/` 下的所有文件
- `wiki/<profile_id>/` 下的所有文件
- crawl_log.jsonl 中的每个事件
- crawl_state.json 中的 config
- crawl_report.md

## 验收标准

1. `python scripts/crawl_ip.py --profile fsn --dry-run` 输出到 `data/raw/moegirl/fsn/`
2. `python scripts/crawl_fsn.py --max-depth 1 --max-pages 5` 仍能运行
3. 不同 profile 的输出不会混在同一个目录
4. 旧的 `data/raw/moegirl/` 中的数据不受影响
5. wiki 输出按 profile 隔离到 `wiki/<profile_id>/`

## 建议验证命令

```bash
# 1. 测试通用入口
python scripts/crawl_ip.py --profile fsn --dry-run --max-depth 1

# 2. 检查输出路径
ls data/raw/moegirl/fsn/ 2>/dev/null || echo "No fsn output dir"

# 3. 测试旧命令兼容
python scripts/crawl_fsn.py --max-depth 1 --max-pages 3 --force

# 4. 检查旧命令输出是否在 fsn 目录
ls data/raw/moegirl/fsn/ 2>/dev/null

# 5. 检查 wiki 输出
ls wiki/fsn/ 2>/dev/null || echo "No wiki/fsn dir"
```

## 阶段完成后必须输出的报告

写入 `docs/agent_runs/<run_id>/P1-3_report.md`，包含：

1. 修改了哪些文件
2. 输出目录结构
3. 旧命令兼容验证结果
4. 新旧输出路径对比
5. 未完成项
6. 下一阶段（P1-4）需要注意的事项
