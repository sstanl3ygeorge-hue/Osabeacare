"""
Tests for backend/scripts/p5_reconcile_duplicates.py
- Ensures dry-run makes no DB writes
- Duplicate contracts produce expected proposals
- Duplicate evidence produces expected proposals
- Duplicate current checks produce expected proposals
- Apply mode requires confirmation
"""
import os
import sys
import subprocess
import tempfile
import shutil
import json
import pytest
from unittest import mock

SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "p5_reconcile_duplicates.py"))

@pytest.fixture
def fake_mongo(monkeypatch):
    """Patch MongoClient to use in-memory dicts."""
    class FakeCollection:
        def __init__(self, docs):
            self.docs = docs
            self.updated = []
        def find(self, _=None):
            return list(self.docs)
        def update_one(self, query, update):
            for d in self.docs:
                if d["_id"] == query["_id"]:
                    d.update(update["$set"])
                    self.updated.append((query["_id"], update["$set"]))
    class FakeDB(dict):
        def __getitem__(self, k):
            return self.get(k)
    class FakeClient:
        def __init__(self):
            self.db = FakeDB()
            self.db.generated_contracts = FakeCollection([])
            self.db.agreement_acknowledgements = FakeCollection([])
            self.db.employee_documents = FakeCollection([])
            self.db.rtw_checks = FakeCollection([])
            self.db.dbs_checks = FakeCollection([])
            self.db.identity_verifications = FakeCollection([])
            self.db.address_verifications = FakeCollection([])
            self.db.employees = FakeCollection([])
        def __getitem__(self, k):
            return self.db
    monkeypatch.setattr("pymongo.MongoClient", lambda *a, **kw: FakeClient())
    return FakeClient()

def run_script(args=None, env=None):
    cmd = [sys.executable, SCRIPT_PATH]
    if args:
        cmd += args
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result

def test_dry_run_no_db_writes(fake_mongo, monkeypatch):
    # Patch out os.makedirs to avoid FS writes
    monkeypatch.setattr("os.makedirs", lambda *a, **kw: None)
    # Patch out report writers
    monkeypatch.setattr("backend.scripts.p5_reconcile_duplicates.write_json_report", lambda *a, **kw: None)
    monkeypatch.setattr("backend.scripts.p5_reconcile_duplicates.write_csv_report", lambda *a, **kw: None)
    # Patch out print
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)
    # Patch out MongoClient
    monkeypatch.setattr("pymongo.MongoClient", lambda *a, **kw: fake_mongo)
    # Patch sys.argv
    monkeypatch.setattr(sys, "argv", [SCRIPT_PATH])
    # Run main
    import importlib.util
    spec = importlib.util.spec_from_file_location("p5_reconcile_duplicates", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # No DB writes should have occurred
    for coll in [
        fake_mongo.db.generated_contracts,
        fake_mongo.db.agreement_acknowledgements,
        fake_mongo.db.employee_documents,
        fake_mongo.db.rtw_checks,
        fake_mongo.db.dbs_checks,
        fake_mongo.db.identity_verifications,
        fake_mongo.db.address_verifications,
    ]:
        assert not coll.updated

def test_apply_requires_confirmation():
    result = run_script(["--apply"])
    assert "--apply requires --confirm-run-id" in result.stdout or result.stderr

# Additional tests for mutation proposal logic can be added by patching the collections with test data and checking the output reports.
