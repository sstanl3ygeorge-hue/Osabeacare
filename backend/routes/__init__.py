# Routes package for modular FastAPI routers
# This package contains refactored routes extracted from server.py

from .auth import router as auth_router
from .workers import router as workers_router
