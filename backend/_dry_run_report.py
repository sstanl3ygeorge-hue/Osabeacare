"""Dry-run report for application backfill. Temporary script — safe to delete."""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

async def main():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    from application_resolver import backfill_dry_run
    report = await backfill_dry_run(db)

    # ---- SUMMARY ----
    print("=" * 60)
    print("BACKFILL DRY-RUN REPORT")
    print("=" * 60)
    print(f"Total employees scanned:       {report['total_employees']}")
    print(f"Already have form_submission:   {report['already_have_form']}")
    print(f"Skipped (online_structured):    {report['skipped_online']}")
    print(f"Would backfill:                 {report['would_backfill']}")
    print()

    # ---- CANDIDATES BY SOURCE ----
    candidates = report["candidates"]
    from collections import Counter
    source_counts = Counter(c["application_source"] for c in candidates)
    print("CANDIDATES BY SOURCE:")
    for src, cnt in source_counts.most_common():
        print(f"  {src:30s} {cnt}")
    print()

    # ---- SKIPPED BREAKDOWN ----
    skipped = report["skipped"]
    skip_reasons = Counter(s["reason"] for s in skipped)
    print("SKIPPED BREAKDOWN:")
    for reason, cnt in skip_reasons.most_common():
        print(f"  {reason:45s} {cnt}")
    print()

    # ---- COMPLETENESS ----
    complete_count = sum(1 for c in candidates if c.get("application_data_complete"))
    incomplete_count = len(candidates) - complete_count
    print(f"Application data complete:   {complete_count}")
    print(f"Application data incomplete: {incomplete_count}")
    print()

    # ---- INCOMPLETE DETAILS ----
    if incomplete_count > 0:
        print("INCOMPLETE CANDIDATES (missing required sections):")
        for c in candidates:
            if not c.get("application_data_complete"):
                eid = c["employee_id"][:20]
                ename = c["employee_name"][:25]
                esrc = c["application_source"][:20]
                miss = c["missing_sections"]
                print(f"  {eid:22s} {ename:27s} source={esrc:20s} missing={miss}")
    print()

    # ---- MALFORMED CHECK ----
    malformed = []
    for c in candidates:
        issues = []
        if c["sections_present"] == 0:
            issues.append("zero_sections_present")
        if not c.get("employee_name") or c["employee_name"].strip() == "":
            issues.append("no_name")
        if c.get("application_source") in (None, "", "unknown"):
            issues.append("unknown_source")
        if issues:
            malformed.append({**c, "issues": issues})

    if malformed:
        print(f"MALFORMED RECORDS ({len(malformed)}):")
        for m in malformed:
            eid = m["employee_id"][:20]
            ename = m["employee_name"]
            esrc = m["application_source"]
            issues = m["issues"]
            print(f"  {eid:22s} name=\"{ename}\" source={esrc} issues={issues}")
    else:
        print("MALFORMED RECORDS: NONE")

    # ---- PER-CANDIDATE DETAIL (first 15) ----
    print()
    print("FIRST 15 CANDIDATES (detail):")
    for c in candidates[:15]:
        flag = "COMPLETE" if c.get("application_data_complete") else "INCOMPLETE"
        code = c.get("employee_code") or c.get("applicant_reference") or "no-code"
        print(f"  {c['employee_id'][:16]:18s} {code:14s} {c['employee_name'][:22]:24s} {c['application_source']:20s} {c['sections_present']}/{c['sections_total']} sections  {flag}")

    client.close()

asyncio.run(main())
