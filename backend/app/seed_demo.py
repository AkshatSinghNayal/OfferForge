"""Seed demo data: user + DSA problems + resources + notes + tracked companies.

Idempotent — creates the demo user + demo data only once. On subsequent calls
it just returns the existing demo user without duplicating data.

Usage from the auth router:
    from app.seed_demo import seed_demo_data
    user = await seed_demo_data(session)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.activity_log import ActivityLog
from app.models.company import CHECKLIST_ITEMS, ChecklistItem, Company, UserCompany
from app.models.dsa import DsaProblem, DsaProblemTag, DsaTag
from app.models.note import Note
from app.models.resource import Resource
from app.models.resume import Resume
from app.models.user import User

DEMO_EMAIL = "demo@offerforge.dev"
DEMO_PASSWORD = "Demo@123"
DEMO_FULL_NAME = "Demo User"

# ── DSA problems (exactly 18 problems, all Solved) ───────────────────────────
# (title, platform, url, difficulty, status, revision_status, notes, [tags])
PROBLEMS: list[tuple[str, str, str, str, str, str, str, list[str]]] = [
    ("Two Sum", "LeetCode", "https://leetcode.com/problems/two-sum/", "Easy", "Solved", "Done", "Classic O(n) hashmap solution", ["Arrays", "Hash Maps"]),
    ("Best Time to Buy and Sell Stock", "LeetCode", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/", "Easy", "Solved", "None", "Single pass tracking min", ["Arrays"]),
    ("Maximum Subarray", "LeetCode", "https://leetcode.com/problems/maximum-subarray/", "Medium", "Solved", "Done", "Kadane's algorithm O(n)", ["Arrays", "Dynamic Programming"]),
    ("Product of Array Except Self", "LeetCode", "https://leetcode.com/problems/product-of-array-except-self/", "Medium", "Solved", "None", "Prefix + suffix products", ["Arrays"]),
    ("N-Queens", "LeetCode", "https://leetcode.com/problems/n-queens/", "Hard", "Solved", "None", "Classic backtracking", ["Recursion"]),
    ("Subset Sum Problem", "GFG", "https://www.geeksforgeeks.org/subset-sum-problem-dp-25/", "Medium", "Solved", "None", "Classic DP", ["Dynamic Programming"]),
    ("Number of Islands", "LeetCode", "https://leetcode.com/problems/number-of-islands/", "Medium", "Solved", "None", "DFS flood-fill on grid", ["Graphs"]),
    ("Course Schedule", "LeetCode", "https://leetcode.com/problems/course-schedule/", "Medium", "Solved", "None", "Topological sort (Kahn's)", ["Greedy"]),
    ("Valid Parentheses", "LeetCode", "https://leetcode.com/problems/valid-parentheses/", "Easy", "Solved", "Done", "Stack-based matching", ["Hash Maps"]),
    ("Longest Consecutive Sequence", "LeetCode", "https://leetcode.com/problems/longest-consecutive-sequence/", "Medium", "Solved", "Done", "HashSet O(n) approach", ["Hash Maps"]),
    ("LRU Cache", "LeetCode", "https://leetcode.com/problems/lru-cache/", "Medium", "Solved", "None", "DLL + hashmap", ["Hash Maps"]),
    ("Minimum Window Substring", "LeetCode", "https://leetcode.com/problems/minimum-window-substring/", "Hard", "Solved", "None", "Sliding window", ["Hash Maps"]),
    ("Valid Anagram", "LeetCode", "https://leetcode.com/problems/valid-anagram/", "Easy", "Solved", "None", "Hash map frequency count", ["Hash Maps"]),
    ("Group Anagrams", "LeetCode", "https://leetcode.com/problems/group-anagrams/", "Medium", "Solved", "None", "Categorize by sorted string", ["Hash Maps"]),
    ("Merge Two Sorted Lists", "LeetCode", "https://leetcode.com/problems/merge-two-sorted-lists/", "Easy", "Solved", "None", "Iterative with dummy head", ["Linked Lists", "Recursion"]),
    ("Maximum Depth of Binary Tree", "LeetCode", "https://leetcode.com/problems/maximum-depth-of-binary-tree/", "Easy", "Solved", "None", "Recursive DFS", ["Recursion"]),
    ("Invert Binary Tree", "LeetCode", "https://leetcode.com/problems/invert-binary-tree/", "Easy", "Solved", "None", "Swap children recursively", ["Recursion"]),
    ("Reverse Linked List", "LeetCode", "https://leetcode.com/problems/reverse-linked-list/", "Easy", "Solved", "None", "Iterative pointer reversal", ["Linked Lists"]),
]

# ── Resources (exactly 6 resources) ──────────────────────────────────────────
RESOURCES: list[tuple[str, str, str, str]] = [
    ("Google Careers", "https://careers.google.com/", "Career Portal", "Official Google job listings and applications"),
    ("LinkedIn Jobs", "https://www.linkedin.com/jobs/", "Career Portal", "Network-driven job search platform"),
    ("Striver's SDE Sheet", "https://takeuforward.org/interviews/strivers-sde-sheet-top-coding-interview-problems/", "Coding Sheet", "Comprehensive DSA sheet for placement prep — 450+ problems"),
    ("Blind 75", "https://leetcode.com/discuss/general-discussion/460599/blind-75-leetcode-questions", "Coding Sheet", "Curated list of 75 most frequently asked LeetCode problems"),
    ("InterviewBit", "https://www.interviewbit.com/", "Interview Prep", "Structured DSA + system design prep with company-wise questions"),
    ("Pramp", "https://www.pramp.com/", "Interview Prep", "Free peer-to-peer mock interviews with real-time feedback"),
]

# ── Notes (exactly 6 notes) ───────────────────────────────────────────────────
# (title, type, content, company_name or None)
NOTES: list[tuple[str, str, str, str | None]] = [
    ("Google Interview Strategy", "Interview Note",
     "## Key Points\n\n- Focus on communication during DSA rounds — explain trade-offs\n- Use STARR framework for behavioural questions\n- Practice Googliness questions: leadership, collaboration, conflict\n- System design: start with requirements, go broad then deep\n- Expect 4-5 rounds: 3-4 DSA, 1 System Design, 1 Googliness",
     "Google"),
    ("Meta Onsite Preparation", "Interview Note",
     "## Meta-specific Tips\n\n- Coding in CoderPad (no autocomplete, practice writing code from scratch)\n- Expect 2 DSA + 1 System Design + 1 Behavioural\n- Common problems: merge k sorted lists, LRU cache, word ladder\n- Interviewers want to see you iterate and improve solutions\n- Hiring Committee review takes 1-2 weeks after onsites",
     "Meta"),
    ("Dynamic Programming Patterns", "Concept",
     "## Common DP Patterns\n\n1. **Fibonacci-style**: climbing stairs, house robber, fibonacci numbers\n2. **Grid DP**: unique paths, minimum path sum, dungeon game\n3. **2D DP**: longest common subsequence, edit distance\n4. **Subset DP**: subset sum, partition equal subset sum, target sum\n5. **Interval DP**: matrix chain multiplication, burst balloons\n\n### Key Insight\nRecognise the pattern: if a problem asks for optimal/min/max or number of ways, it's likely DP. Start with recursion + memoisation, then optimise to tabulation.",
     None),
    ("Graph Algorithms Quick Reference", "Concept",
     "## Graph Traversal\n- **BFS**: shortest path in unweighted graphs, level-order\n- **DFS**: connectivity, cycle detection, topological sort\n\n## Shortest Path\n- **Dijkstra**: weighted, non-negative edges (PQ based)\n- **Bellman-Ford**: handles negative edges, detects negative cycles\n- **Floyd-Warshall**: all-pairs shortest path (DP)\n\n## Union Find\n- Kruskal's MST, connected components, redundant connections\n- Optimisations: path compression + union by rank",
     None),
    ("Week 12 Revision Plan", "Revision Schedule",
     "## Mon-Wed\n- Finish remaining DP problems: 5 left (subset, edit-distance, boolean-parenthesisation)\n- Revise Trees: BST validation, LCA, serialization, Morris traversal\n\n## Thu-Fri\n- System Design: design WhatsApp, design YouTube\n- HR prep: prepare stories for 'weakness', 'conflict', 'failure'\n\n## Sat-Sun\n- Mock interview with friend (2 DSA + 1 System Design)\n- Review all notes from the week",
     "Google"),
    ("Tell Me About Yourself — HR Prep", "HR Answer",
     "**Structure**: Present → Past → Future\n\n**Present**: 'I'm a final-year CS student passionate about building scalable systems...'\n**Past**: 'Previously interned at XYZ where I designed and built a real-time analytics dashboard serving 10k+ users, reducing report generation time by 80%.'\n**Future**: 'I'm looking to join a company where I can solve challenging problems at scale and continue growing as an engineer.'\n\n**Keep it**: under 60 seconds, highlight 2-3 key achievements, connect to the role.",
     None),
]

# ── Tracked companies (exactly 8 companies) ──────────────────────────
# (name, application_status, deadline_days_from_now, [done_checklist_keys])
TRACKED_COMPANIES: list[tuple[str, str, int | None, list[str]]] = [
    ("Atlassian", "OA Received", 44, []),  # 0% (0 completed checks)
    ("Razorpay", "Researching", 6, ["resume_tailored", "resume_ats_checked", "projects_revised"]),  # 20% (3 completed checks)
    ("Microsoft", "Applied", 29, ["resume_tailored", "applied"]),  # 13.3% (2 completed checks)
    ("Google", "Interview Scheduled", 13, ["resume_tailored", "resume_ats_checked", "applied", "dsa_sheet_completed", "oa_practice_completed", "interview_scheduled"]),  # 40% (6 completed checks)
    ("Amazon", "Applied", None, []),  # 0% (0 completed checks)
    ("Meta", "OA Received", None, []),  # 0% (0 completed checks)
    ("Stripe", "Applied", None, []),  # 0% (0 completed checks)
    ("Swiggy", "Rejected", None, []),  # Rejected (terminal)
]


async def seed_demo_data(session: AsyncSession) -> User:
    """Seed demo data if it does not yet exist. Returns the demo user."""
    existing = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if existing is not None:
        # Wipe old demo data so updated dates take effect on re-seed
        await session.delete(existing)
        await session.commit()

    # ── 1. Demo user ──────────────────────────────────────────────────────────
    demo = User(
        email=DEMO_EMAIL,
        full_name=DEMO_FULL_NAME,
        hashed_password=await hash_password(DEMO_PASSWORD),
        google_sub=None,
        is_active=True,
    )
    session.add(demo)
    await session.flush()

    # ── 2. Mock Active Resume (for 40% Resume readiness) ──────────────────────
    resume = Resume(
        user_id=demo.id,
        version_label="SDE Resume v1.0",
        pdf_data=b"%PDF-1.4 mock pdf data",
        is_active=True,
    )
    session.add(resume)
    await session.flush()

    # ── 3. DSA tags (reuse existing, create missing) ───────────────────────
    tag_names = [
        "Arrays", "Strings", "Trees", "Graphs", "Dynamic Programming",
        "Hash Maps", "Two Pointers", "Heaps", "Stacks", "Linked Lists",
        "Greedy", "Binary Search", "Sliding Window", "Recursion", "Divide and Conquer",
    ]
    tag_map: dict[str, DsaTag] = {}
    for name in tag_names:
        tag = await session.scalar(select(DsaTag).where(func.lower(DsaTag.name) == name.lower()))
        if tag is None:
            tag = DsaTag(name=name)
            session.add(tag)
            await session.flush()
        tag_map[name] = tag

    # ── 4. Dynamic Date Set Formulator (guarantees streak & weekly target) ──────
    now = datetime.now(timezone.utc)
    today = now.date()

    # Base active dates to guarantee streak logic:
    # - Today is active
    # - Yesterday (today-1) and today-2 are inactive -> current streak = 1
    # - days -3 to -9 are active -> longest streak = 7
    # - day -10 is inactive
    active_dates = {today}
    for i in range(3, 10):
        active_dates.add(today - timedelta(days=i))

    # Add isolated active dates to prevent longer streaks, separated by >=2 days
    monday_0 = today - timedelta(days=today.weekday())
    for w in (2, 3, 4):
        monday_w = monday_0 - timedelta(weeks=w)
        for d_offset in (1, 2, 3, 4):
            active_dates.add(monday_w + timedelta(days=d_offset))

    # Map active dates by week ago:
    def get_weeks_ago(d: date) -> int:
        monday_d = d - timedelta(days=d.weekday())
        monday_today = today - timedelta(days=today.weekday())
        return (monday_today - monday_d).days // 7

    active_dates_by_week = {i: [] for i in range(5)}
    for d in active_dates:
        wa = get_weeks_ago(d)
        if wa in active_dates_by_week:
            active_dates_by_week[wa].append(d)
        else:
            active_dates_by_week[4].append(d)

    # Sort them deterministically
    for wa in range(5):
        active_dates_by_week[wa].sort()

    # Calculate target counts per week:
    week_targets = {0: 12, 1: 12, 2: 6, 3: 10, 4: 4}
    date_counts = {d: 1 for d in active_dates}

    week_current = {i: 0 for i in range(5)}
    for d in active_dates:
        wa = get_weeks_ago(d)
        if wa in week_current:
            week_current[wa] += 1

    for wa in range(5):
        needed = week_targets[wa] - week_current[wa]
        if needed > 0 and active_dates_by_week[wa]:
            date_counts[active_dates_by_week[wa][0]] += needed

    # Solved dates for DSA problems:
    # 18 problems, so we use all active dates except the oldest one
    sorted_active_dates = sorted(list(active_dates))
    solved_dates = [datetime.combine(d, datetime.min.time(), timezone.utc) + timedelta(hours=10) for d in sorted_active_dates[1:]]

    # ── 5. DSA problems + tags ───────────────────────────────────────────────
    problem_tag_pairs: list[tuple[DsaProblem, list[str]]] = []
    solved_problem_info = []
    solved_idx = 0
    for title, platform, url, difficulty, status, revision, notes, tags in PROBLEMS:
        completed_at = None
        if status == "Solved":
            completed_at = solved_dates[solved_idx] if solved_idx < len(solved_dates) else now
            solved_idx += 1
            solved_problem_info.append((title, difficulty, completed_at))
        problem = DsaProblem(
            user_id=demo.id,
            title=title,
            platform=platform,
            external_url=url,
            difficulty=difficulty,
            status=status,
            revision_status=revision,
            notes=notes or None,
            completed_at=completed_at,
        )
        session.add(problem)
        await session.flush()
        problem_tag_pairs.append((problem, tags))

    for problem, tags in problem_tag_pairs:
        for tag_name in tags:
            tag = tag_map.get(tag_name)
            if tag is not None:
                session.add(DsaProblemTag(dsa_problem_id=problem.id, dsa_tag_id=tag.id))
    await session.flush()

    # ── 6. Resources ──────────────────────────────────────────────────────────
    for title, url, category, description in RESOURCES:
        session.add(Resource(
            user_id=demo.id,
            title=title,
            url=url,
            category=category,
            description=description,
        ))
    await session.flush()

    # ── 7. Notes ──────────────────────────────────────────────────────────────
    for title, note_type, content, company_name in NOTES:
        company_id = None
        if company_name is not None:
            company = await session.scalar(select(Company).where(Company.name == company_name))
            # Create dynamically if missing (e.g. Microsoft)
            if company is None:
                company = Company(
                    name=company_name,
                    cluster="Product-based" if company_name in ("Atlassian", "Microsoft") else "FAANG",
                    hiring_process="Standard hiring process",
                    oa_pattern="Standard OA pattern",
                    frequent_dsa_topics=["Arrays", "Hashing"],
                    core_cs_subjects=["DBMS", "OS"],
                    resume_requirements="Tailored resume",
                    is_custom=False,
                )
                session.add(company)
                await session.flush()
            company_id = company.id

        session.add(Note(
            user_id=demo.id,
            title=title,
            content=content,
            type=note_type,
            company_id=company_id,
        ))
    await session.flush()

    # ── 8. Tracked companies + checklist items ────────────────────────────────
    # Insert in order with increasing creation timestamps so sort order matches exactly
    for idx, (company_name, status, deadline_days, done_keys) in enumerate(TRACKED_COMPANIES):
        company = await session.scalar(select(Company).where(Company.name == company_name))
        if company is None:
            company = Company(
                name=company_name,
                cluster="Product-based" if company_name in ("Atlassian", "Microsoft") else "FAANG",
                hiring_process="Standard hiring process",
                oa_pattern="Standard OA pattern",
                frequent_dsa_topics=["Arrays", "Hashing"],
                core_cs_subjects=["DBMS", "OS"],
                resume_requirements="Tailored resume",
                is_custom=False,
            )
            session.add(company)
            await session.flush()

        deadline = None
        if deadline_days is not None:
            deadline = datetime.now(timezone.utc) + timedelta(days=deadline_days)

        uc = UserCompany(
            user_id=demo.id,
            company_id=company.id,
            application_status=status,
            deadline=deadline,
            created_at=now - timedelta(minutes=idx),
        )
        session.add(uc)
        await session.flush()

        for item_key, label in CHECKLIST_ITEMS:
            session.add(ChecklistItem(
                user_company_id=uc.id,
                item_key=item_key,
                label=label,
                is_done=item_key in done_keys,
                completed_at=now - timedelta(days=15) if item_key in done_keys else None
            ))
    await session.flush()

    # ── 9. Activity log (exactly 26 non-DSA activities, total 44 logs) ──────────
    extra_activities = [
        ("company_tracked", "company", {"company_name": "Swiggy", "cluster": "Product-based", "application_status": "Rejected"}),
        ("company_tracked", "company", {"company_name": "Stripe", "cluster": "FinTech", "application_status": "Applied"}),
        ("company_tracked", "company", {"company_name": "Meta", "cluster": "FAANG", "application_status": "OA Received"}),
        ("company_tracked", "company", {"company_name": "Amazon", "cluster": "FAANG", "application_status": "Applied"}),
        ("company_tracked", "company", {"company_name": "Google", "cluster": "FAANG", "application_status": "Interview Scheduled"}),
        ("company_tracked", "company", {"company_name": "Razorpay", "cluster": "FinTech", "application_status": "Researching"}),
        ("company_tracked", "company", {"company_name": "Atlassian", "cluster": "Product-based", "application_status": "OA Received"}),
        ("company_tracked", "company", {"company_name": "Microsoft", "cluster": "Product-based", "application_status": "Applied"}),
        
        ("checklist_item_completed", "checklist", {"company_name": "Google", "item_key": "resume_tailored"}),
        ("checklist_item_completed", "checklist", {"company_name": "Google", "item_key": "resume_ats_checked"}),
        ("checklist_item_completed", "checklist", {"company_name": "Meta", "item_key": "resume_tailored"}),
        ("checklist_item_completed", "checklist", {"company_name": "Meta", "item_key": "resume_ats_checked"}),
        ("checklist_item_completed", "checklist", {"company_name": "Amazon", "item_key": "resume_tailored"}),
        ("checklist_item_completed", "checklist", {"company_name": "Swiggy", "item_key": "resume_tailored"}),
        
        ("note_created", "note", {"title": "Google Interview Strategy", "note_type": "Interview Note"}),
        ("note_created", "note", {"title": "Meta Onsite Preparation", "note_type": "Interview Note"}),
        ("note_created", "note", {"title": "Dynamic Programming Patterns", "note_type": "Concept"}),
        ("note_created", "note", {"title": "Graph Algorithms Quick Reference", "note_type": "Concept"}),
        ("note_created", "note", {"title": "Week 12 Revision Plan", "note_type": "Revision Schedule"}),
        ("note_created", "note", {"title": "Tell Me About Yourself — HR Prep", "note_type": "HR Answer"}),
        
        ("resource_added", "resource", {"title": "Google Careers", "category": "Career Portal"}),
        ("resource_added", "resource", {"title": "LinkedIn Jobs", "category": "Career Portal"}),
        ("resource_added", "resource", {"title": "Striver's SDE Sheet", "category": "Coding Sheet"}),
        ("resource_added", "resource", {"title": "Blind 75", "category": "Coding Sheet"}),
        ("resource_added", "resource", {"title": "InterviewBit", "category": "Interview Prep"}),
        ("resource_added", "resource", {"title": "Pramp", "category": "Interview Prep"}),
    ]

    extra_idx = 0
    solved_date_set = {sd.date() for sd in solved_dates}
    for d in sorted_active_dates:
        day_dt = datetime.combine(d, datetime.min.time(), timezone.utc) + timedelta(hours=12)
        has_dsa = (d in solved_date_set)
        needed_extra = date_counts[d] - 1 if has_dsa else date_counts[d]

        if has_dsa:
            p_title = "Two Sum"
            p_diff = "Easy"
            for title, diff, dt in solved_problem_info:
                if dt.date() == d:
                    p_title = title
                    p_diff = diff
                    break
            session.add(ActivityLog(
                user_id=demo.id,
                action="dsa_solved",
                entity_type="dsa_problem",
                entity_id=None,
                metadata_={"title": p_title, "difficulty": p_diff, "platform": "LeetCode"},
                created_at=day_dt
            ))

        for k in range(needed_extra):
            if extra_idx < len(extra_activities):
                action, entity_type, meta = extra_activities[extra_idx]
                extra_idx += 1
                session.add(ActivityLog(
                    user_id=demo.id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=None,
                    metadata_=meta,
                    created_at=day_dt + timedelta(hours=1 + k)
                ))

    await session.commit()
    await session.refresh(demo)
    return demo
