"""Disable all dummy cameras (192.168.1.x) and start the real camera."""
import asyncio
from app.database.connection import connect_db, AsyncSessionLocal
from sqlalchemy import text

REAL_CAM_ID = "4e09b542-98b1-4974-9e6c-8f3a8c3d7f0a"
REAL_CAM_URL = "rtsp://admin:Veeru%40555@192.168.0.102:554/Streaming/Channels/101"

async def main():
    await connect_db()
    async with AsyncSessionLocal() as session:
        # 1. Disable all dummy cameras (192.168.1.x)
        result = await session.execute(text(
            "UPDATE cameras SET stream_enabled = false, is_active = false "
            "WHERE rtsp_url LIKE 'rtsp://192.168.1.%'"
        ))
        await session.commit()
        print(f"Disabled {result.rowcount} dummy cameras")

        # 2. Make sure real camera is active
        result2 = await session.execute(text(
            "UPDATE cameras SET stream_enabled = true, is_active = true "
            f"WHERE id = '{REAL_CAM_ID}'"
        ))
        await session.commit()
        print(f"Real camera enabled: {result2.rowcount} row(s)")

        # 3. Verify
        cams = await session.execute(text(
            "SELECT id, rtsp_url, stream_enabled, is_active FROM cameras ORDER BY created_at"
        ))
        print("\nAll cameras:")
        for r in cams.fetchall():
            flag = "✅" if r.stream_enabled else "❌"
            print(f"  {flag} {str(r.id)[:8]}... | stream={r.stream_enabled} | {r.rtsp_url[:50]}")

asyncio.run(main())
