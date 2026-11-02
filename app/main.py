import os
import time
import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

app = FastAPI(title="Sarah Mini API")

def get_connection():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=3,
        row_factory=dict_row,
    )

def initialize_database():
    # Reintentos limitados: útiles durante el arranque local.
    # No sustituyen una estrategia completa de recuperación.
    for attempt in range(10):
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS checkins (
                        id SERIAL PRIMARY KEY,
                        mood TEXT NOT NULL,
                        activity TEXT NOT NULL,
                        note TEXT NOT NULL
                    )
                    """
                )
                return
        except psycopg.OperationalError:
            if attempt == 9:
                raise
            time.sleep(2)

@app.on_event("startup")
def startup():
    initialize_database()

class CheckInCreate(BaseModel):
    mood: str = Field(min_length=1, max_length=80)
    activity: str = Field(min_length=1, max_length=120)
    note: str = Field(min_length=1, max_length=500)

@app.get("/")
def root():
    return {"message": "Sarah Mini: registro de bienestar de demostración"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/checkins")
def list_checkins(mood: str | None = None, activity: str | None = None):
    try:
        with get_connection() as conn:
            # Iniciamos una consulta base
            query = "SELECT id, mood, activity, note FROM checkins WHERE 1=1"
            params = []

            # Agregamos filtros dinámicamente si el usuario los envía
            if mood:
                query += " AND mood = %s"
                params.append(mood)
            if activity:
                query += " AND activity = %s"
                params.append(activity)

            query += " ORDER BY id"

            rows = conn.execute(query, params).fetchall()
            return rows
    except psycopg.OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Base de datos no disponible",
        )