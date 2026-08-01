import asyncio
import uuid
from app.database.connection import connect_db, AsyncSessionLocal
from app.models.camera import Camera
from app.models.roi import ROI
from app.common.enums import CameraType, CameraStatus, ROIType, ROIDirection
from sqlalchemy import select

async def main():
    await connect_db()
    cam4_id = uuid.UUID('44444444-4444-4444-a444-444444444444')
    rtsp_url = "rtsp://admin:Admin%40123@192.168.1.100:554/cam/realmonitor?channel=15&subtype=1"
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Camera).where(Camera.id == cam4_id))
        cam4 = res.scalar_one_or_none()
        if not cam4:
            cam4 = Camera(
                id=cam4_id,
                camera_name="Exit Counter Camera 4 (192.168.1.100 ch15)",
                camera_type=CameraType.EXIT,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                ai_enabled=True,
                rtsp_url=rtsp_url,
                resolution="1920x1080",
                location="Main Gate Exit 4"
            )
            session.add(cam4)
            print(f"CREATED Camera 4 in DB: {cam4_id}")
        else:
            cam4.camera_name = "Exit Counter Camera 4 (192.168.1.100 ch15)"
            cam4.camera_type = CameraType.EXIT
            cam4.status = CameraStatus.ONLINE
            cam4.is_active = True
            cam4.stream_enabled = True
            cam4.ai_enabled = True
            cam4.rtsp_url = rtsp_url
            cam4.resolution = "1920x1080"
            print(f"UPDATED Camera 4 in DB: {cam4_id}")

        # Check ROI for Camera 4
        res_r = await session.execute(select(ROI).where(ROI.camera_id == cam4_id))
        roi4 = res_r.scalar_one_or_none()
        if not roi4:
            roi4 = ROI(
                id=uuid.uuid4(),
                camera_id=cam4_id,
                name="Main Exit Counting Line 4",
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
            session.add(roi4)
            print("CREATED ROI for Camera 4")
        
        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
