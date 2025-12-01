from pydantic import BaseModel

from .flotilla import FlotillaClient


class OutOfBandResponse(BaseModel):
    pubkey: bytes


class OfflineInfoResponse(BaseModel):
    domain: str
    key: bytes
    hint: bytes
    rows: int
    cols: int
    db_id_hash: bytes

    # sign(sk, hash(domain||key||hint||rows||cols||db_id_hash))
    ed25519_signature: bytes


class AnswerRequest(BaseModel):
    query: bytes


class AnswerResponse(BaseModel):
    answer: bytes

    # TODO: to be verifiable on chain we'd need to provide all the inputs.
    # sign(sk, hash(hash(domain||key||hint||rows||cols||db_id_hash)||query||answer))
    ed25519_signature: bytes


class FlotillaRestServer:
    def __init__(self, cfg, flotilla_client):
        self.cfg = cfg
        self.flotilla_client = FlotillaClient(cfg["flotilla"])

    def out_of_band(self) -> OutOfBandResponse:
        return OutOfBandResponse(
            pubkey=b"pubkey",
        )

    async def get_offline_info(self) -> OfflineInfoResponse:
        return await self.flotilla_client.get_offline_info()

    async def get_answer(self, request: AnswerRequest) -> AnswerResponse:
        return await self.flotilla_client.answer(query)
