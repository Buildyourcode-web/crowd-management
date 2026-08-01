import asyncio
import uuid
from app.database.connection import connect_db, AsyncSessionLocal
from app.models.camera import Camera
from app.models.roi import ROI
from app.common.enums import CameraType, CameraStatus, ROIType, ROIDirection
from sqlalchemy import select

async def main():
    await connect_db()
    cam5_id = uuid.UUID('55555555-5555-5555-a555-555555555555')
    rtsp_url = "rtsp://admin:Admin%40123@192.168.1.243:554/video/live?channel=1&subtype=0"
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Camera).where(Camera.id == cam5_id))
        cam5 = res.scalar_one_or_none()
        if not cam5:
            cam5 = Camera(
                id=cam5_id,
                camera_name="Exit Counter Camera 5 (192.168.1.243)",
                camera_type=CameraType.EXIT,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                ai_enabled=True,
                rtsp_url=rtsp_url,
                resolution="1920x1080",
                location="Main Gate Exit 5"
            )
            session.add(cam5)
            print(f"CREATED Camera 5 in DB: {cam5_id}")
        else:
            cam5.camera_name = "Exit Counter Camera 5 (192.168.1.243)"
            cam5.camera_type = CameraType.EXIT
            cam5.status = CameraStatus.ONLINE
            cam5.is_active = True
            cam5.stream_enabled = True
            cam5.ai_enabled = True
            cam5.rtsp_url = rtsp_url
            cam5.resolution = "1920x1080"
            print(f"UPDATED Camera 5 in DB: {cam5_id}")

        # Check ROI for Camera 5
        res_r = await session.execute(select(ROI).where(ROI.camera_id == cam5_id))
        roi5 = res_r.scalar_one_or_none()
        if not roi5:
            roi5 = ROI(
                id=uuid.uuid4(),
                camera_id=cam5_id,
                name="Main Exit Counting Line 5",
                roi_type=ROIType.COUNTING_LINE,
                direction=ROIDirection.EXIT,
                polygon={
                    "start_x": 0.0,
                    "start_y": 540.0,
                    "end_x": 1920.0,
                    "end_y": 540.0,
                    "orientation": "horizontal"
                },
                is_active=True
            )
            session.add(roi5)
            print("CREATED ROI for Camera 5")
        
        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
