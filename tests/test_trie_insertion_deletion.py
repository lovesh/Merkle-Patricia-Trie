from copy import deepcopy
from random import randint

from tests.helper import random_string


def add_and_check_key_vals_to_trie(trie, key_vals):
    for k, v in key_vals.items():
        trie.update(k, v)

    root_hash = trie.root_hash
    root_node = trie.root_node

    for k, v in key_vals.items():
        assert v == trie.get(k)
        v, proof = trie.get(k, with_proof=True)
        proof.append(root_node)
        assert trie.verify_proof(root_hash, k, v, proof_nodes=proof)


def test_update_get_from_trie_small(ephem_trie):
    trie = ephem_trie

    key_vals = dict([
        (b'91', b'v1'),
        (b'92', b'v2'),
        (b'93', b'v3'),
        (b'94', b'v4'),
        (b'95', b'v5'),
        (b'911', b'v11'),
        (b'922', b'v22'),
        (b'9123', b'v123'),
        (b'abacew1212nnnnnkasassw', b'dsdu2b s212121212 dssd dsd')
    ])

    add_and_check_key_vals_to_trie(trie, key_vals)


def test_update_get_from_trie_large(ephem_trie):
    trie = ephem_trie
    key_vals = {}
    for _ in range(10000):
        key_vals[random_string(randint(30, 50)).encode()] = random_string(randint(100, 1000)).encode()

    add_and_check_key_vals_to_trie(trie, key_vals)


def test_update_get_different_roots(ephem_trie):
    trie = ephem_trie
    for key in [b'k1', b'k2212', b'xq1212', b'abfsbas83220samnopervf1294605', b'92912sqwopalkc4901']:
        trie.update(key, b'v1')
        assert b'v1' == trie.get(key)
        old_root1 = deepcopy(trie.root_node)
        old_root_hash1 = trie.root_hash

        trie.update(key, b'v2')
        assert b'v2' == trie.get(key)
        old_root2 = deepcopy(trie.root_node)
        old_root_hash2 = trie.root_hash

        trie.update(key, b'v3')
        assert b'v3' == trie.get(key)
        _, proof = trie.get(key, with_proof=True)
        proof.append(deepcopy(trie.root_node))
        assert trie.verify_proof(trie.root_hash, key, b'v3', proof_nodes=proof)

        assert b'v2' == trie.get(key, root_node=old_root2)
        assert b'v1' == trie.get(key, root_node=old_root1)

        _, proof = trie.get(key, root_node=old_root2, with_proof=True)
        proof.append(old_root2)
        assert trie.verify_proof(old_root_hash2, key, b'v2', proof_nodes=proof)

        _, proof = trie.get(key, root_node=old_root1, with_proof=True)
        proof.append(old_root1)
        assert trie.verify_proof(old_root_hash1, key, b'v1', proof_nodes=proof)
