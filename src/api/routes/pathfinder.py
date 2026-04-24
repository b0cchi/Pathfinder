# api/routes/pathfinder.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from fastapi.responses import StreamingResponse

from services.pathfinder_service import run_pathfinder, stream_pathfinder
from logger import logger

router = APIRouter(prefix="/pathfinder", tags=["pathfinder"])

class ScrapeRequest(BaseModel):
    url: HttpUrl

class VenueItem(BaseModel):
    name: str
    address: str

class ScrapeResponse(BaseModel):
    venues: list[VenueItem]


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest):
    """
    指定URLから開催会場と住所を抽出して返す。
    """
    logger.info("Received scrape request: %s", req.url)
    try:
        result = await run_pathfinder(str(req.url))
        return ScrapeResponse(venues=result["venues"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/scrape/stream")
async def scrape_stream(req: ScrapeRequest):
    """
    進捗をSSEでリアルタイムに返す。
    """
    return StreamingResponse(
        stream_pathfinder(str(req.url)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )