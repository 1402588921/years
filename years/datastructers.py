from collections.abc import Mapping


class Hearders(Mapping):
    def __init__(self, hearders: list):
        self._headers = hearders

    def __getitem__(self, key: str):
        for hearder_key, hearder_value in self._headers:
            if hearder_key.decode("latin-1").lower() == key.lower():
                return hearder_value.decode("latin-1").lower()
        raise KeyError(f"Headers 中不存在{key.lower()}")

    def __len__(self):
        return len(self._headers)

    def __iter__(self):
        for key, _ in self._headers:
            yield key.decode("latin-1")

    def dump(self):
        return dict(self)
