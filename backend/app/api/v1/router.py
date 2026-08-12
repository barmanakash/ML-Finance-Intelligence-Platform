"""Aggregates all v1 routers under a single /api/v1 prefix.

Future phases add their routers here (transactions, imports, categories,
anomalies, recurring, forecasts, insights, ml) — nothing else needs to change.
"""

from fastapi import APIRouter

from app.api.v1 import auth, imports, transactions, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(imports.router)
api_router.include_router(transactions.router)
