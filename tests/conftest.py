import pytest

from storage.ephem_db import EphemDB
from trie.trie import Trie


@pytest.fixture(scope='function')
def tempdir(tmpdir_factory):
    return tmpdir_factory.mktemp('').strpath


@pytest.fixture(scope='function')
def ephem_trie():
    return Trie(EphemDB())
