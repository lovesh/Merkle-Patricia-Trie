import binascii

from eth_utils import int_to_big_endian
from rlp.utils import ALL_BYTES

from trie.constants import NIBBLE_TERMINATOR, hex_to_int, TT256


def ascii_chr(n):
    return ALL_BYTES[n]


def decode_hex(s):
    if isinstance(s, str):
        return bytes.fromhex(s)
    if isinstance(s, bytes):
        return binascii.unhexlify(s)
    raise TypeError('Value must be an instance of str or bytes')


def encode_hex(b):
    if isinstance(b, str):
        b = bytes(b, 'utf-8')
    if isinstance(b, bytes):
        return str(binascii.hexlify(b), 'utf-8')
    raise TypeError('Value must be an instance of str or bytes')


def encode_int(v):
    """encodes an integer into serialization"""
    if not isinstance(v, int) or v < 0 or v >= TT256:
        raise Exception("Integer invalid or out of range: %r" % v)
    return int_to_big_endian(v)


def bin_to_nibbles(s):
    """convert string s to nibbles (half-bytes)
    >>> bin_to_nibbles("")
    []
    >>> bin_to_nibbles("h")
    [6, 8]
    >>> bin_to_nibbles("he")
    [6, 8, 6, 5]
    >>> bin_to_nibbles("hello")
    [6, 8, 6, 5, 6, 12, 6, 12, 6, 15]
    """
    return [hex_to_int[c] for c in encode_hex(s)]


def nibbles_to_bin(nibbles):
    if any(x > 15 or x < 0 for x in nibbles):
        raise Exception("nibbles can only be [0,..15]")

    if len(nibbles) % 2:
        raise Exception("nibbles must be of even numbers")

    res = b''
    for i in range(0, len(nibbles), 2):
        res += ascii_chr(16 * nibbles[i] + nibbles[i + 1])
    return res


def with_terminator(nibbles):
    nibbles = nibbles[:]
    if not nibbles or nibbles[-1] != NIBBLE_TERMINATOR:
        nibbles.append(NIBBLE_TERMINATOR)
    return nibbles


def without_terminator(nibbles):
    nibbles = nibbles[:]
    if nibbles and nibbles[-1] == NIBBLE_TERMINATOR:
        del nibbles[-1]
    return nibbles


def adapt_terminator(nibbles, has_terminator):
    if has_terminator:
        return with_terminator(nibbles)
    else:
        return without_terminator(nibbles)


def without_terminator_and_flags(nibbles):
    nibbles = nibbles[:]
    if nibbles and nibbles[-1] == NIBBLE_TERMINATOR:
        del nibbles[-1]
    if len(nibbles) % 2:
        del nibbles[0]
    return nibbles


def pack_nibbles(nibbles):
    """pack nibbles to binary
    :param nibbles: a nibbles sequence. may have a terminator
    """

    """
    hex char    bits    |    node type partial     path length
    ----------------------------------------------------------
       0        0000    |       extension              even        
       1        0001    |       extension              odd         
       2        0010    |   terminating (leaf)         even        
       3        0011    |   terminating (leaf)         odd    
    """

    if nibbles[-1] == NIBBLE_TERMINATOR:
        flags = 2
        nibbles = nibbles[:-1]
    else:
        flags = 0

    oddlen = len(nibbles) % 2
    flags |= oddlen  # set lowest bit if odd number of nibbles
    if oddlen:
        nibbles = [flags] + nibbles
    else:
        nibbles = [flags, 0] + nibbles
    o = b''
    for i in range(0, len(nibbles), 2):
        o += ascii_chr(16 * nibbles[i] + nibbles[i + 1])
    return o


def unpack_to_nibbles(bindata):
    """unpack packed binary data to nibbles
    :param bindata: binary packed from nibbles
    :return: nibbles sequence, may have a terminator
    """
    o = bin_to_nibbles(bindata)
    flags = o[0]
    if flags & 2:
        o.append(NIBBLE_TERMINATOR)
    if flags & 1 == 1:
        o = o[1:]
    else:
        o = o[2:]
    return o


def str_to_bytes(v):
    if isinstance(v, bytes):
        return v
    if isinstance(v, bytearray):
        return bytes(v)
    if isinstance(v, str):
        return v.encode()


def is_bytes(v):
    return isinstance(v, bytes)


def nibble_to_bytes(nibble):
    return str(nibble).encode()


def starts_with(full, part) -> bool:
    """ return True if part is prefix of full
    """
    if len(full) < len(part):
        return False
    return full[:len(part)] == part


def zpad(x, l):
    """ Left zero pad value `x` at least to length `l`.
    >>> zpad('', 1)
    '\x00'
    >>> zpad('\xca\xfe', 4)
    '\x00\x00\xca\xfe'
    >>> zpad('\xff', 1)
    '\xff'
    >>> zpad('\xca\xfe', 2)
    '\xca\xfe'
    """
    return b'\x00' * max(0, l - len(x)) + x