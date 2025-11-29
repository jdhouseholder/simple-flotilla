import httpx


class FlotillaApiClient:
    def __init__(self, base_url: str):
        self.offline_info = None
        self.base_url = base_url

    async def setup(self):
        async with httpx.AsyncClient() as client:
            # TODO: fetch Out Of Band data
            r = await client.get(self.base_url + "/out-of-band")

            # TODO: fetch offline data
            r = await client.get(self.base_url + "/offline")

    def get_offline_info(self):
        return self.offline_info

    async def answer(self, query: np.ndarray) -> np.ndarray:
        data = {
            "query": "",
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(self.base_url + "/answer", data=data)
