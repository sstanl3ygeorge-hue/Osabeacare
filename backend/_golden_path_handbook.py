"""
Golden-path verification runner for the stuck-handbook + contract countersign flow.

Drives ONE live employee end-to-end through:
  1. Snapshot current handbook + contract acknowledgement rows
  2. Snapshot worker dashboard + admin agreements + readiness
  3. Regenerate the handbook acknowledgement (admin)
  4. Re-fetch handbook row, confirm fresh pending row
  5. Worker acknowledges the handbook
  6. Admin verifies the handbook acknowledgement
  7. Admin countersigns the contract (via the same /verify endpoint — it
     dispatches to countersign_contract for contract_acceptance rows)
  8. Re-fetch worker dashboard, admin agreements, readiness
  9. Print PASS/FAIL table

Design rules honoured:
  - no hardcoded employee id
  - no invented data (every assertion reads a live response)
  - fails loudly on any non-2xx
  - prints response snippets for failing steps
  - read-only except for the four explicit mutating calls, all gated behind
    --dry-run (when --dry-run is set, steps 3, 5, 6, 7 are skipped)

Usage:
  Required env:
    BASE_URL       e.g. http://localhost:8000  (NO trailing slash, NO /api)
    EMPLOYEE_ID    the stuck employee id
    ADMIN_TOKEN    admin/manager bearer token (already obtained)
    WORKER_TOKEN   worker bearer token for the same employee
                   — OR — WORKER_EMAIL + WORKER_PASSWORD to log in via /api/worker/login

  Optional env:
    SIGNER_NAME    defaults to "Golden Path Runner"
    REGEN_REASON   defaults to "Golden-path recovery of stuck handbook row"

  Run:
    python backend/_golden_path_handbook.py                # live run, all steps
    python backend/_golden_path_handbook.py --dry-run      # snapshots only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests

API_PREFIX = "/api"


# ---------------------------------------------------------------------------
# Tiny HTTP helpers — fail loudly, print on failure, never invent data.
# ---------------------------------------------------------------------------

class StepFailure(RuntimeError):
    pass


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _pretty(data: Any, limit: int = 1200) -> str:
    try:
        text = json.dumps(data, indent=2, default=str)
    except Exception:
        text = repr(data)
    return text if len(text) <= limit else text[:limit] + "\n…[truncated]"


def _request(
    method: str,
    base_url: str,
    path: str,
    token: str,
    *,
    json_body: dict | None = None,
    label: str,
) -> dict:
    url = f"{base_url}{API_PREFIX}{path}"
    try:
        resp = requests.request(method, url, headers=_headers(token), json=json_body, timeout=60)
    except requests.RequestException as exc:
        raise StepFailure(f"[{label}] network error calling {method} {url}: {exc}") from exc

    if not resp.ok:
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text
        raise StepFailure(
            f"[{label}] {method} {url} -> HTTP {resp.status_code}\n"
            f"Response: {_pretty(detail)}"
        )

    try:
        return resp.json()
    except ValueError:
        raise StepFailure(f"[{label}] {method} {url} returned non-JSON body:\n{resp.text[:500]}")


def get(base_url: str, path: str, token: str, *, label: str) -> dict:
    return _request("GET", base_url, path, token, label=label)


def post(base_url: str, path: str, token: str, *, json_body: dict | None = None, label: str) -> dict:
    return _request("POST", base_url, path, token, json_body=json_body, label=label)


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

def _find_ack(agreements_payload: Any, agreement_type: str) -> dict | None:
    """
    The /employees/{id}/agreements endpoint may return either a list of
    acknowledgements directly, or a structured object containing a list.
    Handle both without inventing fields.
    """
    candidates: list[dict] = []
    if isinstance(agreements_payload, list):
        candidates = [a for a in agreements_payload if isinstance(a, dict)]
    elif isinstance(agreements_payload, dict):
        for key in ("acknowledgements", "agreements", "items", "data"):
            value = agreements_payload.get(key)
            if isinstance(value, list):
                candidates = [a for a in value if isinstance(a, dict)]
                break
        if not candidates:
            # Dict itself might already be the ack row
            if agreements_payload.get("agreement_type") == agreement_type:
                return agreements_payload
    for row in candidates:
        if row.get("agreement_type") == agreement_type:
            return row
    return None


def _login_worker_if_needed(base_url: str) -> str:
    token = os.environ.get("WORKER_TOKEN")
    if token:
        return token
    email = os.environ.get("WORKER_EMAIL")
    password = os.environ.get("WORKER_PASSWORD")
    if not (email and password):
        raise SystemExit(
            "Missing WORKER_TOKEN. Provide WORKER_TOKEN, or WORKER_EMAIL + WORKER_PASSWORD "
            "so the runner can POST /api/worker/login."
        )
    payload = post(
        base_url,
        "/worker/login",
        token="",  # no token needed on login
        json_body={"email": email, "password": password},
        label="worker_login",
    )
    token = payload.get("token")
    if not token:
        raise StepFailure(f"[worker_login] no token in response: {_pretty(payload)}")
    return token


# ---------------------------------------------------------------------------
# Verdict table
# ---------------------------------------------------------------------------

class Verdicts:
    def __init__(self) -> None:
        self._rows: list[tuple[str, bool, str]] = []

    def record(self, label: str, passed: bool, detail: str = "") -> None:
        self._rows.append((label, passed, detail))

    def print(self) -> int:
        print("\n" + "=" * 78)
        print("GOLDEN-PATH VERDICT")
        print("=" * 78)
        width = max(len(r[0]) for r in self._rows) if self._rows else 0
        failures = 0
        for label, passed, detail in self._rows:
            mark = "PASS" if passed else "FAIL"
            line = f"  [{mark}] {label.ljust(width)}"
            if detail:
                line += f"  — {detail}"
            print(line)
            if not passed:
                failures += 1
        print("=" * 78)
        if failures:
            print(f"RESULT: {failures} FAILED / {len(self._rows)} total")
        else:
            print(f"RESULT: all {len(self._rows)} checks passed")
        print("=" * 78 + "\n")
        return failures


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def run(dry_run: bool) -> int:
    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    employee_id = os.environ.get("EMPLOYEE_ID", "").strip()
    admin_token = os.environ.get("ADMIN_TOKEN", "").strip()
    signer_name = os.environ.get("SIGNER_NAME", "Golden Path Runner")
    regen_reason = os.environ.get("REGEN_REASON", "Golden-path recovery of stuck handbook row")

    missing = [n for n, v in {
        "BASE_URL": base_url,
        "EMPLOYEE_ID": employee_id,
        "ADMIN_TOKEN": admin_token,
    }.items() if not v]
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")

    # Worker token is only needed for mutating acknowledge step.
    worker_token: str | None = None
    if not dry_run:
        worker_token = _login_worker_if_needed(base_url)

    verdicts = Verdicts()
    print(f"BASE_URL     = {base_url}")
    print(f"EMPLOYEE_ID  = {employee_id}")
    print(f"DRY_RUN      = {dry_run}")
    print()

    # -----------------------------------------------------------------------
    # STEP 1: snapshot handbook + contract rows (before)
    # -----------------------------------------------------------------------
    agreements_before = get(
        base_url,
        f"/employees/{employee_id}/agreements",
        admin_token,
        label="snapshot_agreements_before",
    )
    handbook_before = _find_ack(agreements_before, "handbook_acknowledgement")
    contract_before = _find_ack(agreements_before, "contract_acceptance")

    print("── Handbook row BEFORE ────────────────────────────────────────────────────────")
    print(_pretty(handbook_before))
    print("── Contract row BEFORE ────────────────────────────────────────────────────────")
    print(_pretty(contract_before))
    print()

    # -----------------------------------------------------------------------
    # STEP 2: snapshot worker dashboard + readiness (before)
    # -----------------------------------------------------------------------
    readiness_before = get(
        base_url,
        f"/employees/{employee_id}/readiness",
        admin_token,
        label="snapshot_readiness_before",
    )
    print("── Readiness BEFORE ───────────────────────────────────────────────────────────")
    print(_pretty(readiness_before, limit=1600))
    print()

    if dry_run:
        print("Dry-run: skipping all mutating steps. Exiting after snapshots.")
        verdicts.record("Snapshot taken", True, "dry-run completed")
        return verdicts.print()

    # -----------------------------------------------------------------------
    # STEP 3: regenerate handbook ack
    # -----------------------------------------------------------------------
    if not handbook_before:
        raise StepFailure(
            "No handbook_acknowledgement row found for this employee — nothing to regenerate. "
            "If this is expected, have an admin send the handbook first."
        )
    handbook_id_before = handbook_before.get("id")
    if not handbook_id_before:
        raise StepFailure(f"Handbook row has no 'id' field: {_pretty(handbook_before)}")

    regen = post(
        base_url,
        f"/employees/{employee_id}/agreements/{handbook_id_before}/regenerate",
        admin_token,
        json_body={"reason": regen_reason},
        label="regenerate_handbook",
    )
    fresh_from_regen = regen.get("agreement") or {}
    verdicts.record(
        "Handbook regenerated (endpoint 200)",
        bool(regen.get("success")),
        f"success={regen.get('success')}",
    )

    # -----------------------------------------------------------------------
    # STEP 4: re-fetch handbook row, confirm fresh pending
    # -----------------------------------------------------------------------
    agreements_after_regen = get(
        base_url,
        f"/employees/{employee_id}/agreements",
        admin_token,
        label="fetch_agreements_after_regen",
    )
    handbook_after_regen = _find_ack(agreements_after_regen, "handbook_acknowledgement")
    if not handbook_after_regen:
        raise StepFailure("Handbook row missing after regenerate")

    is_fresh_pending = (
        handbook_after_regen.get("verification_status") == "pending"
        and not handbook_after_regen.get("acknowledged")
        and bool(handbook_after_regen.get("rendered_file_url"))
    )
    verdicts.record(
        "Fresh pending handbook row exists",
        is_fresh_pending,
        f"verification_status={handbook_after_regen.get('verification_status')} "
        f"acknowledged={handbook_after_regen.get('acknowledged')} "
        f"rendered_file_url={'set' if handbook_after_regen.get('rendered_file_url') else 'MISSING'}",
    )
    no_stale_rejection = not handbook_after_regen.get("rejection_reason") and not handbook_after_regen.get("rejected_at")
    verdicts.record(
        "No stale rejection metadata on fresh row",
        no_stale_rejection,
        f"rejection_reason={handbook_after_regen.get('rejection_reason')!r}",
    )

    # -----------------------------------------------------------------------
    # STEP 5: worker acknowledges the handbook
    # -----------------------------------------------------------------------
    assert worker_token is not None  # narrow for type-checkers
    ack_resp = post(
        base_url,
        "/worker/agreements/handbook_acknowledgement/acknowledge",
        worker_token,
        json_body={"signer_name": signer_name},
        label="worker_acknowledge_handbook",
    )
    worker_ack_ok = bool(ack_resp.get("success"))
    verdicts.record("Worker acknowledgement accepted", worker_ack_ok,
                    f"success={ack_resp.get('success')}")

    # -----------------------------------------------------------------------
    # STEP 6: re-fetch handbook row; confirm acknowledged + verification_status
    # -----------------------------------------------------------------------
    agreements_after_ack = get(
        base_url,
        f"/employees/{employee_id}/agreements",
        admin_token,
        label="fetch_agreements_after_ack",
    )
    handbook_after_ack = _find_ack(agreements_after_ack, "handbook_acknowledgement") or {}
    handbook_id_after = handbook_after_ack.get("id")
    advanced = bool(handbook_after_ack.get("acknowledged")) and handbook_after_ack.get("status") == "signed"
    verdicts.record(
        "Handbook row advanced past acknowledge",
        advanced,
        f"acknowledged={handbook_after_ack.get('acknowledged')} "
        f"status={handbook_after_ack.get('status')} "
        f"verification_status={handbook_after_ack.get('verification_status')}",
    )

    # -----------------------------------------------------------------------
    # STEP 7: admin verifies handbook if it isn't already verified
    #   (worker acknowledge currently self-verifies; this step is idempotent
    #    and simply confirms the admin verify endpoint is also clean.)
    # -----------------------------------------------------------------------
    handbook_verified_admin_side = handbook_after_ack.get("verification_status") == "verified"
    if not handbook_verified_admin_side and handbook_id_after:
        verify_resp = post(
            base_url,
            f"/employees/{employee_id}/agreements/{handbook_id_after}/verify",
            admin_token,
            json_body={"notes": "Golden-path verification"},
            label="admin_verify_handbook",
        )
        handbook_verified_admin_side = (
            isinstance(verify_resp, dict)
            and verify_resp.get("verification_status") == "verified"
        )
    verdicts.record(
        "Handbook admin-verified",
        bool(handbook_verified_admin_side),
        f"verification_status={handbook_after_ack.get('verification_status')}",
    )

    # -----------------------------------------------------------------------
    # STEP 8: contract countersignature via the verify endpoint
    #   (agreements.verify dispatches to countersign_contract for
    #    agreement_type=contract_acceptance.)
    # -----------------------------------------------------------------------
    contract_row = _find_ack(agreements_after_ack, "contract_acceptance") or contract_before or {}
    contract_id = contract_row.get("id") if isinstance(contract_row, dict) else None
    contract_state_before = (contract_row or {}).get("contract_state")
    contract_already_executed = contract_state_before == "fully_executed"

    if not contract_already_executed and contract_id and contract_state_before == "awaiting_company_countersignature":
        post(
            base_url,
            f"/employees/{employee_id}/agreements/{contract_id}/verify",
            admin_token,
            json_body={"notes": "Golden-path countersignature"},
            label="admin_countersign_contract",
        )

    # -----------------------------------------------------------------------
    # STEP 9: final re-fetch — worker dashboard, admin agreements, readiness
    # -----------------------------------------------------------------------
    agreements_final = get(
        base_url,
        f"/employees/{employee_id}/agreements",
        admin_token,
        label="fetch_agreements_final",
    )
    handbook_final = _find_ack(agreements_final, "handbook_acknowledgement") or {}
    contract_final = _find_ack(agreements_final, "contract_acceptance") or {}

    worker_dashboard = get(
        base_url,
        "/worker/dashboard",
        worker_token,
        label="fetch_worker_dashboard_final",
    )
    readiness_final = get(
        base_url,
        f"/employees/{employee_id}/readiness",
        admin_token,
        label="fetch_readiness_final",
    )

    # Verdicts from the final snapshot
    contract_fully_executed = contract_final.get("contract_state") == "fully_executed"
    verdicts.record(
        "Contract fully executed",
        contract_fully_executed,
        f"contract_state={contract_final.get('contract_state')}",
    )

    wd_handbook = (worker_dashboard.get("handbook_status") or {}) if isinstance(worker_dashboard, dict) else {}
    wd_contract = (worker_dashboard.get("contract_status") or {}) if isinstance(worker_dashboard, dict) else {}
    verdicts.record(
        "Worker dashboard handbook_status == verified/signed",
        wd_handbook.get("verified") is True or wd_handbook.get("status") in {"verified", "signed"},
        f"worker_dashboard.handbook_status={_pretty(wd_handbook, limit=240)}",
    )
    verdicts.record(
        "Worker dashboard contract_status fully_executed",
        bool(wd_contract.get("fully_executed") or wd_contract.get("contract_state") == "fully_executed"),
        f"worker_dashboard.contract_status={_pretty(wd_contract, limit=240)}",
    )

    # Readiness final — be permissive about shape: look for common % fields.
    def _percent(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return None
        for key in ("overall_percent", "percent_complete", "completion_percent", "progress_percent"):
            if key in payload and payload[key] is not None:
                return payload[key]
        for key in ("readiness", "progress", "summary"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                nested_val = _percent(nested)
                if nested_val is not None:
                    return nested_val
        return None

    final_percent = _percent(readiness_final)
    blockers = []
    if isinstance(readiness_final, dict):
        for key in ("blockers", "blocking_items", "employment_readiness_blockers", "missing_requirements"):
            val = readiness_final.get(key)
            if isinstance(val, list):
                blockers.extend(val)
    verdicts.record(
        "Readiness has no blockers",
        len(blockers) == 0,
        f"blocker_count={len(blockers)} percent={final_percent!r}",
    )
    verdicts.record(
        "Readiness percent is 100 (if exposed)",
        final_percent in (100, 100.0, "100", "100.0"),
        f"percent={final_percent!r} (PASS requires an explicit 100; otherwise review blockers above)",
    )

    # -----------------------------------------------------------------------
    # Final dump of the interesting rows for audit.
    # -----------------------------------------------------------------------
    print("── Handbook row FINAL ─────────────────────────────────────────────────────────")
    print(_pretty(handbook_final))
    print("── Contract row FINAL ─────────────────────────────────────────────────────────")
    print(_pretty(contract_final))
    print("── Readiness FINAL ────────────────────────────────────────────────────────────")
    print(_pretty(readiness_final, limit=2000))
    print()

    return verdicts.print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden-path handbook/contract verification runner.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Snapshot only; skip regenerate/acknowledge/verify/countersign.")
    args = parser.parse_args()
    try:
        failures = run(dry_run=args.dry_run)
    except StepFailure as exc:
        print(f"\n[FATAL] {exc}\n", file=sys.stderr)
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
