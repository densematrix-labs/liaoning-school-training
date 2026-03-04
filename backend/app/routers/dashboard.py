from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json

from app.database import get_db, AsyncSessionLocal
from app.services.dashboard import DashboardService
from app.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["大屏展示"])


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """获取大屏展示数据"""
    service = DashboardService(db)
    return await service.get_dashboard_data()


@router.websocket("/ws")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket 实时推送大屏数据"""
    await websocket.accept()
    
    try:
        while True:
            async with AsyncSessionLocal() as db:
                service = DashboardService(db)
                data = await service.get_dashboard_data()
                
                # Convert to JSON-serializable dict
                await websocket.send_json(data.model_dump(mode='json'))
            
            # Update every 30 seconds
            await asyncio.sleep(30)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
