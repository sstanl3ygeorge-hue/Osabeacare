"""Quick test: simulate the worker dashboard endpoint to find crash."""
import asyncio
import os
import traceback

from dotenv import load_dotenv
load_dotenv()

from motor.motor_asyncio import AsyncIOMotorClient


async def test():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # Find a worker account to test with
    worker = await db.worker_accounts.find_one({}, {"_id": 0})
    if not worker:
        print("No worker accounts found. Trying employees directly...")
        emp = await db.employees.find_one({}, {"_id": 0, "id": 1, "first_name": 1})
        if not emp:
            print("No employees found either")
            client.close()
            return
        employee_id = emp["id"]
        print(f"Using employee: {emp.get('first_name')} id={employee_id}")
    else:
        employee_id = worker.get("employee_id")
        print(f"Worker account found, employee_id={employee_id}")

    if not employee_id:
        print("No employee_id on worker account")
        client.close()
        return

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        print(f"Employee {employee_id} not found in DB")
        client.close()
        return

    print(f"Employee: {employee.get('first_name')} {employee.get('last_name')}, status={employee.get('status')}")

    # Step 1: Test unified_compliance_engine
    print("\n--- Step 1: get_unified_employee_status ---")
    try:
        from unified_compliance_engine import get_unified_employee_status
        unified_status = await get_unified_employee_status(
            employee_id, db, user_role="worker", include_details=True
        )
        print("OK. progress:", unified_status.get("progress"))
        cats = unified_status.get("categories", {})
        for cat_name, cat_data in cats.items():
            items = cat_data.get("items", [])
            print(f"  {cat_name}: {len(items)} items")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()

    # Step 2: Test induction status
    print("\n--- Step 2: get_employee_induction_status ---")
    try:
        from induction_definitions import get_employee_induction_status
        induction = await get_employee_induction_status(db, employee_id)
        print(f"OK. total={induction['total']}, completed={induction['completed']}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()

    # Step 3: Test DB queries the dashboard does
    print("\n--- Step 3: DB queries ---")
    try:
        docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "status": {"$nin": ["deleted", "superseded", "rejected"]},
        }).to_list(length=200)
        print(f"Documents: {len(docs)}")
    except Exception as e:
        print(f"Documents query FAILED: {e}")

    try:
        trainings = await db.training_records.find({
            "employee_id": employee_id,
            "record_status": {"$nin": ["superseded", "deleted"]}
        }).to_list(length=100)
        print(f"Training records: {len(trainings)}")
    except Exception as e:
        print(f"Training query FAILED: {e}")

    try:
        ref_doc = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
        print(f"References doc: {'found' if ref_doc else 'none'}")
    except Exception as e:
        print(f"References query FAILED: {e}")

    try:
        comps = await db.competency_assessments.find({"employee_id": employee_id}).to_list(20)
        print(f"Competency assessments: {len(comps)}")
    except Exception as e:
        print(f"Competency query FAILED: {e}")

    try:
        spots = await db.spot_checks.find({"employee_id": employee_id}).to_list(20)
        print(f"Spot checks: {len(spots)}")
    except Exception as e:
        print(f"Spot checks query FAILED: {e}")

    # Step 4: Test the WORKER_FORM_DEFINITIONS import
    print("\n--- Step 4: Lazy imports ---")
    try:
        from server import WORKER_FORM_DEFINITIONS
        print(f"WORKER_FORM_DEFINITIONS: {len(WORKER_FORM_DEFINITIONS)} forms")
    except Exception as e:
        print(f"WORKER_FORM_DEFINITIONS FAILED: {e}")

    try:
        from server import EXCLUDED_DOC_STATUSES
        print(f"EXCLUDED_DOC_STATUSES: {EXCLUDED_DOC_STATUSES}")
    except Exception as e:
        print(f"EXCLUDED_DOC_STATUSES FAILED: {e}")

    try:
        from unified_compliance_engine import DOC_REQUIREMENT_ALIASES, DOC_REQUIREMENT_EXCLUSIONS
        print(f"DOC_REQUIREMENT_ALIASES: {len(DOC_REQUIREMENT_ALIASES)} entries")
        print(f"DOC_REQUIREMENT_EXCLUSIONS: {len(DOC_REQUIREMENT_EXCLUSIONS)} entries")
    except Exception as e:
        print(f"DOC_REQUIREMENT_ALIASES FAILED: {e}")

    # Step 5: Test the full endpoint via httpx if possible
    print("\n--- Step 5: Full endpoint test via TestClient ---")
    try:
        from httpx import AsyncClient, ASGITransport
        from server import app

        # Create a fake JWT for the worker
        import jwt as pyjwt
        token_payload = {
            "employee_id": employee_id,
            "type": "worker",
            "exp": 9999999999
        }
        from routes.dependencies import JWT_SECRET
        token = pyjwt.encode(token_payload, JWT_SECRET, algorithm="HS256")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                "/api/worker/dashboard",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Response: {resp.text[:2000]}")
            else:
                data = resp.json()
                print(f"OK. Keys: {list(data.keys())}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()

    client.close()
    print("\nDone.")


asyncio.run(test())
