import argparse
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from .load_cfg import load_cfg
from .flotilla_rest import (
    FlotillaRestServer,
    OutOfBandResponse,
    OfflineInfo,
    AnswerRequest,
    AnswerResponse,
)


server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # on start
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cfg_path", type=str, nargs="?", default="./cfg/flotilla.toml"
    )
    args = parser.parse_args()

    cfg = load_cfg(args.cfg_path)

    global server
    server = FlotillaRestServer(cfg=cfg)

    yield

    # on shutdown


app = FastAPI(lifespan=lifespan)


@app.get("/out-of-band")
async def out_of_band() -> OutOfBandResponse:
    return server.out_of_band()


@app.get("/offline")
async def get_offline_info() -> OfflineInfoResponse:
    return await server.get_offline_info()


@app.post("/answer")
async def answer(req: AnswerRequest) -> AnswerResponse:
    return await sever.answer(query)
