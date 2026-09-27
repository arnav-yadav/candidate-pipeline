"""
RESOLVE: decide which applications belong to the same person, and which tracker row records
the recruiter's handling of which application.

The chosen matching rule (see docs/data_model.md#identity-resolution for the evidence):

    merge automatically  <=>  same normalised email
                          OR  same normalised phone AND both names known AND compatible
    send to review queue <=>  same phone, but one side has no name (a nameless WhatsApp message)

Phone alone is not enough: siblings share a phone, and referrers type their own number.
Name alone is not enough: common names collide and name formats differ by channel.
Nameless phone matches are not merged automatically: on a shared phone they would silently fold
one sibling's application into the other's -- the incorrect merge Assignment 1's guardrail forbids.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from .normalize import names_compatible


class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if rb < ra:
                ra, rb = rb, ra
            self.parent[rb] = ra


# ---------------------------------------------------------------- tracker -> application links
def link_tracker(tracker: pd.DataFrame, apps: pd.DataFrame, cfg) -> pd.DataFrame:
    """Every tracker row gets application_id + link_method.
    ref       - auto-imported rows carry the source ID (job board, careers page)
    identity  - manual rows: same channel, same phone or email, logged 0-N days after applying
    tracker_only - nothing in any source system (walk-ins, or a row nobody can trace): becomes its own application
    """
    max_days = cfg["matching"]["tracker_link_max_days"]
    t = tracker.copy()
    t["application_id"], t["link_method"] = None, None
    by_ref = {(r.source, r.source_record_id): r.application_id for r in apps.itertuples()}
    for i, r in t.iterrows():
        if r["ref"] and r["channel"] in ("job_board", "careers"):
            aid = by_ref.get((r["channel"], r["ref"]))
            if aid:
                t.at[i, "application_id"], t.at[i, "link_method"] = aid, "ref"

    taken = set(t.loc[t["link_method"].eq("ref"), "application_id"])
    pool = apps[apps["is_valid"]].copy()
    for i, r in t[t["link_method"].isna() & t["is_valid"]].sort_values("row").iterrows():
        cand = pool[(pool["source"] == r["channel"]) & ~pool["application_id"].isin(taken)]
        ident = pd.Series(False, index=cand.index)
        if r["phone_norm"]:
            ident |= cand["phone_norm"].eq(r["phone_norm"])
        if r["email_norm"]:
            ident |= cand["email_norm"].eq(r["email_norm"])
        cand = cand[ident]
        lag = pd.Series([(r["logged_on"] - d).days for d in cand["applied_date"]], index=cand.index)
        cand = cand[(lag >= 0) & (lag <= max_days)]
        if len(cand):
            best = cand.assign(lag=lag[cand.index]).sort_values(["lag", "application_id"]).index[0]
            aid = cand.at[best, "application_id"]
            t.at[i, "application_id"], t.at[i, "link_method"] = aid, "identity"
            taken.add(aid)

    # third pass: identifiers missing on one side (referral forms often lack the candidate's email);
    # link on a compatible name only when exactly one application in the window fits
    for i, r in t[t["link_method"].isna() & t["is_valid"] & t["first_name"].notna()].sort_values("row").iterrows():
        cand = pool[(pool["source"] == r["channel"]) & ~pool["application_id"].isin(taken)]
        lag = pd.Series([(r["logged_on"] - d).days for d in cand["applied_date"]], index=cand.index)
        cand = cand[(lag >= 0) & (lag <= max_days)]
        fits = [j for j in cand.index if names_compatible(r["first_name"], r["last_name"],
                                                           cand.at[j, "first_name"], cand.at[j, "last_name"]) is True]
        if len(fits) == 1:
            aid = cand.at[fits[0], "application_id"]
            t.at[i, "application_id"], t.at[i, "link_method"] = aid, "name_in_window"
            taken.add(aid)

    orphan = t["link_method"].isna() & t["is_valid"]
    t.loc[orphan, "application_id"] = "tracker:" + t.loc[orphan, "row"].astype(str)
    t.loc[orphan, "link_method"] = "tracker_only"
    t.loc[orphan, "warning_reasons"] = t.loc[orphan, "warning_reasons"].map(lambda s: f"{s};T08" if s else "T08")
    return t


def tracker_only_applications(tracker: pd.DataFrame) -> pd.DataFrame:
    """Rows that exist only in the tracker (walk-ins, untraceable manual rows) are applications too."""
    o = tracker[tracker["link_method"].eq("tracker_only")]
    return pd.DataFrame({
        "source": o["channel"].where(o["channel"].eq("walk_in"), "tracker_only"),
        "source_record_id": "row" + o["row"].astype(str), "application_id": o["application_id"],
        "applied_at": pd.to_datetime(o["logged_on"]), "applied_date": o["logged_on"],
        "name_raw": o["name_raw"], "email_raw": o["email_raw"], "phone_raw": o["phone_raw"], "context": "{}",
        "first_name": o["first_name"], "last_name": o["last_name"], "email_norm": o["email_norm"],
        "phone_norm": o["phone_norm"], "failure_reasons": "", "warning_reasons": "", "is_valid": True})


# ---------------------------------------------------------------- matching rules
def _edges(apps: pd.DataFrame, rule: str):
    """Yield (a, b, reason) edges between applications under a named rule. Blocking keys keep this linear-ish."""
    cols = ["application_id", "first_name", "last_name", "email_norm", "phone_norm"]
    clean = apps[cols].astype(object).where(apps[cols].notna(), None)     # NaN is truthy: never let it act as a key
    rows = [{k: (v if v != "" else None) for k, v in r.items()} for r in clean.to_dict("records")]
    def pairs(key):
        groups = {}
        for r in rows:
            if r[key]:
                groups.setdefault(r[key], []).append(r)
        for g in groups.values():
            for a, b in zip(g, g[1:]):             # chain within a block is enough for union-find
                yield a, b
    if rule in ("email_only", "email_or_phone", "chosen", "chosen_plus_unverified"):
        for a, b in pairs("email_norm"):
            yield a["application_id"], b["application_id"], "email"
    if rule in ("phone_only", "email_or_phone"):
        for a, b in pairs("phone_norm"):
            yield a["application_id"], b["application_id"], "phone"
    if rule in ("chosen", "chosen_plus_unverified"):
        groups = {}
        for r in rows:
            if r["phone_norm"]:
                groups.setdefault(r["phone_norm"], []).append(r)
        for g in groups.values():                   # all pairs: compatibility is not transitive
            known = sorted({r["first_name"] for r in g if r["first_name"]})
            contested = any(names_compatible(x, None, y, None) is False for k, x in enumerate(known) for y in known[k + 1:])
            for i in range(len(g)):
                for j in range(i + 1, len(g)):
                    ok = names_compatible(g[i]["first_name"], g[i]["last_name"], g[j]["first_name"], g[j]["last_name"])
                    if ok is True:
                        yield g[i]["application_id"], g[j]["application_id"], "phone+name"
                    elif ok is None and not contested and rule == "chosen_plus_unverified":
                        # upper-bound variant only: a nameless record joins a phone that looks single-owner
                        yield g[i]["application_id"], g[j]["application_id"], "phone,name_unknown"
    if rule == "name_only":
        for r in rows:
            r["full"] = f"{r['first_name']} {r['last_name']}" if r["first_name"] and r["last_name"] else None
        for a, b in pairs("full"):
            yield a["application_id"], b["application_id"], "name"


def resolve(apps: pd.DataFrame, rule: str = "chosen"):
    """Return (application_id -> candidate_id, application_id -> strongest link reason)."""
    ids = sorted(apps["application_id"])
    uf, reason = UnionFind(ids), {}
    rank = {"email": 0, "phone+name": 1, "phone": 2, "name": 3, "phone,name_unknown": 4}
    for a, b, why in _edges(apps, rule):
        uf.union(a, b)
        for x in (a, b):
            if x not in reason or rank[why] < rank[reason[x]]:
                reason[x] = why
    root = {i: uf.find(i) for i in ids}
    cand = {i: "CAND-" + root[i].replace(":", "-") for i in ids}
    return cand, {i: reason.get(i, "singleton") for i in ids}


def name_conflicts(apps: pd.DataFrame) -> pd.DataFrame:
    """Candidates whose applications carry first names that contradict each other: a possible over-merge."""
    out = []
    for cid, g in apps.dropna(subset=["first_name"]).groupby("candidate_id"):
        firsts = sorted({f for f in g["first_name"] if isinstance(f, str) and len(f) > 1})
        if any(not names_compatible(a, None, b, None) for i, a in enumerate(firsts) for b in firsts[i + 1:]):
            out.append({"candidate_id": cid, "first_names": ",".join(firsts), "applications": len(g)})
    return pd.DataFrame(out, columns=["candidate_id", "first_names", "applications"])


def evaluate_rules(apps: pd.DataFrame, audit: pd.DataFrame | None) -> pd.DataFrame:
    """Compare matching rules against the recruiter-labelled pairs (the only ground truth a client can give us)."""
    if audit is None or not len(audit):
        return pd.DataFrame()
    known = set(apps["application_id"])
    a = audit.assign(left=audit["left_source"] + ":" + audit["left_record"],
                     right=audit["right_source"] + ":" + audit["right_record"])
    a = a[a["left"].isin(known) & a["right"].isin(known)]
    truth = a["same_person"].eq("yes")
    rows = []
    for rule in ("name_only", "email_only", "phone_only", "email_or_phone", "chosen_plus_unverified", "chosen"):
        cand, _ = resolve(apps, rule)
        pred = pd.Series([cand[l] == cand[r] for l, r in zip(a["left"], a["right"])], index=a.index)
        tp, fp = int((pred & truth).sum()), int((pred & ~truth).sum())
        fn, tn = int((~pred & truth).sum()), int((~pred & ~truth).sum())
        rows.append({"rule": rule, "pairs_evaluated": len(a), "true_matches_found": tp, "false_merges": fp,
                     "missed_matches": fn, "correctly_kept_apart": tn,
                     "precision_pct": round(100 * tp / (tp + fp), 1) if tp + fp else None,
                     "recall_pct": round(100 * tp / (tp + fn), 1) if tp + fn else None})
    return pd.DataFrame(rows)


def review_queue(apps: pd.DataFrame) -> pd.DataFrame:
    """Nameless applications whose phone matches a named candidate: one phone call confirms or rejects."""
    named = apps[apps["first_name"].notna() & apps["phone_norm"].notna()]
    nameless = apps[apps["first_name"].isna() & apps["phone_norm"].notna()]
    m = nameless.merge(named, on="phone_norm", suffixes=("", "_named"))
    m = m[m["candidate_id"] != m["candidate_id_named"]]
    firsts = named.groupby("phone_norm")["first_name"].nunique()
    m["phone_shared_by_named_people"] = m["phone_norm"].map(firsts).gt(1)
    out = (m.sort_values(["application_id", "applied_at_named"])
             .drop_duplicates(["application_id", "candidate_id_named"])
             [["application_id", "source", "applied_date", "phone_norm", "candidate_id_named", "name_raw_named",
               "phone_shared_by_named_people"]]
             .rename(columns={"candidate_id_named": "possible_candidate", "name_raw_named": "possible_name"}))
    return out.reset_index(drop=True)
