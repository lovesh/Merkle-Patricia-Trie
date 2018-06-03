from copy import deepcopy

from serializer.rlp import RLPSerializer
from serializer.serializer import sha3_hash
from storage.ephem_db import EphemDB
from trie.constants import BLANK_NODE, NODE_TYPE_BLANK, NODE_TYPE_LEAF, \
    NODE_TYPE_EXTENSION, NODE_TYPE_BRANCH, NIBBLE_TERMINATOR
from trie.utils import without_terminator, unpack_to_nibbles, str_to_bytes, \
    bin_to_nibbles, is_bytes, nibbles_to_bin, nibble_to_bytes, pack_nibbles, \
    with_terminator, starts_with


class Trie:
    def __init__(self, db, root_hash=None, node_serializer=RLPSerializer):
        """it also present a dictionary like interface
        :param db key value database
        :root: blank or trie node in form of [key, value] or [v0,v1..v15,v]
        """
        self.db = db  # Pass in a database object directly
        self.node_serializer = node_serializer
        self.BLANK_ROOT = self.node_serializer.hash_node(BLANK_NODE)
        self.set_root_hash(root_hash)

        self.deletes = []

    @property
    def root_hash(self):
        """always empty or a 32 bytes string
        """
        return self._root_hash

    def get_root_hash(self):
        return self._root_hash

    def _update_root_hash(self):
        key, val = self.node_serializer.hash_node(self.root_node)
        self.db.put(key, val)
        self._root_hash = key

    @root_hash.setter
    def root_hash(self, value):
        self.set_root_hash(value)

    def set_root_hash(self, root_hash=None):
        if root_hash is None:
            self.root_node = BLANK_NODE
            self._root_hash = self.BLANK_ROOT
            return
        assert is_bytes(root_hash)
        assert len(root_hash) in [0, 32]
        self.root_node = self._decode_to_node(root_hash)
        self._root_hash = root_hash

    def get(self, key, root_node=None, with_proof=False):
        root_node = root_node or self.root_node
        proof_nodes = [] if with_proof else None
        val = self._get(root_node, self.key_to_nibbles(key), proof_nodes=proof_nodes)
        if with_proof:
            return val, proof_nodes
        else:
            return val

    def get_node_for_prefix(self, key, root_node=None, with_proof=False):
        # TODO:
        pass

    def update(self, key, value):
        """
        :param key: a string
        :value: a string
        """
        if not is_bytes(key):
            raise Exception("Key must be string")

        if not is_bytes(value):
            raise Exception("Value must be string")

        # if value == '':
        #     return self.delete(key)
        self.root_node = self._update_and_delete_storage(
            self.root_node,
            self.key_to_nibbles(key),
            self.value_to_bytes(value))

        self._update_root_hash()

    def delete(self, key):
        """
        :param key: a string with length of [0, 32]
        """
        if not is_bytes(key):
            raise Exception("Key must be string")

        if len(key) > 32:
            raise Exception("Max key length is 32")

        self.root_node = self._delete_and_delete_storage(
            self.root_node, self.key_to_nibbles(key))

        self._update_root_hash()

    def clear(self):
        """ clear all tree data
        """
        self._delete_child_storage(self.root_node)
        self._delete_node_storage(self.root_node)
        self.root_node = BLANK_NODE
        self._root_hash = self.BLANK_ROOT

    def _get(self, node, key, proof_nodes=None):
        """ get value inside a node
        :param node: node in form of list, or BLANK_NODE
        :param key: nibble list without terminator
        :return:
            KeyError if does not exist, otherwise value or hash
        """
        node_type = self._get_node_type(node)

        if node_type == NODE_TYPE_BLANK:
            return BLANK_NODE

        if node_type == NODE_TYPE_BRANCH:
            # already reach the expected node
            if not key:
                return node[-1]
            sub_node = self._decode_to_node(node[key[0]])
            if sub_node == BLANK_NODE and key:
                # TODO: Add proof to exception
                raise KeyError
            self._update_proof_nodes(node[key[0]], sub_node, proof_nodes=proof_nodes)
            return self._get(sub_node, key[1:], proof_nodes)

        # key value node
        curr_key = self.key_nibbles_from_key_value_node(node)
        if node_type == NODE_TYPE_LEAF:
            if key == curr_key:
                return node[1]
            else:
                # TODO: Add proof to exception
                raise KeyError

        if node_type == NODE_TYPE_EXTENSION:
            # traverse child nodes
            if starts_with(key, curr_key):
                sub_node = self._get_inner_node_from_extension(node)
                if sub_node == BLANK_NODE and key[len(curr_key):]:
                    # TODO: Add proof to exception
                    raise KeyError
                self._update_proof_nodes(node[1], sub_node,
                                         proof_nodes=proof_nodes)
                return self._get(sub_node, key[len(curr_key):], proof_nodes)
            else:
                # TODO: Add proof to exception
                raise KeyError

    def _update(self, node, key, value):
        """ update item inside a node
        :param node: node in form of list, or BLANK_NODE
        :param key: nibble list without terminator
            .. note:: key may be []
        :param value: value string
        :return: new node
        if this node is changed to a new node, it's parent will take the
        responsibility to *store* the new node storage, and delete the old
        node storage
        """
        node_type = self._get_node_type(node)

        if node_type == NODE_TYPE_BLANK:
            return [self.key_nibbles_to_bytes(key, add_terminator=True), value]

        elif node_type == NODE_TYPE_BRANCH:
            if not key:
                node[-1] = value
            else:
                new_node = self._update_and_delete_storage(
                    self._decode_to_node(node[key[0]]),
                    key[1:], value)
                node[key[0]] = self._encode_node(new_node)
            return node

        elif self.is_key_value_type(node_type):
            return self._update_kv_node(node, key, value)

    def _update_and_delete_storage(self, node, key, value):
        old_node = node[:]
        new_node = self._update(node, key, value)
        if old_node != new_node:
            self._delete_node_storage(old_node)
        return new_node

    def _update_kv_node(self, node, key, value):
        node_type = self._get_node_type(node)
        curr_key = self.key_nibbles_from_key_value_node(node)
        is_extension_node = node_type == NODE_TYPE_EXTENSION

        # find longest common prefix
        prefix_length = 0
        for i in range(min(len(curr_key), len(key))):
            if key[i] != curr_key[i]:
                break
            prefix_length = i + 1

        remain_key = key[prefix_length:]
        remain_curr_key = curr_key[prefix_length:]

        if remain_key == [] == remain_curr_key:
            if not is_extension_node:
                return [node[0], value]
            new_node = self._update_and_delete_storage(
                self._get_inner_node_from_extension(node), remain_key, value)

        elif not remain_curr_key:
            if is_extension_node:
                new_node = self._update_and_delete_storage(
                    self._get_inner_node_from_extension(node),
                    remain_key, value)
            else:
                new_node = [BLANK_NODE] * 17
                new_node[-1] = node[1]
                new_node[remain_key[0]] = self._store_leaf_node(remain_key[1:],
                                                                value)
        else:
            new_node = [BLANK_NODE] * 17
            if len(remain_curr_key) == 1 and is_extension_node:
                new_node[remain_curr_key[0]] = node[1]
            else:
                if is_extension_node:
                    new_node[remain_curr_key[0]] = self._store_extension_node(
                        remain_curr_key[1:], node[1])
                else:
                    new_node[remain_curr_key[0]] = self._store_leaf_node(
                        remain_curr_key[1:], node[1])

            if not remain_key:
                new_node[-1] = value
            else:
                new_node[remain_key[0]] = self._store_leaf_node(remain_key[1:], value)

        if prefix_length:
            # create node for key prefix
            return [self.key_nibbles_to_bytes(curr_key[:prefix_length]),
                    self._encode_node(new_node)]
        else:
            return new_node

    def _to_dict(self, node):
        """convert (key, value) stored in this and the descendant nodes
        to dict items.
        :param node: node in form of list, or BLANK_NODE
        .. note::
            Here key is in full form, rather than key of the individual node
        """
        if node == BLANK_NODE:
            return {}

        node_type = self._get_node_type(node)

        if self.is_key_value_type(node_type):
            nibbles = self.key_nibbles_from_key_value_node(node)
            key = b'+'.join([nibble_to_bytes(x) for x in nibbles])
            if node_type == NODE_TYPE_EXTENSION:
                sub_dict = self._to_dict(self._get_inner_node_from_extension(node))
            else:
                sub_dict = {nibble_to_bytes(NIBBLE_TERMINATOR): node[1]}

            # prepend key of this node to the keys of children
            res = {}
            for sub_key, sub_value in sub_dict.items():
                full_key = (key + b'+' + sub_key).strip(b'+')
                res[full_key] = sub_value
            return res

        elif node_type == NODE_TYPE_BRANCH:
            res = {}
            for i in range(16):
                sub_dict = self._to_dict(self._decode_to_node(node[i]))

                for sub_key, sub_value in sub_dict.items():
                    full_key = (
                            str_to_bytes(
                                str(i)) +
                            b'+' +
                            sub_key).strip(b'+')
                    res[full_key] = sub_value

            if node[16]:
                res[nibble_to_bytes(NIBBLE_TERMINATOR)] = node[-1]
            return res

    def to_dict(self):
        d = self._to_dict(self.root_node)
        res = {}
        for key_str, value in d.items():
            if key_str:
                nibbles = [int(x) for x in key_str.split(b'+')]
            else:
                nibbles = []
            key = nibbles_to_bin(without_terminator(nibbles))
            res[key] = value
        return res

    def _encode_node(self, node, put_in_db=True):
        if node == BLANK_NODE:
            return BLANK_NODE

        encoded = self.node_serializer.serialize_node(node)
        if len(encoded) < 32:
            return node

        hashkey = sha3_hash(encoded)
        if put_in_db:
            self.db.put(hashkey, encoded)
        return hashkey

    def _decode_to_node(self, encoded):
        if encoded == BLANK_NODE:
            return BLANK_NODE
        if isinstance(encoded, list):
            return encoded
        o = self.node_serializer.deserialize_to_node(self.db.get(encoded))
        return o

    def _delete_child_storage(self, node):
        node_type = self._get_node_type(node)
        if node_type == NODE_TYPE_BRANCH:
            for item in node[:16]:
                self._delete_child_storage(self._decode_to_node(item))
        elif node_type == NODE_TYPE_EXTENSION:
            self._delete_child_storage(self._get_inner_node_from_extension(
                node))

    def _delete_node_storage(self, node):
        """delete storage
        :param node: node in form of list, or BLANK_NODE
        """
        if node == BLANK_NODE:
            return
        # assert isinstance(node, list)
        encoded = self._encode_node(node, put_in_db=False)
        if len(encoded) < 32:
            return
        """
        ===== FIXME ====
        in the current trie implementation two nodes can share identical subtrees
        thus we can not safely delete nodes for now
        """
        self.deletes.append(encoded)

    def _get_inner_node_from_extension(self, node):
        return self._decode_to_node(node[1])

    def _store_leaf_node(self, key, value):
        k = self.key_nibbles_to_bytes(key, add_terminator=True)
        return self._encode_node([k, value])

    def _store_extension_node(self, key, value):
        k = self.key_nibbles_to_bytes(key, remove_terminator=True)
        return self._encode_node([k, value])

    @staticmethod
    def _update_proof_nodes(existing_node, new_node, proof_nodes=None):
        if isinstance(proof_nodes, list) and existing_node != BLANK_NODE and \
                not isinstance(existing_node, list):
            proof_nodes.append(deepcopy(new_node))

    @staticmethod
    def verify_proof_of_existence(root, key, value, proof_nodes):
        # Checks that `key` exists with `value` in the trie
        # NOTE: `root` is a derivative of the last element of `proof_nodes`
        # but it's important to keep `root` as a separate as signed root
        # hashes will be published.

        new_trie = Trie.get_new_trie_with_proof_nodes(proof_nodes)

        try:
            new_trie.root_hash = root
            v = new_trie.get(key)
            return v == value
        except Exception as e:
            print(e)
        return False

    @staticmethod
    def get_new_trie_with_proof_nodes(proof_nodes,
                                      node_serializer=RLPSerializer):
        new_trie = Trie(EphemDB())

        for node in proof_nodes:
            H, R = node_serializer.hash_node(node)
            new_trie.db.put(H, R)

        return new_trie

    @staticmethod
    def _get_node_type(node):
        """ get node type and content
        :param node: node in form of list, or BLANK_NODE
        :return: node type
        """
        if node == BLANK_NODE:
            return NODE_TYPE_BLANK
        if len(node) == 2:
            nibbles = unpack_to_nibbles(node[0])
            has_terminator = (nibbles and nibbles[-1] == NIBBLE_TERMINATOR)
            return NODE_TYPE_LEAF if has_terminator \
                else NODE_TYPE_EXTENSION
        if len(node) == 17:
            return NODE_TYPE_BRANCH

    @staticmethod
    def is_key_value_type(node_type):
        return node_type in [NODE_TYPE_LEAF, NODE_TYPE_EXTENSION]

    @staticmethod
    def key_nibbles_from_key_value_node(node):
        return without_terminator(unpack_to_nibbles(node[0]))

    @staticmethod
    def key_to_nibbles(key):
        return bin_to_nibbles(str_to_bytes(key))

    @staticmethod
    def key_nibbles_to_bytes(key, add_terminator=None, remove_terminator=None):
        if add_terminator and remove_terminator:
            raise ValueError('Both with_terminator and without_terminator cannot be true')
        if add_terminator:
            return pack_nibbles(with_terminator(key))
        if remove_terminator:
            return pack_nibbles(without_terminator(key))
        return pack_nibbles(key)

    @staticmethod
    def value_to_bytes(value):
        if isinstance(value, int):
            return str(value).encode()
        return str_to_bytes(value)
