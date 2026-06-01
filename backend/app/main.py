from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import admin, draw
from .services.gift_state import release_expired_locks
from .database import SessionLocal
from .config import CORS_ORIGINS
from .utils.migrate import migrate


@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate()
    Base.metadata.create_all(bind=engine)
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
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(draw.router)


@app.get("/")
def root():
    return {"message": "Birthday Gift System API", "version": "1.0.0"}

