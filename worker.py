import argparse
from concurrent import futures
import grpc
import numpy as np

import flotilla_pb2, flotilla_pb2_grpc

from load_cfg import load_cfg
import serde
from crypto import shake_rand_A_rows

from simple_pirate import supa_fast


class Worker:
    def __init__(self, cfg):
        self.rows = cfg["rows"]
        self.cols = cfg["cols"]
        self.shard_start = cfg["shard_start"]
        self.shard_stop = cfg["shard_stop"]
        self.lwe_secret_dim = 1024

        np.random.seed(0)
        db = np.random.randint(0, 32, (self.rows, self.cols), dtype=np.uint32)
        self.db = db[:, self.shard_start : self.shard_stop]

    def hint(self, key: bytes) -> bytes:
        A = shake_rand_A_rows(
            key,
            start=self.shard_start,
            stop=self.shard_stop,
            lwe_secret_dim=self.lwe_secret_dim,
        )
        # hint = (self.db @ A).astype(np.uint32)
        hint = supa_fast.matmul_u32_tiled(self.db, A)
        hint = serde.uint32_ndarray_to_bytes(hint)
        return hint

    def answer(self, query: bytes) -> bytes:
        query = serde.uint32_ndarray_from_bytes(query)
        query = np.reshape(query, (self.shard_stop - self.shard_start, 1))
        #out = self.db @ query
        out = supa_fast.matmul_u32_tiled(self.db, query)
        return serde.uint32_ndarray_to_bytes(out)


class WorkerService(flotilla_pb2_grpc.WorkerService):
    def __init__(self, w):
        super().__init__()
        self.w = w

    def Hint(self, req, context):
        share = self.w.hint(req.key)
        return flotilla_pb2.HintResponse(share=share)

    def Answer(self, req, context):
        share = self.w.answer(req.query)
        return flotilla_pb2.AnswerResponse(share=share)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cfg_path", type=str, nargs="?", default="./cfg/worker.toml")
    args = parser.parse_args()

    cfg = load_cfg(args.cfg_path)

    rpc_cfg = cfg["rpc"]
    port = rpc_cfg["port"]

    worker = Worker(cfg["worker"])
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    flotilla_pb2_grpc.add_WorkerServiceServicer_to_server(WorkerService(worker), server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started, listening on " + port)
    server.wait_for_termination()


if __name__ == "__main__":
    main()
