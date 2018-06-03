from trie.utils import str_to_bytes

try:
    from hashlib import sha3_256
except ImportError:
    import sha3
    sha3_256 = sha3.sha3_256


def sha3_hash(v):
    return sha3_256(str_to_bytes(v)).digest()


class Serializer:
    @classmethod
    def serialize_node(cls, node):
        pass

    @classmethod
    def deserialize_to_node(cls, serz):
        pass

    @classmethod
    def hash_node(cls, node):
        pass
