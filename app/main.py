from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.routers import projects, items, invoices, customers, credits, imposition, lookups


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="EQ Projekty", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(items.router)
app.include_router(invoices.router)
app.include_router(customers.router)
app.include_router(credits.router)
app.include_router(imposition.router)
app.include_router(lookups.router)
app.include_router(lookups.stavy_router)
app.include_router(lookups.status_polozky_router)
app.include_router(lookups.typ_zakazky_router)
app.include_router(lookups.vazby_router)
app.include_router(lookups.povrch_router)
app.include_router(lookups.dph_router)
app.include_router(lookups.users_router)
app.include_router(lookups.podfilter_router)
app.include_router(lookups.odmeny_router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
