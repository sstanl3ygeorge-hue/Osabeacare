"""
Phase 3: Extract references from embedded employee fields to separate table.

Also extracts employment_history and employment_gaps.

Idempotent: Uses UNIQUE constraint on (employee_id, reference_number).
Resumable: Tracks last_processed_id.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_date, parse_timestamp, sanitize_string,
    derive_reference_status, derive_gap_status, calculate_gap_months,
    safe_jsonb
)


class Phase3ReferencesMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_3_references", dry_run)
    
    async def migrate(self):
        # Get all employees from MongoDB (need embedded reference data)
        cursor = self.mongo_db.employees.find({})
        employees = await cursor.to_list(length=None)
        self.result.total_records = len(employees)
        
        self.logger.info(f"Extracting references from {len(employees)} employees")
        
        employees.sort(key=lambda x: x.get("id", "") or str(x.get("_id", "")))
        
        for emp in employees:
            mongo_id = emp.get("id") or str(emp.get("_id"))
            
            if self.result.last_processed_id:
                if mongo_id <= self.result.last_processed_id:
                    self.record_skip(mongo_id, "already processed")
                    continue
            
            try:
                # Get postgres employee ID
                new_employee_id = self.map_employee_id(mongo_id)
                if not new_employee_id:
                    self.record_warning(f"No mapping for employee {mongo_id}")
                    continue
                
                # Extract references
                await self._extract_references(emp, new_employee_id)
                
                # Extract employment history
                await self._extract_employment_history(emp, new_employee_id)
                
                # Extract employment gaps
                await self._extract_employment_gaps(emp, new_employee_id)
                
                self.result.migrated_records += 1
                self.result.last_processed_id = mongo_id
                
                if self.result.migrated_records % 10 == 0:
                    await self._save_state()
                    
            except Exception as e:
                self.record_error(mongo_id, str(e))
    
    async def _extract_references(self, emp: dict, employee_id: str):
        """Extract reference_1_* and reference_2_* to employee_references table."""
        
        for ref_num in [1, 2]:
            prefix = f"reference_{ref_num}_"
            
            # Check if reference exists
            referee_name = emp.get(f"{prefix}name")
            if not referee_name:
                continue
            
            # Derive status from multiple fields
            status = derive_reference_status(emp, ref_num)
            
            if not self.dry_run and self.pg_pool:
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO employee_references (
                            id, employee_id, reference_number,
                            referee_name, referee_company, referee_email, referee_phone, referee_job_title,
                            employment_start_date, employment_end_date,
                            from_cv, cv_matched, mismatch_detected, mismatch_notes,
                            override_reason, override_at, override_by,
                            status, request_sent_at, request_token, request_viewed_at,
                            last_reminder_at, resend_count,
                            response_received_at, response_source, response_data,
                            verified, verified_at, verified_by, verified_by_name,
                            rejected, rejected_at, rejected_by, rejection_reason,
                            replacement_requested, replacement_requested_at, replacement_requested_by,
                            replacement_reason, change_history,
                            created_at, updated_at
                        )
                        VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                            $11, $12, $13, $14, $15, $16, $17, $18::reference_status,
                            $19, $20, $21, $22, $23, $24, $25, $26,
                            $27, $28, $29, $30, $31, $32, $33, $34,
                            $35, $36, $37, $38, $39, $40, $41
                        )
                        ON CONFLICT (employee_id, reference_number) DO NOTHING
                    """,
                        generate_uuid(),
                        employee_id,
                        ref_num,
                        sanitize_string(referee_name),
                        sanitize_string(emp.get(f"{prefix}company")),
                        sanitize_string(emp.get(f"{prefix}email")),
                        sanitize_string(emp.get(f"{prefix}phone")),
                        sanitize_string(emp.get(f"{prefix}job_title")),
                        parse_date(emp.get(f"{prefix}start_date")),
                        parse_date(emp.get(f"{prefix}end_date")),
                        emp.get(f"{prefix}from_cv", False),
                        emp.get(f"{prefix}cv_matched"),
                        emp.get(f"{prefix}mismatch_detected", False),
                        sanitize_string(emp.get(f"{prefix}mismatch_notes")),
                        sanitize_string(emp.get(f"{prefix}override_reason")),
                        parse_timestamp(emp.get(f"{prefix}override_at")),
                        self.map_user_id(emp.get(f"{prefix}override_by")),
                        status,
                        parse_timestamp(emp.get(f"{prefix}request_sent_at")),
                        emp.get(f"{prefix}request_token"),
                        parse_timestamp(emp.get(f"{prefix}request_viewed_at")),
                        parse_timestamp(emp.get(f"{prefix}last_reminder_at")),
                        emp.get(f"{prefix}resend_count", 0),
                        parse_timestamp(emp.get(f"{prefix}response_received_at")),
                        sanitize_string(emp.get(f"{prefix}response_source")),
                        safe_jsonb(emp.get(f"{prefix}response_data")),
                        emp.get(f"{prefix}verified", False),
                        parse_timestamp(emp.get(f"{prefix}verified_at")),
                        self.map_user_id(emp.get(f"{prefix}verified_by")),
                        sanitize_string(emp.get(f"{prefix}verified_by_name")),
                        emp.get(f"{prefix}rejected", False),
                        parse_timestamp(emp.get(f"{prefix}rejected_at")),
                        self.map_user_id(emp.get(f"{prefix}rejected_by")),
                        sanitize_string(emp.get(f"{prefix}rejection_reason") or emp.get(f"{prefix}rejected_reason")),
                        emp.get(f"{prefix}replacement_requested", False),
                        parse_timestamp(emp.get(f"{prefix}replacement_requested_at")),
                        self.map_user_id(emp.get(f"{prefix}replacement_requested_by")),
                        sanitize_string(emp.get(f"{prefix}replacement_reason")),
                        safe_jsonb(emp.get(f"{prefix}referee_change_history")),
                        parse_timestamp(emp.get("created_at")),
                        parse_timestamp(emp.get("updated_at"))
                    )
            
            self.logger.debug(f"Extracted reference {ref_num} for employee {employee_id}")
    
    async def _extract_employment_history(self, emp: dict, employee_id: str):
        """Extract employment_history array to separate table."""
        history = emp.get("employment_history", [])
        if not history:
            return
        
        for idx, job in enumerate(history):
            company = job.get("company") or job.get("company_name") or job.get("employer")
            if not company:
                continue
            
            start_date = parse_date(job.get("start_date"))
            if not start_date:
                continue
            
            if not self.dry_run and self.pg_pool:
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO employment_history (
                            id, employee_id, company_name, job_title,
                            start_date, end_date, is_current,
                            source, extraction_confidence, sort_order,
                            created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                        generate_uuid(),
                        employee_id,
                        sanitize_string(company),
                        sanitize_string(job.get("job_title") or job.get("title") or job.get("role")),
                        start_date,
                        parse_date(job.get("end_date")),
                        job.get("is_current", False),
                        job.get("source", "cv_extraction"),
                        float(job.get("confidence", 0)) if job.get("confidence") else None,
                        idx,
                        parse_timestamp(emp.get("created_at")),
                        parse_timestamp(emp.get("updated_at"))
                    )
    
    async def _extract_employment_gaps(self, emp: dict, employee_id: str):
        """Extract employment_gaps from embedded array and separate collection."""
        mongo_emp_id = emp.get("id") or str(emp.get("_id"))
        
        # First check separate collection
        collection_gaps = await self.mongo_db.employment_gaps.find(
            {"employee_id": mongo_emp_id}
        ).to_list(length=None)
        
        # Also check embedded array
        embedded_gaps = emp.get("employment_gaps", [])
        
        # Process collection gaps (authoritative)
        seen_gaps = set()
        
        for gap in collection_gaps:
            start = parse_date(gap.get("start_date"))
            end = parse_date(gap.get("end_date"))
            if not start or not end:
                continue
            
            key = (str(start), str(end))
            if key in seen_gaps:
                continue
            seen_gaps.add(key)
            
            await self._insert_gap(employee_id, gap, start, end)
        
        # Process embedded gaps (if not already processed)
        for gap in embedded_gaps:
            start = parse_date(gap.get("start_date"))
            end = parse_date(gap.get("end_date"))
            if not start or not end:
                continue
            
            key = (str(start), str(end))
            if key in seen_gaps:
                continue
            seen_gaps.add(key)
            
            await self._insert_gap(employee_id, gap, start, end)
    
    async def _insert_gap(self, employee_id: str, gap: dict, start_date, end_date):
        """Insert a single employment gap."""
        status = derive_gap_status(gap)
        gap_months = calculate_gap_months(start_date, end_date)
        
        if not self.dry_run and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO employment_gaps (
                        id, employee_id, gap_start_date, gap_end_date, gap_months,
                        status, explanation, explanation_submitted_at, explanation_submitted_by,
                        verified, verified_at, verified_by, verification_notes,
                        rejected, rejected_at, rejected_by, rejection_reason,
                        created_at, updated_at, mongo_id
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::gap_status, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                """,
                    generate_uuid(),
                    employee_id,
                    start_date,
                    end_date,
                    gap_months,
                    status,
                    sanitize_string(gap.get("explanation")),
                    parse_timestamp(gap.get("explanation_submitted_at")),
                    self.map_user_id(gap.get("explanation_submitted_by")),
                    gap.get("verified", False),
                    parse_timestamp(gap.get("verified_at")),
                    self.map_user_id(gap.get("verified_by")),
                    sanitize_string(gap.get("verification_notes")),
                    gap.get("rejected", False),
                    parse_timestamp(gap.get("rejected_at")),
                    self.map_user_id(gap.get("rejected_by")),
                    sanitize_string(gap.get("rejection_reason")),
                    parse_timestamp(gap.get("created_at")),
                    parse_timestamp(gap.get("updated_at")),
                    gap.get("id")
                )


async def run(dry_run: bool = False):
    """Entry point for phase 3."""
    migration = Phase3ReferencesMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    asyncio.run(run(dry_run=args.dry_run))
