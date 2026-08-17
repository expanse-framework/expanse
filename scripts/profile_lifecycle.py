#!/usr/bin/env python
"""
Profiles the Expanse HTTP request/response lifecycle end-to-end.

Boots a real (minimal) Expanse application in-process and drives a batch of
synthetic requests directly through the ASGI callable (Portal.__call__) --
no sockets, no subprocess -- while timing the key lifecycle stages. It also
runs the same batch under cProfile so you can see which functions actually
dominate self time.

Replay it any time with:

    uv run python scripts/profile_lifecycle.py
    uv run python scripts/profile_lifecycle.py --iterations 1000 --top 30
    uv run python scripts/profile_lifecycle.py --save-prof /tmp/lifecycle.prof
    uv run python scripts/profile_lifecycle.py --route json_pydantic --iterations 2000

Then, optionally, inspect the saved profile with:

    uv run snakeviz /tmp/lifecycle.prof
"""

import argparse
import asyncio
import cProfile
import io
import pstats
import statistics
import sys
import time

from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import msgspec

from pydantic import BaseModel


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expanse.container.container import Container  # noqa: E402
from expanse.core.application import Application  # noqa: E402
from expanse.core.http.middleware.middleware_stack import MiddlewareStack  # noqa: E402
from expanse.core.http.portal import Portal  # noqa: E402
from expanse.http.helpers import json as json_response  # noqa: E402
from expanse.http.json import JSON  # noqa: E402
from expanse.http.response import Response  # noqa: E402
from expanse.http.response_adapter import ResponseAdapter  # noqa: E402
from expanse.http.responses.file import FileResponse  # noqa: E402
from expanse.http.responses.redirect import RedirectResponse  # noqa: E402
from expanse.http.responses.streamed import StreamedResponse  # noqa: E402
from expanse.http.responses.view import ViewResponse  # noqa: E402
from expanse.routing.finder import Finder  # noqa: E402
from expanse.routing.pipeline import Pipeline  # noqa: E402
from expanse.support.service_provider import ServiceProvider  # noqa: E402
from expanse.support.service_providers_list import ServiceProvidersList  # noqa: E402
from expanse.types import Receive  # noqa: E402
from expanse.types import Scope  # noqa: E402
from expanse.types import Send  # noqa: E402


# --------------------------------------------------------------------------
# A tiny synthetic app: one route per lifecycle "feature" we want to weigh.
# --------------------------------------------------------------------------


class Greeter:
    """A singleton dependency, to price plain container lookups."""

    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


class RequestCounter:
    """A scoped (per-request) dependency, to price scoped construction."""

    def __init__(self, greeter: Greeter) -> None:
        self.greeter = greeter


class EchoModel(BaseModel):
    name: str
    count: int


class EchoStruct(msgspec.Struct):
    name: str
    count: int


class DemoServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(Greeter)
        self._container.scoped(RequestCounter)


async def hello() -> Response:
    return json_response({"message": "Hello, world!"})


async def get_user(user_id: str) -> Response:
    return json_response({"id": user_id})


async def with_dependencies(greeter: Greeter, counter: RequestCounter) -> Response:
    return json_response({"message": counter.greeter.greet("dependency")})


async def adapted() -> dict[str, str]:
    # Returning a plain dict forces the route handler through
    # ResponseAdapter.adapt() instead of returning a Response directly.
    return {"message": "adapted"}


async def echo_pydantic(payload: JSON[EchoModel]) -> Response:
    return json_response({"name": payload.name, "count": payload.count})


async def echo_msgspec(payload: JSON[EchoStruct]) -> Response:
    return json_response({"name": payload.name, "count": payload.count})


async def build_app() -> Application:
    async def configure_middleware(stack: MiddlewareStack) -> None:
        # No global middleware: we want the core framework cost (routing,
        # DI, response building), not TrustHosts/TrustProxies/ManageCors.
        stack.use([])

    app = (
        Application.configure(ROOT)
        .with_middleware(configure_middleware)
        .with_providers(ServiceProvidersList.default())
        .create()
    )

    await app.bootstrap()

    app.config["app.env"] = "test"
    app.config["app.debug"] = True
    app.config["app.secret_key"] = "k" * 32
    app.config["encryption.salt"] = "s" * 32

    await app.boot()

    await app.register(DemoServiceProvider(app.container))

    router = await app.container.get("router")
    router.get("/hello", hello, name="hello")
    router.get("/users/{user_id}", get_user, name="user")
    router.get("/deps", with_dependencies, name="deps")
    router.get("/adapted", adapted, name="adapted")
    router.post("/echo/pydantic", echo_pydantic, name="echo.pydantic")
    router.post("/echo/msgspec", echo_msgspec, name="echo.msgspec")

    return app


# --------------------------------------------------------------------------
# A minimal in-process ASGI driver (no threads, no sockets) so timings
# reflect only framework overhead, not transport overhead.
# --------------------------------------------------------------------------


class ScenarioRequest:
    def __init__(
        self,
        name: str,
        method: str,
        path: str,
        body: bytes = b"",
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        self.name = name
        self.method = method
        self.path = path
        self.body = body
        self.headers = headers or []
        if body and not any(h[0] == b"content-type" for h in self.headers):
            self.headers = [*self.headers, (b"content-type", b"application/json")]

    def scope(self) -> Scope:
        return {
            "type": "http",
            "http_version": "1.1",
            "method": self.method,
            "path": self.path,
            "raw_path": self.path.encode(),
            "root_path": "",
            "scheme": "http",
            "query_string": b"",
            "headers": [(b"host", b"testserver"), *self.headers],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "extensions": {},
        }


def _make_receive(body: bytes) -> Receive:
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _make_send() -> tuple[Send, list[dict[str, Any]]]:
    messages: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    return send, messages


SCENARIOS: list[ScenarioRequest] = [
    ScenarioRequest("hello", "GET", "/hello"),
    ScenarioRequest("path_param", "GET", "/users/42"),
    ScenarioRequest("di_scoped", "GET", "/deps"),
    ScenarioRequest("response_adapter", "GET", "/adapted"),
    ScenarioRequest(
        "json_pydantic",
        "POST",
        "/echo/pydantic",
        body=b'{"name": "ada", "count": 3}',
    ),
    ScenarioRequest(
        "json_msgspec",
        "POST",
        "/echo/msgspec",
        body=b'{"name": "ada", "count": 3}',
    ),
]


# --------------------------------------------------------------------------
# Stage instrumentation: wraps well-defined lifecycle boundaries with wall
# clock timers. Stages are declared as a tree because the pipeline is
# genuinely nested (global middleware wraps routing wraps route middleware
# wraps the handler) -- percentages are relative to total wall time, and a
# child's time is *included* in its parent's, not subtracted from it.
# --------------------------------------------------------------------------

# Each entry is (key, parent_key, label).
STAGE_TREE: list[tuple[str, str | None, str]] = [
    ("wall_total", None, "Full ASGI call (scope in -> bytes sent)"),
    ("handle_total", "wall_total", "Portal.handle() -- build the Response object"),
    ("scoped_container", "handle_total", "Per-request scoped container enter/exit"),
    (
        "global_pipeline",
        "handle_total",
        "Global middleware chain + routing (nested below)",
    ),
    ("route_matching", "global_pipeline", "Matching the request path to a Route"),
    (
        "route_pipeline",
        "global_pipeline",
        "Route middleware chain + endpoint handler (nested below)",
    ),
    (
        "container_resolve",
        "route_pipeline",
        "DI: resolving constructor/endpoint parameters",
    ),
    (
        "response_adapt",
        "route_pipeline",
        "Adapting a non-Response return value into a Response",
    ),
    (
        "response_prepare",
        "handle_total",
        "Response.prepare() -- headers, cookies, content-length",
    ),
    ("asgi_send", "wall_total", "Sending status/headers + body over ASGI `send`"),
    ("run_deferred", "wall_total", "Deferred callbacks after the response is sent"),
]


class Stage:
    __slots__ = ("durations", "key", "label", "parent")

    def __init__(self, key: str, parent: str | None, label: str) -> None:
        self.key = key
        self.parent = parent
        self.label = label
        self.durations: list[float] = []


class Instrumentation:
    def __init__(self) -> None:
        self.stages: dict[str, Stage] = {
            key: Stage(key, parent, label) for key, parent, label in STAGE_TREE
        }
        self._patches: list[tuple[Any, str, Any]] = []
        self._portal: Portal | None = None
        self._original_portal_handle: Callable[..., Awaitable[Any]] | None = None

    def record(self, key: str, duration: float) -> None:
        self.stages[key].durations.append(duration)

    def _patch(self, target: Any, attr: str, wrapped: Callable[..., Any]) -> None:
        original = target.__dict__.get(attr) or getattr(target, attr)
        self._patches.append((target, attr, original))
        setattr(target, attr, wrapped(original))

    def _timed_async(
        self, key: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def factory(original: Callable[..., Awaitable[Any]]) -> Callable[..., Any]:
            @wraps(original)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                try:
                    return await original(*args, **kwargs)
                finally:
                    self.record(key, time.perf_counter() - start)

            return wrapper

        return factory

    def _timed_sync(
        self, key: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def factory(original: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(original)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                try:
                    return original(*args, **kwargs)
                finally:
                    self.record(key, time.perf_counter() - start)

            return wrapper

        return factory

    def install(self, portal: Portal) -> None:
        self._patch(Container, "__aenter__", self._timed_async("scoped_container"))
        self._patch(Container, "__aexit__", self._timed_async("scoped_container"))
        self._patch(Finder, "match", self._timed_sync("route_matching"))
        self._patch(
            Container, "_resolve_signature", self._timed_async("container_resolve")
        )
        self._patch(ResponseAdapter, "adapt", self._timed_async("response_adapt"))

        for cls in (Response, RedirectResponse, FileResponse, ViewResponse):
            if "prepare" in cls.__dict__:
                self._patch(cls, "prepare", self._timed_async("response_prepare"))

        for cls in (Response, FileResponse, StreamedResponse):
            if "send_body" in cls.__dict__:
                self._patch(cls, "send_body", self._timed_async("asgi_send"))

        self._patch(Response, "start_response", self._timed_async("asgi_send"))
        self._patch(Response, "run_deferred", self._timed_async("run_deferred"))

        # Pipeline.to() is used both for the global middleware stack (called
        # from portal.py) and the per-route middleware stack (called from
        # router.py). We tell them apart by looking at the immediate caller's
        # file, since they're otherwise the same code path.
        original_to = Pipeline.__dict__["to"]

        @wraps(original_to)
        async def timed_pipeline_to(pipeline_self: Pipeline, handler: Any) -> Any:
            caller_file = sys._getframe(1).f_code.co_filename
            key = (
                "route_pipeline"
                if caller_file.endswith("router.py")
                else "global_pipeline"
            )
            start = time.perf_counter()
            try:
                return await original_to(pipeline_self, handler)
            finally:
                self.record(key, time.perf_counter() - start)

        self._patches.append((Pipeline, "to", original_to))
        Pipeline.to = timed_pipeline_to

        original_handle = portal.handle

        @wraps(original_handle)
        async def timed_handle(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await original_handle(*args, **kwargs)
            finally:
                self.record("handle_total", time.perf_counter() - start)

        self._portal = portal
        self._original_portal_handle = original_handle
        portal.handle = timed_handle

    def uninstall(self) -> None:
        for target, attr, original in reversed(self._patches):
            setattr(target, attr, original)
        self._patches.clear()

        if self._portal is not None and self._original_portal_handle is not None:
            self._portal.handle = self._original_portal_handle
        self._portal = None
        self._original_portal_handle = None


# --------------------------------------------------------------------------
# Driving requests + reporting
# --------------------------------------------------------------------------


async def run_requests(
    portal: Portal,
    scenarios: list[ScenarioRequest],
    instrumentation: Instrumentation | None = None,
) -> list[float]:
    """Runs one pass over `scenarios` through the real ASGI callable, returning
    per-request wall times (seconds)."""

    wall_times = []
    for scenario in scenarios:
        receive = _make_receive(scenario.body)
        send, messages = _make_send()

        start = time.perf_counter()
        await portal(scenario.scope(), receive, send)
        duration = time.perf_counter() - start
        wall_times.append(duration)
        if instrumentation is not None:
            instrumentation.record("wall_total", duration)

        status = next(
            (m["status"] for m in messages if m["type"] == "http.response.start"), None
        )
        if status is None or status >= 400:
            body = b"".join(
                m.get("body", b"")
                for m in messages
                if m["type"] == "http.response.body"
            )
            raise RuntimeError(
                f"Scenario {scenario.name!r} failed with status {status}: {body!r}"
            )

    return wall_times


def _fmt_seconds(seconds: float) -> str:
    if seconds < 1e-3:
        return f"{seconds * 1e6:8.1f} us"
    return f"{seconds * 1e3:8.3f} ms"


def print_stage_report(instrumentation: Instrumentation, total_requests: int) -> None:
    wall_total = instrumentation.stages["wall_total"].durations
    denom = sum(wall_total) or 1.0

    depth: dict[str, int] = {}

    def compute_depth(key: str) -> int:
        if key in depth:
            return depth[key]
        parent = instrumentation.stages[key].parent
        d = 0 if parent is None else compute_depth(parent) + 1
        depth[key] = d
        return d

    print()
    print(f"Lifecycle stage breakdown -- {total_requests} requests")
    print(
        "(percentages are of total wall time; a nested stage's time is "
        "included in its parent's, not subtracted from it)"
    )
    print("-" * 92)
    header = f"{'stage':38s} {'count':>6s} {'total':>12s} {'mean':>12s} {'% wall':>8s}"
    print(header)
    print("-" * 92)

    for key, _parent, _label in STAGE_TREE:
        stage = instrumentation.stages[key]
        durations = stage.durations
        indent = "  " * compute_depth(key)
        name = f"{indent}{key}"
        if not durations:
            print(f"{name:38s} {'-':>6s} {'-':>12s} {'-':>12s} {'-':>8s}")
            continue

        total = sum(durations)
        mean = total / len(durations)
        pct = 100 * total / denom
        print(
            f"{name:38s} {len(durations):6d} {_fmt_seconds(total):>12s} "
            f"{_fmt_seconds(mean):>12s} {pct:7.1f}%"
        )

    print("-" * 92)
    for key, _parent, label in STAGE_TREE:
        indent = "  " * depth[key]
        print(f"{indent}{key}: {label}")


def print_scenario_report(scenario_timings: dict[str, list[float]]) -> None:
    print()
    print("Per-scenario wall time (full ASGI call)")
    print("-" * 78)
    print(f"{'scenario':20s} {'n':>6s} {'mean':>12s} {'median':>12s} {'p95':>12s}")
    print("-" * 78)
    for name, durations in scenario_timings.items():
        durations_sorted = sorted(durations)
        mean = statistics.mean(durations_sorted)
        median = statistics.median(durations_sorted)
        p95_index = min(len(durations_sorted) - 1, int(len(durations_sorted) * 0.95))
        p95 = durations_sorted[p95_index]
        print(
            f"{name:20s} {len(durations):6d} {_fmt_seconds(mean):>12s} "
            f"{_fmt_seconds(median):>12s} {_fmt_seconds(p95):>12s}"
        )


def print_cprofile_report(profiler: cProfile.Profile, top: int) -> None:
    def dump(sort_key: str, title: str) -> None:
        print()
        print(f"cProfile -- top {top} by {title} (expanse/* frames only)")
        print("-" * 92)
        buf = io.StringIO()
        s = pstats.Stats(profiler, stream=buf)
        s.sort_stats(sort_key)
        s.print_stats(r"src[\\/]expanse", top)
        # Drop pstats' own header/footer noise, keep the table.
        lines = buf.getvalue().splitlines()
        for line in lines:
            if line.strip():
                print(line)

    dump("cumulative", "cumulative time")
    dump("tottime", "self (own) time")


async def main_async(args: argparse.Namespace) -> None:
    scenarios = SCENARIOS
    if args.route:
        scenarios = [s for s in SCENARIOS if s.name == args.route]
        if not scenarios:
            available = ", ".join(s.name for s in SCENARIOS)
            raise SystemExit(f"Unknown --route {args.route!r}. Available: {available}")

    print(f"Building app and warming up ({args.warmup} iterations)...")
    app = await build_app()
    portal: Portal = await app.container.get(Portal)

    for _ in range(args.warmup):
        await run_requests(portal, scenarios)

    instrumentation = Instrumentation()
    instrumentation.install(portal)

    scenario_timings: dict[str, list[float]] = {s.name: [] for s in scenarios}

    print(f"Profiling {args.iterations} iterations x {len(scenarios)} scenario(s)...")

    profiler: cProfile.Profile | None = (
        cProfile.Profile() if not args.no_cprofile else None
    )
    if profiler is not None:
        profiler.enable()

    try:
        for _ in range(args.iterations):
            wall_times = await run_requests(portal, scenarios, instrumentation)
            for scenario, wall_time in zip(scenarios, wall_times, strict=True):
                scenario_timings[scenario.name].append(wall_time)
    finally:
        if profiler is not None:
            profiler.disable()
        instrumentation.uninstall()

    total_requests = args.iterations * len(scenarios)

    print_stage_report(instrumentation, total_requests)
    print_scenario_report(scenario_timings)

    if profiler is not None:
        print_cprofile_report(profiler, args.top)

        if args.save_prof:
            pstats.Stats(profiler).dump_stats(args.save_prof)
            print()
            print(f"Saved raw cProfile stats to {args.save_prof}")
            print(f"Inspect with: uv run snakeviz {args.save_prof}")

    await app.container.terminate()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=200,
        help="Number of profiling passes over the scenario set (default: 200).",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=20,
        help="Number of untimed warmup passes, to avoid import/JIT noise (default: 20).",
    )
    parser.add_argument(
        "--route",
        type=str,
        default=None,
        help="Only profile a single scenario by name "
        f"({', '.join(s.name for s in SCENARIOS)}).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of functions to show in each cProfile table (default: 20).",
    )
    parser.add_argument(
        "--no-cprofile",
        action="store_true",
        help="Skip the cProfile pass and only show the stage breakdown.",
    )
    parser.add_argument(
        "--save-prof",
        type=str,
        default=None,
        help="Path to dump raw cProfile stats to (e.g. for snakeviz).",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
