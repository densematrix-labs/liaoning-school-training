#!/usr/bin/env python3
"""对公网 Demo 执行 50 并发、仅 GET 的脱敏工程验证。"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx


DEFAULT_TARGET = "https://shixun.demo.densematrix.ai"
TARGET_LABEL = "公网 Demo（HTTPS）"
DISCLAIMER = "Demo 工程验证，不替代正式验收。正式验收须由双方确认测试环境、标准业务脚本、原始日志和汇总报告。"
THRESHOLDS = {"regular": 3.0, "aggregate": 10.0}
GROUP_LABELS = {"regular": "常规查询", "aggregate": "班级统计 / 能力汇总"}


@dataclass
class Sample:
    sequence: int
    timestamp: str
    group: str
    operation: str
    status: int | None
    elapsed_ms: float
    success: bool
    error_type: str | None = None


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * ratio) - 1))
    return ordered[index]


def safe_git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def extract_items(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return [item for item in payload[key] if isinstance(item, dict)]
    return []


async def get_json(client: httpx.AsyncClient, path: str) -> Any:
    response = await client.get(path)
    response.raise_for_status()
    return response.json()


async def run_test(args: argparse.Namespace, token: str, root: Path) -> tuple[dict[str, Any], list[Sample], Path]:
    target = args.target.rstrip("/")
    parsed = urlparse(target)
    if parsed.scheme != "https" and not (args.allow_http and parsed.hostname in {"localhost", "127.0.0.1"}):
        raise ValueError("目标必须使用 HTTPS；仅显式 --allow-http 时允许本机 HTTP")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("目标地址不得包含凭证、查询参数或片段")

    limits = httpx.Limits(max_connections=max(args.concurrency + 10, 60), max_keepalive_connections=args.concurrency)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "Liaogui-ReadOnly-Performance-Demo/1.0"}
    async with httpx.AsyncClient(base_url=target, headers=headers, timeout=httpx.Timeout(args.timeout), limits=limits, follow_redirects=False) as client:
        await get_json(client, "/api/v1/auth/me")
        classes = extract_items(await get_json(client, "/api/v1/students/classes"), "classes")
        if not classes or not classes[0].get("id"):
            raise RuntimeError("当前令牌没有可用于只读验证的授权班级")
        class_id = str(classes[0]["id"])
        students = extract_items(await get_json(client, f"/api/v1/students/classes/{class_id}/students"), "students")
        if not students or not students[0].get("id"):
            raise RuntimeError("授权班级没有可用于能力汇总验证的学生")
        student_id = str(students[0]["id"])
        routes = {
            "regular": [
                ("当前用户信息", "/api/v1/auth/me"),
                ("授权班级列表", "/api/v1/students/classes"),
                ("实训项目列表", "/api/v1/scores/projects"),
            ],
            "aggregate": [
                ("班级统计汇总", f"/api/v1/students/classes/{class_id}/overview"),
                ("学生能力汇总", f"/api/v1/abilities/student/{student_id}"),
            ],
        }
        samples: list[Sample] = []
        lock = asyncio.Lock()
        started_monotonic = time.monotonic()
        stop_at = started_monotonic + args.duration
        sequence = 0

        async def worker(index: int) -> None:
            nonlocal sequence
            group = "regular" if index % 2 == 0 else "aggregate"
            choices = routes[group]
            position = index % len(choices)
            while time.monotonic() < stop_at:
                operation, path = choices[position % len(choices)]
                position += 1
                request_started = time.perf_counter()
                status: int | None = None
                error_type: str | None = None
                try:
                    response = await client.get(path)
                    status = response.status_code
                    success = 200 <= status < 300
                    if not success:
                        error_type = f"HTTP_{status}"
                except httpx.TimeoutException:
                    success = False
                    error_type = "TIMEOUT"
                except httpx.HTTPError:
                    success = False
                    error_type = "HTTP_CLIENT_ERROR"
                elapsed_ms = round((time.perf_counter() - request_started) * 1000, 3)
                async with lock:
                    sequence += 1
                    samples.append(Sample(
                        sequence=sequence,
                        timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                        group=group,
                        operation=operation,
                        status=status,
                        elapsed_ms=elapsed_ms,
                        success=success,
                        error_type=error_type,
                    ))
                if args.think_time > 0:
                    await asyncio.sleep(args.think_time)

        await asyncio.gather(*(worker(index) for index in range(args.concurrency)))
        actual_duration = round(time.monotonic() - started_monotonic, 3)

    now_local = datetime.now(ZoneInfo(args.timezone))
    tested_at = now_local.isoformat(timespec="seconds")
    groups: dict[str, Any] = {}
    for group in ("regular", "aggregate"):
        group_samples = [item for item in samples if item.group == group]
        successful = [item for item in group_samples if item.success]
        latencies = [item.elapsed_ms / 1000 for item in successful]
        p95 = percentile(latencies, 0.95)
        groups[group] = {
            "label": GROUP_LABELS[group],
            "requests": len(group_samples),
            "success": len(successful),
            "failed": len(group_samples) - len(successful),
            "throughput_rps": round(len(group_samples) / actual_duration, 3) if actual_duration else 0,
            "p50_seconds": round(percentile(latencies, 0.50), 3),
            "p95_seconds": round(p95, 3),
            "p99_seconds": round(percentile(latencies, 0.99), 3),
            "target_p95_seconds": THRESHOLDS[group],
            "passed": bool(group_samples) and len(successful) == len(group_samples) and p95 <= THRESHOLDS[group],
        }
    total = len(samples)
    success = sum(item.success for item in samples)
    result = {
        "schema_version": 1,
        "test_id": now_local.strftime("liaogui-readonly-%Y%m%dT%H%M%S%z"),
        "tested_at": tested_at,
        "timezone": args.timezone,
        "environment": TARGET_LABEL,
        "source_commit": safe_git_commit(root),
        "method": "50 个并发虚拟用户持续轮询已授权 GET 只读业务接口",
        "concurrency": args.concurrency,
        "configured_duration_seconds": args.duration,
        "actual_duration_seconds": actual_duration,
        "total_requests": total,
        "success": success,
        "failed": total - success,
        "success_rate": round(success / total * 100, 3) if total else 0,
        "throughput_rps": round(total / actual_duration, 3) if actual_duration else 0,
        "groups": groups,
        "passed": total > 0 and success == total and all(item["passed"] for item in groups.values()),
        "request_method": "GET only",
        "credentials_logged": False,
        "identifiers_logged": False,
        "disclaimer": DISCLAIMER,
    }
    stamp = now_local.strftime("%Y%m%dT%H%M%S")
    return result, samples, root / args.output_root / stamp


def render_lines(result: dict[str, Any]) -> list[str]:
    lines = [
        "$ PERF_TOKEN=[已从环境变量读取] ./scripts/performance_demo.sh",
        "NOTICE 凭证已脱敏；测试仅发起 GET 只读请求",
        f"NOTICE 测试时间 {result['tested_at']} · {result['environment']}",
        f"NOTICE 并发虚拟用户 {result['concurrency']} · 实际持续 {result['actual_duration_seconds']:.3f} 秒",
        "",
    ]
    for key in ("regular", "aggregate"):
        item = result["groups"][key]
        lines.extend([
            f"=== {item['label']}（目标 P95 ≤ {item['target_p95_seconds']:.0f}s） ===",
            f"请求 {item['requests']}  成功 {item['success']}  失败 {item['failed']}  吞吐 {item['throughput_rps']:.3f} req/s",
            f"P50 {item['p50_seconds']:.3f}s  P95 {item['p95_seconds']:.3f}s  P99 {item['p99_seconds']:.3f}s",
            f"{'PASS' if item['passed'] else 'FAIL'} 阈值判断：{'通过' if item['passed'] else '未通过'}",
            "",
        ])
    lines.extend([
        "=== 总体结果 ===",
        f"总请求 {result['total_requests']}  成功 {result['success']}  失败 {result['failed']}  成功率 {result['success_rate']:.3f}%",
        f"总体吞吐 {result['throughput_rps']:.3f} req/s",
        f"{'PASS' if result['passed'] else 'FAIL'} Demo 工程验证{'通过' if result['passed'] else '未通过'}",
        f"NOTICE {DISCLAIMER}",
    ])
    return lines


def write_artifacts(root: Path, output_dir: Path, result: dict[str, Any], samples: list[Sample]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw.jsonl"
    raw_path.write_text("".join(json.dumps(asdict(item), ensure_ascii=False) + "\n" for item in samples), encoding="utf-8")
    result_path = output_dir / "result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = render_lines(result)
    summary_path = output_dir / "summary.txt"
    summary_path.write_text("\n".join(lines[2:]) + "\n", encoding="utf-8")
    replay = {
        "title": "公网 Demo · 50 并发只读业务验证",
        "tested_at": result["tested_at"],
        "environment": result["environment"],
        "concurrency": result["concurrency"],
        "duration_seconds": result["actual_duration_seconds"],
        "terminal_lines": lines,
    }
    replay_path = root / "frontend/src/data/performanceReplay.json"
    replay_path.write_text(json.dumps(replay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\n证据文件（均已脱敏）：")
    for path in (raw_path, result_path, summary_path):
        print(f"- {path.relative_to(root)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="公网 Demo 50 并发只读性能演示")
    parser.add_argument("--target", default=os.environ.get("PERF_TARGET", DEFAULT_TARGET), help=argparse.SUPPRESS)
    parser.add_argument("--token-env", default="PERF_TOKEN", help="承载访问令牌的环境变量名（默认 PERF_TOKEN）")
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--think-time", type=float, default=0.5, help="每个虚拟用户两次操作间隔（默认 0.5 秒）")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--timezone", default="America/Los_Angeles")
    parser.add_argument("--output-root", default="performance-results")
    parser.add_argument("--allow-http", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.concurrency <= 100:
        parser.error("--concurrency 必须在 1 到 100 之间")
    if not 1 <= args.duration <= 300:
        parser.error("--duration 必须在 1 到 300 秒之间")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    token = os.environ.get(args.token_env, "").strip()
    if not token:
        print(f"缺少认证信息：请通过环境变量 {args.token_env} 提供访问令牌；脚本不会记录该值。", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    try:
        result, samples, output_dir = asyncio.run(run_test(args, token, root))
        write_artifacts(root, output_dir, result, samples)
    except (ValueError, RuntimeError, httpx.HTTPError) as exc:
        print(f"测试未执行：{type(exc).__name__}。请检查只读令牌权限、网络和目标环境。", file=sys.stderr)
        return 2
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
