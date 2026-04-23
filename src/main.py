import asyncio
import traceback
import json
from services.pathfinder_service import run_pathfinder
from logger import logger

async def main():
    try:
        result = await run_pathfinder("https://www.congre.co.jp/130jos/index.html")
        logger.info("\n" + "=" * 60)
        logger.info("最終回答")
        logger.info("=" * 60)
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        logger.info("=" * 60)

    except Exception:
        logger.error("CRITICAL ERROR CAUGHT:\n%s", traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())