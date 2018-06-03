import random
import string


def random_string(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _
                   in range(size))
