from functools import lru_cache

from eth_utils import big_endian_to_int

from trie.utils import str_to_bytes, encode_int, zpad


@lru_cache(128)
def add1(b):
    v = big_endian_to_int(b)
    return zpad(encode_int(v + 1), 4)


@lru_cache(128)
def sub1(b):
    v = big_endian_to_int(b)
    return zpad(encode_int(v - 1), 4)


class RefcountDB:
    def __init__(self, db):
        self.db = db
        self.kv = None

    def get(self, key):
        return self.db.get(key)[4:]

    def get_refcount(self, key):
        try:
            return big_endian_to_int(self.db.get(key)[:4])
        except KeyError:
            return 0

    def put(self, key, value):
        try:
            existing = self.db.get(key)
            assert existing[4:] == value
            self.db.put(key, add1(existing[:4]) + value)
            # print('putin', key, utils.big_endian_to_int(existing[:4]) + 1)
        except KeyError:
            self.db.put(key, b'\x00\x00\x00\x01' + value)
            # print('putin', key, 1)

    def delete(self, key):
        existing = self.db.get(key)
        if existing[:4] == b'\x00\x00\x00\x01':
            # print('deletung')
            self.db.delete(key)
        else:
            # print(repr(existing[:4]))
            self.db.put(key, sub1(existing[:4]) + existing[4:])

    def commit(self):
        pass

    def _has_key(self, key):
        return key in self.db

    def __contains__(self, key):
        return self._has_key(key)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.db == other.db

    def __hash__(self):
        return big_endian_to_int(str_to_bytes(self.__repr__()))
