"""Seed demo data: user + DSA problems + resources + notes + tracked companies.

Idempotent — creates the demo user + demo data only once. On subsequent calls
it just returns the existing demo user without duplicating data.

Usage from the auth router:
    from app.seed_demo import seed_demo_data
    user = await seed_demo_data(session)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.activity_log import ActivityLog
from app.models.company import CHECKLIST_ITEMS, ChecklistItem, Company, UserCompany
from app.models.dsa import DsaProblem, DsaProblemTag, DsaTag
from app.models.note import Note
from app.models.resource import Resource
from app.models.user import User

DEMO_EMAIL = "demo@offerforge.dev"
DEMO_PASSWORD = "Demo@123"
DEMO_FULL_NAME = "Demo User"

# ── DSA problems ──────────────────────────────────────────────────────────────
# (title, platform, url, difficulty, status, revision_status, notes, [tags])
PROBLEMS: list[tuple[str, str, str, str, str, str, str, list[str]]] = [
    ("Two Sum", "LeetCode", "https://leetcode.com/problems/two-sum/", "Easy", "Solved", "Done", "Classic O(n) hashmap solution", ["Arrays", "Hash Maps"]),
    ("Valid Parentheses", "LeetCode", "https://leetcode.com/problems/valid-parentheses/", "Easy", "Solved", "Done", "Stack-based matching", ["Stacks", "Strings"]),
    ("Merge Two Sorted Lists", "LeetCode", "https://leetcode.com/problems/merge-two-sorted-lists/", "Easy", "Solved", "None", "Iterative with dummy head", ["Linked Lists", "Recursion"]),
    ("Maximum Depth of Binary Tree", "LeetCode", "https://leetcode.com/problems/maximum-depth-of-binary-tree/", "Easy", "Solved", "None", "Recursive DFS", ["Trees", "Recursion"]),
    ("Invert Binary Tree", "LeetCode", "https://leetcode.com/problems/invert-binary-tree/", "Easy", "Solved", "None", "Swap children recursively", ["Trees", "Recursion"]),
    ("Best Time to Buy and Sell Stock", "LeetCode", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/", "Easy", "Solved", "None", "Single pass tracking min", ["Arrays", "Greedy"]),
    ("Maximum Subarray", "LeetCode", "https://leetcode.com/problems/maximum-subarray/", "Medium", "Solved", "Done", "Kadane's algorithm O(n)", ["Arrays", "Dynamic Programming"]),
    ("Product of Array Except Self", "LeetCode", "https://leetcode.com/problems/product-of-array-except-self/", "Medium", "Solved", "None", "Prefix + suffix products", ["Arrays"]),
    ("Maximum Product Subarray", "LeetCode", "https://leetcode.com/problems/maximum-product-subarray/", "Medium", "Solved", "None", "Track min & max simultaneously", ["Arrays", "Dynamic Programming"]),
    ("Find Minimum in Rotated Sorted Array", "LeetCode", "https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/", "Medium", "Solved", "Done", "Binary search variant", ["Binary Search", "Arrays"]),
    ("Search in Rotated Sorted Array", "LeetCode", "https://leetcode.com/problems/search-in-rotated-sorted-array/", "Medium", "Solved", "None", "Modified binary search", ["Binary Search", "Arrays"]),
    ("3Sum", "LeetCode", "https://leetcode.com/problems/3sum/", "Medium", "Solved", "None", "Sort + two-pointer", ["Arrays", "Two Pointers"]),
    ("Container With Most Water", "LeetCode", "https://leetcode.com/problems/container-with-most-water/", "Medium", "In Progress", "None", "", ["Arrays", "Two Pointers", "Greedy"]),
    ("Longest Substring Without Repeating Characters", "LeetCode", "https://leetcode.com/problems/longest-substring-without-repeating-characters/", "Medium", "Solved", "Done", "Sliding window with set", ["Strings", "Sliding Window"]),
    ("Longest Palindromic Substring", "LeetCode", "https://leetcode.com/problems/longest-palindromic-substring/", "Medium", "Solved", "None", "Expand around centre", ["Strings", "Dynamic Programming"]),
    ("Word Break", "LeetCode", "https://leetcode.com/problems/word-break/", "Medium", "Marked for Revision", "Due", "DP + memoisation", ["Dynamic Programming", "Strings"]),
    ("Number of Islands", "LeetCode", "https://leetcode.com/problems/number-of-islands/", "Medium", "Solved", "None", "DFS flood-fill on grid", ["Graphs", "Recursion"]),
    ("Clone Graph", "LeetCode", "https://leetcode.com/problems/clone-graph/", "Medium", "Solved", "None", "BFS + hashmap", ["Graphs", "Hash Maps"]),
    ("Course Schedule", "LeetCode", "https://leetcode.com/problems/course-schedule/", "Medium", "Solved", "None", "Topological sort (Kahn's)", ["Graphs", "Greedy"]),
    ("Pacific Atlantic Water Flow", "LeetCode", "https://leetcode.com/problems/pacific-atlantic-water-flow/", "Medium", "In Progress", "None", "", ["Graphs", "Arrays"]),
    ("Longest Consecutive Sequence", "LeetCode", "https://leetcode.com/problems/longest-consecutive-sequence/", "Medium", "Solved", "Done", "HashSet O(n) approach", ["Arrays", "Hash Maps"]),
    ("Binary Tree Level Order Traversal", "LeetCode", "https://leetcode.com/problems/binary-tree-level-order-traversal/", "Medium", "Solved", "Done", "BFS with queue", ["Trees", "Recursion"]),
    ("Validate Binary Search Tree", "LeetCode", "https://leetcode.com/problems/validate-binary-search-tree/", "Medium", "Solved", "None", "In-order traversal check", ["Trees", "Recursion"]),
    ("Kth Smallest Element in a BST", "LeetCode", "https://leetcode.com/problems/kth-smallest-element-in-a-bst/", "Medium", "In Progress", "None", "", ["Trees", "Binary Search"]),
    ("LRU Cache", "LeetCode", "https://leetcode.com/problems/lru-cache/", "Medium", "Marked for Revision", "Due", "DLL + hashmap", ["Linked Lists", "Hash Maps"]),
    ("Subset Sum Problem", "GFG", "https://www.geeksforgeeks.org/subset-sum-problem-dp-25/", "Medium", "Solved", "None", "Classic DP", ["Dynamic Programming", "Arrays"]),
    ("Longest Common Subsequence", "GFG", "https://www.geeksforgeeks.org/longest-common-subsequence-dp-4/", "Medium", "Solved", "None", "2D DP table", ["Dynamic Programming", "Strings"]),
    ("Merge k Sorted Lists", "LeetCode", "https://leetcode.com/problems/merge-k-sorted-lists/", "Hard", "Not Started", "None", "", ["Heaps", "Linked Lists", "Divide and Conquer"]),
    ("Serialize and Deserialize Binary Tree", "LeetCode", "https://leetcode.com/problems/serialize-and-deserialize-binary-tree/", "Hard", "In Progress", "None", "", ["Trees", "Strings"]),
    ("Sliding Window Maximum", "LeetCode", "https://leetcode.com/problems/sliding-window-maximum/", "Hard", "Marked for Revision", "Due", "Deque-based O(n)", ["Arrays", "Sliding Window", "Heaps"]),
    ("Median of Two Sorted Arrays", "LeetCode", "https://leetcode.com/problems/median-of-two-sorted-arrays/", "Hard", "Not Started", "None", "", ["Binary Search", "Arrays"]),
    ("Minimum Window Substring", "LeetCode", "https://leetcode.com/problems/minimum-window-substring/", "Hard", "In Progress", "None", "", ["Strings", "Sliding Window", "Hash Maps"]),
    ("Word Ladder", "LeetCode", "https://leetcode.com/problems/word-ladder/", "Hard", "Marked for Revision", "Due", "BFS + pattern generation", ["Graphs", "Strings"]),
    ("Trapping Rain Water", "LeetCode", "https://leetcode.com/problems/trapping-rain-water/", "Hard", "Not Started", "None", "", ["Arrays", "Two Pointers", "Stacks"]),
    ("N-Queens", "LeetCode", "https://leetcode.com/problems/n-queens/", "Hard", "Not Started", "None", "", ["Recursion", "Arrays"]),
]

# ── Resources ─────────────────────────────────────────────────────────────────
RESOURCES: list[tuple[str, str, str, str]] = [
    ("Google Careers", "https://careers.google.com/", "Career Portal", "Official Google job listings and applications"),
    ("LinkedIn Jobs", "https://www.linkedin.com/jobs/", "Career Portal", "Network-driven job search platform"),
    ("Striver's SDE Sheet", "https://takeuforward.org/interviews/strivers-sde-sheet-top-coding-interview-problems/", "Coding Sheet", "Comprehensive DSA sheet for placement prep — 450+ problems"),
    ("Blind 75", "https://leetcode.com/discuss/general-discussion/460599/blind-75-leetcode-questions", "Coding Sheet", "Curated list of 75 most frequently asked LeetCode problems"),
    ("InterviewBit", "https://www.interviewbit.com/", "Interview Prep", "Structured DSA + system design prep with company-wise questions"),
    ("Pramp", "https://www.pramp.com/", "Interview Prep", "Free peer-to-peer mock interviews with real-time feedback"),
    ("NeetCode", "https://neetcode.io/", "YouTube", "Visual DSA explanations with roadmap and problem list"),
    ("takeUForward", "https://www.youtube.com/c/takeUforward", "YouTube", "A2Z DSA sheet with video solutions by Raj Vikramaditya"),
    ("DSA Patterns Cheatsheet", "https://github.com/ashishps1/awesome-leetcode-resources", "Notes", "Collection of DSA patterns, templates, and topic-wise resources"),
    ("System Design Primer", "https://github.com/donnemartin/system-design-primer", "Notes", "Comprehensive system design resource with examples at scale"),
    ("OOP Concepts Explained", "https://www.geeksforgeeks.org/object-oriented-programming-oops-concept-in-java/", "Article", "Core OOP concepts with Java examples — encapsulation, inheritance, polymorphism"),
    ("DBMS Interview Questions", "https://www.geeksforgeeks.org/dbms/", "Article", "Complete DBMS tutorial covering SQL, normalisation, transactions, indexing"),
]

# ── Notes ─────────────────────────────────────────────────────────────────────
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
    ("Daily Log — Day 15 of Prep", "Personal",
     "## Today's Progress\n\n**Solved**:\n- Minimum Window Substring (Hard) — finally cracked the sliding window approach\n- Course Schedule II — topological sort using Kahn's algorithm\n\n**Struggling with**:\n- DP on subsets, need more practice on partition problems\n\n**Tomorrow**: tackle 3 hard problems from Blind 75 + revise LRU cache\n\n**Mood**: Making steady progress, confidence building!",
     None),
    ("Project Ideas for Resume", "Personal",
     "## Shortlist\n\n1. **Real-time Chat App** — WebSocket + Redis pub/sub + React\n2. **URL Shortener** — with rate limiting, analytics dashboard, custom aliases\n3. **Portfolio Tracker** — live stock data via API, portfolio allocation charts\n4. **Mini Code Judge** — like LeetCode clone, sandboxed code execution\n\n### Decision\nGo with URL Shortener first — it covers system design, has clear scaling challenges, and shows full-stack capability. Deploy on AWS with Terraform.",
     None),
]

# ── Companies to track ────────────────────────────────────────────────────────
# (name, application_status, deadline_days_from_now, [done_checklist_keys])
TRACKED_COMPANIES: list[tuple[str, str, int | None, list[str]]] = [
    ("Google", "Interview Scheduled", 21, ["resume_tailored", "resume_ats_checked", "dsa_sheet_completed", "oa_practice_completed", "dbms_revised", "os_revised", "cn_revised", "oop_revised", "hr_questions_prepared", "projects_revised", "applied"]),
    ("Meta", "OA Received", 10, ["resume_tailored", "resume_ats_checked", "dsa_sheet_completed", "applied"]),
    ("Amazon", "Applied", None, ["resume_tailored", "resume_ats_checked", "applied"]),
    ("Razorpay", "Researching", None, ["resume_tailored"]),
    ("Stripe", "Not Started", None, []),
    ("Swiggy", "Rejected", None, ["resume_tailored", "resume_ats_checked", "dsa_sheet_completed", "oa_practice_completed", "applied", "oa_received"]),
]

# ── Activity log entries ──────────────────────────────────────────────────────
ACTIVITIES: list[tuple[str, str, dict | None]] = [
    ("company_tracked", "company", {"company_name": "Google", "cluster": "FAANG", "application_status": "Interview Scheduled"}),
    ("company_tracked", "company", {"company_name": "Meta", "cluster": "FAANG", "application_status": "OA Received"}),
    ("company_tracked", "company", {"company_name": "Amazon", "cluster": "FAANG", "application_status": "Applied"}),
    ("company_tracked", "company", {"company_name": "Razorpay", "cluster": "FinTech", "application_status": "Researching"}),
    ("company_tracked", "company", {"company_name": "Stripe", "cluster": "FinTech", "application_status": "Not Started"}),
    ("company_tracked", "company", {"company_name": "Swiggy", "cluster": "Product-based", "application_status": "Rejected"}),
    ("company_status_changed", "company", {"company_name": "Swiggy", "previous_status": "Applied", "new_status": "Rejected"}),
    ("dsa_solved", "dsa_problem", {"title": "Two Sum", "difficulty": "Easy", "platform": "LeetCode"}),
    ("dsa_solved", "dsa_problem", {"title": "Maximum Subarray", "difficulty": "Medium", "platform": "LeetCode"}),
    ("dsa_solved", "dsa_problem", {"title": "Number of Islands", "difficulty": "Medium", "platform": "LeetCode"}),
    ("dsa_solved", "dsa_problem", {"title": "Course Schedule", "difficulty": "Medium", "platform": "LeetCode"}),
    ("dsa_solved", "dsa_problem", {"title": "Longest Palindromic Substring", "difficulty": "Medium", "platform": "LeetCode"}),
    ("note_created", "note", {"title": "Google Interview Strategy", "note_type": "Interview Note"}),
    ("resource_added", "resource", {"title": "Striver's SDE Sheet", "category": "Coding Sheet"}),
    ("resource_added", "resource", {"title": "System Design Primer", "category": "Notes"}),
]


async def seed_demo_data(session: AsyncSession) -> User:
    """Seed demo data if it does not yet exist. Returns the demo user."""
    existing = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if existing is not None:
        # Wipe old demo data so updated dates take effect on re-seed
        await session.delete(existing)
        await session.flush()

    # ── 1. Demo user ──────────────────────────────────────────────────────────
    demo = User(
        email=DEMO_EMAIL,
        full_name=DEMO_FULL_NAME,
        hashed_password=hash_password(DEMO_PASSWORD),
        google_sub=None,
        is_active=True,
    )
    session.add(demo)
    await session.flush()

    # ── 2. DSA tags (reuse existing, create missing) ───────────────────────
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

    # ── 3. DSA problems + tags ───────────────────────────────────────────────
    problem_tag_pairs: list[tuple[DsaProblem, list[str]]] = []
    now = datetime.now(timezone.utc)
    solved_idx = 0
    # Spread solved dates evenly from June 18 to July 18
    jun_18 = datetime(2026, 6, 18, tzinfo=timezone.utc)
    solved_count = sum(1 for p in PROBLEMS if p[4] == "Solved")
    solved_dates = [
        jun_18 + timedelta(days=i * 29 // (solved_count - 1)) if solved_count > 1 else jun_18
        for i in range(solved_count)
    ]
    for title, platform, url, difficulty, status, revision, notes, tags in PROBLEMS:
        completed_at = None
        if status == "Solved":
            completed_at = solved_dates[solved_idx] if solved_idx < len(solved_dates) else now
            solved_idx += 1
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

    # ── 4. Resources ──────────────────────────────────────────────────────────
    for title, url, category, description in RESOURCES:
        session.add(Resource(
            user_id=demo.id,
            title=title,
            url=url,
            category=category,
            description=description,
        ))
    await session.flush()

    # ── 5. Notes ──────────────────────────────────────────────────────────────
    for title, note_type, content, company_name in NOTES:
        company_id = None
        if company_name is not None:
            company = await session.scalar(select(Company).where(Company.name == company_name))
            if company is not None:
                company_id = company.id
        session.add(Note(
            user_id=demo.id,
            title=title,
            content=content,
            type=note_type,
            company_id=company_id,
        ))
    await session.flush()

    # ── 6. Tracked companies + checklist items ────────────────────────────────
    for company_name, status, deadline_days, done_keys in TRACKED_COMPANIES:
        company = await session.scalar(select(Company).where(Company.name == company_name))
        if company is None:
            continue

        deadline = None
        if deadline_days is not None:
            deadline = datetime.now(timezone.utc) + timedelta(days=deadline_days)

        uc = UserCompany(
            user_id=demo.id,
            company_id=company.id,
            application_status=status,
            deadline=deadline,
        )
        session.add(uc)
        await session.flush()

        for item_key, label in CHECKLIST_ITEMS:
            session.add(ChecklistItem(
                user_company_id=uc.id,
                item_key=item_key,
                label=label,
                is_done=item_key in done_keys,
            ))
    await session.flush()

    # ── 7. Activity log ───────────────────────────────────────────────────────
    for action, entity_type, meta in ACTIVITIES:
        entry = ActivityLog(
            user_id=demo.id,
            action=action,
            entity_type=entity_type,
            entity_id=None,
            metadata_=meta,
        )
        session.add(entry)

    await session.commit()
    await session.refresh(demo)
    return demo
