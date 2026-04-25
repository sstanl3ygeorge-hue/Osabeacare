# Routes package for modular FastAPI routers
# This package contains refactored routes extracted from server.py

from .auth import router as auth_router
from .workers import router as workers_router
from .admin import router as admin_router
from .training import router as training_router
from .documents import router as documents_router
from .recruitment import router as recruitment_router
from .employees import router as employees_router
from .references import router as references_router
from .appraisals import router as appraisals_router
