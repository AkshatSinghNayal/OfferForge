"""Versioned demo fixtures. Never runs against ordinary user accounts."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.models.activity_log import ActivityLog
from app.models.company import UserCompany
from app.models.dsa import DsaProblem, DsaProblemTag, DsaTag
from app.models.note import Note
from app.models.resume import Resume, ResumeKeyword, ResumeCompanyMap, ResumeJobMatchAnalysis
from app.models.workspace import Application, PreparationTask

VERSION = 'demo_workspace_v1'


def sample_pdf():
    """A valid, self-contained PDF fixture with calculated stream/xref offsets."""
    lines = ['Alex Morgan - Software Engineer', 'SAMPLE RESUME - Fictional demo profile',
             'alex.morgan@example.com | Portfolio: example.com', 'SUMMARY',
             'Software engineer building accessible products and reliable APIs.',
             'EXPERIENCE', 'CloudTech - Software Engineering Intern (fictional)',
             'Built FastAPI services with PostgreSQL and automated unit tests.',
             'Created React dashboards using TypeScript and Tailwind CSS.',
             'PROJECTS', 'Offer tracking workspace: authentication, search and analytics.',
             'SKILLS', 'Python, TypeScript, React, FastAPI, PostgreSQL, Git',
             'EDUCATION', 'B.Tech Computer Science - Sample University']
    stream = 'BT /F1 12 Tf 48 740 Td 22 TL\n' + '\n'.join(f'({line}) Tj T*' for line in lines) + '\nET'
    objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               f'<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream']
    data = b'%PDF-1.4\n'
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f'{i} 0 obj\n{obj}\nendobj\n'.encode()
    start = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n'
    data += ''.join(f'{offset:010d} 00000 n \n' for offset in offsets[1:]).encode()
    data += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode()
    return data


async def upgrade_demo_workspace(session, demo):
    if demo.email != 'demo@offerforge.dev':
        raise ValueError('Demo fixtures may only populate the demo account')
    if await session.scalar(select(ActivityLog.id).where(ActivityLog.user_id == demo.id, ActivityLog.action == VERSION)):
        return
    now = datetime.now(timezone.utc)
    today = now.date()
    resumes = list((await session.scalars(select(Resume).where(Resume.user_id == demo.id))).all())
    resume = next((r for r in resumes if r.is_active), None)
    if resume is None:
        resume = Resume(user_id=demo.id, version_label='Full-stack Engineer · Demo', is_active=True, pdf_data=sample_pdf())
        session.add(resume)
        await session.flush()
    # Repair the old demo's malformed PDF, without replacing user-uploaded versions.
    if resume.version_label == 'SDE Resume v1.0':
        resume.pdf_data = sample_pdf()
    second = Resume(user_id=demo.id, version_label='Backend Engineer · Demo', is_active=False, pdf_data=sample_pdf())
    session.add(second)
    await session.flush()
    for target in (resume, second):
        existing = set((await session.scalars(select(ResumeKeyword.keyword).where(ResumeKeyword.resume_id == target.id))).all())
        for keyword, present in [('Python', True), ('React', True), ('PostgreSQL', True), ('REST APIs', True), ('Docker', False), ('Integration testing', False)]:
            if keyword not in existing:
                session.add(ResumeKeyword(resume_id=target.id, keyword=keyword, is_present=present))
    analysis = ResumeJobMatchAnalysis(user_id=demo.id, resume_id=resume.id, job_title='Backend Engineer (sample)', company_name='Atlassian',
        job_description='FICTIONAL DEMO ROLE: Build Python REST APIs with PostgreSQL. Write integration tests and deploy services with Docker. Collaborate on accessible web products.',
        overall_score=72, confidence='medium', summary='Sample analysis: strong Python and API foundations; add evidence of integration testing and container deployment. This is seeded demonstration data, not a live AI assessment.',
        model_name='demo-fixture', prompt_version='demo-v1', result={
            'requirements': [
                {'requirement':'Python and REST APIs','category':'skills','importance':'required','status':'matched','evidence':['Built FastAPI services with PostgreSQL'],'gap':None,'recommendation':None},
                {'requirement':'Docker deployment','category':'skills','importance':'required','status':'missing','evidence':[],'gap':'Container deployment is not documented.','recommendation':'Containerize your API and write a short deployment guide.'},
                {'requirement':'Automated integration tests','category':'skills','importance':'required','status':'partial','evidence':['Automated unit tests'],'gap':'No end-to-end API workflow is covered.','recommendation':'Test a complete authenticated API workflow.'}],
            'breakdown':[{'category':'skills','label':'Skills','score':72,'matched':1,'partial':1,'missing':1}],
            'strengths':['Python and PostgreSQL project experience','React and TypeScript foundations'],
            'recommendations':['Add measurable project outcomes','Document deployment and integration testing']})
    session.add(analysis)
    await session.flush()
    stages = ['Saved','Applied','Assessment','Interview','Offer','Closed']
    roles = [
        ('Atlassian','Backend Engineer','Saved','Tailor your resume to the role'),
        ('Razorpay','Software Engineer Intern','Applied','Prepare a concise recruiter follow-up'),
        ('Microsoft','Graduate Software Engineer','Assessment','Complete a timed coding practice'),
        ('Google','Software Engineer','Interview','Rehearse your project walkthrough'),
        ('Freshworks','Graduate Engineer','Offer','Compare the offer and prepare questions'),
        ('Swiggy','Backend Engineer','Closed','Record takeaways for the next application'),
        ('Atlassian','Frontend Engineer','Saved','Review accessibility and React requirements')]
    for i, (company, role, stage, action) in enumerate(roles):
        history = [{'stage': s, 'at': (now - timedelta(days=20-j*3)).isoformat()} for j, s in enumerate(stages[:stages.index(stage)+1] if stage != 'Closed' else ['Saved','Applied','Closed'])]
        app = Application(user_id=demo.id, company_name=company, role=role, stage=stage,
            deadline=today + timedelta(days=[0,2,4,7,10,-2,14][i]), next_action=action,
            notes='Fictional demo opportunity.\n\nPreparation: review the role, explain project trade-offs, and prepare questions.\nContact: recruiting@example.com',
            is_pinned=i in (0,3), resume_id=resume.id if i%2 == 0 else second.id, history=history,
            created_at=now-timedelta(days=20), updated_at=now-timedelta(hours=i))
        session.add(app)
    for i, (title, minutes, days, done) in enumerate([
        ('Containerize the sample API',45,1,False), ('Practice two graph problems',30,0,False),
        ('Rehearse the project walkthrough',25,2,False), ('Review SQL joins and indexes',20,-1,False),
        ('Tailor the resume summary',15,0,True), ('Prepare behavioral interview stories',30,4,True)]):
        session.add(PreparationTask(user_id=demo.id, title=title, details='Demo preparation task. Write a short summary of what you learned and one concrete next step.',
            minutes=minutes,due_date=today+timedelta(days=days),is_done=done,
            source_analysis_id=analysis.id if i==0 else None, source_index=1 if i==0 else None,
            source_label='Atlassian · Backend Engineer (sample)' if i==0 else None))
    for i, (title, status, difficulty, tag_name) in enumerate([
        ('Binary Search','In Progress','Easy','Binary Search'), ('Word Ladder','Not Started','Hard','Graphs'),
        ('Coin Change','Marked for Revision','Medium','Dynamic Programming'), ('Merge Intervals','Skipped','Medium','Arrays')]):
        problem = DsaProblem(user_id=demo.id,title=title,platform='LeetCode',external_url='https://leetcode.com/problems/'+title.lower().replace(' ','-')+'/', difficulty=difficulty,status=status,revision_status='Due' if i==2 else 'None',notes='Sample exercise: explain the approach, complexity, and edge cases.')
        session.add(problem)
        await session.flush()
        tag = await session.scalar(select(DsaTag).where(DsaTag.name==tag_name))
        if tag:
            session.add(DsaProblemTag(dsa_problem_id=problem.id,dsa_tag_id=tag.id))
        if i==0:
            session.add(Note(user_id=demo.id,title='Binary search boundary checklist',type='Concept',dsa_problem_id=problem.id,content='## Before coding\n- Define the search interval.\n- Check empty and single-item inputs.\n- Explain why each iteration shrinks the interval.'))
    tracked = list((await session.scalars(select(UserCompany).where(UserCompany.user_id==demo.id))).all())
    for company in tracked[:3]:
        if not await session.scalar(select(ResumeCompanyMap.id).where(ResumeCompanyMap.user_company_id==company.id,ResumeCompanyMap.resume_id==resume.id)):
            session.add(ResumeCompanyMap(user_company_id=company.id,resume_id=resume.id,notes='Sample tailored resume for this company.'))
    session.add(Note(user_id=demo.id,title='Welcome to your demo workspace',type='Personal',content='## Explore OfferForge\nThis account contains fictional sample data.\n\n- Move an application between stages.\n- Complete a task and try Undo.\n- Open the saved sample resume analysis.\n- Explore practice, checklists, calendar, and analytics.'))
    for i, action in enumerate(['application_created','resume_job_match_analyzed','preparation_task_completed',VERSION]):
        session.add(ActivityLog(user_id=demo.id,action=action,entity_type='workspace',metadata_={'demo':True},created_at=now-timedelta(minutes=i*15)))
    await session.flush()
