# Agent Tasks — 分阶段自动执行脚手架

## 目的

将 profile 化爬虫改造大任务拆成多个阶段，每阶段启动独立 opencode 会话执行。

## 为什么要分阶段新开 opencode 会话

单次 opencode 会话的上下文有限。超长任务会导致模型能力下降、遗漏细节、重复犯错。分阶段执行可以：

- 每个阶段的 prompt 更短、更聚焦
- 阶段之间通过文件和报告传递状态，而非依赖长上下文记忆
- 失败后可以从失败阶段恢复，不必从头开始
- 每个阶段的改动范围明确，便于审查

## 阶段列表

| 阶段 ID | 名称 | 类型 |
|---------|------|------|
| P0-1 | 通用链接过滤 | 通用核心 |
| P0-2 | 优先队列与 checkpoint | 通用核心 |
| P0-3 | score_detail 可解释日志 | 通用核心 |
| P0-4 | dry-run / score-only 模式 | 通用核心 |
| P0-5 | crawl_report 生成 | 通用核心 |
| P1-1 | profile loader 与通用入口 | Profile 化 |
| P1-2 | fsn.yaml 与 template.yaml | Profile 化 |
| P1-3 | 输出目录隔离与旧命令兼容 | Profile 化 |
| P1-4 | 文档更新与最终验证 | 收尾 |

## 查看阶段列表

```bash
python tools/opencode_stage_runner.py --list
```

## Dry-run（只打印不执行）

```bash
# 查看所有阶段
python tools/opencode_stage_runner.py --dry-run

# 查看指定范围
python tools/opencode_stage_runner.py --from P0-3 --until P0-4 --dry-run

# 查看单个阶段
python tools/opencode_stage_runner.py --only P1-2 --dry-run
```

## 执行指定阶段

```bash
# 执行所有阶段
python tools/opencode_stage_runner.py

# 执行 P0-3 到 P0-4
python tools/opencode_stage_runner.py --from P0-3 --until P0-4

# 只执行 P1-2
python tools/opencode_stage_runner.py --only P1-2

# 从 P1-1 执行到最后
python tools/opencode_stage_runner.py --from P1-1
```

## Resume（跳过已完成阶段）

```bash
python tools/opencode_stage_runner.py --resume
```

会自动查找最近一次运行的日志，跳过已成功完成的阶段，从第一个未完成阶段继续。

## 指定 opencode 命令

```bash
# 通过参数指定
python tools/opencode_stage_runner.py --agent-cmd "opencode" --agent-args "run"

# 通过环境变量指定
set OPENCODE_CMD=opencode
set OPENCODE_ARGS=run
python tools/opencode_stage_runner.py
```

## 日志位置

每次运行创建一个 run_id 目录：

```
docs/agent_runs/20260602_153000/
  run_config.json       # 运行配置
  run_log.jsonl         # 事件日志
  P0-1_prompt.md        # 合成 prompt
  P0-1_stdout.log       # 标准输出
  P0-1_stderr.log       # 标准错误
  P0-1_report.md        # 阶段报告
  ...
```

## 失败后如何继续

1. 查看失败阶段的 stderr 日志
2. 手动修复问题
3. 从失败阶段重新执行：

```bash
python tools/opencode_stage_runner.py --from <failed_stage_id>
```

4. 或使用 resume 自动跳过已完成阶段：

```bash
python tools/opencode_stage_runner.py --resume
```

## 不要把大任务一次性丢给单个窗口

这正是脚手架存在的原因。请使用阶段化执行，而不是把整个改造计划直接发给 opencode。
