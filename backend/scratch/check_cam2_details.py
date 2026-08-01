import asyncio
from app.database.connection import connect_db, AsyncSessionLocal
from sqlalchemy import text

async def check():
    await connect_db()
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT id, camera_name, rtsp_url, is_active, stream_enabled, status FROM cameras WHERE id = '67676767-6767-4e67-a676-676767676767'"))
        r = res.fetchone()
        if r:
            print(f"CAM2 RECORD: id={r.id}, name={r.camera_name}, rtsp={r.rtsp_url}, active={r.is_active}, stream={r.stream_enabled}, status={r.status}")
        else:
            print("CAM2 NOT FOUND IN DB!")

if __name__ == "__main__":
    asyncio.run(check())
