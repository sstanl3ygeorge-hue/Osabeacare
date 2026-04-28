import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routes import recruitment


def test_calculate_completion_percentage_simple_handles_string_db(monkeypatch):
    monkeypatch.setattr(recruitment, "get_db", lambda: "mongodb://bad-handle")

    warnings = []

    def _warn(msg, *args):
        if args:
            msg = msg % args
        warnings.append(msg)

    monkeypatch.setattr(recruitment.logger, "warning", _warn)

    result = asyncio.run(recruitment.calculate_completion_percentage_simple("emp-xyz"))

    assert result == {
        "overall_percentage": 0,
        "completed_requirements": 0,
        "total_requirements": 0,
        "blockers_count": 0,
        "awaiting_review_count": 0,
    }
    assert any("invalid db handle" in msg for msg in warnings)
