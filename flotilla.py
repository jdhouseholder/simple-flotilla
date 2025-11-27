import argparse
import math

from pydantic import BaseModel
import asyncio
import numpy as np
import grpc

import flotilla_pb2, flotilla_pb2_grpc

import serde
from crypto import shake_rand_A_full
from load_cfg import load_cfg


class WorkerClient:
    def __init__(self, worker_ref):
        self.worker_ref = worker_ref
        self.channel = grpc.aio.insecure_channel(self.worker_ref["address"])
        self.stub = flotilla_pb2_grpc.WorkerServiceStub(self.channel)

    async def hint(self, key: bytes, rows: int, lwe_secret_dim: int) -> np.ndarray:
        resp = await self.stub.Hint(flotilla_pb2.HintRequest(key=key))
        a = serde.uint32_ndarray_from_bytes(resp.share)
        return np.reshape(a, (rows, lwe_secret_dim))

    async def answer(self, query: np.ndarray) -> np.ndarray:
        query = serde.uint32_ndarray_to_bytes(query)
        resp = await self.stub.Answer(flotilla_pb2.AnswerRequest(query=query))
        a = serde.uint32_ndarray_from_bytes(resp.share)
        return np.reshape(a, (-1, 1))


class FlotillaClient:
    def __init__(self, cfg):
        self.worker_refs = cfg["worker_refs"]
        self.key = cfg["key"].encode("utf8")
        self.rows = cfg["rows"]
        self.lwe_secret_dim = cfg["lwe_secret_dim"]
        self.worker_clients = [WorkerClient(w) for w in self.worker_refs]

        self.offline_info = None

    async def get_offline_info(self):
        if self.offline_info is not None:
            return self.offline_info

        responses = await asyncio.gather(
            *[w.hint(self.key, self.rows, self.lwe_secret_dim) for w in self.worker_clients]
        )
        hint = np.sum(responses, axis=0, dtype=np.uint32)

        self.offline_info = {"key": self.key, "hint": hint}

        return self.offline_info

    async def answer(self, query: np.ndarray):
        futs = []
        n_workers = len(self.worker_clients)
        chunk_size = int(math.floor(len(query) / n_workers))
        rem = len(query) % n_workers
        for i, w in enumerate(self.worker_clients):
            start = i * chunk_size
            end = (i + 1) * chunk_size
            if i == n_workers - 1:
                end += rem
            q = query[start:end]
            futs.append(w.answer(q))
        responses = await asyncio.gather(*futs)
        resp = np.sum(responses, axis=0)
        return resp


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cfg_path", type=str, nargs="?", default="./cfg/flotilla.toml"
    )
    args = parser.parse_args()
    cfg = load_cfg(args.cfg_path)
    flotilla_cfg = cfg["flotilla"]
    key = flotilla_cfg["key"].encode("utf8")
    c = FlotillaClient(flotilla_cfg)

    np.random.seed(0)
    db = np.random.randint(0, 32, (64, 64), dtype=np.uint32)

    A = shake_rand_A_full(key, 64, 1024)
    want = (db @ A).astype(np.uint32)

    print("get_offline_info")
    o = await c.get_offline_info()
    hint = o["hint"]
    assert np.all(hint == want)

    print("answer")
    query = np.random.randint(0, 5, (64, 1), dtype=np.uint32)
    a = await c.answer(query)
    want = db @ query
    assert np.all(a == want)


if __name__ == "__main__":
    asyncio.run(main())
