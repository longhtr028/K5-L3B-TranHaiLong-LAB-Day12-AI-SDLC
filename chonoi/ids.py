"""Sắp id và cấp id (Contract E): F2 đứng trước F10; id sinh tiếp sau hậu tố lớn nhất."""

import re

_TAIL = re.compile(r"^(.*?)([0-9]+)$")


def id_key(ident: str):
    """Khóa sắp: (tiền tố, hậu tố số hoặc -1, id gốc)."""
    m = _TAIL.match(ident)
    if m:
        return (m.group(1), int(m.group(2)), ident)
    return (ident, -1, ident)


def sort_by_id(items, key=lambda x: x["id"]):
    return sorted(items, key=lambda x: id_key(key(x)))


class IdAllocator:
    """Cấp id theo họ (prefix), nối tiếp hậu tố lớn nhất đã nạp, không cấp lại trong lượt."""

    def __init__(self):
        self._next = {}

    def reserve(self, ident: str):
        m = _TAIL.match(ident)
        if m:
            prefix, n = m.group(1), int(m.group(2))
            self._next[prefix] = max(self._next.get(prefix, 1), n + 1)

    def new(self, prefix: str) -> str:
        n = self._next.get(prefix, 1)
        self._next[prefix] = n + 1
        return f"{prefix}{n}"
