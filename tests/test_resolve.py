import json

import pandas as pd

from pipeline.config import load_config
from pipeline.resolve import evaluate_rules, resolve, review_queue
from pipeline.validate import standardize_applications

CFG = load_config()


def apps(rows):
    df = pd.DataFrame([{"source": r.get("source", "job_board"), "source_record_id": str(i), "applied_at": pd.Timestamp("2026-05-01"),
                        "name_raw": r.get("name"), "email_raw": r.get("email"), "phone_raw": r.get("phone"),
                        "context": json.dumps(r.get("context", {}))} for i, r in enumerate(rows)])
    return standardize_applications([df], CFG, pd.Timestamp("2026-08-31").date())


def same(df, rule="chosen"):
    cand, _ = resolve(df, rule)
    return len(set(cand.values())) == 1


def test_same_email_different_formats_is_one_person():
    df = apps([{"name": "Sharma, Rahul", "email": "rahul.sharma@gmail.com"}, {"name": "Rahul S", "email": "RahulSharma@gmail.com"}])
    assert same(df)


def test_siblings_sharing_a_phone_are_not_merged():
    df = apps([{"name": "Rahul Sharma", "phone": "9812345670"}, {"name": "Priya Sharma", "phone": "+91 98123 45670"}])
    assert not same(df)
    assert same(df, "phone_only")            # the naive rule would merge them


def test_nameless_record_does_not_bridge_two_siblings():
    df = apps([{"name": "Rahul Sharma", "phone": "9812345670"}, {"source": "whatsapp", "phone": "9812345670"},
               {"name": "Priya Sharma", "phone": "9812345670"}])
    cand, _ = resolve(df, "chosen_plus_unverified")
    assert len(set(cand.values())) == 3       # contested phone: even the upper bound keeps them apart


def test_nameless_phone_match_goes_to_review_not_merge():
    df = apps([{"name": "Rahul Sharma", "phone": "9812345670"}, {"source": "whatsapp", "phone": "9812345670"}])
    assert not same(df)
    assert same(df, "chosen_plus_unverified")
    cand, _ = resolve(df)
    df["candidate_id"] = df["application_id"].map(cand)
    assert len(review_queue(df)) == 1


def test_placeholder_phone_never_links_strangers():
    df = apps([{"name": "Rahul Sharma", "phone": "9999999999"}, {"name": "Rahul Sharma", "phone": "9999999999", "source": "careers"}])
    assert df["phone_norm"].isna().all()
    assert "A06" in df["warning_reasons"].iloc[0]


def test_referrers_own_number_is_not_the_candidates():
    df = apps([{"source": "referral", "name": "Amit K", "phone": "9123456780", "context": {"referrer_phone": "9123456780"}},
               {"source": "referral", "name": "Amit Kumar", "phone": "9123456780", "context": {"referrer_phone": "9123456780"}}])
    assert df["phone_norm"].isna().all() and df["warning_reasons"].str.contains("A07").all()


def test_rule_evaluation_counts_false_merges():
    df = apps([{"name": "Rahul Sharma", "phone": "9812345670"}, {"name": "Priya Sharma", "phone": "9812345670"}])
    audit = pd.DataFrame([{"left_source": "job_board", "left_record": "0", "right_source": "job_board", "right_record": "1",
                           "same_person": "no"}])
    ev = evaluate_rules(df, audit).set_index("rule")
    assert ev.loc["phone_only", "false_merges"] == 1
    assert ev.loc["chosen", "false_merges"] == 0
