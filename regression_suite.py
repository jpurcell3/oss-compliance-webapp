#!/usr/bin/env python3
import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

import requests


@dataclass
class RepoResult:
    repo: str
    success: bool
    total_components: int
    compliant_components: int
    unconfirmed_components: int
    non_compliant_components: int
    compliance_pct: float
    findings_total: int
    findings_runtime_compliant: int
    endpoint_by_type: Dict[str, int]
    endpoint_total_configurations: int
    runtime_counts: Dict[str, int]
    checks_passed: bool
    check_failures: List[str]


def post_scan(base_url: str, repo: str) -> Dict:
    r = requests.post(
        f"{base_url}/scan/remote",
        data={"repo_names": repo, "github_instance": "eos2git", "use_enhanced": "true"},
        timeout=1200,
    )
    r.raise_for_status()
    payload = r.json()
    if not payload.get("success"):
        raise RuntimeError(f"Scan failed for {repo}: {payload}")
    return payload.get("report", {})


def _int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def evaluate(repo: str, report: Dict) -> RepoResult:
    summary = report.get("summary", {}) or {}
    comp = summary.get("component_analysis", {}) or {}
    endpoint_summary = summary.get("endpoint_summary", {}) or {}
    scan_summary = report.get("scan_summary", {}) or {}

    total = _int(comp.get("total_components"))
    compliant = _int(comp.get("compliant_components"))
    unconfirmed = _int(comp.get("warning_components"))
    non_compliant = _int(comp.get("non_compliant_components"))
    pct = float(comp.get("component_compliance_percentage") or 0.0)

    findings = report.get("findings", []) or []
    findings_total = len(findings)
    findings_runtime = len([f for f in findings if f.get("status") == "compliant_via_runtime_config"])

    endpoint_by_type = endpoint_summary.get("by_type", {}) or {}
    endpoint_total = _int(endpoint_summary.get("total_configurations"))

    runtime_cfg = report.get("runtime_configurations", {}) or {}
    runtime_counts = {k: len(v or []) for k, v in runtime_cfg.items()}

    failures: List[str] = []

    # Core arithmetic consistency
    if total != compliant + unconfirmed + non_compliant:
        failures.append(
            f"Component math mismatch: total({total}) != compliant({compliant}) + unconfirmed({unconfirmed}) + non_compliant({non_compliant})"
        )

    # Scan summary consistency
    if scan_summary:
        if _int(scan_summary.get("total_items")) != total:
            failures.append(
                f"scan_summary.total_items({_int(scan_summary.get('total_items'))}) != component_analysis.total_components({total})"
            )
        if _int(scan_summary.get("total_findings")) != findings_total:
            failures.append(
                f"scan_summary.total_findings({_int(scan_summary.get('total_findings'))}) != findings.len({findings_total})"
            )

    # Endpoint consistency: by_type should sum to total_components
    # Note: total_configurations is the number of config files, not components
    by_type_sum = sum(_int(v) for v in endpoint_by_type.values())
    if by_type_sum > 0 and by_type_sum != total:
        failures.append(
            f"Endpoint mismatch: by_type sum({by_type_sum}) != total_components({total})"
        )

    # Contradiction guard: runtime-compliant findings but no translated endpoints
    translated = _int(endpoint_by_type.get("translated"))
    direct_public = _int(endpoint_by_type.get("direct_public"))
    if findings_runtime > 0 and direct_public > 0 and translated == 0:
        failures.append(
            "Contradiction: runtime-compliant findings exist while endpoint types remain direct_public only (translated=0)"
        )

    # Contradiction guard: critical issue text must align with component summary
    for issue in (report.get("critical_issues", []) or []):
        if issue.get("issue") == "High Non-Compliance Rate":
            desc = str(issue.get("description", ""))
            # Parse "NN.N% of components are non-compliant"
            try:
                pct_txt = desc.split("%")[0].strip()
                stated_pct = float(pct_txt)
                expected_pct = (non_compliant / total * 100) if total > 0 else 0.0
                if abs(stated_pct - expected_pct) > 0.1:
                    failures.append(
                        f"Critical issue mismatch: stated non-compliance {stated_pct:.1f}% != computed {expected_pct:.1f}%"
                    )
            except Exception:
                failures.append("Critical issue format invalid for High Non-Compliance Rate")

    # Sanity: runtime evidence should correspond to runtime config presence
    if findings_runtime > 0 and sum(runtime_counts.values()) == 0:
        failures.append(
            "Contradiction: findings marked compliant_via_runtime_config but runtime_configurations is empty"
        )

    return RepoResult(
        repo=repo,
        success=True,
        total_components=total,
        compliant_components=compliant,
        unconfirmed_components=unconfirmed,
        non_compliant_components=non_compliant,
        compliance_pct=pct,
        findings_total=findings_total,
        findings_runtime_compliant=findings_runtime,
        endpoint_by_type=endpoint_by_type,
        endpoint_total_configurations=endpoint_total,
        runtime_counts=runtime_counts,
        checks_passed=len(failures) == 0,
        check_failures=failures,
    )


def compare_baseline(results: List[RepoResult], baseline: Dict) -> List[str]:
    failures = []
    by_repo = {r.repo: r for r in results}
    for repo, expected in (baseline or {}).items():
        if repo not in by_repo:
            failures.append(f"Baseline repo missing from run: {repo}")
            continue
        r = by_repo[repo]
        # Stable checks only; avoid brittle exact comparisons
        min_compliant = _int(expected.get("min_compliant_components"), -1)
        max_non_compliant = _int(expected.get("max_non_compliant_components"), 10**9)
        require_runtime_pm = expected.get("require_runtime_package_managers", [])
        if min_compliant >= 0 and r.compliant_components < min_compliant:
            failures.append(
                f"{repo}: compliant_components {r.compliant_components} < baseline min {min_compliant}"
            )
        if r.non_compliant_components > max_non_compliant:
            failures.append(
                f"{repo}: non_compliant_components {r.non_compliant_components} > baseline max {max_non_compliant}"
            )
        for pm in require_runtime_pm:
            if _int(r.runtime_counts.get(pm, 0)) <= 0:
                failures.append(f"{repo}: expected runtime evidence for '{pm}' but found none")
    return failures


def main():
    ap = argparse.ArgumentParser(description="OSS scanner regression suite")
    ap.add_argument("--base-url", default="http://localhost:5001")
    ap.add_argument(
        "--repos",
        default="fusion-stage,dsp-catalog-svc,dap-catalog-workflows",
        help="Comma-separated repository names",
    )
    ap.add_argument("--baseline", help="Path to baseline JSON")
    ap.add_argument("--save-baseline", help="Write suggested baseline JSON to path")
    ap.add_argument("--output", default="regression_results.json", help="Result JSON output file")
    args = ap.parse_args()

    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    print(f"Running regression suite for {len(repos)} repos: {repos}")

    results: List[RepoResult] = []
    for repo in repos:
        print(f"\n=== Scanning {repo} ===")
        try:
            report = post_scan(args.base_url, repo)
            rr = evaluate(repo, report)
            results.append(rr)
            print(
                f"{repo}: components={rr.total_components} compliant={rr.compliant_components} "
                f"unconfirmed={rr.unconfirmed_components} non_compliant={rr.non_compliant_components} "
                f"findings={rr.findings_total} runtime_findings={rr.findings_runtime_compliant}"
            )
            if rr.check_failures:
                print("  FAILURES:")
                for f in rr.check_failures:
                    print(f"   - {f}")
            else:
                print("  Checks: PASS")
        except Exception as e:
            print(f"{repo}: ERROR: {e}")
            results.append(
                RepoResult(
                    repo=repo,
                    success=False,
                    total_components=0,
                    compliant_components=0,
                    unconfirmed_components=0,
                    non_compliant_components=0,
                    compliance_pct=0.0,
                    findings_total=0,
                    findings_runtime_compliant=0,
                    endpoint_by_type={},
                    endpoint_total_configurations=0,
                    runtime_counts={},
                    checks_passed=False,
                    check_failures=[str(e)],
                )
            )

    payload = {"generated_at": int(time.time()), "results": [asdict(r) for r in results]}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote results to {args.output}")

    all_failures = []
    for r in results:
        if not r.success:
            all_failures.append(f"{r.repo}: scan failed")
        all_failures.extend([f"{r.repo}: {x}" for x in r.check_failures])

    if args.baseline:
        with open(args.baseline, "r", encoding="utf-8") as f:
            baseline = json.load(f)
        baseline_failures = compare_baseline(results, baseline)
        all_failures.extend(baseline_failures)
        if baseline_failures:
            print("\nBaseline failures:")
            for bf in baseline_failures:
                print(f" - {bf}")

    if args.save_baseline:
        suggested = {}
        for r in results:
            suggested[r.repo] = {
                "min_compliant_components": r.compliant_components,
                "max_non_compliant_components": r.non_compliant_components,
                "require_runtime_package_managers": [
                    pm for pm, c in r.runtime_counts.items() if _int(c) > 0
                ],
            }
        with open(args.save_baseline, "w", encoding="utf-8") as f:
            json.dump(suggested, f, indent=2)
        print(f"Wrote suggested baseline to {args.save_baseline}")

    if all_failures:
        print("\nRegression suite FAILED")
        for af in all_failures:
            print(f" - {af}")
        sys.exit(1)

    print("\nRegression suite PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
