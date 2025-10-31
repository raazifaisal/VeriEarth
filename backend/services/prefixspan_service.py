"""
PrefixSpan service (unified)

Reference logic (provided) — kept here for parity of intent (not executed):

# -*- coding: utf-8 -*-
import re

class pyprefixspan:
    # init
    def __init__(self, pattern, minsup=2, len=1):
        self.minsup = minsup
        self.seq = pattern
        self.len = len
        self.out = {}

    def setlen(self, len=1):
        self.len = len
        print(self)

    def setminsup(self, minsup=2):
        self.minsup = minsup
        print(self)

    def extract(self, minsup, seq):
        h = dict()
        for i, item in enumerate(seq):
            dist = re.split(' +', item)
            for j in dist:
                if j in h:
                    h[j] += 1
                else:
                    h[j] = 1
        for k in list(h):
            # minsup
            if h[k] < minsup:
                del h[k]
        return h

    def projection(self, seq, b):
        h = []
        for i, item in enumerate(seq):
            list = re.split(' +', item)
            if b in list:
                dist = list[list.index(b)+1:]
                if len(dist) > 0:
                    h.append(" ".join(dist))
        return h

    def _prefixspan(self, prefix, seq):
        minsup = self.minsup;

        pattern = self.extract(minsup, seq)
        for key, value in pattern.items():
            p = prefix + " " + key

            count = len(re.findall(' +', p))
            # length
            if count >= self.len:
                p = p.strip()
                self.out.update({p:value})
            j = self.projection(seq, key)
            self._prefixspan(p, j);
        return

    def run(self):
        self._prefixspan("", self.seq)
        return

    def out(self, str):
        print(str)

This service implements a native miner following the same principles,
using token lists instead of space-joined strings and returning
support plus emission proxies per ANALYTICS_OPTIMIZATION_PLAN.md.
"""

from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

Token = str
Sequence = List[Token]

class PrefixSpanMiner:
    def __init__(self, sequences: List[Sequence], min_support: int, max_len: int = 5):
        self.sequences = sequences
        self.min_support = min_support
        self.max_len = max_len

    def mine(self) -> List[Tuple[Sequence, int]]:
        patterns: List[Tuple[Sequence, int]] = []
        self._prefixspan([], self.sequences, patterns)
        return patterns

    def _is_subsequence(self, pattern: Sequence, seq: Sequence) -> bool:
        i = 0
        for t in seq:
            if i < len(pattern) and t == pattern[i]:
                i += 1
                if i == len(pattern):
                    return True
        return False

    def _project_db(self, pattern: Sequence, sequences: List[Sequence]) -> List[Sequence]:
        projected: List[Sequence] = []
        for seq in sequences:
            # find indices where pattern occurs and return suffix after last match
            start = 0
            for tok in pattern:
                try:
                    idx = seq.index(tok, start)
                except ValueError:
                    idx = -1
                if idx < 0:
                    start = -1
                    break
                start = idx + 1
            if start >= 0 and start < len(seq):
                projected.append(seq[start:])
        return projected

    def _prefixspan(self, prefix: Sequence, sequences: List[Sequence], out: List[Tuple[Sequence, int]]):
        # Check max length first
        if len(prefix) >= self.max_len:
            # Record if valid before stopping
            if len(prefix) >= 3:
                sup = sum(1 for s in self.sequences if self._is_subsequence(prefix, s))
                if sup >= self.min_support:
                    out.append((prefix[:], sup))
            return
        
        # Record prefix if frequent and >= 3 tokens
        if prefix and len(prefix) >= 3:
            sup = sum(1 for s in self.sequences if self._is_subsequence(prefix, s))
            if sup >= self.min_support:
                out.append((prefix[:], sup))
            elif prefix:  # prune if not frequent
                return
        
        # frequent single tokens in projected DB
        freq: Dict[Token, int] = {}
        for s in sequences:
            seen = set()
            for t in s:
                if t in seen:
                    continue
                seen.add(t)
                freq[t] = freq.get(t, 0) + 1
        # extend with frequent tokens
        for t, sup in freq.items():
            if sup < self.min_support:
                continue
            new_prefix = prefix + [t]
            projected = self._project_db(new_prefix, self.sequences)
            self._prefixspan(new_prefix, projected, out)


def build_event_sequences(db: Session, org_id: str, limit: int = 5000) -> Tuple[List[Sequence], Dict[Tuple[str, str, str], float]]:
    """
    Build sequences per shipment as [origin_facility_id, transport_mode, destination_facility_id].
    Returns sequences and a map from (origin, mode, dest) -> accumulated total_emissions_kg_co2.
    """
    sql = text(
        """
        SELECT rt.origin_facility_id AS o, rt.destination_facility_id AS d, rt.transport_mode AS m,
               sh.total_emissions_kg_co2 AS emis
        FROM shipments sh
        JOIN routes rt ON rt.id = sh.route_id
        WHERE sh.organization_id = :org
        ORDER BY sh.shipment_date DESC
        LIMIT :lim
        """
    )
    rows = db.execute(sql, {"org": org_id, "lim": limit}).mappings().all()
    sequences: List[Sequence] = []
    leg_weight: Dict[Tuple[str, str, str], float] = {}
    for r in rows:
        o = (r["o"] or "").strip()
        d = (r["d"] or "").strip()
        m = (str(r["m"]) or "").strip()
        emis = float(r["emis"] or 0.0)
        if not o or not d or not m:
            continue
        seq: Sequence = [o, m, d]
        sequences.append(seq)
        # accumulate actual emissions (kg CO2) for this leg triplet
        key = (o, m, d)
        leg_weight[key] = leg_weight.get(key, 0.0) + emis
    return sequences, leg_weight


def score_patterns(patterns: List[Tuple[Sequence, int]], leg_weight: Dict[Tuple[str, str, str], float]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for seq, sup in patterns:
        emis_sum = 0.0
        legs = 0
        for i in range(len(seq) - 2):
            o, m, d = seq[i], seq[i+1], seq[i+2]
            w = leg_weight.get((o, m, d))
            if w is not None:
                emis_sum += w
                legs += 1
        emis_avg = (emis_sum / legs) if legs > 0 else None
        out.append({
            "pattern": seq,
            "support_count": sup,
            "emission_sum": round(emis_sum, 3),
            "emission_avg": round(emis_avg, 3) if emis_avg is not None else None,
        })
    out.sort(key=lambda x: (x["support_count"], x["emission_sum"]), reverse=True)
    return out
