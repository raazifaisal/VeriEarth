# -*- coding: utf-8 -*-
import re
from typing import Dict, List

class pyprefixspan:
    def __init__(self, pattern: List[str], minsup: int = 2, length: int = 1):
        self.minsup = minsup
        self.seq = pattern
        self.length = length
        self.out: Dict[str, int] = {}

    def setlen(self, length: int = 1):
        self.length = length

    def setminsup(self, minsup: int = 2):
        self.minsup = minsup

    def extract(self, minsup: int, seq: List[str]) -> Dict[str, int]:
        h: Dict[str, int] = {}
        for item in seq:
            dist = re.split(' +', item)
            for j in dist:
                if j in h:
                    h[j] += 1
                else:
                    h[j] = 1
        for k in list(h):
            if h[k] < minsup:
                del h[k]
        return h

    def projection(self, seq: List[str], b: str) -> List[str]:
        h: List[str] = []
        for item in seq:
            lst = re.split(' +', item)
            if b in lst:
                dist = lst[lst.index(b)+1:]
                if len(dist) > 0:
                    h.append(" ".join(dist))
        return h

    def _prefixspan(self, prefix: str, seq: List[str]):
        minsup = self.minsup
        pattern = self.extract(minsup, seq)
        for key, value in pattern.items():
            p = (prefix + " " + key).strip()
            count = len(re.findall(' +', p))
            if count >= self.length:
                self.out[p] = value
            j = self.projection(seq, key)
            self._prefixspan(p, j)

    def run(self) -> Dict[str, int]:
        self.out = {}
        self._prefixspan("", self.seq)
        return self.out
