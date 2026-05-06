import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


def test_matrix_lookup_maps_cstf_health_safety_to_health_safety_column_id():
    record = {
        "requirement_id": None,
        "mapped_training_code": None,
        "training_name": "CSTF Health, Safety and Welfare",
    }

    keys = server._training_matrix_lookup_keys(record)

    # Column ID used by MANDATORY_ITEMS / visible training matrix.
    assert "health_safety" in keys


def test_matrix_lookup_maps_adult_bls_canonical_to_bls_column_id():
    record = {
        "requirement_id": None,
        "mapped_training_code": "cstf_resuscitation_adults",
        "training_name": "CSTF Resuscitation Adults",
    }

    keys = server._training_matrix_lookup_keys(record)

    # Matrix column ID for BLS in this product is 'bls'.
    assert "bls" in keys
