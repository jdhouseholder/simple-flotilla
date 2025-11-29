import hashlib
import numpy as np
import struct


def shake_rand_A_rows(
    key: bytes, start: int, stop: int, lwe_secret_dim: int
) -> np.ndarray:
    out = np.empty((stop - start, lwe_secret_dim), dtype=np.uint32)
    for j in range(stop - start):
        xof = hashlib.shake_256(key + b'\x13\x37' + struct.pack("<I", start + j))
        buf = xof.digest(4 * lwe_secret_dim)
        col = np.frombuffer(buf, dtype="<u4")
        out[j, :] = col
    return out


def shake_rand_A_full(key: bytes, cols: int, lwe_secret_dim: int) -> np.ndarray:
    return shake_rand_A_rows(
        key=key,
        start=0,
        stop=cols,
        lwe_secret_dim=lwe_secret_dim,
    )
