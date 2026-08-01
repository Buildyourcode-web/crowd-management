import asyncio
import uuid
from app.database.connection import connect_db, AsyncSessionLocal
from app.models.camera import Camera
from app.models.roi import ROI
from app.common.enums import CameraType, CameraStatus, ROIType, ROIDirection
from sqlalchemy import select

async def main():
    await connect_db()
    cam6_id = uuid.UUID('66666666-6666-6666-a666-666666666666')
    rtsp_url = "rtsp://admin:Admin%40123@192.168.1.100:554/cam/realmonitor?channel=12&subtype=0"
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Camera).where(Camera.id == cam6_id))
        cam6 = res.scalar_one_or_none()
        if not cam6:
            cam6 = Camera(
                id=cam6_id,
                camera_name="Person Counter Camera 6 (192.168.1.100 ch12)",
                camera_type=CameraType.ENTRY,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                ai_enabled=True,
                rtsp_url=rtsp_url,
                resolution="1920x1080",
                location="Main Gate Entrance 6"
            )
            session.add(cam6)
            print(f"CREATED Camera 6 in DB: {cam6_id}")
        else:
            cam6.camera_name = "Person Counter Camera 6 (192.168.1.100 ch12)"
            cam6.camera_type = CameraType.ENTRY
            cam6.status = CameraStatus.ONLINE
            cam6.is_active = True
            cam6.stream_enabled = True
            cam6.ai_enabled = True
            cam6.rtsp_url = rtsp_url
            cam6.resolution = "1920x1080"
            print(f"UPDATED Camera 6 in DB: {cam6_id}")

        # Check ROI for Camera 6
        res_r = await session.execute(select(ROI).where(ROI.camera_id == cam6_id))
        roi6 = res_r.scalar_one_or_none()
        if not roi6:
            roi6 = ROI(
                id=uuid.uuid4(),
                camera_id=cam6_id,
                name="Main Entrance Counting Line 6",
                roi_type=ROIType.COUNTING_LINE,
                direction=ROIDirection.ENTRY,
                polygon={
                    "start_x": 0.0,
                    "start_y": 540.0,
                    "end_x": 1920.0,
                    "end_y": 540.0,
                    "orientation": "horizontal"
                },
                is_active=True
            )
            session.add(roi6)
            print("CREATED ROI for Camera 6")
        
        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
