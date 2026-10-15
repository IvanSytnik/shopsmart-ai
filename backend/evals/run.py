"""Offline evaluation: run fixed scenarios through the planner with the real OpenAI API.

    cd backend
    .venv/bin/python -m evals.run                 # all cases in evals/cases.yaml
    .venv/bin/python -m evals.run --cases 2       # the first 2 cases
    .venv/bin/python -m evals.run --repeat 3      # every case 3 times

Costs money (OPENAI_API_KEY from the environment or backend/.env), so it is not part of
CI. Calls the planner in-process, sequentially. Writes evals/results/<timestamp>.json and
evals/report.md; exits with 1 if any plan is over budget or breaks a requested diet.
"""

import argparse
import asyncio
import json
import logging
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import openai
import yaml
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import Settings
from app.schemas.catalog import NON_FOOD_CATEGORIES
from app.schemas.requests import GenerateRequest
from app.services.catalog import ProductCatalog, load_catalog
from app.services.llm import LLMOutputError, create_llm_client
from app.services.planner import (
    NotEnoughProductsError,
    PlanTrace,
    create_plan,
    select_candidates,
    to_response,
)

EVALS = Path(__file__).resolve().parent
CASES_FILE = EVALS / "cases.yaml"
RESULTS_DIR = EVALS / "results"
REPORT_FILE = EVALS / "report.md"

# USD per 1M tokens (input, output). OpenAI's published gpt-4o-mini price at its launch
# (2024-07-18), not re-checked since; update when it changes. Other models: cost not shown.
PRICES_PER_M_TOKENS: dict[str, tuple[float, float]] = {"gpt-4o-mini": (0.15, 0.60)}

# Statuses for a request the planner was never asked about.
REJECTED = ("unknown_store", "not_enough_products")


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    note: str = ""
    request: GenerateRequest


@dataclass
class CaseResult:
    id: str
    run: int
    mode: str
    status: (
        str  # ok | unknown_store | not_enough_products | generation_failed | timeout | api_error
    )
    attempts: int = 0
    first_attempt_accepted: bool = False
    repaired: bool = False
    used_fallback: bool = False
    scaled: bool = False
    trimmed_count: int = 0
    total: float | None = None
    budget: float = 0
    within_budget: bool | None = None
    diet_violations: list[str] = field(default_factory=list)
    kcal_per_person_day: float | None = None
    kcal_basis: str | None = None
    kcal_in_range: bool | None = None  # menu mode only
    warnings: list[str] = field(default_factory=list)
    latency_s: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float | None = None
    error: str | None = None


def load_cases(path: Path = CASES_FILE) -> list[EvalCase]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [EvalCase.model_validate(case) for case in data["cases"]]


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    prices = PRICES_PER_M_TOKENS.get(model)
    if prices is None:
        return None
    return (prompt_tokens * prices[0] + completion_tokens * prices[1]) / 1_000_000


def diet_violations(
    items: list[Any], request: GenerateRequest, catalog: ProductCatalog
) -> list[str]:
    """`product_id:diet` for every food item whose catalog tags miss a requested diet."""
    found = []
    for item in items:
        product = catalog.get(item.product_id)
        if product is None or product.category in NON_FOOD_CATEGORIES:
            continue
        found += [f"{product.id}:{diet}" for diet in request.diets if diet not in product.diet_tags]
    return found


async def run_case(
    case: EvalCase,
    run: int,
    client: AsyncOpenAI,
    settings: Settings,
    catalog: ProductCatalog,
) -> CaseResult:
    request = case.request
    result = CaseResult(id=case.id, run=run, mode=request.mode, status="ok", budget=request.budget)
    stores = catalog.stores_by_country()[request.country]
    if any(store not in stores for store in request.supermarkets):
        result.status = "unknown_store"
        return result
    trace = PlanTrace()
    start = time.perf_counter()
    try:
        candidates = select_candidates(catalog, request)
        plan = await create_plan(client, settings, catalog, request, candidates, trace)
        response = to_response(plan, request, catalog, settings)
    except NotEnoughProductsError:
        result.status = "not_enough_products"
    except (openai.APITimeoutError, TimeoutError) as e:
        result.status, result.error = "timeout", type(e).__name__
    except openai.APIError as e:
        result.status, result.error = "api_error", type(e).__name__
    except LLMOutputError as e:
        result.status, result.error = "generation_failed", e.problem[:200]
    else:
        result.scaled = plan.scaled
        result.trimmed_count = len(response.trimmed)
        result.total = response.total
        result.within_budget = response.total <= response.budget
        result.diet_violations = diet_violations(response.items, request, catalog)
        result.kcal_per_person_day = response.kcal_per_person_day
        result.kcal_basis = response.kcal_basis
        if request.mode == "menu":
            kcal = response.kcal_per_person_day
            low, high = settings.min_kcal_per_person_day, settings.max_kcal_per_person_day
            result.kcal_in_range = low <= kcal <= high
        result.warnings = list(response.warnings)
    result.latency_s = round(time.perf_counter() - start, 2)
    result.attempts = trace.attempts
    result.first_attempt_accepted = trace.accepted_attempt == 1
    result.repaired = trace.attempts > 1
    result.used_fallback = trace.used_fallback
    result.prompt_tokens = sum(u.prompt_tokens for u in trace.usage)
    result.completion_tokens = sum(u.completion_tokens for u in trace.usage)
    result.cost_usd = cost_usd(
        settings.openai_model, result.prompt_tokens, result.completion_tokens
    )
    return result


async def run_cases(
    cases: list[EvalCase],
    client: AsyncOpenAI,
    settings: Settings,
    catalog: ProductCatalog,
    repeat: int = 1,
    progress: bool = False,
) -> list[CaseResult]:
    results = []
    for run in range(1, repeat + 1):
        for case in cases:
            result = await run_case(case, run, client, settings, catalog)
            if progress:
                print(
                    f"{case.id} #{run}: {result.status}, {result.attempts} attempt(s), "
                    f"{result.latency_s}s",
                    flush=True,
                )
            results.append(result)
    return results


# --- summary ----------------------------------------------------------------------


def rate(hits: int, total: int) -> float | None:
    return round(hits / total, 3) if total else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return round(statistics.quantiles(values, n=100, method="inclusive")[int(q) - 1], 2)


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    planned = [r for r in results if r.status not in REJECTED]  # the LLM was asked
    ok = [r for r in results if r.status == "ok"]
    menus = [r for r in ok if r.mode == "menu"]
    per_mode = {}
    for mode in ("shopping", "menu"):
        mode_runs = [r for r in planned if r.mode == mode]
        per_mode[mode] = {
            "runs": len(mode_runs),
            "first_attempt_acceptance": rate(
                sum(r.first_attempt_accepted for r in mode_runs), len(mode_runs)
            ),
            "repair_rate": rate(sum(r.repaired for r in mode_runs), len(mode_runs)),
        }
    costs = [r.cost_usd for r in planned if r.cost_usd is not None]
    latencies = sorted(r.latency_s for r in planned)
    return {
        "runs": len(results),
        "rejected_before_llm": len(results) - len(planned),
        "valid_output_rate": rate(len(ok), len(planned)),
        "per_mode": per_mode,
        "budget_adherence": rate(sum(bool(r.within_budget) for r in ok), len(ok)),
        "diet_violations": sum(len(r.diet_violations) for r in ok),
        "kcal_in_range_rate_menu": rate(sum(bool(r.kcal_in_range) for r in menus), len(menus)),
        "trimmed_runs": sum(r.trimmed_count > 0 for r in ok),
        "scaled_menu_runs": sum(r.scaled for r in menus),
        "latency_p50_s": percentile(latencies, 50),
        "latency_p95_s": percentile(latencies, 95),
        "avg_cost_usd": round(statistics.mean(costs), 5) if costs else None,
        "total_cost_usd": round(sum(costs), 4) if costs else None,
    }


def passed(summary: dict[str, Any]) -> bool:
    """Hard requirements: every plan within budget, no diet violations."""
    adherence = summary["budget_adherence"]
    return (adherence is None or adherence == 1) and summary["diet_violations"] == 0


def pct(value: float | None) -> str:
    return "–" if value is None else f"{value * 100:.0f}%"


def num(value: float | None, digits: int = 2) -> str:
    return "–" if value is None else f"{value:.{digits}f}"


def render_report(results: list[CaseResult], summary: dict[str, Any], meta: dict[str, Any]) -> str:
    shopping, menu = summary["per_mode"]["shopping"], summary["per_mode"]["menu"]
    verdict = "PASS" if passed(summary) else "FAIL"
    lines = [
        "# Offline eval report",
        "",
        f"{meta['timestamp']} · model `{meta['model']}` · catalog `{meta['catalog_version']}` · "
        f"{summary['runs']} runs ({meta['cases']} cases × {meta['repeat']}) · **{verdict}**",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Valid output rate | {pct(summary['valid_output_rate'])} |",
        f"| First-attempt acceptance, shopping / menu | {pct(shopping['first_attempt_acceptance'])}"
        f" / {pct(menu['first_attempt_acceptance'])} |",
        f"| Repair rate, shopping / menu | {pct(shopping['repair_rate'])} / "
        f"{pct(menu['repair_rate'])} |",
        f"| Budget adherence (must be 100%) | {pct(summary['budget_adherence'])} |",
        f"| Diet violations (must be 0) | {summary['diet_violations']} |",
        f"| kcal in range (menu) | {pct(summary['kcal_in_range_rate_menu'])} |",
        f"| Runs trimmed to budget | {summary['trimmed_runs']} |",
        f"| Menus with scaled portions | {summary['scaled_menu_runs']} |",
        f"| Latency p50 / p95 | {num(summary['latency_p50_s'], 1)} s / "
        f"{num(summary['latency_p95_s'], 1)} s |",
        f"| Avg cost per request | ${num(summary['avg_cost_usd'], 4)} |",
        f"| Rejected before the LLM (not enough products, unknown store) | "
        f"{summary['rejected_before_llm']} |",
        "",
        "## Cases",
        "",
        "| Case | Run | Status | Attempts | Scaled | Trimmed | Total / budget (€) "
        "| kcal/person/day | Diet violations | Latency (s) | Tokens in/out | Cost ($) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        kcal = "–"
        if r.kcal_per_person_day is not None:
            kcal = f"{r.kcal_per_person_day:.0f} ({r.kcal_basis})"
            if r.kcal_in_range is False:
                kcal += " ⚠"
        total = f"{num(r.total)} / {r.budget:.2f}"
        lines.append(
            f"| {r.id} | {r.run} | {r.status} | {r.attempts} | {'yes' if r.scaled else ''} | "
            f"{r.trimmed_count or ''} | {total} | {kcal} | "
            f"{', '.join(r.diet_violations) or ''} | {r.latency_s:.1f} | "
            f"{r.prompt_tokens}/{r.completion_tokens} | {num(r.cost_usd, 4)} |"
        )
    lines += [
        "",
        f"Cost uses {PRICES_PER_M_TOKENS} USD per 1M tokens (input, output); see "
        "`evals/run.py`. kcal basis: `menu` = what the portions provide, `purchased` = all "
        "bought packs.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run offline evals with the real OpenAI API.")
    parser.add_argument("--cases", type=int, help="run only the first N cases")
    parser.add_argument("--repeat", type=int, default=1, help="run every case N times")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    try:
        settings = Settings()  # type: ignore[call-arg]  # values come from the environment
    except ValidationError as e:
        print(f"Settings are incomplete (is OPENAI_API_KEY set?):\n{e}", file=sys.stderr)
        return 2
    cases = load_cases()[: args.cases]
    catalog = load_catalog(settings.catalog_path)
    client = create_llm_client(settings)
    results = asyncio.run(run_cases(cases, client, settings, catalog, args.repeat, progress=True))

    summary = summarize(results)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    meta = {
        "timestamp": timestamp,
        "model": settings.openai_model,
        "catalog_version": catalog.catalog.version,
        "cases": len(cases),
        "repeat": args.repeat,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    result_file = RESULTS_DIR / f"{timestamp}.json"
    payload = {"meta": meta, "summary": summary, "results": [asdict(r) for r in results]}
    result_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    REPORT_FILE.write_text(render_report(results, summary, meta), encoding="utf-8")
    print(f"Wrote {result_file} and {REPORT_FILE}")
    print(json.dumps(summary, indent=2))
    return 0 if passed(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
