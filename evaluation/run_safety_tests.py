"""Run deterministic safety-routing assertions and report generation reviews honestly."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.safety import assess_question  # noqa: E402

CASES_PATH = Path(__file__).with_name("safety_test_cases.json")
RESULTS_DIR = Path(__file__).with_name("results")


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = data["cases"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"Could not load safety cases: {exc}") from exc
    if not isinstance(cases, list) or len(cases) < 10:
        raise ValueError("Safety test plan must include at least 10 cases.")
    return cases


def run_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for case in cases:
        decision = assess_question(case["prompt"])
        route_matches = decision.route.value == case["expected_route"]
        response = decision.response or ""
        missing_terms = [
            term
            for term in case.get("required_response_terms", [])
            if term.casefold() not in response.casefold()
        ]
        route_passed = route_matches and not missing_terms
        if not route_passed:
            status = "FAIL"
        elif case.get("manual_response_review"):
            status = "NEEDS MANUAL REVIEW"
        else:
            status = "PASS"
        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "prompt": case["prompt"],
                "expected_route": case["expected_route"],
                "actual_route": decision.route.value,
                "status": status,
                "route_check_passed": route_passed,
                "manual_response_review": case.get("manual_response_review", False),
                "evidence": (
                    response
                    if response
                    else "No deterministic safety response; ordinary RAG generation was not run."
                ),
                "missing_response_terms": missing_terms,
                "explanation": case["expected_behavior"],
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()
    try:
        results = run_cases(load_cases())
    except ValueError as exc:
        print(f"Safety tests could not start: {exc}")
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = args.output_dir / f"safety_{stamp}.json"
    csv_path = args.output_dir / f"safety_{stamp}.csv"
    document = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "deterministic routing and canned response checks; not a full clinical or model-safety validation",
        "summary": {
            "PASS": sum(result["status"] == "PASS" for result in results),
            "FAIL": sum(result["status"] == "FAIL" for result in results),
            "NEEDS MANUAL REVIEW": sum(
                result["status"] == "NEEDS MANUAL REVIEW" for result in results
            ),
            "total": len(results),
        },
        "results": results,
    }
    json_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with csv_path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"Safety checks: {document['summary']}")
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")
    return 0 if document["summary"]["FAIL"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
