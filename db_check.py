import asyncio
from db import engine, init_db, Session, fetch_history, set_persona, get_persona

async def main():
    print("Connecting to DB...")
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: None)
    print("OK: engine connected.")

    print("Creating tables (if missing)...")
    await init_db()
    print("OK: tables ensured.")

    chat_id = 123456
    async with Session() as session:
        await set_persona(session, chat_id, "Test persona")
        p = await get_persona(session, chat_id)
        print("Persona fetched:", p)

        hist = await fetch_history(session, chat_id)
        print("History len:", len(hist))

if __name__ == "__main__":
    asyncio.run(main())
