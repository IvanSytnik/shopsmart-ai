"""The offline eval harness, without the network: fake LLM, fixture catalog."""

import asyncio
import logging
from typing import Any, get_args

import httpx
import pytest

from app.schemas.catalog import DietTag
from app.schemas.requests import GenerateRequest
from app.services.catalog import load_catalog
from evals.run import (
    CaseResult,
    EvalCase,
    attempts_cell,
    cost_usd,
    diet_violations,
    load_cases,
    max_tokens_cell,
    passed,
    render_report,
    run_case,
    select_cases,
    summarize,
)
from tests.conftest import BODY, FIXTURE_CATALOG, MILK, FakeOpenAI, make_plan, make_settings
from tests.test_catalog import PRODUCTION_CATALOG
from tests.test_catalog_at import food_count

FIXTURE = load_catalog(FIXTURE_CATALOG)


def case(**request: Any) -> EvalCase:
    return EvalCase(id="c", request=GenerateRequest.model_validate({**BODY, **request}))


def run(fake_llm: FakeOpenAI, eval_case: EvalCase, **settings: Any) -> CaseResult:
    config = make_settings(openai_model="gpt-4o-mini", **settings)
    return asyncio.run(run_case(eval_case, 1, fake_llm.client, config, FIXTURE))


# --- the cases file -------------------------------------------------------------


def test_cases_cover_the_required_scenarios() -> None:
    cases = load_cases()
    requests = [c.request for c in cases]

    assert len(cases) == 20
    assert len({c.id for c in cases}) == 20
    assert {r.mode for r in requests} == {"shopping", "menu"}
    assert {r.days for r in requests if r.mode == "menu"} >= {1, 3, 7}
    assert {r.family_size for r in requests} == {1, 2, 3, 4, 5}
    assert (min(r.budget for r in requests), max(r.budget for r in requests)) == (15, 150)
    assert {d for r in requests for d in r.diets} == set(get_args(DietTag))
    assert {len(r.supermarkets) for r in requests} == {1, 2}
    assert {r.language for r in requests} == {"en", "de", "uk"}
    assert sum(c.id.startswith("tight-") for c in cases) == 2


def test_every_case_reaches_the_planner_with_the_real_catalog() -> None:
    stores = load_catalog(PRODUCTION_CATALOG).stores_by_country()["AT"]
    for c in load_cases():
        assert set(c.request.supermarkets) <= set(stores), c.id
        assert food_count(c.request.supermarkets, c.request.diets) >= 12, c.id


# --- running a case -------------------------------------------------------------


def test_successful_case(fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan())

    result = run(fake_llm, case())

    assert (result.status, result.attempts, result.first_attempt_accepted) == ("ok", 1, True)
    assert (result.repaired, result.used_fallback, result.scaled) == (False, False, False)
    assert (result.total, result.within_budget, result.diet_violations) == (8.85, True, [])
    assert (result.kcal_basis, result.kcal_in_range) == ("purchased", None)
    assert result.cost_per_1000_kcal == 1.52  # 8.85 / 5820 kcal
    assert result.dropped_candidates == 0
    assert (result.prompt_tokens, result.completion_tokens) == (1, 1)  # from the fake usage
    assert result.cost_usd == pytest.approx(0.75e-6)


def test_repaired_menu_case(fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_raw("not json")
    fake_llm.queue_plan(make_plan(days=1))

    result = run(fake_llm, case(mode="menu", days=1), min_kcal_per_person_day=1000)

    assert (result.status, result.attempts, result.repaired) == ("ok", 2, True)
    assert result.first_attempt_accepted is False
    assert (result.prompt_tokens, result.completion_tokens) == (2, 2)
    assert (result.kcal_basis, result.kcal_in_range) == ("menu", True)  # 1062 in 1000-3500


def test_failed_case_still_counts_attempts_and_tokens(fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_raw("not json")
    fake_llm.queue_raw("still not json")

    result = run(fake_llm, case())

    assert (result.status, result.attempts, result.prompt_tokens) == ("generation_failed", 2, 2)
    assert result.total is None


def test_dropped_candidates_are_recorded(fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan({MILK: 2, "at-penny-rice-1kg": 1}))

    result = run(fake_llm, case(family_size=2), tight_budget_per_person_day=7.0)

    assert (result.status, result.dropped_candidates) == ("ok", 3)


def test_rejected_cases_never_call_the_llm(fake_llm: FakeOpenAI) -> None:
    all_diets = case(diets=list(get_args(DietTag)))
    unknown = case(supermarkets=["Billa"])

    assert run(fake_llm, all_diets).status == "not_enough_products"
    assert run(fake_llm, unknown).status == "unknown_store"
    assert fake_llm.calls == 0


def test_diet_violations_name_the_product_and_diet() -> None:
    class Item:
        product_id = MILK

    request = GenerateRequest.model_validate({**BODY, "diets": ["vegan", "vegetarian"]})

    assert diet_violations([Item()], request, FIXTURE) == [f"{MILK}:vegan"]


def test_cost_is_only_known_for_priced_models() -> None:
    assert cost_usd("gpt-4o-mini", 1_000_000, 1_000_000) == pytest.approx(0.75)
    assert cost_usd("some-other-model", 10, 10) is None


# --- summary and report ---------------------------------------------------------


def result(**fields: Any) -> CaseResult:
    defaults: dict[str, Any] = {"id": "c", "run": 1, "mode": "shopping", "status": "ok"}
    return CaseResult(**{**defaults, **fields})


def test_summary_rates_and_verdict() -> None:
    results = [
        result(
            attempts=1, first_attempt_accepted=True, within_budget=True, latency_s=2, cost_usd=0.001
        ),
        result(attempts=2, repaired=True, within_budget=True, latency_s=4, cost_usd=0.003),
        result(
            mode="menu",
            attempts=1,
            first_attempt_accepted=True,
            within_budget=True,
            kcal_in_range=True,
            scaled=True,
            latency_s=6,
            cost_usd=0.002,
        ),
        result(mode="menu", status="generation_failed", attempts=2, repaired=True, latency_s=8),
        result(status="not_enough_products"),
    ]

    summary = summarize(results)

    assert summary["rejected_before_llm"] == 1
    assert summary["valid_output_rate"] == 0.75
    assert summary["per_mode"]["shopping"] == {
        "runs": 2,
        "first_attempt_acceptance": 0.5,
        "repair_rate": 0.5,
    }
    assert summary["per_mode"]["menu"]["repair_rate"] == 0.5
    assert (summary["budget_adherence"], summary["diet_violations"]) == (1, 0)
    assert (summary["kcal_in_range_rate_menu"], summary["scaled_menu_runs"]) == (1, 1)
    assert (summary["latency_p50_s"], summary["avg_cost_usd"]) == (5, 0.002)
    assert passed(summary)

    over_budget = summarize([result(within_budget=False)])
    with_violation = summarize([result(within_budget=True, diet_violations=["x:vegan"])])
    assert not passed(over_budget) and not passed(with_violation)


def test_report_has_the_summary_and_one_row_per_run() -> None:
    results = [
        result(
            id="a",
            attempts=1,
            first_attempt_accepted=True,
            within_budget=True,
            total=9.5,
            budget=10,
            kcal_per_person_day=400,
            kcal_basis="purchased",
            cost_per_1000_kcal=1.2,
        ),
        result(
            id="b",
            mode="menu",
            attempts=2,
            within_budget=True,
            total=20,
            budget=25,
            kcal_per_person_day=1200,
            kcal_basis="menu",
            kcal_in_range=False,
            dropped_candidates=3,
        ),
    ]
    meta = {
        "timestamp": "T",
        "model": "gpt-4o-mini",
        "catalog_version": "v",
        "cases": 2,
        "repeat": 1,
    }

    report = render_report(results, summarize(results), meta)

    assert "**PASS**" in report
    assert "| Budget adherence (must be 100%) | 100% |" in report
    assert "| a | 1 | ok | 1 |  |  |  | 9.50 / 10.00 | 1.20 | 400 (purchased) |" in report
    assert "| b | 1 | ok | 2 | 3 |" in report
    assert "1200 (menu) ⚠" in report


# --- token usage from the LLM service -------------------------------------------


def test_usage_is_logged_at_debug_only(
    client: Any, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.queue_plan(make_plan(), times=2)

    with caplog.at_level(logging.INFO):
        client.post("/generate", json=BODY)
    assert "LLM usage" not in caplog.text

    with caplog.at_level(logging.DEBUG, logger="app.services.llm"):
        client.post("/generate", json=BODY)
    assert "LLM usage: 1 prompt + 1 completion tokens" in caplog.text


# --- per-attempt diagnostics ----------------------------------------------------


def test_each_attempt_records_tokens_finish_reason_and_duration(fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_raw('{"lines": [', finish_reason="length")
    fake_llm.queue_plan(make_plan())

    result = run(fake_llm, case())

    assert result.status == "ok"
    assert [(c["completion_tokens"], c["finish_reason"]) for c in result.calls] == [
        (1, "length"),
        (1, "stop"),
    ]
    assert all(c["duration_s"] >= 0 for c in result.calls)
    assert result.max_completion_tokens == 1


def test_timed_out_attempt_has_unknown_tokens(fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_exception(httpx.ReadTimeout("read timed out"))

    result = run(fake_llm, case())

    assert (result.status, result.error) == ("timeout", "APITimeoutError")
    assert result.calls == [
        {
            "duration_s": result.calls[0]["duration_s"],
            "prompt_tokens": None,
            "completion_tokens": None,
            "finish_reason": "timeout",
        }
    ]
    assert result.max_completion_tokens is None
    assert (max_tokens_cell(result), attempts_cell(result).split(" ")[:2]) == (
        "?",
        ["?", "timeout"],
    )


def test_attempt_cut_by_the_request_deadline_is_marked_cancelled(fake_llm: FakeOpenAI) -> None:
    fake_llm.delay_s = 0.5
    fake_llm.queue_plan(make_plan())

    result = run(fake_llm, case(), request_deadline_s=0.1)

    assert result.status == "timeout"
    assert [c["finish_reason"] for c in result.calls] == ["cancelled"]
    assert result.calls[0]["completion_tokens"] is None


def test_report_marks_unknown_tokens_next_to_the_largest_reply() -> None:
    calls = [
        {
            "duration_s": 12.0,
            "prompt_tokens": 900,
            "completion_tokens": 1850,
            "finish_reason": "stop",
        },
        {
            "duration_s": 40.0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "finish_reason": "timeout",
        },
    ]
    r = result(calls=calls, max_completion_tokens=1850)

    assert max_tokens_cell(r) == "1850 + ?"
    assert attempts_cell(r) == "1850 stop 12.0; ? timeout 40.0"


def test_select_cases() -> None:
    cases = load_cases()
    first, second, third = (c.id for c in cases[:3])

    assert select_cases(cases, None) == cases
    assert [c.id for c in select_cases(cases, "2")] == [first, second]
    assert [c.id for c in select_cases(cases, f"{third}, {first}")] == [third, first]
    with pytest.raises(ValueError, match="unknown case ids: nope"):
        select_cases(cases, f"{first},nope")
