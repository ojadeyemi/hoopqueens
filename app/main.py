from fastapi import FastAPI
from routes import router

app = FastAPI(
    title="HoopQueens API",
    description="An API for managing HoopQueens basketball project.",
    version="1.0.0",
)

app.include_router(router)
