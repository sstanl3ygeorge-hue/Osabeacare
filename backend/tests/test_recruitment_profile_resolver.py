import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routes import recruitment


class _FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if _matches(doc, query):
                if projection and projection.get("_id") == 0:
                    out = dict(doc)
                    out.pop("_id", None)
                    return out
                return dict(doc)
        return None


class _FakeDB:
    def __init__(self, docs):
        self.employees = _FakeCollection(docs)


def _matches(doc, query):
    if "$or" in query:
        return any(_matches(doc, part) for part in query["$or"])
    for key, value in query.items():
        if key == "$or":
            continue
        if isinstance(value, dict) and "$in" in value:
            if doc.get(key) not in value["$in"]:
                return False
        else:
            if doc.get(key) != value:
                return False
    return True


def test_resolve_person_profile_falls_back_to_linked_record():
    docs = [
        {
            "id": "new-employee-id",
            "first_name": "Test",
            "last_name": "User",
            "status": "onboarding",
            "previous_applicant_id": "old-applicant-id",
        }
    ]
    db = _FakeDB(docs)
    result = asyncio.run(recruitment.resolve_person_profile(db, "old-applicant-id"))
    assert result["person"] is not None
    assert result["person"]["id"] == "new-employee-id"
    assert result["source_type"] == "linked_record"


def test_resolve_person_profile_prefers_direct_id():
    docs = [
        {
            "id": "direct-id",
            "first_name": "A",
            "last_name": "B",
            "status": "new",
            "applicant_reference": "APP-1234",
        }
    ]
    db = _FakeDB(docs)
    result = asyncio.run(recruitment.resolve_person_profile(db, "direct-id"))
    assert result["person"] is not None
    assert result["source_type"] == "id"
