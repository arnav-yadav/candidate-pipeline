"""
Generates the SIMULATED client systems for this project.

The client in this project is constructed (see docs/simulation.md). No real person's data
is used. The generator encodes the mechanisms described in Assignment 1 -- five intake
channels, one recruiter, a hand-maintained tracker, name-only duplicate spotting, review in
recency order, silent rejections, and re-application driven by silence -- and lets the
messiness emerge from those mechanisms rather than planting individual errors.

The pipeline never reads anything in simulator/_ground_truth/. That folder exists only so
that the recruiter-labelled audit sample can be produced, which is what a real engagement
would do by hand.

Run:  python simulator/generate_client_systems.py
"""
from __future__ import annotations

import csv
import json
import mailbox
import os
import random
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path

SEED = 20260901
ROOT = Path(__file__).resolve().parents[1]
# SIM_OUT_DIR lets the determinism test generate into a scratch folder instead of the repo
_SIM_OUT = os.environ.get("SIM_OUT_DIR")
OUT = Path(_SIM_OUT) / "client_systems" if _SIM_OUT else ROOT / "client_systems"
TRUTH = Path(_SIM_OUT) / "_ground_truth" if _SIM_OUT else ROOT / "simulator" / "_ground_truth"

START = date(2026, 1, 1)
END = date(2026, 8, 31)            # last application date
EXPORT_DATE = date(2026, 9, 25)    # when the client exported the tracker / chat / mailbox
IST = timezone(timedelta(hours=5, minutes=30))

rng = random.Random(SEED)

# ---------------------------------------------------------------- names
FIRST = (["Rahul"] * 9 + ["Priya"] * 8 + ["Amit"] * 7 + ["Neha"] * 7 + ["Rohit"] * 6 + ["Pooja"] * 6 +
         ["Vikas", "Anjali", "Suresh", "Kavya", "Arjun", "Sneha", "Karan", "Divya", "Manish", "Ritu",
          "Sanjay", "Meera", "Deepak", "Nisha", "Ajay", "Swati", "Rakesh", "Shreya", "Vivek", "Aarti",
          "Nitin", "Payal", "Gaurav", "Komal", "Harish", "Jyoti", "Imran", "Farah", "Joseph", "Mary",
          "Sandeep", "Rekha", "Tarun", "Bhavna", "Mohit", "Ankita", "Prakash", "Lakshmi", "Venkat",
          "Sai", "Harpreet", "Gurpreet", "Arun", "Sunita", "Ravi", "Geeta", "Naveen", "Preeti"] * 2)
LAST = (["Sharma"] * 10 + ["Kumar"] * 9 + ["Singh"] * 9 + ["Verma"] * 5 + ["Gupta"] * 5 + ["Patel"] * 4 +
        ["Reddy", "Nair", "Iyer", "Das", "Khan", "Joshi", "Mishra", "Yadav", "Mehta", "Rao", "Pillai",
         "Chauhan", "Shaikh", "Bose", "Menon", "Kapoor", "Malhotra", "Saxena", "Pandey", "Tiwari",
         "Naidu", "Fernandes", "D'Souza", "Ghosh", "Jain", "Agarwal", "Bhat", "Thomas", "Kaur", "Gill"] * 2)
DOMAINS = ["gmail.com"] * 8 + ["yahoo.com", "outlook.com", "rediffmail.com", "hotmail.com"]


@dataclass
class Person:
    pid: int
    first: str
    last: str
    email: str
    alt_email: str | None
    phone: str
    applications: list = field(default_factory=list)
    hired: bool = False


@dataclass
class Application:
    app_key: str          # ground-truth key, never exported
    pid: int
    channel: str
    applied_at: datetime  # IST
    is_reapplication: bool
    email_used: str | None = None
    # recruiter-side state
    tracker_row: int | None = None
    screened_on: date | None = None
    outcome: str | None = None
    first_contact_on: date | None = None


def make_email(first, last, n):
    f, l = first.lower(), last.lower().replace("'", "")
    pattern = rng.choice([f"{f}.{l}", f"{f}{l}", f"{f}.{l}{n}", f"{f}{n}", f"{f[0]}{l}{n}", f"{l}.{f}"])
    return f"{pattern}@{rng.choice(DOMAINS)}"


def make_phone():
    return rng.choice("6789") + "".join(rng.choice("0123456789") for _ in range(9))


EMAILS_USED: set = set()


def unique_email(first, last):
    """One mailbox belongs to one person; Gmail treats dots as the same mailbox, so compare without them."""
    while True:
        e = make_email(first, last, rng.randint(1, 99))
        local, dom = e.split("@")
        key = (local.replace(".", "") if dom == "gmail.com" else local) + "@" + dom
        if key not in EMAILS_USED:
            EMAILS_USED.add(key)
            return e


def make_people(n):
    people, phones = [], set()
    for pid in range(n):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        phone = make_phone()
        while phone in phones:
            phone = make_phone()
        phones.add(phone)
        alt = unique_email(first, last) if rng.random() < 0.18 else None
        people.append(Person(pid, first, last, unique_email(first, last), alt, phone))
    # ~3% share a phone with a sibling: a different person, same surname, same phone number
    for p in rng.sample(people, int(n * 0.03)):
        sib_first = rng.choice(sorted(f for f in set(FIRST) if f != p.first))   # sorted: set order changes between Python processes
        people.append(Person(len(people), sib_first, p.last, unique_email(sib_first, p.last), None, p.phone))
    return people


CHANNEL_W = {"job_board": 0.40, "careers": 0.20, "whatsapp": 0.18, "referral": 0.12, "email": 0.10}


def pick_channel(previous=None):
    if previous and rng.random() < 0.45:
        return previous
    return rng.choices(list(CHANNEL_W), weights=list(CHANNEL_W.values()))[0]


def rand_time(d):
    return datetime(d.year, d.month, d.day, rng.randint(8, 23), rng.randint(0, 59), rng.randint(0, 59), tzinfo=IST)


# ---------------------------------------------------------------- identity rendering per channel
def fmt_phone(p, style):
    return {
        "plain": p, "plus91": f"+91{p}", "plus91sp": f"+91 {p[:5]} {p[5:]}", "dash": f"+91-{p}",
        "zero": f"0{p}", "spaced": f"{p[:3]} {p[3:6]} {p[6:]}",
    }[style]


def gmail_variant(email):
    local, dom = email.split("@")
    if dom == "gmail.com" and "." in local and rng.random() < 0.3:
        return local.replace(".", "") + "@" + dom
    return email


def render_name(p, channel):
    if channel == "job_board":
        return rng.choice([f"{p.last}, {p.first}", f"{p.first.upper()} {p.last.upper()}", f"{p.first} {p.last}"])
    if channel == "referral":
        return rng.choice([f"{p.first} {p.last}", f"{p.first} {p.last[0]}", f"{p.first} {p.last}", f"{p.first}"])
    if channel == "email":
        return rng.choice([f"{p.first} {p.last}", f"{p.first} {p.last}", f"{p.first}", ""])
    return f"{p.first} {p.last}"


# ---------------------------------------------------------------- simulation
def simulate():
    people = make_people(1900)
    days = [START + timedelta(d) for d in range((END - START).days + 1)]
    first_day = {p.pid: rng.choice(days) for p in people}
    by_day: dict[date, list] = {}
    for p in people:
        by_day.setdefault(first_day[p.pid], []).append((p, False))

    apps: list[Application] = []
    tracker: list[dict] = []
    queue: list[Application] = []           # logged but not yet screened
    pending_log: list[tuple[date, Application]] = []
    reapply_plan: list[tuple[date, Person, str]] = []
    walkins = 0

    def log_to_tracker(a, on):
        a.tracker_row = len(tracker)
        tracker.append({"app": a, "logged_on": on})
        queue.append(a)

    sim_day = START
    while sim_day <= EXPORT_DATE:
        # 1. arrivals (new people + planned re-applications)
        todays = list(by_day.get(sim_day, []))
        todays += [(p, True) for d, p, _ in reapply_plan if d == sim_day]
        if sim_day <= END:
            for p, is_re in todays:
                if p.hired:
                    continue
                prev = p.applications[-1].channel if p.applications else None
                a = Application(f"A{len(apps):05d}", p.pid, pick_channel(prev if is_re else None),
                                rand_time(sim_day), is_re)
                a.email_used = p.alt_email if (is_re and p.alt_email and rng.random() < 0.6) else p.email
                p.applications.append(a)
                apps.append(a)
                if a.channel in ("job_board", "careers"):      # auto-export, next morning
                    pending_log.append((sim_day + timedelta(1), a))
                    if a.channel == "job_board" and rng.random() < 0.012:
                        pending_log.append((sim_day + timedelta(1), a))   # double import
                elif rng.random() < 0.70:                        # B1: manual forwarding, sometimes forgotten
                    pending_log.append((sim_day + timedelta(rng.randint(0, 12)), a))
            # walk-ins: exist only in the tracker
            if sim_day.weekday() < 5 and rng.random() < 0.22:
                walkins += 1
                p = rng.choice(people)
                if not p.hired:
                    w = Application(f"W{walkins:04d}", p.pid, "walk_in", rand_time(sim_day), bool(p.applications))
                    w.email_used = p.email if rng.random() < 0.3 else None
                    p.applications.append(w)
                    apps.append(w)
                    log_to_tracker(w, sim_day)

        for d, a in [x for x in pending_log if x[0] == sim_day]:
            log_to_tracker(a, sim_day)
        pending_log = [x for x in pending_log if x[0] != sim_day]

        # 2. recruiter screens newest-first (B3), with name-only DUP marking (B2)
        if sim_day.weekday() < 5:
            capacity = rng.randint(18, 23)
            queue.sort(key=lambda a: tracker[a.tracker_row]["logged_on"], reverse=True)
            seen_names = {}
            for row in tracker:
                if row.get("screened_name"):
                    seen_names.setdefault(row["screened_name"], row["logged_on"])
            done = []
            for a in queue:
                if capacity == 0:
                    break
                row = tracker[a.tracker_row]
                if row.get("status_final"):
                    done.append(a); continue
                p = people[a.pid]
                name_key = f"{p.first} {p.last}".lower()
                if name_key in seen_names and rng.random() < 0.30:
                    row["status_final"] = "DUP"          # recruiter recognises the name string
                    done.append(a); continue
                capacity -= 1
                row["screened_name"] = name_key
                a.screened_on = sim_day
                if rng.random() < 0.28:
                    a.outcome = "shortlisted"
                    a.first_contact_on = sim_day + timedelta(rng.randint(2, 16))
                    r = rng.random()
                    if r < 0.18:
                        a.outcome = "hired"; p.hired = True
                    elif r < 0.45:
                        a.outcome = "rejected_after_call"
                else:
                    a.outcome = "rejected"               # B4: nobody tells the candidate
                row["status_final"] = a.outcome
                done.append(a)
            queue = [a for a in queue if a not in done]
            # rows older than 45 days quietly sink below the fold for good
            queue = [a for a in queue if (sim_day - tracker[a.tracker_row]["logged_on"]).days <= 45]

        # 3. silence drives re-application (Assignment 1, H2), decided 30 days after applying
        for a in apps:
            if a.applied_at.date() + timedelta(30) == sim_day and not people[a.pid].hired:
                heard_back = a.first_contact_on is not None and a.first_contact_on <= sim_day
                prob = 0.08 if heard_back else 0.52
                if rng.random() < prob:
                    reapply_plan.append((sim_day + timedelta(rng.randint(0, 45)), people[a.pid], a.channel))
        sim_day += timedelta(1)
    return people, apps, tracker


# ---------------------------------------------------------------- export helpers
def placeholder_phone():
    return rng.choice(["9999999999", "0000000000", "9876543210"])


def write_job_board(people, apps):
    recs = []
    for a in (x for x in apps if x.channel == "job_board"):
        p = people[a.pid]
        phone = fmt_phone(p.phone, rng.choice(["plus91", "dash", "plain"])) if rng.random() < 0.7 else None
        recs.append({
            "application_id": f"JB-{len(recs) + 100001}",
            "applied_at": a.applied_at.isoformat(),
            "board": rng.choice(["naukri", "naukri", "indeed"]),
            "job": {"id": "CS-AGENT-BLR", "title": "Customer Support Associate"},
            "candidate": {"name": render_name(p, "job_board"),
                          "email": gmail_variant(a.email_used).upper() if rng.random() < 0.08 else gmail_variant(a.email_used),
                          "phone": phone,
                          "experience_years": rng.choice([0, 0, 1, 1, 2, 3, 4, 5])},
        })
        a.source_ref = recs[-1]["application_id"]
    recs.sort(key=lambda r: r["applied_at"])
    (OUT / "job_board_api").mkdir(parents=True, exist_ok=True)
    (OUT / "job_board_api" / "applications.json").write_text(json.dumps(recs, indent=1))


def write_careers(people, apps):
    path = OUT / "careers_site" / "careers_site.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE job_posts (post_id TEXT PRIMARY KEY, title TEXT, city TEXT, opened_on TEXT)""")
    con.execute("INSERT INTO job_posts VALUES ('CS-AGENT-BLR','Customer Support Associate','Bengaluru','2025-11-15')")
    con.execute("""CREATE TABLE career_applications (
        id INTEGER PRIMARY KEY, post_id TEXT, submitted_at_utc TEXT, full_name TEXT, email TEXT,
        phone TEXT, city TEXT, consent INTEGER)""")
    i = 5000
    for a in (x for x in apps if x.channel == "careers"):
        p = people[a.pid]
        i += 1
        phone = placeholder_phone() if rng.random() < 0.02 else fmt_phone(p.phone, rng.choice(["plain", "spaced", "zero", "plus91sp"]))
        name = f"{p.first} {p.last}" if rng.random() > 0.1 else f"{p.first.lower()} {p.last.lower()}"
        con.execute("INSERT INTO career_applications VALUES (?,?,?,?,?,?,?,?)",
                    (i, "CS-AGENT-BLR", a.applied_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                     name, gmail_variant(a.email_used), phone,
                     rng.choice(["Bengaluru", "Bangalore", "BLR", "Bengaluru", "Mysuru", "Hosur"]), 1))
        a.source_ref = str(i)
    con.commit(); con.close()


def write_referrals(people, apps):
    path = OUT / "referral_form" / "referral_form_responses.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    referrers = [(f"{rng.choice(FIRST)} {rng.choice(LAST)}", make_phone()) for _ in range(25)]
    rows = []
    for a in (x for x in apps if x.channel == "referral"):
        p = people[a.pid]
        ref_name, ref_phone = rng.choice(referrers)
        cand_phone = ref_phone if rng.random() < 0.05 else (fmt_phone(p.phone, rng.choice(["plain", "spaced", "plus91sp"])) if rng.random() < 0.92 else "")
        cand_email = gmail_variant(a.email_used) if rng.random() < 0.4 else rng.choice(["", "", "na", "NA", "-"])
        rows.append({"Timestamp": a.applied_at.strftime("%d/%m/%Y %H:%M:%S"),
                     "Your name (referrer)": ref_name, "Your phone": fmt_phone(ref_phone, "plain"),
                     "Candidate name": render_name(p, "referral"), "Candidate phone": cand_phone,
                     "Candidate email": cand_email,
                     "How do you know them?": rng.choice(["Friend", "Cousin", "Ex-colleague", "Neighbour", "College"]),
                     "form_response_id": f"RF{len(rows) + 1:04d}"})
        a.source_ref = rows[-1]["form_response_id"]
    rows.sort(key=lambda r: datetime.strptime(r["Timestamp"], "%d/%m/%Y %H:%M:%S"))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def write_whatsapp(people, apps):
    lines = []
    intros = ["Hi, I saw your post for customer support job. {n}", "Hello sir, is the support associate vacancy still open? {n}",
              "Good morning. I want to apply for the customer care role. {n}", "Hi {n} I am interested in the job"]
    for a in (x for x in apps if x.channel == "whatsapp"):
        p = people[a.pid]
        sender = fmt_phone(p.phone, "plus91sp")
        t = a.applied_at
        name_part = f"My name is {p.first} {p.last}." if rng.random() < 0.6 else ""
        body = rng.choice(intros).format(n=name_part).strip()
        if rng.random() < 0.1:
            body += f" My email is {gmail_variant(a.email_used)}"
        lines.append((t, sender, body))
        if rng.random() < 0.8:
            lines.append((t + timedelta(minutes=rng.randint(1, 20)), sender, "<Media omitted>"))
        if rng.random() < 0.45:
            lines.append((t + timedelta(minutes=rng.randint(25, 300)), "Ops Hiring", "Thanks, received. We will get back to you."))
        if rng.random() < 0.15:
            lines.append((t + timedelta(days=rng.randint(3, 20)), sender, "Any update on my application?"))
        a.source_ref = None
    # unrelated chatter from the same business number
    for _ in range(60):
        d = START + timedelta(rng.randint(0, (END - START).days))
        lines.append((rand_time(d), fmt_phone(make_phone(), "plus91sp"), rng.choice(["Is my order shipped?", "Refund status pls", "Hi"])))
    lines.sort(key=lambda x: x[0])
    path = OUT / "whatsapp" / "WhatsApp Chat with Hiring - Ops.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write("Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them.\n")
        for t, s, b in lines:
            f.write(f"{t.strftime('%d/%m/%y')}, {t.strftime('%I:%M %p').lstrip('0').lower()} - {s}: {b}\n")


def write_mailbox(people, apps):
    path = OUT / "ops_head_inbox" / "ops_head_inbox.mbox"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    box = mailbox.mbox(path)
    subjects = ["Application for Customer Support Associate", "Job application - customer support",
                "Resume for support role", "Applying for the vacancy", "CV"]
    msgs = []
    for a in (x for x in apps if x.channel == "email"):
        p = people[a.pid]
        m = EmailMessage()
        nm = render_name(p, "email")
        m["From"] = f"{nm} <{gmail_variant(a.email_used)}>" if nm else gmail_variant(a.email_used)
        m["To"] = "ops.head@client-brand.in"
        m["Subject"] = rng.choice(subjects)
        m["Date"] = format_datetime(a.applied_at)
        m["Message-ID"] = f"<cand-{len(msgs) + 1:05d}@mail.gmail.com>"
        a.source_ref = m["Message-ID"]
        body = f"Dear Sir/Madam,\n\nPlease find my resume attached for the customer support position."
        if rng.random() < 0.4:
            body += f"\nYou can reach me on {fmt_phone(p.phone, rng.choice(['plain', 'plus91', 'spaced']))}."
        body += f"\n\nRegards,\n{p.first}"
        m.set_content(body)
        msgs.append((a.applied_at, m))
    noise = [("Weekly sales dashboard", "reports@client-brand.in"), ("Vendor invoice INV-2231", "accounts@packwell.in"),
             ("Re: warehouse shift roster", "ops.lead@client-brand.in"), ("Your LinkedIn job post is performing well", "jobs-noreply@linkedin.com")]
    for _ in range(140):
        d = START + timedelta(rng.randint(0, (END - START).days))
        s, frm = rng.choice(noise)
        m = EmailMessage(); m["From"] = frm; m["To"] = "ops.head@client-brand.in"; m["Subject"] = s
        m["Date"] = format_datetime(rand_time(d)); m.set_content("See attached.")
        msgs.append((rand_time(d), m))
    for _, m in sorted(msgs, key=lambda x: x[0]):
        mm = mailbox.mboxMessage(m)
        # stamp the mbox separator with the message's own date, not the wall clock, so the file is reproducible
        mm.set_from("MAILER-DAEMON", parsedate_to_datetime(m["Date"]).astimezone(timezone.utc).timetuple())
        box.add(mm)
    box.flush(); box.close()


SOURCE_LABEL = {"job_board": ["Naukri", "naukri.com", "Indeed"], "careers": ["Careers", "Website", "careers page"],
                "referral": ["Referral", "referral", "Ref"], "whatsapp": ["WhatsApp", "WA", "whatsapp"],
                "email": ["Email", "Mail", "email - ops head"], "walk_in": ["Walk-in", "Walk in"]}
STATUS_LABEL = {"rejected": ["Rejected", "rejected", "Not suitable", "NS", "Rejected "],
                "shortlisted": ["Shortlisted", "CV OK", "Phone screen done", "Screened - OK"],
                "rejected_after_call": ["Rejected after call", "Not selected", "Mock call - fail"],
                "hired": ["Hired", "Joined"], "DUP": ["DUP", "Duplicate", "dup"], None: ["", "", "New", "On hold"]}


def fmt_manual_date(d):
    r = rng.random()
    if r < 0.8:
        return d.strftime("%d/%m/%Y")
    if r < 0.93:
        return d.strftime("%d-%b-%y")
    return d.strftime("%-d/%-m/%Y")


def write_tracker(people, apps, tracker):
    rows = []
    for i, row in enumerate(tracker):
        a, p = row["app"], people[row["app"].pid]
        auto = a.channel in ("job_board", "careers")
        status = row.get("status_final")
        screened = a.screened_on if status not in ("DUP", None) else None
        if a.channel in ("whatsapp",):
            phone, email = fmt_phone(p.phone, "plus91sp"), ""
        elif a.channel == "email":
            phone, email = "", a.email_used
        elif a.channel == "walk_in":
            phone, email = fmt_phone(p.phone, "plain"), a.email_used or ""
        else:
            phone = fmt_phone(p.phone, rng.choice(["plain", "spaced"])) if rng.random() < 0.8 else ""
            email = a.email_used if rng.random() < 0.9 else ""
        name = render_name(p, a.channel) if a.channel == "job_board" else (f"{p.first} {p.last}" if rng.random() < 0.85 else f"{p.first}")
        contact = a.first_contact_on if status not in ("DUP",) else None
        rows.append({
            "Row": i + 2,   # sheet row numbers start at 2
            "Date Logged": row["logged_on"].isoformat() if auto else fmt_manual_date(row["logged_on"]),
            "Name": name, "Phone": phone, "Email": email,
            "Source": rng.choice(SOURCE_LABEL[a.channel]),
            "Ref": getattr(a, "source_ref", "") if auto else "",
            "Status": rng.choice(STATUS_LABEL[status]) if status in STATUS_LABEL else rng.choice(STATUS_LABEL[None]),
            "Screened On": (fmt_manual_date(screened) if screened and rng.random() > 0.04 else ""),
            "First Contact": fmt_manual_date(contact) if contact else "",
            "Notes": rng.choice(["", "", "", "good communication", "no Kannada", "asked for night shift", "call back", "same as earlier?"]),
        })
    path = OUT / "recruiter_tracker" / "Hiring Tracker - Support Agents.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def write_audit_sample(people, apps):
    """Recruiter-labelled pairs: what a real engagement produces by hand to test the matching rule."""
    exportable = [a for a in apps if a.channel != "walk_in" and getattr(a, "source_ref", None) is not None or a.channel == "whatsapp"]
    def ref(a):
        return {"job_board": "job_board", "careers": "careers", "referral": "referral", "email": "email", "whatsapp": "whatsapp"}[a.channel]
    by_phone, by_email, by_name = {}, {}, {}
    for a in exportable:
        p = people[a.pid]
        by_phone.setdefault(p.phone, []).append(a)
        by_email.setdefault(a.email_used, []).append(a)
        by_name.setdefault((p.first, p.last), []).append(a)
    pairs = set()
    for groups, n in ((by_phone, 90), (by_email, 70), (by_name, 90)):
        multi = [g for g in groups.values() if len(g) > 1]
        rng.shuffle(multi)
        for g in multi[:n]:
            a, b = rng.sample(g, 2)
            pairs.add(tuple(sorted((a.app_key, b.app_key))))
    idx = {a.app_key: a for a in apps}
    rows = []
    for k1, k2 in sorted(pairs):
        a, b = idx[k1], idx[k2]
        rows.append({"pair_id": f"P{len(rows) + 1:03d}",
                     "left_source": ref(a), "left_record": a.audit_ref, "right_source": ref(b), "right_record": b.audit_ref,
                     "same_person": "yes" if a.pid == b.pid else "no",
                     "labelled_by": "recruiter", "labelled_on": "2026-09-20",
                     "how_checked": "called the candidate / compared CVs"})
    path = OUT / "audit" / "recruiter_labelled_pairs.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    people, apps, tracker = simulate()
    write_job_board(people, apps)
    write_careers(people, apps)
    write_referrals(people, apps)
    write_whatsapp(people, apps)
    write_mailbox(people, apps)
    write_tracker(people, apps, tracker)
    # stable per-record references for the audit sample (whatsapp: sender phone + minute; email: address + minute)
    for a in apps:
        p = people[a.pid]
        if a.channel == "whatsapp":   # the pipeline's record id for a chat application: sender digits @ first-message minute
            a.audit_ref = f"91{p.phone}@{a.applied_at.strftime('%Y-%m-%dT%H:%M')}"
        else:
            a.audit_ref = getattr(a, "source_ref", None)
    write_audit_sample(people, apps)
    TRUTH.mkdir(parents=True, exist_ok=True)
    with open(TRUTH / "applications_truth.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["app_key", "person_id", "channel", "applied_at", "is_reapplication", "source_ref", "tracker_row",
                    "screened_on", "outcome", "first_contact_on"])
        for a in apps:
            w.writerow([a.app_key, a.pid, a.channel, a.applied_at.isoformat(), a.is_reapplication,
                        getattr(a, "source_ref", "") or getattr(a, "audit_ref", ""),
                        "" if a.tracker_row is None else a.tracker_row + 2,
                        a.screened_on or "", a.outcome or "", a.first_contact_on or ""])
    n_re = sum(a.is_reapplication for a in apps)
    print(f"people={len(people)} applications={len(apps)} reapplications={n_re} tracker_rows={len(tracker)}")


if __name__ == "__main__":
    main()
