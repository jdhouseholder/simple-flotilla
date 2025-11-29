import argparse
import math

from pydantic import BaseModel
import asyncio
import numpy as np
import grpc

import flotilla_pb2, flotilla_pb2_grpc

import serde
from load_cfg import load_cfg

from simple_pirate.demo_utils import random_db
from simple_pirate.parameters import solve_system_parameters
from simple_pirate import simplepir


class WorkerClient:
    def __init__(self, worker_ref):
        self.worker_ref = worker_ref
        self.channel = grpc.aio.insecure_channel(self.worker_ref["address"])
        self.stub = flotilla_pb2_grpc.WorkerServiceStub(self.channel)

    async def hint(self, rows: int, lwe_secret_dim: int) -> np.ndarray:
        resp = await self.stub.Hint(flotilla_pb2.HintRequest())
        a = serde.uint32_ndarray_from_bytes(resp.share)
        return np.reshape(a, (rows, lwe_secret_dim))

    async def answer(self, query: np.ndarray) -> np.ndarray:
        query = serde.uint32_ndarray_to_bytes(query)
        resp = await self.stub.Answer(flotilla_pb2.AnswerRequest(query=query))
        a = serde.uint32_ndarray_from_bytes(resp.share)
        return np.reshape(a, (-1, 1))


class FlotillaClient:
    def __init__(self, cfg):
        self.parameters = solve_system_parameters(
            entries=cfg["entries"],
            bits_per_entry=cfg["bits_per_entry"],
        )

        self.worker_refs = cfg["worker_refs"]
        self.key = cfg["key"].encode("utf8")
        self.worker_clients = [WorkerClient(w) for w in self.worker_refs]

        self.offline_info = None

    async def get_offline_info(self):
        if self.offline_info is not None:
            return self.offline_info

        responses = await asyncio.gather(
            *[
                w.hint(self.parameters.db_rows, self.parameters.lwe_secret_dimension)
                for w in self.worker_clients
            ]
        )
        hint = np.sum(responses, axis=0, dtype=np.uint32)

        self.offline_info = {"key": self.key, "hint": hint}

        return self.offline_info

    async def answer(self, query: np.ndarray):
        futs = []
        for i, w in enumerate(self.worker_clients):
            shard_start = w.worker_ref["shard_start"]
            shard_stop = w.worker_ref["shard_stop"]
            q = query[shard_start:shard_stop]
            futs.append(w.answer(q))
        responses = await asyncio.gather(*futs)
        resp = np.sum(responses, axis=0)
        return resp

    async def answer_old(self, query: np.ndarray):
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

    parameters = solve_system_parameters(
        entries=flotilla_cfg["entries"],
        bits_per_entry=flotilla_cfg["bits_per_entry"],
    )

    np.random.seed(0)
    db = random_db(flotilla_cfg["entries"], flotilla_cfg["bits_per_entry"])

    print("Getting offline info")
    o = await c.get_offline_info()
    hint = o["hint"]
    print("Got offline info")

    simplepirClient = simplepir.SimplePirClient(parameters, simplepir.OfflineData(
        A_key=key,
        hint=hint,
    ))

    index = 1020
    query_state, query = simplepirClient.query(index)
    print("Getting answer")
    answer = await c.answer(query)
    print("Got answer")
    got = simplepirClient.recover(query_state, answer)
    print(got, db[index])

if __name__ == "__main__":
    asyncio.run(main())
