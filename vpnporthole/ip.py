from functools import reduce


class IPv4Address(object):
    def __init__(self, addr):
        if isinstance(addr, IPv4Address):
            self._raw = addr._raw
        elif isinstance(addr, str):
            self._raw = ip_to_int(addr)
        elif isinstance(addr, int):
            self._raw = addr
        else:
            raise ValueError('Can\'t convert "%s" to IPv4Address' % repr(addr))

    @property
    def int(self):
        return self._raw

    def __str__(self):
        return int_to_ip(self._raw)

    def __repr__(self):
        return '<IPv4Address %s>' % int_to_ip(self._raw)

    def __lt__(self, other):
        return self._raw < other._raw

    def __eq__(self, other):
        return self._raw == other._raw

    def __hash__(self):
        return hash(self.__repr__())


class IPv4Subnet(object):
    def __init__(self, cidr):
        if isinstance(cidr, self.__class__):
            self._ip = cidr._ip
            self._size = cidr._size
            return
        if '/' not in cidr:
            base, size = cidr, 32
        else:
            base, size = cidr.split('/', 1)
        self._size = int(size)
        base = self.__mask(IPv4Address(base).int, self._size)
        self._ip = IPv4Address(base)

    @staticmethod
    def __mask(addr, size):
        mask = 0xFFFFFFFF << (32 - size)
        assert isinstance(addr, int)
        return addr & mask

    def __contains__(self, other):
        if isinstance(other, self.__class__):
            if other._size < self._size:
                return False
            return self.__mask(other._ip.int, self._size) == self.__mask(self._ip.int, self._size)
        addr = IPv4Address(other)
        return self.__mask(addr.int, self._size) == self.__mask(self._ip.int, self._size)

    def __getitem__(self, item):
        i = int(item)
        if i >= 0:
            return IPv4Address(self._ip.int + i)
        else:
            mask = 0xFFFFFFFF >> (self._size)
            raw = self._ip.int | mask
            return IPv4Address(raw + i + 1)

    def __str__(self):
        return '%s/%s' % (self._ip, self._size)

    def __repr__(self):
        return '<IPv4Subnet %s>' % self.__str__()

    def __eq__(self, other):
        return self._ip.int == other._ip.int and self._size == other._size

    def __hash__(self):
        return hash(self.__repr__())


def ip_to_int(addr):
    fields = addr.split('.')
    assert len(fields) == 4
    assert all([int(x) >= 0 and int(x) <= 255 for x in fields])
    return reduce(lambda x, y: x * 0x100 + int(y), fields, 0)


def int_to_ip(raw):
    addr = []
    for _ in range(4):
        addr.append(str(raw % 0x100))
        raw //= 0x100

    assert raw == 0
    return '.'.join(reversed(addr))
