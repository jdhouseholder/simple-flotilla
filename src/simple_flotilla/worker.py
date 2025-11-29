import argparse
from concurrent import futures
import grpc
import numpy as np

import flotilla_pb2, flotilla_pb2_grpc

from load_cfg import load_cfg
import serde

from simple_pirate import supa_fast, parameters, lib, simplepir
from simple_pirate.demo_utils import random_db


class Worker:
    def __init__(self, cfg):
        self.shard_start = cfg["shard_start"]
        self.shard_stop = cfg["shard_stop"]

        # Every node will solve for the same parameters for demo purposes
        self.parameters = parameters.solve_system_parameters(
            entries=cfg["entries"],
            bits_per_entry=cfg["bits_per_entry"],
        )

        np.random.seed(0)
        db = random_db(cfg["entries"], cfg["bits_per_entry"])
        db = simplepir.process_database(self.parameters, db)
        self.db = db[:, self.shard_start : self.shard_stop]
        self.db -= self.parameters.plaintext_modulus // 2
        A = lib.shake_rand_rows(
            cfg["key"].encode("utf8"),
            start=self.shard_start,
            stop=self.shard_stop,
            lwe_secret_dim=self.parameters.lwe_secret_dimension,
        )
        self._hint = supa_fast.matmul_u32_tiled(self.db, A)
        self.db += self.parameters.plaintext_modulus // 2
        self.db = lib.squish(
            self.db,
            basis=self.parameters.compression_basis,
            delta=self.parameters.compression_squishing,
        )

    def hint(self) -> bytes:
        hint = serde.uint32_ndarray_to_bytes(self._hint)
        return hint

    def answer(self, query: bytes) -> bytes:
        query = serde.uint32_ndarray_from_bytes(query)
        query = np.reshape(query, (self.shard_stop - self.shard_start, 1))
        #out = self.db @ query
        out = supa_fast.matvec_packed_fused(
            a=self.db,
            b=query,
            basis=self.parameters.compression_basis,
            compression=self.parameters.compression_squishing,
        ).astype(np.uint32)
        return serde.uint32_ndarray_to_bytes(out)


class WorkerService(flotilla_pb2_grpc.WorkerService):
    def __init__(self, w):
        super().__init__()
        self.w = w

    def Hint(self, req, context):
        share = self.w.hint()
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
