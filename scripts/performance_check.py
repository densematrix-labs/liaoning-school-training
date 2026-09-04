#!/usr/bin/env python3
"""50 并发 Demo 业务接口验收脚本（常规 3s，汇总 10s）。"""

import argparse
import asyncio
import statistics
import time
from collections import defaultdict

import httpx


ACCOUNTS = [
    ("2023010101", "123456", "student"),
    ("T20150012", "123456", "teacher"),
    ("T20100008", "123456", "admin"),
]


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * percent) - 1))
    return ordered[index]


async def login(client: httpx.AsyncClient, username: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def run(base_url: str, users: int, duration: int) -> int:
    limits = httpx.Limits(max_connections=max(users + 10, 60), max_keepalive_connections=users)
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=15, limits=limits) as client:
        tokens = {role: await login(client, username, password) for username, password, role in ACCOUNTS}
        teacher_classes = (await client.get("/api/v1/students/classes", headers=tokens["teacher"])).json()
        class_id = teacher_classes[0]["id"]
        routes = {
            "student": [("basic", "/api/v1/scores/?page_size=20"), ("aggregate", "/api/v1/abilities/profile")],
            "teacher": [("basic", f"/api/v1/students/classes/{class_id}/students"), ("aggregate", f"/api/v1/students/classes/{class_id}/overview")],
            "admin": [("basic", "/api/v1/admin/overview"), ("basic", "/api/v1/admin/projects")],
        }
        samples: dict[str, list[float]] = defaultdict(list)
        errors: list[str] = []
        stop_at = time.monotonic() + duration

        async def worker(index: int) -> None:
            role = ACCOUNTS[index % len(ACCOUNTS)][2]
            position = 0
            while time.monotonic() < stop_at:
                category, path = routes[role][position % len(routes[role])]
                position += 1
                started = time.perf_counter()
                try:
                    response = await client.get(path, headers=tokens[role])
                    elapsed = time.perf_counter() - started
                    samples[category].append(elapsed)
                    if response.status_code >= 400:
                        errors.append(f"{role} {path}: HTTP {response.status_code}")
                except Exception as exc:
                    errors.append(f"{role} {path}: {exc}")
                await asyncio.sleep(.05)

        await asyncio.gather(*(worker(index) for index in range(users)))

    request_count = sum(len(items) for items in samples.values()) + len(errors)
    success_count = request_count - len(errors)
    success_rate = success_count / request_count * 100 if request_count else 0
    print(f"users={users} duration={duration}s requests={request_count} success_rate={success_rate:.2f}%")
    for category, values in samples.items():
        print(f"{category}: count={len(values)} avg={statistics.mean(values):.3f}s p95={percentile(values, .95):.3f}s max={max(values):.3f}s")
    if errors:
        print("errors:")
        for item in errors[:20]:
            print(f"- {item}")
    basic_ok = percentile(samples["basic"], .95) <= 3
    aggregate_ok = percentile(samples["aggregate"], .95) <= 10
    return 0 if success_rate >= 99 and basic_ok and aggregate_ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://shixun.demo.densematrix.ai")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.base_url, args.users, args.duration)))
