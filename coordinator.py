from contextlib import asynccontextmanager
from typing import Union
import tomllib

from fastapi import FastAPI
from pydantic import BaseModel

from flotilla import FlotillaClient, OfflineInfo


flotilla_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # on start

    global flotilla_client
    with open("./cfg/coordinator.toml", "rb") as f:
        cfg = tomllib.load(f)
    flotilla_client = FlotillaClient(cfg["flotilla"])
    yield
    # on shutdown


app = FastAPI(lifespan=lifespan)


@app.get("/offline")
async def get_offline() -> Union[OfflineInfo, None]:
    return await flotilla_client.get_offline_info()


@app.post("/answer")
async def answer(query: bytes) -> bytes:
    return await flotilla_client.answer(query)
