# Merkle Patricia Trie

Python implementation of [Merkle Patricia Trie](https://github.com/ethereum/wiki/wiki/Patricia-Tree) used in Ethereum and [Hyperledger Indy Plenum](https://github.com/hyperledger/indy-plenum).

Supports generating and verifying proof for keys present in the trie.

Most of the implementation is borrowed from [pyethereum](https://github.com/ethereum/pyethereum)
The API is little different from pyethereum though.

TODO:
-   Complete support for prefix nodes
-   Support proof of absence
-   Trie pruning
