from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text

from .config import CORS_ORIGINS
from .database import Base, SessionLocal, engine
from .routers import admin, draw
from .services.gift_state import release_expired_locks


def ensure_schema_compatibility():
    inspector = inspect(engine)
    if "user_action_log" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("user_action_log")}
        if "details" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE user_action_log ADD COLUMN details TEXT"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    db = SessionLocal()
    try:
        released = release_expired_locks(db)
        if released:
            print(f"启动时释放了 {released} 个过期锁定")
    finally:
        db.close()
    yield


app = FastAPI(title="Birthday Gift System", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "X-Fingerprint"],
)

app.include_router(admin.router)
app.include_router(draw.router)


@app.get("/")
def root():
    return {"message": "Birthday Gift System API", "version": "1.0.0"}
