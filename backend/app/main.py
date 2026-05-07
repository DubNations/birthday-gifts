from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text

from .config import CORS_ORIGINS
from .database import Base, SessionLocal, engine
from .routers import admin, draw
from .models.campaign import Campaign
from .models.draw_session import DrawSession
from .models.gift import Gift
from .models.user_action import UserAction
from .services.campaign import ensure_default_campaign
from .services.gift_state import release_expired_locks


def ensure_schema_compatibility():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    compatibility_columns = {
        "user_action_log": {
            "details": "ALTER TABLE user_action_log ADD COLUMN details TEXT",
            "campaign_id": "ALTER TABLE user_action_log ADD COLUMN campaign_id INTEGER",
        },
        "gifts": {
            "campaign_id": "ALTER TABLE gifts ADD COLUMN campaign_id INTEGER",
        },
        "draw_sessions": {
            "campaign_id": "ALTER TABLE draw_sessions ADD COLUMN campaign_id INTEGER",
        },
    }
    with engine.begin() as connection:
        for table, columns_to_add in compatibility_columns.items():
            if table not in table_names:
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            for column_name, ddl in columns_to_add.items():
                if column_name not in columns:
                    connection.execute(text(ddl))


def assign_legacy_rows_to_default_campaign():
    db = SessionLocal()
    try:
        campaign = ensure_default_campaign(db)
        db.query(Gift).filter(Gift.campaign_id.is_(None)).update({Gift.campaign_id: campaign.id}, synchronize_session=False)
        db.query(DrawSession).filter(DrawSession.campaign_id.is_(None)).update({DrawSession.campaign_id: campaign.id}, synchronize_session=False)
        db.query(UserAction).filter(UserAction.campaign_id.is_(None)).update({UserAction.campaign_id: campaign.id}, synchronize_session=False)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    assign_legacy_rows_to_default_campaign()
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
