NIBBLE_TERMINATOR = 16

hex_to_int = {c: i for i, c in enumerate('0123456789abcdef')}

TT256 = 2 ** 256


(NODE_TYPE_BLANK, NODE_TYPE_LEAF, NODE_TYPE_EXTENSION,
 NODE_TYPE_BRANCH) = tuple(range(4))

BLANK_NODE = b''


