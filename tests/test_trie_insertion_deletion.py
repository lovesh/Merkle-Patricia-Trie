from copy import deepcopy
from random import randint

import pytest

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
        assert trie.verify_proof_of_existence(root_hash, k, v, proof_nodes=proof)


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
        assert trie.verify_proof_of_existence(trie.root_hash, key, b'v3', proof_nodes=proof)

        assert b'v2' == trie.get(key, root_node=old_root2)
        assert b'v1' == trie.get(key, root_node=old_root1)

        _, proof = trie.get(key, root_node=old_root2, with_proof=True)
        proof.append(old_root2)
        assert trie.verify_proof_of_existence(old_root_hash2, key, b'v2', proof_nodes=proof)

        _, proof = trie.get(key, root_node=old_root1, with_proof=True)
        proof.append(old_root1)
        assert trie.verify_proof_of_existence(old_root_hash1, key, b'v1', proof_nodes=proof)


def test_non_existing_keys(ephem_trie):
    trie = ephem_trie
    trie.update(b'k1', b'v1')
    trie.update(b'k2', b'v2')
    trie.update(b'x3', b'v3')
    trie.update(b'y4', b'v4')
    trie.update(b'z3', b'v5')

    assert b'v1' == trie.get(b'k1')
    with pytest.raises(KeyError) as err:
        trie.get(b'k')

    old_root1 = deepcopy(trie.root_node)

    trie.update(b'k', b'v')
    assert b'v' == trie.get(b'k')

    with pytest.raises(KeyError) as err:
        trie.get(b'k', root_node=old_root1)

    with pytest.raises(KeyError) as err:
        trie.get(b'43')

    with pytest.raises(KeyError) as err:
        trie.get(b'pq1')

    with pytest.raises(KeyError) as err:
        trie.get(b'k11')

    with pytest.raises(KeyError) as err:
        trie.get(b'y44')

    trie.update(b'abcd1', b'x1')
    trie.update(b'abcd2', b'x2')
    trie.update(b'abcd3', b'x3')
    trie.update(b'abcd11', b'x4')
    trie.update(b'abcd12', b'x4')
    trie.update(b'abcd21', b'x5')
    trie.update(b'abcd1111', b'x6')
    trie.update(b'abcd11112', b'x7')

    with pytest.raises(KeyError) as err:
        trie.get(b'abcd')
    with pytest.raises(KeyError) as err:
        trie.get(b'abcd111')


def test_non_existing_keys_large(ephem_trie):
    trie = ephem_trie
    key_vals = {}
    for _ in range(10000):
        key_vals[random_string(randint(30, 50)).encode()] = random_string(
            randint(100, 1000)).encode()

    add_and_check_key_vals_to_trie(trie, key_vals)

    # Choose 1000 non existent keys
    non_existent_keys = set()
    while len(non_existent_keys) < 1000:
        k = random_string(randint(30, 50)).encode()
        if k not in key_vals:
            non_existent_keys.add(k)

    for k in non_existent_keys:
        with pytest.raises(KeyError) as err:
            trie.get(k)
