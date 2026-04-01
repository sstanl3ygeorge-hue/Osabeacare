"""
Migration configuration settings.
Load from environment variables with sensible defaults for staging.
"""

import os

# MongoDB (source)
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("DB_NAME", "test_database")

# Supabase (target)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL", "")

# Emergent Storage (for file downloads)
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
EMERGENT_STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"

# Migration settings
BATCH_SIZE = int(os.environ.get("MIGRATION_BATCH_SIZE", "50"))
MAX_CONCURRENT_FILES = int(os.environ.get("MAX_CONCURRENT_FILES", "5"))
DRY_RUN = os.environ.get("MIGRATION_DRY_RUN", "false").lower() == "true"

# Paths
REPORTS_DIR = "/app/migration/reports"
SQL_DIR = "/app/migration/sql"
