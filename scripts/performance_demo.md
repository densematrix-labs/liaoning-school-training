# 50 并发只读性能 Demo

该脚本面向公网 Demo，以 50 个并发虚拟用户循环访问已授权的 GET 只读接口，分组展示：

- 常规查询：目标 P95 ≤ 3 秒。
- 班级统计 / 能力汇总：目标 P95 ≤ 10 秒。
- 每组与总体：请求数、成功/失败、吞吐、P50、P95、P99、阈值判断。

## 本地终端演示

从安全渠道取得教师访问令牌后，在仓库根目录执行：

```bash
read -s PERF_TOKEN && export PERF_TOKEN
./scripts/performance_demo.sh --duration 30
unset PERF_TOKEN
```

脚本不会回显或写入令牌，只发起 GET 请求，不生成报告、不触发同步、不执行重算，也不写入业务数据。原始日志只记录中文场景别名、HTTP 状态与耗时，不记录 URL、Cookie、令牌或业务对象 ID。

证据保存到带时间戳的 `performance-results/` 子目录：

- `raw.jsonl`：逐请求脱敏原始日志。
- `result.json`：机器可读汇总。
- `summary.txt`：终端汇总文本。

## 无本地终端时

部署后访问：<https://shixun.demo.densematrix.ai/performance-terminal>

该直链与产品导航隔离，只自动回放仓库内最新一轮脱敏结果。页面不是实时 Shell，不提供命令输入、任务触发或后台控制，仅支持暂停、重新播放和全屏。

> Demo 工程验证，不替代正式验收。正式验收须由双方确认测试环境、标准业务脚本、原始日志和汇总报告。
