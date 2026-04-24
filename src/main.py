from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.pathfinder import router as pathfinder_router

app = FastAPI(
    title="Pathfinder API",
    description="ブラウザエージェントによる会場情報抽出API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WARNING: 開発中は全許可、本番では絞る
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pathfinder_router)