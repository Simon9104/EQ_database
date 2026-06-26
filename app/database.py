from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./eq_database.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns that may be missing from existing databases
        migrations = [
            "ALTER TABLE users ADD COLUMN password_hash TEXT",
            "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1",
            # Invoice extensions
            "ALTER TABLE faktury ADD COLUMN id_projektu INTEGER",
            "ALTER TABLE faktury ADD COLUMN firma_id INTEGER",
            "ALTER TABLE faktury ADD COLUMN vs TEXT",
            "ALTER TABLE faktury ADD COLUMN forma_uhrady TEXT",
            "ALTER TABLE faktury ADD COLUMN iban TEXT",
            "ALTER TABLE faktury ADD COLUMN swift TEXT",
            "ALTER TABLE faktury ADD COLUMN poznamka TEXT",
            # Imposition links
            "ALTER TABLE vyradovanie ADD COLUMN id_projektu INTEGER",
            "ALTER TABLE vyradovanie ADD COLUMN id_polozky INTEGER",
            # Default flags for lookup tables
            "ALTER TABLE vazby ADD COLUMN is_default INTEGER DEFAULT 0",
            "ALTER TABLE sadzba_dph ADD COLUMN is_default INTEGER DEFAULT 0",
            # Company defaults for invoice pre-fill
            "ALTER TABLE firemne_udaje ADD COLUMN forma_uhrady TEXT",
            # Firemne udaje table (failsafe if create_all missed it)
            """CREATE TABLE IF NOT EXISTS firemne_udaje (
                id INTEGER PRIMARY KEY DEFAULT 1,
                nazov TEXT, adresa TEXT, mesto TEXT, psc TEXT,
                ico TEXT, ic_dph TEXT, dic TEXT,
                iban TEXT, swift TEXT, banka TEXT,
                telefon TEXT, email TEXT, web TEXT, poznamka_fa TEXT
            )""",
        ]
        for sql in migrations:
            try:
                await conn.execute(__import__('sqlalchemy').text(sql))
            except Exception:
                pass  # Column already exists
