import asyncio
import uuid
from app.database.connection import connect_db, AsyncSessionLocal
from app.models.camera import Camera
from sqlalchemy import select

async def update_cam2():
    await connect_db()
    cam2_id = uuid.UUID('67676767-6767-4e67-a676-676767676767')
    new_rtsp = "rtsp://admin:cctv%40321@192.168.1.65:554/Streaming/Channels/101"
    new_name = "Queue Monitor 2 (192.168.1.65)"

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Camera).where(Camera.id == cam2_id))
        cam2 = res.scalar_one_or_none()
        if cam2:
            cam2.rtsp_url = new_rtsp
            cam2.camera_name = new_name
            cam2.is_active = True
            cam2.stream_enabled = True
            cam2.status = "ONLINE"
            await session.commit()
            print(f"SUCCESS: Updated Camera 2 RTSP URL to: {new_rtsp}")
        else:
            print("ERROR: Camera 2 not found in database!")

if __name__ == "__main__":
    asyncio.run(update_cam2())
