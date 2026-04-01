"""
Phase 1: Migrate users from MongoDB to Postgres profiles table.

For staging without Supabase Auth, we create profiles directly.
In production, use Supabase Auth admin API to create auth.users first.

Idempotent: Checks mongo_id before inserting.
Resumable: Tracks last_processed_id in migration_state.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_timestamp, sanitize_string, extract_mongo_id
)
from config.mappings import ROLE_MAP, get_mapped_value


class Phase1UserMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_1_users", dry_run)
    
    async def migrate(self):
        # Count total users
        cursor = self.mongo_db.users.find({})
        users = await cursor.to_list(length=None)
        self.result.total_records = len(users)
        
        self.logger.info(f"Found {len(users)} users to migrate")
        
        # Sort for consistent ordering
        users.sort(key=lambda x: x.get("user_id", ""))
        
        for user in users:
            mongo_id = user.get("user_id") or str(user.get("_id"))
            
            # Resume support: skip if before last processed
            if self.result.last_processed_id:
                if mongo_id <= self.result.last_processed_id:
                    self.record_skip(mongo_id, "already processed")
                    continue
            
            try:
                await self._migrate_user(user)
                self.result.migrated_records += 1
                self.result.last_processed_id = mongo_id
                
                # Periodic state save
                if self.result.migrated_records % 10 == 0:
                    await self._save_state()
                    
            except Exception as e:
                self.record_error(mongo_id, str(e))
    
    async def _migrate_user(self, mongo_user: dict):
        """Migrate a single user to profiles table."""
        mongo_id = mongo_user.get("user_id") or str(mongo_user.get("_id"))
        email = mongo_user.get("email")
        
        if not email:
            raise ValueError("User has no email")
        
        # Idempotent check
        if await self.is_already_migrated("profiles", mongo_id):
            self.record_skip(mongo_id, "already exists in profiles")
            return
        
        # Check if already in mapping
        if mongo_id in self.user_id_map:
            self.record_skip(mongo_id, "already in mapping")
            return
        
        # Generate new UUID
        new_id = generate_uuid()
        
        # Map role
        role = get_mapped_value(
            mongo_user.get("role", "employee"),
            ROLE_MAP,
            "employee"
        )
        
        self.logger.debug(f"Migrating user: {email} ({mongo_id} -> {new_id})")
        
        if not self.dry_run and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO profiles (
                        id, email, name, role, branch, picture_url, 
                        created_at, updated_at, mongo_id, migration_reviewed
                    )
                    VALUES ($1, $2, $3, $4::user_role, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (mongo_id) DO NOTHING
                """,
                    new_id,
                    email,
                    sanitize_string(mongo_user.get("name")),
                    role,
                    sanitize_string(mongo_user.get("branch")),
                    mongo_user.get("picture"),
                    parse_timestamp(mongo_user.get("created_at")),
                    parse_timestamp(mongo_user.get("created_at")),
                    mongo_id,
                    False
                )
        
        # Save mapping
        await self.save_user_mapping(mongo_id, new_id)
        self.logger.info(f"Migrated user: {email}")


async def run(dry_run: bool = False):
    """Entry point for phase 1."""
    migration = Phase1UserMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    asyncio.run(run(dry_run=args.dry_run))
