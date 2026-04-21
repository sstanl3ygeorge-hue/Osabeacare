import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "caretrust_production")

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("DB:", DB_NAME)

    total = await db.employee_documents.count_documents({})
    verified = await db.employee_documents.count_documents({"verified": True})
    stamped = await db.employee_documents.count_documents({
        "stamped_file_url": {"$exists": True, "$nin": [None, ""]}
    })
    missing = await db.employee_documents.count_documents({
        "verified": True,
        "$or": [
            {"stamped_file_url": {"$exists": False}},
            {"stamped_file_url": None},
            {"stamped_file_url": ""}
        ]
    })

    print("employee_documents total =", total)
    print("verified=True =", verified)
    print("has stamped_file_url =", stamped)
    print("verified but missing stamped_file_url =", missing)

    sample = await db.employee_documents.find_one(
        {"verified": True},
        {
            "_id": 0,
            "id": 1,
            "employee_id": 1,
            "file_name": 1,
            "file_type": 1,
            "verified": 1,
            "status": 1,
            "review_status": 1,
            "verification_stamp": 1,
            "verification_stamp_by_name": 1,
            "verification_stamp_at": 1,
            "file_url": 1,
            "stamped_file_url": 1,
            "requirement_id": 1,
            "requirement_key": 1
        }
    )

    print("\nSample verified doc:")
    print(json.dumps(sample, default=str, indent=2))

    client.close()

asyncio.run(main())