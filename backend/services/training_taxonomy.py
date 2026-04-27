"""
Shared canonical training taxonomy.

Used by both server-side extraction mapping and training evaluator resolution
to prevent taxonomy drift.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

# Batch 1 canonical keys (plus legacy compatibility keys kept for reads)
CANONICAL_TRAINING_KEYS = {
    "safeguarding",
    "basic_life_support_adults",
    "paediatric_basic_life_support",
    "equality_diversity_human_rights",
    "health_safety_welfare",
    "prevent",
    "infection_control",
    "information_governance",
    "fire_safety",
    "manual_handling",
    "mca_dols",
    "mental_capacity_act",
    "deprivation_of_liberty_safeguards",
    "medication_administration",
    "clinical_observations_news2",
}

# Legacy/read compatibility keys (do not use for new extraction output).
LEGACY_COMPATIBILITY_KEYS = {
    "safeguarding",
    "basic_life_support",
    "mca_dols",
}

TRAINING_TITLES_CANONICAL = {
    "safeguarding": "Safeguarding",
    "basic_life_support_adults": "Basic Life Support (Adults)",
    "paediatric_basic_life_support": "Paediatric Basic Life Support",
    "equality_diversity_human_rights": "Equality, Diversity and Human Rights",
    "health_safety_welfare": "Health, Safety and Welfare",
    "prevent": "Prevent",
    "infection_control": "Infection Prevention and Control",
    "information_governance": "Information Governance",
    "fire_safety": "Fire Safety",
    "manual_handling": "Manual Handling",
    "mca_dols": "MCA and DoLS",
    "mental_capacity_act": "Mental Capacity Act",
    "deprivation_of_liberty_safeguards": "Deprivation of Liberty Safeguards",
    "medication_administration": "Medication Administration",
    "clinical_observations_news2": "Clinical Observations (NEWS2)",
}


def normalize_training_text(value: str) -> str:
    if not value:
        return ""
    normalized = value.lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_training_key(value: str) -> str:
    return normalize_training_text(value).replace(" ", "_")


CANONICAL_TRAINING_ALIASES = {
    # Unified safeguarding requirement (single mandatory competency).
    "safeguarding": "safeguarding",
    "safeguarding_adults": "safeguarding",
    "safeguarding_children": "safeguarding",
    "cstf_safeguarding_adults": "safeguarding",
    "cstf_safeguarding_children": "safeguarding",
    "safeguarding_level_1": "safeguarding",
    "safeguarding_level_2": "safeguarding",
    "safeguarding_level_3": "safeguarding",
    "adult_support_and_protection": "safeguarding",
    "safeguarding_adults_level_1": "safeguarding",
    "safeguarding_adults_level_2": "safeguarding",
    "safeguarding_adults_levels_1_and_2": "safeguarding",
    "safeguarding_children_levels_1_2": "safeguarding",
    "safeguarding_children_levels_1_and_2": "safeguarding",
    "cstf_safeguarding_adults_level_1": "safeguarding",
    "cstf_safeguarding_adults_level_2": "safeguarding",
    "cstf_safeguarding_adults_levels_1_and_2": "safeguarding",
    "cstf_safeguarding_children_levels_1_and_2": "safeguarding",
    # Distinct BLS keys (no collapse)
    "basic_life_support_adults": "basic_life_support_adults",
    "basic_life_support": "basic_life_support_adults",
    "adult_basic_life_support": "basic_life_support_adults",
    "adult_resuscitation": "basic_life_support_adults",
    "resuscitation_adults": "basic_life_support_adults",
    "cstf_resuscitation_adults": "basic_life_support_adults",
    "cstf_resuscitation_adults_levels_1_2_3": "basic_life_support_adults",
    "cstf_resuscitation_adults_levels_1_2_and_3": "basic_life_support_adults",
    "cstf_resuscitation_adults_levels_1_2_3_practical": "basic_life_support_adults",
    "bls_adults": "basic_life_support_adults",
    "adult_immediate_life_support": "basic_life_support_adults",
    "paediatric_basic_life_support": "paediatric_basic_life_support",
    "pediatric_basic_life_support": "paediatric_basic_life_support",
    "paediatric_resuscitation": "paediatric_basic_life_support",
    "pediatric_resuscitation": "paediatric_basic_life_support",
    "resuscitation_paediatric": "paediatric_basic_life_support",
    "cstf_resuscitation_paediatric_levels_2_and_3_practical": "paediatric_basic_life_support",
    "paediatric_immediate_life_support": "paediatric_basic_life_support",
    # Core
    "equality_diversity_human_rights": "equality_diversity_human_rights",
    "equality_diversity_and_human_rights": "equality_diversity_human_rights",
    "equality_and_diversity_and_human_rights": "equality_diversity_human_rights",
    "cstf_equality_diversity_and_human_rights": "equality_diversity_human_rights",
    "cstf_equality_and_diversity_and_human_rights": "equality_diversity_human_rights",
    "equality_and_diversity": "equality_diversity_human_rights",
    "health_safety_welfare": "health_safety_welfare",
    "health_and_safety": "health_safety_welfare",
    "health_safety": "health_safety_welfare",
    "health_and_safety_and_welfare": "health_safety_welfare",
    "health_safety_and_welfare": "health_safety_welfare",
    "cstf_health_safety_and_welfare": "health_safety_welfare",
    "cstf_health_and_safety_and_welfare": "health_safety_welfare",
    "prevent": "prevent",
    "preventing_radicalisation": "prevent",
    "preventing_radicalization": "prevent",
    "cstf_prevent": "prevent",
    "cstf_preventing_radicalisation": "prevent",
    "infection_control": "infection_control",
    "infection_prevention_and_control": "infection_control",
    "infection_prevention_and_control_levels_1_and_2": "infection_control",
    "cstf_infection_prevention_and_control": "infection_control",
    "cstf_infection_prevention_and_control_levels_1_and_2": "infection_control",
    "ipc": "infection_control",
    "information_governance": "information_governance",
    "information_governance_and_data_security": "information_governance",
    "information_governance_gdpr": "information_governance",
    "gdpr": "information_governance",
    "fire_safety": "fire_safety",
    "cstf_fire_safety": "fire_safety",
    "manual_handling": "manual_handling",
    "moving_and_handling": "manual_handling",
    "moving_and_handling_levels_1_and_2": "manual_handling",
    "cstf_moving_and_handling_levels_1_and_2": "manual_handling",
    "medication_administration": "medication_administration",
    "medication": "medication_administration",
    "safe_handling_and_administration_of_medication": "medication_administration",
    "the_safe_handling_and_administration_of_medication": "medication_administration",
    # MCA / DoLS (combined mandatory competency for current product behaviour)
    "mca_dols": "mca_dols",
    "mca_and_dols": "mca_dols",
    "mental_capacity_act": "mca_dols",
    "mental_capacity_act_2005": "mca_dols",
    "mental_capacity_act_2007": "mca_dols",
    "mca": "mca_dols",
    "deprivation_of_liberty_safeguards": "mca_dols",
    "deprivation_of_liberty": "mca_dols",
    "dols": "mca_dols",
    # NEWS2
    "clinical_observations_news2": "clinical_observations_news2",
    "news2": "clinical_observations_news2",
    "news_2": "clinical_observations_news2",
    "clinical_observations": "clinical_observations_news2",
    # Legacy compatibility (existing rows)
    "basic_life_support": "basic_life_support",
    "bls": "basic_life_support",
    "mca_dols": "mca_dols",
}


def resolve_training_to_canonical(value: str) -> Optional[str]:
    """
    Resolve a raw title/key to canonical training code.
    """
    key = normalize_training_key(value or "")
    if not key:
        return None
    direct = CANONICAL_TRAINING_ALIASES.get(key)
    if direct:
        return direct

    # Fuzzy fallback: prefer longest alias match.
    best = None
    best_len = 0
    for alias, canonical in CANONICAL_TRAINING_ALIASES.items():
        if alias and alias in key and len(alias) > best_len:
            best = canonical
            best_len = len(alias)
    return best


def map_training_title_to_canonical(raw_title: str) -> Tuple[Optional[str], Optional[str]]:
    canonical = resolve_training_to_canonical(raw_title)
    if not canonical:
        return None, None
    return canonical, TRAINING_TITLES_CANONICAL.get(canonical, raw_title)
