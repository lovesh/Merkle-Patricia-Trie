from copy import deepcopy
from random import randint

from tests.helper import random_string
from trie.constants import NODE_TYPE_LEAF, BLANK_NODE, NODE_TYPE_EXTENSION, \
    NODE_TYPE_BRANCH
from trie.trie import Trie
from trie.utils import bin_to_nibbles


def test_get_prefix_nodes(ephem_trie):
    trie = ephem_trie
    prefix = 'abcd'
    prefix_nibbles = bin_to_nibbles(prefix)
    key1 = prefix + '1'
    key2 = prefix + '2'
    key3 = prefix + '3'
    trie.update(key1.encode(), b'v1')
    seen_prefix = []
    last_node = trie._get_last_node_for_prfx(trie.root_node, prefix_nibbles,
                                             seen_prfx=seen_prefix)
    # The last node should be a leaf since only 1 key
    assert trie._get_node_type(last_node) == NODE_TYPE_LEAF
    # Seen prefix matches the prefix exactly
    assert seen_prefix == []

    # The queried key is larger than prefix, results in blank node
    last_node_ = trie._get_last_node_for_prfx(trie.root_node,
                                              bin_to_nibbles(prefix + '5'), [])
    assert last_node_ == BLANK_NODE

    seen_prefix = []
    trie.update(key2.encode(), b'v2')
    last_node = trie._get_last_node_for_prfx(trie.root_node, prefix_nibbles,
                                             seen_prfx=seen_prefix)
    # The last node should be an extension since more than 1 key
    assert trie._get_node_type(last_node) == NODE_TYPE_EXTENSION
    assert seen_prefix == []

    seen_prefix = []
    trie.update(key3.encode(), b'v3')
    last_node = trie._get_last_node_for_prfx(trie.root_node, prefix_nibbles,
                                             seen_prfx=seen_prefix)
    assert trie._get_node_type(last_node) == NODE_TYPE_EXTENSION
    assert seen_prefix == []

    last_node_key = ephem_trie.key_nibbles_from_key_value_node(last_node)
    # Key for the fetched prefix nodes (ignore last nibble) is same as prefix nibbles
    assert last_node_key[:-1] == prefix_nibbles

    # The extension node is correctly decoded.
    decoded_extension = trie._decode_to_node(last_node[1])
    assert decoded_extension[1] == [b' ', b'v1']
    assert decoded_extension[2] == [b' ', b'v2']
    assert decoded_extension[3] == [b' ', b'v3']

    # Add keys with extended prefix
    extended_prefix = '1'
    key4 = prefix + extended_prefix + '85'
    trie.update(key4.encode(), b'v11')
    key5 = prefix + extended_prefix + '96'
    trie.update(key5.encode(), b'v21')
    seen_prefix = []
    new_prefix_nibbs = bin_to_nibbles(prefix + extended_prefix)
    last_node = trie._get_last_node_for_prfx(trie.root_node, new_prefix_nibbs,
                                             seen_prfx=seen_prefix)

    assert trie._get_node_type(last_node) == NODE_TYPE_BRANCH
    assert new_prefix_nibbs == seen_prefix
    assert seen_prefix == bin_to_nibbles(prefix + '1')

    # traverse to the next node
    remaining_key4_nibbs = bin_to_nibbles(key4)[len(seen_prefix):]
    remaining_key5_nibbs = bin_to_nibbles(key5)[len(seen_prefix):]
    next_nibble = remaining_key4_nibbs[0] if remaining_key4_nibbs[0] > remaining_key5_nibbs[0] else remaining_key5_nibbs[0]
    next_node = trie._decode_to_node(last_node[next_nibble])

    assert trie._get_node_type(next_node) == NODE_TYPE_BRANCH

    # The 8th index should lead to a node with key '5', key4 ended in '85'
    assert trie._get_node_type(next_node[8]) == NODE_TYPE_LEAF
    assert ephem_trie.key_nibbles_from_key_value_node(next_node[8]) == bin_to_nibbles('5')

    # The 9th index should lead to a node with key '6', key5 ended in '96'
    assert trie._get_node_type(next_node[9]) == NODE_TYPE_LEAF
    assert ephem_trie.key_nibbles_from_key_value_node(next_node[9]) == bin_to_nibbles('6')


def test_proof_prefix_only_prefix_nodes(ephem_trie):
    trie = ephem_trie
    prefix = 'abcdefgh'
    keys_suffices = set()
    while len(keys_suffices) != 20:
        keys_suffices.add(randint(25, 25000))

    key_vals = {'{}{}'.format(prefix, k): str(randint(3000, 5000))
                for k in keys_suffices}
    for k, v in key_vals.items():
        trie.update(k.encode(), v.encode())

    val, proof = trie.get_keys_with_prefix(prefix.encode(), with_proof=True)
    encoded = {k.encode(): v.encode() for k, v in key_vals.items()}
    # Check returned values match the actual values
    assert encoded == val
    proof.append(trie.root_node)
    assert Trie.verify_proof_of_existence_multi_keys(trie.root_hash, encoded,
                                                     proof)
    # Check without value
    _, proof = trie.get_keys_with_prefix(prefix.encode(), get_value=False, with_proof=True)
    proof.append(trie.root_node)
    assert Trie.verify_proof_of_existence_multi_keys(trie.root_hash, encoded, proof)


def test_proof_prefix_with_other_nodes(ephem_trie):
    trie = ephem_trie
    prefix = 'abcdefgh'

    other_nodes_count = 1000
    prefix_nodes_count = 100

    # Some nodes before prefix node
    others = {}
    for _ in range(other_nodes_count):
        k, v = random_string(randint(8, 19)).encode(), random_string(15).encode()
        others[k] = v
        trie.update(k, v)

    keys_suffices = set()
    while len(keys_suffices) != prefix_nodes_count:
        keys_suffices.add(randint(25, 250000))

    key_vals = {'{}{}'.format(prefix, k): str(randint(3000, 5000))
                for k in keys_suffices}
    for k, v in key_vals.items():
        trie.update(k.encode(), v.encode())

    # Some nodes after prefix node
    for _ in range(other_nodes_count):
        k, v = random_string(randint(8, 19)).encode(), random_string(15).encode()
        others[k] = v
        trie.update(k, v)

    val, proof = trie.get_keys_with_prefix(prefix.encode(), with_proof=True)
    encoded = {k.encode(): v.encode() for k, v in key_vals.items()}
    # Check returned values match the actual values
    assert encoded == val
    print(val)
    print(others)
    proof.append(trie.root_node)
    assert Trie.verify_proof_of_existence_multi_keys(trie.root_hash,
                                                     encoded, proof)
    # Check without value
    _, proof = trie.get_keys_with_prefix(prefix.encode(), get_value=False,
                                         with_proof=True)
    proof.append(trie.root_node)
    assert Trie.verify_proof_of_existence_multi_keys(trie.root_hash,
                                                     encoded, proof)

    # Change value of one of any random key
    encoded_new = deepcopy(encoded)
    random_key = next(iter(encoded_new.keys()))
    encoded_new[random_key] = encoded_new[random_key] + b'2212'
    assert not Trie.verify_proof_of_existence_multi_keys(trie.root_hash,
                                                         encoded_new, proof)


def test_proof_multiple_prefix_nodes(ephem_trie):
    trie = ephem_trie
    prefix_1 = 'abcdefgh'
    prefix_2 = 'abcdefxy'   # Prefix overlaps with previous
    prefix_3 = 'pqrstuvw'
    prefix_4 = 'mnoptuvw'   # Suffix overlaps

    all_prefixes = (prefix_1, prefix_2, prefix_3, prefix_4)

    other_nodes_count = 1000
    prefix_nodes_count = 100

    # Some nodes before prefix nodes
    for _ in range(other_nodes_count):
        k, v = random_string(randint(8, 19)).encode(), random_string(15).encode()
        trie.update(k, v)

    keys_suffices = set()
    while len(keys_suffices) != prefix_nodes_count:
        keys_suffices.add(randint(25, 250000))

    key_vals = {'{}{}'.format(prefix, k): str(randint(3000, 5000))
                for prefix in all_prefixes for k in keys_suffices}
    for k, v in key_vals.items():
        trie.update(k.encode(), v.encode())

    # Some nodes after prefix nodes
    for _ in range(other_nodes_count):
        trie.update(random_string(randint(8, 19)).encode(),
                    random_string(15).encode())

    for prefix in all_prefixes:
        val, proof = trie.get_keys_with_prefix(prefix.encode(), with_proof=True)
        encoded = {k.encode(): v.encode() for k, v in key_vals.items() if k.startswith(prefix)}
        # Check returned values match the actual values
        assert encoded == val
        proof.append(trie.root_node)
        assert Trie.verify_proof_of_existence_multi_keys(trie.root_hash,
                                                         encoded, proof)
        # Check without value
        _, proof = trie.get_keys_with_prefix(prefix.encode(), get_value=False,
                                             with_proof=True)
        proof.append(trie.root_node)
        assert Trie.verify_proof_of_existence_multi_keys(trie.root_hash,
                                                         encoded, proof)

        # Verify keys with a different prefix
        encoded = {k.encode(): v.encode() for k, v in key_vals.items() if
                   not k.startswith(prefix)}
        assert not Trie.verify_proof_of_existence_multi_keys(trie.root_hash,
                                                             encoded, proof)

