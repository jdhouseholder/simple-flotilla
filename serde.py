import numpy as np


def uint64_ndarray_to_bytes(arr: np.ndarray) -> bytes:
    arr_big_endian = arr.astype(">u8")
    return arr_big_endian.tobytes()


def uint64_ndarray_from_bytes(b: bytes) -> np.ndarray:
    dtype_big_endian = np.dtype(">u8")
    arr = np.frombuffer(b, dtype=dtype_big_endian)
    return arr.astype("=u8", copy=False)


def uint32_ndarray_to_bytes(arr: np.ndarray) -> bytes:
    arr_big_endian = arr.astype(">u4")
    return arr_big_endian.tobytes()


def uint32_ndarray_from_bytes(b: bytes) -> np.ndarray:
    dtype_big_endian = np.dtype(">u4")
    arr = np.frombuffer(b, dtype=dtype_big_endian)
    return arr.astype("=u4", copy=False)
