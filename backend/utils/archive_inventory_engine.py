"""
Archive Inventory & Duplicate Detection Engine
Maps Osabea Healthcare Solutions Ltd archive to Digital Care Agency system
Detects duplicates, near-duplicates, gaps, and generates import manifest
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import json


@dataclass
class TemplateMetadata:
    """Archive template metadata"""
    filename: str
    folder_path: str
    file_size: int
    file_hash: str
    extension: str
    detected_type: str
    destination_section: str
    confidence: float
    priority: str
    notes: Optional[str] = None


class ArchiveInventoryEngine:
    """Inventory + duplicate detection for archive"""
    
    def __init__(self, archive_root: str):
        self.archive_root = Path(archive_root)
        self.templates: List[TemplateMetadata] = []
        self.hash_map: Dict[str, List[TemplateMetadata]] = {}
        self.filename_map: Dict[str, List[TemplateMetadata]] = {}
        
    def scan_archive(self) -> None:
        """Scan archive and build inventory"""
        for root, dirs, files in os.walk(self.archive_root):
            for file in files:
                if not self._is_template_file(file):
                    continue
                
                filepath = Path(root) / file
                folder_relative = str(Path(root).relative_to(self.archive_root))
                
                metadata = self._extract_metadata(filepath, folder_relative)
                self.templates.append(metadata)
                
                # Index by hash and filename for duplicate detection
                if metadata.file_hash not in self.hash_map:
                    self.hash_map[metadata.file_hash] = []
                self.hash_map[metadata.file_hash].append(metadata)
                
                if metadata.filename not in self.filename_map:
                    self.filename_map[metadata.filename] = []
                self.filename_map[metadata.filename].append(metadata)
    
    def _is_template_file(self, filename: str) -> bool:
        """Check if file is a template (docx, pdf, xlsx, doc)"""
        extensions = {'.docx', '.pdf', '.xlsx', '.xls', '.doc'}
        return any(filename.endswith(ext) for ext in extensions)
    
    def _extract_metadata(self, filepath: Path, folder_path: str) -> TemplateMetadata:
        """Extract template metadata"""
        filename = filepath.name
        file_size = filepath.stat().st_size
        file_hash = self._compute_hash(filepath)
        extension = filepath.suffix.lower()
        detected_type = self._detect_template_type(filename, folder_path)
        destination_section = self._map_destination(detected_type, folder_path, filename)
        confidence = self._compute_confidence(detected_type, filename)
        priority = self._compute_priority(detected_type, destination_section)
        
        return TemplateMetadata(
            filename=filename,
            folder_path=folder_path,
            file_size=file_size,
            file_hash=file_hash,
            extension=extension,
            detected_type=detected_type,
            destination_section=destination_section,
            confidence=confidence,
            priority=priority,
        )
    
    def _compute_hash(self, filepath: Path, chunk_size: int = 8192) -> str:
        """Compute SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _detect_template_type(self, filename: str, folder_path: str) -> str:
        """Detect template type from filename and folder"""
        filename_lower = filename.lower()
        folder_lower = folder_path.lower()
        
        # Folder-based detection (highest priority)
        if "care plan" in folder_lower:
            if "assessment" in filename_lower:
                return "care_plan_assessment"
            if "review" in filename_lower:
                return "care_plan_review"
            if "monitoring" in filename_lower or "chart" in filename_lower:
                return "monitoring_chart"
            return "care_plan_template"
        
        if "recruitment" in folder_lower:
            if "application" in filename_lower:
                return "recruitment_application"
            if "interview" in filename_lower:
                return "recruitment_interview"
            if "offer" in filename_lower:
                return "recruitment_offer"
            return "recruitment_template"
        
        if "disciplinary" in folder_lower:
            return "disciplinary_template"
        
        if "health" in folder_lower and "safety" in folder_lower:
            if "medication" in filename_lower or "mar" in filename_lower:
                return "medication_template"
            if "body map" in filename_lower:
                return "body_map_template"
            if "incident" in filename_lower or "accident" in filename_lower:
                return "incident_template"
            if "risk" in filename_lower:
                return "risk_assessment_template"
            if "moving" in filename_lower or "handling" in filename_lower:
                return "moving_handling_template"
            return "health_safety_template"
        
        if "audit" in folder_lower:
            if "competency" in filename_lower:
                return "competency_template"
            return "audit_template"
        
        if "safeguarding" in folder_lower:
            if "whistleblowing" in filename_lower:
                return "whistleblowing_template"
            return "safeguarding_template"
        
        if "human resource" in folder_lower:
            if "absence" in filename_lower:
                return "absence_template"
            if "performance" in filename_lower or "review" in filename_lower:
                return "performance_template"
            if "induction" in filename_lower:
                return "onboarding_template"
            return "hr_template"
        
        if "operations" in folder_lower:
            if "rota" in filename_lower:
                return "rota_template"
            if "complaint" in filename_lower:
                return "complaint_template"
            return "operations_template"
        
        if "quality" in folder_lower:
            return "quality_template"
        
        if "covid" in folder_lower:
            return "covid_template"
        
        if "winter" in folder_lower:
            return "seasonal_template"
        
        if "policy" in filename_lower:
            return "policy_template"
        
        return "unclassified"
    
    def _map_destination(self, detected_type: str, folder_path: str, filename: str) -> str:
        """Map detected type + folder to destination section"""
        type_to_destination = {
            # Service-user care plans
            "care_plan_assessment": "su_assessments",
            "care_plan_review": "su_reviews",
            "care_plan_template": "su_care_plans",
            "monitoring_chart": "su_monitoring_charts",
            
            # Operational
            "medication_template": "medication_operational",
            "body_map_template": "body_maps",
            "incident_template": "incidents",
            "risk_assessment_template": "risk_assessments_operational",
            "moving_handling_template": "moving_handling",
            "health_safety_template": "equipment_safety",
            
            # HR
            "recruitment_template": "recruitment",
            "recruitment_application": "recruitment",
            "recruitment_interview": "recruitment",
            "recruitment_offer": "recruitment",
            "disciplinary_template": "disciplinary_hr",
            "absence_template": "absence_management",
            "performance_template": "performance_management",
            "onboarding_template": "onboarding",
            "hr_template": "compliance_hr",
            
            # Policies
            "policy_template": "operational_policies",
            "safeguarding_template": "safeguarding_policies",
            "whistleblowing_template": "safeguarding_policies",
            "covid_template": "operational_policies",
            
            # Quality
            "audit_template": "audit_records",
            "competency_template": "competency_assessments",
            "quality_template": "quality_feedback",
            
            # Other
            "rota_template": "staffing_operational",
            "complaint_template": "operational_policies",
            "seasonal_template": "operational_policies",
            
            "unclassified": "unclassified",
        }
        
        return type_to_destination.get(detected_type, "unclassified")
    
    def _compute_confidence(self, detected_type: str, filename: str) -> float:
        """Compute classification confidence 0.0-1.0"""
        if detected_type == "unclassified":
            return 0.3
        if detected_type in ("care_plan_template", "medication_template", "policy_template"):
            return 0.95
        if "osabea" in filename.lower():
            return min(0.99, 0.7 + 0.1)  # +0.1 for consistent naming
        return 0.7
    
    def _compute_priority(self, detected_type: str, destination_section: str) -> str:
        """Compute import priority: CRITICAL, HIGH, MEDIUM, LOW"""
        if destination_section in ("su_care_plans", "su_assessments", "incidents", "medication_operational"):
            return "CRITICAL"
        if destination_section in ("su_reviews", "body_maps", "risk_assessments_operational", "safeguarding_policies"):
            return "HIGH"
        if destination_section in ("recruitment", "performance_management", "operational_policies"):
            return "MEDIUM"
        return "LOW"
    
    def detect_duplicates(self) -> Dict[str, List[TemplateMetadata]]:
        """Detect exact duplicates by content hash"""
        duplicates = {}
        for file_hash, templates in self.hash_map.items():
            if len(templates) > 1:
                duplicates[file_hash] = templates
        return duplicates
    
    def detect_near_duplicates(self) -> List[Tuple[str, List[TemplateMetadata]]]:
        """Detect near-duplicates by filename similarity"""
        near_duplicates = []
        processed = set()
        
        for filename, templates in self.filename_map.items():
            if filename in processed or len(templates) <= 1:
                continue
            
            # Check for variants (e.g., Body Map, Body Map Female, Body Map Male)
            base_name = self._extract_base_name(filename)
            variants = [t for t in self.templates if self._extract_base_name(t.filename) == base_name]
            
            if len(variants) > 1:
                near_duplicates.append((base_name, variants))
                processed.update(t.filename for t in variants)
        
        return near_duplicates
    
    def _extract_base_name(self, filename: str) -> str:
        """Extract base name for duplicate detection"""
        base = filename.replace(".docx", "").replace(".pdf", "").replace(".xlsx", "").replace(".xls", "").replace(".doc", "")
        # Remove variant suffixes
        for suffix in ("_female", "_male", "_for_creams", "_weekly", "_monthly", "_controlled", "_prn", "_overall", "_individual"):
            base = base.replace(suffix, "").rstrip("_")
        return base.lower()
    
    def generate_inventory_report(self) -> Dict[str, any]:
        """Generate comprehensive inventory report"""
        by_destination = {}
        by_type = {}
        by_priority = {}
        
        for template in self.templates:
            # By destination
            if template.destination_section not in by_destination:
                by_destination[template.destination_section] = []
            by_destination[template.destination_section].append(template)
            
            # By type
            if template.detected_type not in by_type:
                by_type[template.detected_type] = []
            by_type[template.detected_type].append(template)
            
            # By priority
            if template.priority not in by_priority:
                by_priority[template.priority] = []
            by_priority[template.priority].append(template)
        
        return {
            "total_templates": len(self.templates),
            "total_size_mb": sum(t.file_size for t in self.templates) / (1024 * 1024),
            "by_destination": {k: len(v) for k, v in by_destination.items()},
            "by_type": {k: len(v) for k, v in by_type.items()},
            "by_priority": {k: len(v) for k, v in by_priority.items()},
            "exact_duplicates": len(self.detect_duplicates()),
            "near_duplicates": len(self.detect_near_duplicates()),
        }
    
    def export_inventory_json(self, output_path: str) -> None:
        """Export inventory to JSON"""
        inventory = {
            "metadata": self.generate_inventory_report(),
            "templates": [asdict(t) for t in self.templates],
            "duplicates": {
                "exact": [
                    {
                        "hash": hash_val,
                        "count": len(templates),
                        "files": [t.filename for t in templates],
                        "folders": [t.folder_path for t in templates],
                    }
                    for hash_val, templates in self.detect_duplicates().items()
                ],
                "near": [
                    {
                        "base_name": base_name,
                        "count": len(templates),
                        "variants": [
                            {
                                "filename": t.filename,
                                "folder": t.folder_path,
                                "size": t.file_size,
                            }
                            for t in templates
                        ],
                        "recommended_action": "KEEP_ALL" if "Female" in [t.filename for t in templates] or "Male" in [t.filename for t in templates] else "CONSOLIDATE"
                    }
                    for base_name, templates in self.detect_near_duplicates()
                ]
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(inventory, f, indent=2, default=str)
    
    def export_import_manifest(self, output_path: str) -> None:
        """Export import manifest for batch processing"""
        manifest = {
            "archive_root": str(self.archive_root),
            "total_templates": len(self.templates),
            "phases": {
                "phase_1_critical": [
                    asdict(t) for t in self.templates 
                    if t.priority == "CRITICAL"
                ],
                "phase_2_high": [
                    asdict(t) for t in self.templates 
                    if t.priority == "HIGH"
                ],
                "phase_3_medium": [
                    asdict(t) for t in self.templates 
                    if t.priority == "MEDIUM"
                ],
                "phase_4_low": [
                    asdict(t) for t in self.templates 
                    if t.priority == "LOW"
                ],
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)


def main():
    """Run inventory + duplicate detection"""
    archive_root = r"C:\Users\sstan\Downloads\Osabea Healthcare Solutions Ltd (2)"
    
    engine = ArchiveInventoryEngine(archive_root)
    engine.scan_archive()
    
    # Generate reports
    engine.export_inventory_json("ARCHIVE_INVENTORY.json")
    engine.export_import_manifest("IMPORT_MANIFEST.json")
    
    # Print summary
    report = engine.generate_inventory_report()
    print("=" * 60)
    print("ARCHIVE INVENTORY SUMMARY")
    print("=" * 60)
    print(f"Total Templates: {report['total_templates']}")
    print(f"Total Size: {report['total_size_mb']:.1f} MB")
    print(f"Exact Duplicates: {report['exact_duplicates']}")
    print(f"Near-Duplicates: {report['near_duplicates']}")
    print("\nDestinations:")
    for dest, count in sorted(report['by_destination'].items(), key=lambda x: -x[1]):
        print(f"  {dest}: {count}")
    print("\nPriorities:")
    for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = report['by_priority'].get(priority, 0)
        print(f"  {priority}: {count}")


if __name__ == "__main__":
    main()
