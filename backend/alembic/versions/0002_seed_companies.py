"""Seed 25 real companies across 5 clusters, with realistic non-empty content.

Note on checklist items:
    The 15 fixed checklist items are NOT seeded globally because
    checklist_items.user_company_id is NOT NULL with a FK to user_company —
    there is no global checklist_templates table. The 15 items are defined
    as the constant CHECKLIST_ITEMS in app/models/company.py and are inserted
    per-user_company by the company-tracking service (added in a later phase)
    when POST /api/v1/companies/{id}/track is called. This matches the
    Phase A design: "Checklist items are seeded automatically when the parent
    user_company row is created".

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02 00:01:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _company(
    name: str,
    cluster: str,
    hiring_process: str,
    oa_pattern: str,
    frequent_dsa_topics: list[str],
    core_cs_subjects: list[str],
    resume_requirements: str,
    interview_experiences: list[dict],
) -> dict:
    """Build a company row dict for bulk_insert."""
    return {
        "name": name,
        "cluster": cluster,
        "hiring_process": hiring_process,
        "oa_pattern": oa_pattern,
        "frequent_dsa_topics": frequent_dsa_topics,
        "core_cs_subjects": core_cs_subjects,
        "resume_requirements": resume_requirements,
        # JSONB column — pass the Python list directly. SQLAlchemy's JSONB
        # type handles serialisation. (Do NOT json.dumps here — that would
        # double-encode and the stored value would be a JSON string, not a
        # JSON array, breaking jsonb_array_length() queries later.)
        "interview_experiences": interview_experiences,
        "is_custom": False,
        "created_by": None,
    }


COMPANIES: list[dict] = [
    # ----------------------------------------------------------------- FAANG
    _company(
        name="Meta",
        cluster="FAANG",
        hiring_process=(
            "## Meta Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min): resume walkthrough + behavioural.\n"
            "2. **Technical Phone Screen** (~45 min): 2 DSA problems on arrays / strings / trees.\n"
            "3. **Onsite** (4 rounds × 45 min): 2 DSA, 1 System Design, 1 Behavioural.\n"
            "4. **Hiring Committee Review** (async, 1–2 weeks).\n"
            "5. **Offer + Team Match**."
        ),
        oa_pattern=(
            "Meta typically skips a formal OA for experienced hires. For new-grad and intern, "
            "a short HackerRank warm-up (1 problem, 30 min) is sometimes used before the phone screen. "
            "Expect arrays + graphs."
        ),
        frequent_dsa_topics=["Arrays", "Trees", "Graphs", "Dynamic Programming", "Two Pointers"],
        core_cs_subjects=["DBMS", "OS", "System Design"],
        resume_requirements=(
            "Strong DSA fundamentals (300+ problems solved), 2+ substantial projects with measurable impact, "
            "leadership evidence (club / open-source / hackathon), and quantified resume bullets."
        ),
        interview_experiences=[
            {
                "title": "Meta New Grad — Onsite, Bangalore",
                "source": "Blind",
                "summary": (
                    "2 DSA rounds (merge-k-sorted-lists + LRU cache variant; word-ladder on graphs), "
                    "1 system design (design Instagram feed), 1 behavioural (STAR format on 2 projects). "
                    "Interviewers were friendly, expected running code in coderpad."
                ),
                "date": "2025-08-14",
            },
            {
                "title": "Meta Intern — Phone Screen",
                "source": "LeetCode Discuss",
                "summary": (
                    "45 min, single problem (valid parentheses with wildcards). Asked for complexity, "
                    "then a follow-up to handle k types of brackets. Solved in 25 min, rest was Q&A."
                ),
                "date": "2025-06-02",
            },
        ],
    ),
    _company(
        name="Amazon",
        cluster="FAANG",
        hiring_process=(
            "## Amazon Interview Process\n\n"
            "1. **Online Assessment** (2 DSA problems + work-style simulation, 90 min).\n"
            "2. **Recruiter Screen** (~30 min).\n"
            "3. **Onsite** (4–5 rounds): 3–4 DSA, 1 System Design, 1 Leadership Principles round.\n"
            "4. **Debrief + Offer**.\n\n"
            "Amazon heavily weights the 16 Leadership Principles in every round."
        ),
        oa_pattern=(
            "Two DSA problems on HackerRank (typically Medium), plus a behavioural work-style survey. "
            "Common patterns: greedy, sliding window, trees. 90 minutes total."
        ),
        frequent_dsa_topics=["Arrays", "Trees", "Greedy", "Sliding Window", "Heap"],
        core_cs_subjects=["DBMS", "OS", "System Design"],
        resume_requirements=(
            "Amazon expects leadership-principle-flavoured bullets: 'Situation, Action, Result' with numbers. "
            "Minimum 1 substantial project, ideally 2. AWS exposure is a plus for SDE roles."
        ),
        interview_experiences=[
            {
                "title": "Amazon SDE-1 OA + Onsite",
                "source": "Glassdoor",
                "summary": (
                    "OA: robot-bounded-in-circle + anagrams grouping. Onsite: 3 DSA (LRU, top-k-frequent, "
                    "course-schedule), 1 system design (design a URL shortener), 1 LP round (4 questions, "
                    "deep-dive on 'Customer Obsession' and 'Deliver Results')."
                ),
                "date": "2025-09-21",
            }
        ],
    ),
    _company(
        name="Apple",
        cluster="FAANG",
        hiring_process=(
            "## Apple Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Technical Phone Screen** (1–2 rounds, DSA + domain).\n"
            "3. **Onsite** (5–6 rounds): mix of DSA, domain (iOS / systems / ML depending on team), "
            "and behavioural. Team-specific, less standardised than Meta/Google.\n"
            "4. **Offer**."
        ),
        oa_pattern=(
            "Apple rarely uses a standard OA. Most teams go straight to phone screens. "
            "Some teams (e.g. IS&T) use HackerRank, but it is team-dependent."
        ),
        frequent_dsa_topics=["Arrays", "Linked Lists", "Trees", "Concurrency", "Bit Manipulation"],
        core_cs_subjects=["OS", "OOP", "DBMS"],
        resume_requirements=(
            "Domain depth matters more than breadth at Apple. For systems roles, show C/C++/Swift projects "
            "work; for ML roles, a publication or substantial model. Resume should be 1 page, clean, "
            "Apple-style minimal."
        ),
        interview_experiences=[
            {
                "title": "Apple IS&T — Software Engineer",
                "source": "Blind",
                "summary": (
                    "Phone screen: reverse-linked-list-in-k-groups + design discussion around caching. "
                    "Onsite: 5 rounds, heavy on concurrency (dining philosophers, producer-consumer), "
                    "1 system design (design Apple Music library), 2 behavioural."
                ),
                "date": "2025-07-10",
            }
        ],
    ),
    _company(
        name="Netflix",
        cluster="FAANG",
        hiring_process=(
            "## Netflix Interview Process\n\n"
            "1. **Recruiter Screen** (~45 min, deep on culture).\n"
            "2. **Hiring Manager Call** (~60 min, behavioural + domain).\n"
            "3. **Take-home or Technical Screen** (team-dependent).\n"
            "4. **Virtual Onsite** (5 rounds: 2 domain/system design, 2 behavioural/culture, 1 coding if relevant).\n"
            "5. **Offer**.\n\n"
            "Netflix is culture-first — the 'Keeper Test' memo is required reading before any interview."
        ),
        oa_pattern=(
            "No standard OA. Some teams use a take-home exercise (e.g. 'design a metrics pipeline') "
            "instead of live coding. Live coding, when used, is conversational and pair-programming style."
        ),
        frequent_dsa_topics=["Arrays", "Hash Maps", "Streaming Algorithms", "Heaps"],
        core_cs_subjects=["System Design", "Distributed Systems", "DBMS"],
        resume_requirements=(
            "Senior-only hiring for most roles. Resume should show scale (QPS, data volume, SLA), "
            "ownership of a system end-to-end, and clear articulation of trade-offs made. "
            "No junior/new-grad pipeline."
        ),
        interview_experiences=[
            {
                "title": "Netflix Senior SWE — Streaming Infrastructure",
                "source": "Blind",
                "summary": (
                    "HM call was 60 min on past system I owned, trade-offs, on-call war stories. "
                    "Onsite: 2 system design (design a real-time metrics pipeline; design playback telemetry "
                    "ingestion), 2 culture (deep on 'freedom and responsibility'), 1 coding (merge intervals variant)."
                ),
                "date": "2025-05-18",
            }
        ],
    ),
    _company(
        name="Google",
        cluster="FAANG",
        hiring_process=(
            "## Google Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Technical Phone Screen** (45 min, 1–2 DSA problems on Google Docs).\n"
            "3. **Onsite** (4–5 rounds × 45 min): 3–4 DSA, 1 System Design (for L4+), 1 Googliness.\n"
            "4. **Hiring Committee** (async, 3–4 weeks).\n"
            "5. **Team Match + Offer**."
        ),
        oa_pattern=(
            "Google does not use an OA. They go straight to phone screens. "
            "For university hires, a sample test may be shared for practice but is not graded."
        ),
        frequent_dsa_topics=["Arrays", "Graphs", "DP", "Trees", "Hash Maps", "Greedy"],
        core_cs_subjects=["Algorithms", "DBMS", "System Design"],
        resume_requirements=(
            "Strong algorithmic foundation (400+ problems), Googley traits (curiosity, persistence), "
            "1 substantial project with technical depth. Resume: 1 page, no fluff, quantified impact."
        ),
        interview_experiences=[
            {
                "title": "Google L3 New Grad — Onsite",
                "source": "LeetCode Discuss",
                "summary": (
                    "4 DSA rounds (valid-sudoku variant, course-schedule-ii, design-a-text-editor, "
                    "max-area-of-island), 1 googliness (collaboration + conflict resolution). "
                    "Hard emphasis on communication — they want to hear your thought process."
                ),
                "date": "2025-10-03",
            }
        ],
    ),
    # ----------------------------------------------------------- Product-based
    _company(
        name="Atlassian",
        cluster="Product-based",
        hiring_process=(
            "## Atlassian Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **HackerRank OA** (2 DSA problems, 90 min).\n"
            "3. **Technical Phone Screen** (~60 min, DSA + design discussion).\n"
            "4. **Onsite** (4 rounds): 2 DSA, 1 System Design, 1 Values/Behavioural.\n"
            "5. **Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (typically 1 Easy-Medium + 1 Medium-Hard) on HackerRank. "
            "90 minutes. Common patterns: graphs, DP, strings."
        ),
        frequent_dsa_topics=["Graphs", "Trees", "DP", "Strings", "Hash Maps"],
        core_cs_subjects=["DBMS", "System Design", "Distributed Systems"],
        resume_requirements=(
            "Collaboration and 'team, not team-mates' values are weighted heavily. Show 1+ substantial project "
            "with team context. Open-source contributions (even small ones) are a plus."
        ),
        interview_experiences=[
            {
                "title": "Atlassian P3 — Backend Engineer",
                "source": "Glassdoor",
                "summary": (
                    "OA: number-of-islands variant + scheduling problem. Onsite: 2 DSA (LRU variant, "
                    "word-ladder), 1 system design (design Jira issue search at scale), 1 values round "
                    "(deep on 'Open company, no bullshit')."
                ),
                "date": "2025-08-22",
            }
        ],
    ),
    _company(
        name="Adobe",
        cluster="Product-based",
        hiring_process=(
            "## Adobe Interview Process\n\n"
            "1. **Online Assessment** (3 DSA + 1 CS-fundamentals MCQ, 90 min).\n"
            "2. **Technical Interview** (1–2 rounds, DSA + puzzles).\n"
            "3. **Managerial Round** (project + behavioural).\n"
            "4. **HR Round**.\n"
            "5. **Offer**."
        ),
        oa_pattern=(
            "3 DSA problems (Easy/Medium/Medium) on Mettl/HirePro + CS fundamentals MCQ (OS/DBMS/OOP). "
            "90 minutes total. Adobe is one of the few FAANG-adjacent companies that still tests CS fundamentals "
            "directly via MCQ."
        ),
        frequent_dsa_topics=["Arrays", "Strings", "DP", "Maths", "Bit Manipulation"],
        core_cs_subjects=["OS", "DBMS", "OOP", "CN"],
        resume_requirements=(
            "Adobe values CS fundamentals heavily (OS, OOP, DBMS). C++/Java proficiency expected. "
            "Projects showing system-level thinking (compilers, graphics, document processing) stand out."
        ),
        interview_experiences=[
            {
                "title": "Adobe ASE — Bangalore",
                "source": "GeeksforGeeks",
                "summary": (
                    "OA: 3 DSA (reverse-words-in-string, subarray-sum-equals-k, sudoku-validator) + 20 MCQs. "
                    "Interview: 2 technical (DP on strings + LRU cache), 1 managerial (deep on past project), "
                    "1 HR (standard behavioural)."
                ),
                "date": "2025-09-15",
            }
        ],
    ),
    _company(
        name="Salesforce",
        cluster="Product-based",
        hiring_process=(
            "## Salesforce Interview Process\n\n"
            "1. **Online Assessment** (2 DSA + 1 SQL, 75 min).\n"
            "2. **Technical Interview** (DSA + design discussion).\n"
            "3. **System Design / HLD Round**.\n"
            "4. **Managerial + Behavioural**.\n"
            "5. **Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) on HackerRank + 1 SQL query question. 75 minutes. "
            "Salesforce values SQL fluency more than most product companies."
        ),
        frequent_dsa_topics=["Arrays", "Trees", "Strings", "SQL", "Hash Maps"],
        core_cs_subjects=["DBMS", "Cloud", "OOP"],
        resume_requirements=(
            "CRM/multi-tenant exposure is a plus. Show database schema design work in projects. "
            "Java/Apex experience is valued for core platform roles."
        ),
        interview_experiences=[
            {
                "title": "Salesforce MTS-2 — Hyderabad",
                "source": "LeetCode Discuss",
                "summary": (
                    "OA: two-sum variant + valid-bst + 1 SQL (find top-3 customers by revenue). "
                    "Onsite: DSA (interval merging), system design (design multi-tenant audit log), "
                    "managerial (ohana culture deep-dive)."
                ),
                "date": "2025-07-29",
            }
        ],
    ),
    _company(
        name="Uber",
        cluster="Product-based",
        hiring_process=(
            "## Uber Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Online Assessment** (2 DSA, 60 min, CodePair).\n"
            "3. **Phone Screen** (45 min, DSA).\n"
            "4. **Onsite** (5 rounds): 3 DSA, 1 System Design, 1 Behavioural.\n"
            "5. **Hiring Committee + Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) on CodePair with live interviewer watching. 60 minutes. "
            "Uber uses this as a real technical screen, not a filter — they grade hard."
        ),
        frequent_dsa_topics=["Graphs", "Arrays", "Greedy", "Geometry", "DP"],
        core_cs_subjects=["System Design", "Distributed Systems", "DBMS"],
        resume_requirements=(
            "Real-time systems experience (chat, maps, streaming) is a big plus. Show scale if you have it. "
            "Uber values 'boldness' — call out ambitious projects even if they failed."
        ),
        interview_experiences=[
            {
                "title": "Uber SDE-2 — Maps Team",
                "source": "Blind",
                "summary": (
                    "OA: 2 problems (closest-pair-of-points + graph shortest-path variant). "
                    "Onsite: 3 DSA (trie-based-autocomplete, lru-cache, sliding-window-maximum), "
                    "1 system design (design Uber ETA service), 1 behavioural."
                ),
                "date": "2025-06-19",
            }
        ],
    ),
    _company(
        name="Swiggy",
        cluster="Product-based",
        hiring_process=(
            "## Swiggy Interview Process\n\n"
            "1. **Online Assessment** (2 DSA + 1 SQL, 90 min, HackerRank).\n"
            "2. **Technical Interview R1** (DSA + problem-solving).\n"
            "3. **Technical Interview R2** (LLD / HLD).\n"
            "4. **Managerial + Culture Fit**.\n"
            "5. **HR + Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (Easy-Medium + Medium) + 1 SQL query on HackerRank. 90 minutes. "
            "Swiggy asks SQL because their backend is data-heavy."
        ),
        frequent_dsa_topics=["Arrays", "Hash Maps", "Graphs", "Strings", "SQL"],
        core_cs_subjects=["DBMS", "System Design", "Distributed Systems"],
        resume_requirements=(
            "Indian product-company context: show projects solving real-world problems (logistics, food, "
            "marketplace). Java/Go proficiency valued. Open-source is a plus."
        ),
        interview_experiences=[
            {
                "title": "Swiggy SDE-1 — Instamart",
                "source": "GeeksforGeeks",
                "summary": (
                    "OA: valid-parentheses + 3sum + SQL (top-selling-stores-by-region). "
                    "R1: DSA (kth-largest-in-stream). R2: LLD (design a coupon system). "
                    "Managerial: deep on past project, on-call scenario."
                ),
                "date": "2025-08-05",
            }
        ],
    ),
    # ----------------------------------------------------------- Service-based
    _company(
        name="TCS",
        cluster="Service-based",
        hiring_process=(
            "## TCS Interview Process\n\n"
            "1. **NQT (National Qualifier Test)** — aptitude + verbal + basic CS MCQs, 90 min.\n"
            "2. **Technical Interview** (basic DSA + project).\n"
            "3. **Managerial Interview**.\n"
            "4. **HR Interview**.\n"
            "5. **Offer** (TCS Digital / Prime / Ninja depending on NQT score)."
        ),
        oa_pattern=(
            "NQT: 80 MCQs in 90 min — aptitude (40), verbal (15), reasoning (15), CS fundamentals (10). "
            "Top performers qualify for Digital/Prime interviews with higher package."
        ),
        frequent_dsa_topics=["Arrays", "Strings", "Maths", "Basic Patterns"],
        core_cs_subjects=["DBMS", "OS", "OOP", "CN", "SQL"],
        resume_requirements=(
            "TCS hires for trainability, not deep expertise. Resume should show 1 project (academic OK), "
            "consistent academic record (60%+ throughout), and basic CS fundamentals. Certifications (Java, "
            "Python, AWS Cloud Practitioner) help."
        ),
        interview_experiences=[
            {
                "title": "TCS Digital — NQT + Interview",
                "source": "IndiaBix",
                "summary": (
                    "NQT cleared with 75%+ for Digital. Technical interview: palindrome check + "
                    "explain OOPs concepts with example + project walkthrough. HR: standard "
                    "(relocation, bond, salary expectations)."
                ),
                "date": "2025-09-10",
            }
        ],
    ),
    _company(
        name="Infosys",
        cluster="Service-based",
        hiring_process=(
            "## Infosys Interview Process\n\n"
            "1. **Infosys Online Test** (verbal + aptitude + pseudocode, 95 min).\n"
            "2. **Technical Interview** (basic DSA + project).\n"
            "3. **HR Interview**.\n"
            "4. **Offer** (Power Programmer track if online test score is high)."
        ),
        oa_pattern=(
            "Online test: 3 sections — verbal (40 Q, 35 min), aptitude (15 Q, 25 min), pseudocode + "
            "SQL (15 Q, 35 min). Power Programmer track adds a hard DSA problem (60 min)."
        ),
        frequent_dsa_topics=["Arrays", "Strings", "Pseudocode Comprehension"],
        core_cs_subjects=["DBMS", "OS", "OOP", "SQL"],
        resume_requirements=(
            "Infosys values consistent academics (60%+ in 10th, 12th, UG) and basic programming fluency. "
            "Power Programmer track requires strong DSA (200+ problems). Resume: 1 page, academic project "
            "front-and-centre."
        ),
        interview_experiences=[
            {
                "title": "Infosys Power Programmer",
                "source": "GeeksforGeeks",
                "summary": (
                    "Online test cleared with 70%+ → Power Programmer track. Technical: 2 DSA "
                    "(reverse-linked-list, longest-substring-without-repeating) + project walkthrough. "
                    "HR: standard Infosys HR round."
                ),
                "date": "2025-08-28",
            }
        ],
    ),
    _company(
        name="Wipro",
        cluster="Service-based",
        hiring_process=(
            "## Wipro Interview Process\n\n"
            "1. **Wipro NLTH (National Level Talent Hunt)** — aptitude + verbal + basic CS, 120 min.\n"
            "2. **Technical Interview**.\n"
            "3. **HR Interview**.\n"
            "4. **Offer** (Elite track for top performers)."
        ),
        oa_pattern=(
            "NLTH: 3 sections — aptitude (48 Q, 48 min), verbal (25 Q, 25 min), analytical + CS (37 Q, 47 min). "
            "Elite track adds a coding round (2 DSA problems, 60 min)."
        ),
        frequent_dsa_topics=["Arrays", "Strings", "Basic Patterns", "Maths"],
        core_cs_subjects=["DBMS", "OS", "OOP", "CN"],
        resume_requirements=(
            "Wipro hires for trainability. 60%+ throughout academics. Basic Java/Python + 1 academic project "
            "suffices for the standard track. Elite track expects 300+ DSA problems solved."
        ),
        interview_experiences=[
            {
                "title": "Wipro Elite NLTH",
                "source": "Glassdoor",
                "summary": (
                    "NLTH cleared → Elite coding round (2 problems: anagram check + staircase DP). "
                    "Technical: explain OOPs + project walkthrough. HR: standard."
                ),
                "date": "2025-09-18",
            }
        ],
    ),
    _company(
        name="Cognizant",
        cluster="Service-based",
        hiring_process=(
            "## Cognizant Interview Process\n\n"
            "1. **Superset Assessment** — aptitude + verbal + SQL + 2 DSA, 100 min.\n"
            "2. **Technical Interview** (basic DSA + project).\n"
            "3. **HR Interview**.\n"
            "4. **Offer** (GenC / GenC Elevate / GenC Pro based on assessment)."
        ),
        oa_pattern=(
            "Superset: 4 sections — aptitude (24 Q, 35 min), SQL (15 Q, 20 min), "
            "automata-fix (7 Q, 20 min) + 2 DSA problems (45 min). Performance on DSA determines track."
        ),
        frequent_dsa_topics=["Arrays", "Strings", "Stacks", "Queues", "SQL"],
        core_cs_subjects=["DBMS", "OS", "OOP", "SQL"],
        resume_requirements=(
            "60%+ throughout. GenC Elevate / Pro tracks expect 100+ DSA problems + 1 solid project. "
            "Resume: highlight SQL fluency, 1 project with a database component."
        ),
        interview_experiences=[
            {
                "title": "Cognizant GenC Elevate",
                "source": "GeeksforGeeks",
                "summary": (
                    "Superset cleared → Elevate interview. Technical: stack-balanced-parentheses + "
                    "SQL (joins + group-by) + project walkthrough. HR: standard Cognizant behavioural."
                ),
                "date": "2025-10-01",
            }
        ],
    ),
    _company(
        name="Accenture",
        cluster="Service-based",
        hiring_process=(
            "## Accenture Interview Process\n\n"
            "1. **Accenture Online Assessment** — cognitive + verbal + coding, 90 min.\n"
            "2. **Technical Interview**.\n"
            "3. **HR / Behavioural Interview**.\n"
            "4. **Offer** (Associate Software Engineer or ASE Advanced)."
        ),
        oa_pattern=(
            "Online assessment: 3 sections — cognitive + technical (90 Q, 90 min) covering aptitude, "
            "verbal, MS Office basics, pseudocode, networking fundamentals. Coding round has 1–2 DSA "
            "problems (45 min)."
        ),
        frequent_dsa_topics=["Arrays", "Strings", "Basic Patterns", "Pseudocode"],
        core_cs_subjects=["DBMS", "OS", "OOP", "CN"],
        resume_requirements=(
            "60%+ throughout, no active backlogs. ASE Advanced track requires strong coding. "
            "Resume: highlight 1 project, certifications (Java/Python/AWS Cloud Practitioner), "
            "and any hackathon participation."
        ),
        interview_experiences=[
            {
                "title": "Accenture ASE Advanced",
                "source": "IndiaBix",
                "summary": (
                    "Online test cleared for ASE Advanced. Technical: 1 DSA (max-subarray-sum) + "
                    "OOP concepts + project walkthrough. HR: behavioural + standard questions."
                ),
                "date": "2025-07-25",
            }
        ],
    ),
    # ---------------------------------------------------------------- FinTech
    _company(
        name="Razorpay",
        cluster="FinTech",
        hiring_process=(
            "## Razorpay Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Online Assessment** (2 DSA, 75 min, HackerRank).\n"
            "3. **Technical Phone Screen** (~60 min, DSA + design).\n"
            "4. **Onsite** (4 rounds): 2 DSA, 1 LLD, 1 HLD.\n"
            "5. **Managerial + Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) on HackerRank. 75 minutes. Razorpay likes greedy + string problems. "
            "They grade on test coverage (hidden test cases count)."
        ),
        frequent_dsa_topics=["Arrays", "Greedy", "Strings", "Hash Maps", "DP"],
        core_cs_subjects=["DBMS", "System Design", "Distributed Systems"],
        resume_requirements=(
            "Razorpay values ownership + 'founder mindset'. Show projects with payment / fintech context "
            "if possible. Go/Rust experience is a plus. Resume should quantify impact."
        ),
        interview_experiences=[
            {
                "title": "Razorpay SDE-1 — Payments",
                "source": "LeetCode Discuss",
                "summary": (
                    "OA: 2 problems (interval-scheduling + string compression variant). "
                    "Phone: trie-based-autocomplete. Onsite: 2 DSA (LRU variant, graph shortest-path), "
                    "1 LLD (design payment-router), 1 HLD (design payment-gateway at 10k TPS)."
                ),
                "date": "2025-08-12",
            }
        ],
    ),
    _company(
        name="Stripe",
        cluster="FinTech",
        hiring_process=(
            "## Stripe Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Manager Call** (~45 min, behavioural + coding-style).\n"
            "3. **Take-home / Pair Programming** (Stripe is famous for the 'bug-fix' pair-programming round).\n"
            "4. **Onsite** (4 rounds): 1 pair-programming (bug fix), 1 system design, 1 integration/debugging, 1 behavioural.\n"
            "5. **Offer**.\n\n"
            "Stripe rarely asks textbook DSA — they grade on engineering judgement."
        ),
        oa_pattern=(
            "No standard OA. Instead, a pair-programming bug-fix session where you fix a real (anonymised) "
            "bug in a Stripe codebase. ~90 minutes with an engineer."
        ),
        frequent_dsa_topics=["Hash Maps", "Strings", "API Design"],
        core_cs_subjects=["System Design", "API Design", "Distributed Systems"],
        resume_requirements=(
            "Stripe hires for engineering judgement over algorithmic speed. Resume should show shipped "
            "products, debugging war stories, and a bias for simple systems. Open-source contributions "
            "weight heavily."
        ),
        interview_experiences=[
            {
                "title": "Stripe Backend Engineer — Pair Programming",
                "source": "Blind",
                "summary": (
                    "Manager call: behavioural + 'how would you design an idempotency key'. "
                    "Pair programming: 90 min debugging a real Stripe-like bug in a payments service. "
                    "Onsite: 1 system design (design webhook retry), 1 integration (build against a Stripe "
                    "API), 1 behavioural."
                ),
                "date": "2025-06-08",
            }
        ],
    ),
    _company(
        name="PayPal",
        cluster="FinTech",
        hiring_process=(
            "## PayPal Interview Process\n\n"
            "1. **Online Assessment** (2 DSA + 1 SQL, 90 min).\n"
            "2. **Technical Interview R1** (DSA).\n"
            "3. **Technical Interview R2** (LLD / system design).\n"
            "4. **Managerial + Behavioural**.\n"
            "5. **HR + Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) + 1 SQL query on HackerRank. 90 minutes. "
            "PayPal is Java-heavy — Java fluency is graded."
        ),
        frequent_dsa_topics=["Arrays", "Strings", "Trees", "SQL", "Hash Maps"],
        core_cs_subjects=["DBMS", "Java", "System Design", "OOP"],
        resume_requirements=(
            "Java proficiency strongly preferred. Show 1+ project with a Spring/Hibernate stack. "
            "Distributed systems experience (caching, queues, idempotency) is a plus for senior roles."
        ),
        interview_experiences=[
            {
                "title": "PayPal SDE-2 — Chennai",
                "source": "Glassdoor",
                "summary": (
                    "OA: 2 DSA (subarray-sum + graph-bfs) + SQL (top-3-merchants-by-volume). "
                    "R1: DSA (LRU cache). R2: LLD (design a payment retry system). "
                    "Managerial: deep on past project + on-call scenarios."
                ),
                "date": "2025-07-15",
            }
        ],
    ),
    _company(
        name="Zerodha",
        cluster="FinTech",
        hiring_process=(
            "## Zerodha Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Take-home Assignment** (small but real — e.g. 'build a portfolio tracker').\n"
            "3. **Technical Discussion** (review of take-home + DSA).\n"
            "4. **System Design** (1 round, focused on Kite-scale problems).\n"
            "5. **Founder Round + Offer**.\n\n"
            "Zerodha is a small, senior-only team. No standard OA, no multiple-choice."
        ),
        oa_pattern=(
            "No OA. Take-home assignment (3–5 hours): build a small, real feature end-to-end. "
            "Examples: order-book visualiser, portfolio calculator, alerts service. Graded on "
            "code quality + simplicity."
        ),
        frequent_dsa_topics=["Hash Maps", "Heaps", "Strings", "Concurrency"],
        core_cs_subjects=["System Design", "Distributed Systems", "DBMS"],
        resume_requirements=(
            "Zerodha values generalists who ship. Resume should show full-stack projects with "
            "real users (even small ones). No junior/new-grad pipeline — minimum 2 years experience."
        ),
        interview_experiences=[
            {
                "title": "Zerodha Backend Engineer — Kite",
                "source": "Twitter",
                "summary": (
                    "Take-home: build a WebSocket ticker mock + portfolio calc. 3 hours. "
                    "Technical: review of take-home (why this data structure, how would you scale to 1M "
                    "users). System design: design real-time OHLC chart. Founder round: culture fit."
                ),
                "date": "2025-05-30",
            }
        ],
    ),
    _company(
        name="PhonePe",
        cluster="FinTech",
        hiring_process=(
            "## PhonePe Interview Process\n\n"
            "1. **Online Assessment** (2 DSA + 1 SQL, 90 min, HackerRank).\n"
            "2. **Technical Interview R1** (DSA + problem-solving).\n"
            "3. **Technical Interview R2** (LLD).\n"
            "4. **System Design (HLD)**.\n"
            "5. **Managerial + HR + Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) + 1 SQL on HackerRank. 90 minutes. "
            "PhonePe grades on test coverage and clean code."
        ),
        frequent_dsa_topics=["Arrays", "Hash Maps", "Trees", "Strings", "SQL"],
        core_cs_subjects=["DBMS", "System Design", "Distributed Systems"],
        resume_requirements=(
            "PhonePe is high-scale (10M+ DAU). Resume should highlight any scale you've worked with. "
            "Java/Kotlin preferred for Android, Go/Java for backend."
        ),
        interview_experiences=[
            {
                "title": "PhonePe SDE-1 — Backend",
                "source": "LeetCode Discuss",
                "summary": (
                    "OA: 2 problems (anagrams-group + min-window-substring) + SQL (top-users-by-volume). "
                    "R1: DSA (kth-largest-in-array). R2: LLD (design UPI payment router). "
                    "HLD: design PhonePe notifications at scale. Managerial: standard behavioural."
                ),
                "date": "2025-09-05",
            }
        ],
    ),
    # -------------------------------------------------------------- Startups
    _company(
        name="CRED",
        cluster="Startups",
        hiring_process=(
            "## CRED Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Take-home / Online Assessment** (team-dependent).\n"
            "3. **Technical Interview R1** (DSA + LLD).\n"
            "4. **Technical Interview R2** (system design).\n"
            "5. **Founder / Culture Round + Offer**.\n\n"
            "CRED is famous for high talent density and a tough culture bar."
        ),
        oa_pattern=(
            "Team-dependent. Some teams use a take-home (build a small feature), others use 2 DSA problems "
            "on HackerRank. CRED grades heavily on code quality and product sense."
        ),
        frequent_dsa_topics=["Arrays", "Hash Maps", "Strings", "Trees"],
        core_cs_subjects=["System Design", "DBMS", "Distributed Systems"],
        resume_requirements=(
            "CRED values 'founder energy' — show projects you shipped end-to-end. Side projects and "
            "open-source contributions matter more than academic credentials. Resume: 1 page, "
            "high-signal bullets only."
        ),
        interview_experiences=[
            {
                "title": "CRED SDE-1 — Backend",
                "source": "Blind",
                "summary": (
                    "Take-home: build a credit-card-bill-reminder service. 4 hours. "
                    "R1: review take-home + LLD (design the reminder scheduler). "
                    "R2: HLD (design at 1M users). Founder round: deep on why CRED."
                ),
                "date": "2025-08-19",
            }
        ],
    ),
    _company(
        name="Zepto",
        cluster="Startups",
        hiring_process=(
            "## Zepto Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Online Assessment** (2 DSA, 60 min).\n"
            "3. **Technical Interview R1** (DSA + problem-solving).\n"
            "4. **Technical Interview R2** (LLD / system design).\n"
            "5. **Founder / Managerial + Offer**.\n\n"
            "Zepto moves fast — total cycle typically under 2 weeks."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) on HackerRank. 60 minutes. Zepto likes graph + greedy problems."
        ),
        frequent_dsa_topics=["Graphs", "Greedy", "Arrays", "Hash Maps", "Strings"],
        core_cs_subjects=["DBMS", "System Design", "Distributed Systems"],
        resume_requirements=(
            "Zepto is a high-growth startup — show ownership and bias for action. Resume should highlight "
            "shipped projects with measurable impact. Go/Kotlin preferred for backend."
        ),
        interview_experiences=[
            {
                "title": "Zepto SDE-1 — Quick Commerce",
                "source": "GeeksforGeeks",
                "summary": (
                    "OA: 2 problems (course-schedule + minimum-window-substring). "
                    "R1: DSA (LRU cache variant). R2: LLD (design order-routing to nearest dark store). "
                    "Founder round: why Zepto, what would you improve in the app."
                ),
                "date": "2025-09-25",
            }
        ],
    ),
    _company(
        name="Zomato",
        cluster="Startups",
        hiring_process=(
            "## Zomato Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Online Assessment** (2 DSA + 1 SQL, 90 min, HackerRank).\n"
            "3. **Technical Interview R1** (DSA).\n"
            "4. **Technical Interview R2** (LLD / HLD).\n"
            "5. **Managerial + HR + Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) + 1 SQL on HackerRank. 90 minutes. "
            "Zomato grades on clean, idiomatic code (Java/Kotlin/Go)."
        ),
        frequent_dsa_topics=["Arrays", "Hash Maps", "Trees", "Strings", "SQL"],
        core_cs_subjects=["DBMS", "System Design", "Distributed Systems"],
        resume_requirements=(
            "Zomato values product-minded engineers. Show projects where you made product decisions, "
            "not just implementation. Hyperlocal / marketplace exposure is a plus."
        ),
        interview_experiences=[
            {
                "title": "Zomato SDE-1 — Hyperpure",
                "source": "Glassdoor",
                "summary": (
                    "OA: 2 DSA (group-anagrams + valid-bst) + SQL (top-restaurants-by-region). "
                    "R1: DSA (sliding-window-maximum). R2: LLD (design a B2B order-management system). "
                    "Managerial: deep on past project + product thinking."
                ),
                "date": "2025-07-22",
            }
        ],
    ),
    _company(
        name="Pine Labs",
        cluster="Startups",
        hiring_process=(
            "## Pine Labs Interview Process\n\n"
            "1. **Online Assessment** (2 DSA + 1 SQL, 90 min).\n"
            "2. **Technical Interview R1** (DSA + problem-solving).\n"
            "3. **Technical Interview R2** (LLD / HLD).\n"
            "4. **Managerial + Behavioural**.\n"
            "5. **HR + Offer**."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) + 1 SQL query on HackerRank. 90 minutes. "
            "Pine Labs is POS / payments focused — SQL fluency expected."
        ),
        frequent_dsa_topics=["Arrays", "Strings", "Hash Maps", "Trees", "SQL"],
        core_cs_subjects=["DBMS", "System Design", "Java", "OOP"],
        resume_requirements=(
            "Java/Spring proficiency strongly preferred. Resume should highlight any payments / POS / "
            "retail-tech exposure. Pine Labs values stability + reliability over flash."
        ),
        interview_experiences=[
            {
                "title": "Pine Labs SDE-2 — POS Platform",
                "source": "GeeksforGeeks",
                "summary": (
                    "OA: 2 DSA (max-subarray + valid-parentheses) + SQL (top-merchants-by-txns). "
                    "R1: DSA (trie-based-autocomplete). R2: LLD (design a POS transaction log). "
                    "Managerial: deep on past project + on-call scenarios."
                ),
                "date": "2025-08-30",
            }
        ],
    ),
    _company(
        name="Groww",
        cluster="Startups",
        hiring_process=(
            "## Groww Interview Process\n\n"
            "1. **Recruiter Screen** (~30 min).\n"
            "2. **Online Assessment** (2 DSA, 75 min, HackerRank).\n"
            "3. **Technical Interview R1** (DSA + LLD).\n"
            "4. **Technical Interview R2** (HLD).\n"
            "5. **Founder / Managerial + Offer**.\n\n"
            "Groww is Android-heavy — mobile engineers are in high demand."
        ),
        oa_pattern=(
            "2 DSA problems (Medium) on HackerRank. 75 minutes. Groww grades on test coverage and "
            "edge-case handling. Mobile roles get a separate Android-specific round."
        ),
        frequent_dsa_topics=["Arrays", "Hash Maps", "Strings", "Trees", "Heaps"],
        core_cs_subjects=["DBMS", "System Design", "Android", "OOP"],
        resume_requirements=(
            "Groww values product-minded engineers who ship. Resume should highlight shipped features "
            "with measurable impact. Kotlin/Compose experience is a strong plus for mobile roles."
        ),
        interview_experiences=[
            {
                "title": "Groww SDE-1 — Android",
                "source": "LeetCode Discuss",
                "summary": (
                    "OA: 2 problems (LRU cache + min-stack). R1: DSA + LLD (design a watchlist component "
                    "with offline cache). R2: HLD (design real-time stock-price streaming). "
                    "Founder round: why Groww + product critique of the app."
                ),
                "date": "2025-09-12",
            }
        ],
    ),
]


def upgrade() -> None:
    """Insert all 25 seeded companies.

    Idempotency: this migration is part of the baseline. Running `alembic
    upgrade head` on a fresh DB inserts these once. To make re-runs safe
    (e.g. if someone downgrades and upgrades again), we DELETE the seeded
    rows first by name + is_custom=false. User-created custom companies
    are not affected.
    """
    # Idempotent pre-clean: only removes seeded rows, never user-added ones.
    op.execute(
        "DELETE FROM companies WHERE is_custom = FALSE AND name IN ("
        + ", ".join(f"'{c['name']}'" for c in COMPANIES)
        + ")"
    )

    companies_table = sa.table(
        "companies",
        sa.column("name", sa.String),
        sa.column("cluster", sa.String),
        sa.column("hiring_process", sa.Text),
        sa.column("oa_pattern", sa.Text),
        sa.column("frequent_dsa_topics", postgresql.ARRAY(sa.String)),
        sa.column("core_cs_subjects", postgresql.ARRAY(sa.String)),
        sa.column("resume_requirements", sa.Text),
        sa.column("interview_experiences", postgresql.JSONB),
        sa.column("is_custom", sa.Boolean),
        sa.column("created_by", postgresql.UUID(as_uuid=True)),
    )
    op.bulk_insert(companies_table, COMPANIES)


def downgrade() -> None:
    """Remove seeded companies. User-added custom companies are untouched."""
    op.execute(
        "DELETE FROM companies WHERE is_custom = FALSE AND name IN ("
        + ", ".join(f"'{c['name']}'" for c in COMPANIES)
        + ")"
    )
