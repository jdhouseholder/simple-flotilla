import tomllib


def load_cfg(path):
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    return cfg
