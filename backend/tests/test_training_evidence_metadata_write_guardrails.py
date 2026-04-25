from services.training_evaluator import derive_training_evidence_metadata


def test_certificate_backed_write_metadata_is_explicit():
    metadata = derive_training_evidence_metadata(
        {
            "completion_method": "certificate",
            "certificate_url": "https://example.com/certificate.pdf",
            "source_document_id": "doc-cert-1",
        }
    )

    assert metadata["source_type"] == "certificate"
    assert metadata["evidence_type"] == "external_certificate"
    assert metadata["source_document_id"] == "doc-cert-1"


def test_manual_internal_write_metadata_is_explicit():
    metadata = derive_training_evidence_metadata(
        {
            "completion_method": "manual",
        },
        internal_source_type="internal_course",
    )

    assert metadata == {
        "source_type": "internal_course",
        "evidence_type": "temporary_internal",
    }