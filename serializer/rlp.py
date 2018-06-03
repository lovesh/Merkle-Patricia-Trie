from typing import Tuple

from rlp import encode, decode

from serializer.serializer import Serializer, sha3_hash


class RLPSerializer(Serializer):
    @classmethod
    def serialize_node(cls, node):
        return encode(node)

    @classmethod
    def deserialize_to_node(cls, serz):
        return decode(serz)

    @classmethod
    def hash_node(cls, node) -> Tuple[bytes, bytes]:
        serz = cls.serialize_node(node)
        return sha3_hash(serz), serz
