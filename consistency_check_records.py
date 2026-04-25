import json
import os

file_path = "exports/production_data_export.json"

total_records = 0
external_evidence_count = 0
internal_evidence_count = 0
missing_source_type_count = 0
missing_evidence_type_count = 0
missing_document_linkage_count = 0
ambiguous_records = 0

if not os.path.exists(file_path):
    print(f"Error: {file_path} not found.")
else:
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from {file_path}")
            data = []

        if isinstance(data, dict):
             # Try to find records if it's a wrapped object
             records = data.get("training_records", [])
        else:
             records = data

        for record in records:
            total_records += 1
            
            source_type = record.get("source_type")
            evidence_type = record.get("evidence_type")
            cert_url = record.get("certificate_url")
            src_doc_id = record.get("source_document_id")
            cert_doc_id = record.get("certificate_document_id")
            doc_id = record.get("document_id")
            evidence_files = record.get("evidence_files", [])

            if not source_type:
                missing_source_type_count += 1
            if not evidence_type:
                missing_evidence_type_count += 1

            # Check document linkage
            has_doc_link = (src_doc_id or cert_doc_id or doc_id or cert_url or (isinstance(evidence_files, list) and len(evidence_files) > 0))
            if not has_doc_link:
                missing_document_linkage_count += 1

            # Heuristics
            is_external = (
                evidence_type == "external_certificate" or 
                source_type == "certificate" or 
                cert_url or 
                src_doc_id or 
                cert_doc_id
            )
            
            internal_source_types = {"internal_course", "questionnaire", "form_submission", "manual", "manual_upload"}
            is_internal = (
                evidence_type == "temporary_internal" or 
                source_type in internal_source_types
            )

            if is_external:
                external_evidence_count += 1
            if is_internal:
                internal_evidence_count += 1
            
            if not is_external and not is_internal:
                ambiguous_records += 1

    print(f"total_records: {total_records}")
    print(f"external_evidence_count: {external_evidence_count}")
    print(f"internal_evidence_count: {internal_evidence_count}")
    print(f"missing_source_type_count: {missing_source_type_count}")
    print(f"missing_evidence_type_count: {missing_evidence_type_count}")
    print(f"missing_document_linkage_count: {missing_document_linkage_count}")
    print(f"ambiguous_records: {ambiguous_records}")
