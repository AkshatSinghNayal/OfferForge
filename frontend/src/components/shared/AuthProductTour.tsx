import { useEffect, useState } from 'react'
import { ArrowRight, Check, ChevronLeft, ChevronRight, Layers3, Pause, Play } from 'lucide-react'

const steps = [
  { name: 'Applications', title: 'Every opportunity. One clear view.', description: 'Save roles, track each stage, and keep your next action in sight.' },
  { name: 'Daily plan', title: 'Turn a big goal into a small next step.', description: 'Plan a focused session, complete a task, and build your momentum.' },
  { name: 'Resume insights', title: 'Know what to improve next.', description: 'Compare your resume with a role and turn the gaps into preparation tasks.' },
]

export function AuthProductTour() {
  const [step, setStep] = useState(0)
  const [paused, setPaused] = useState(false)
  const [reduced, setReduced] = useState(true)
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(media.matches)
    const visibility = () => setVisible(!document.hidden)
    update()
    media.addEventListener('change', update)
    document.addEventListener('visibilitychange', visibility)
    return () => { media.removeEventListener('change', update); document.removeEventListener('visibilitychange', visibility) }
  }, [])
  const playing = !paused && !reduced && visible
  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => setStep(current => (current + 1) % steps.length), 6500)
    return () => window.clearInterval(timer)
  }, [playing, step])
  const select = (index: number) => { setStep((index + steps.length) % steps.length) }
  return <div className="auth-tour" role="region" aria-roledescription="carousel" aria-label="OfferForge product walkthrough">
    <div className="auth-product-preview">
      <div className="auth-preview-top"><span><Layers3 size={14} /> {steps[step].name}</span><span className="auth-preview-label">ILLUSTRATIVE DEMO</span></div>
      <div className="auth-tour-stage">
      {steps.map((scene, sceneStep) => <div className={`auth-tour-scene ${step === sceneStep ? 'is-active' : ''}`} key={scene.name} aria-hidden={step !== sceneStep} role="group" aria-roledescription="slide" aria-label={`${sceneStep + 1} of 3: ${scene.name}`}>
        {sceneStep === 0 && <div className="tour-pipeline"><div className="tour-scene-heading"><span>Your application pipeline</span><span>3 opportunities</span></div><div className="tour-columns">{['Saved', 'Applied', 'Interview'].map((stage, i) => <div key={stage}><p><span className="auth-status-dot" />{stage}<span>1</span></p><div className="tour-role" style={{ animationDelay: `${i * 120}ms` }}><span className="tour-company-icon">{['A','R','M'][i]}</span><strong>{['Atlassian','Razorpay','Microsoft'][i]}</strong><small>{['Backend Engineer','SWE Intern','Software Engineer'][i]}</small><div>{['Tailor resume','Follow up','Prepare stories'][i]}<ArrowRight size={10} /></div></div></div>)}</div><p className="tour-scene-note">From first save to next conversation.</p></div>}
        {sceneStep === 1 && <div className="tour-plan"><div className="tour-scene-heading"><span>Today’s focus</span><span>2 of 3 complete</span></div>{['Tailor your resume summary','Practice a graph problem','Rehearse your project walkthrough'].map((title,i)=><div className="auth-preview-task" key={title}><span className={`auth-preview-check ${i===2?'pending':''}`}>{i<2 && <Check size={12}/>}</span><div><strong>{title}</strong><p>{['Make your experience stand out','Explain the approach and trade-offs','One focused session · 25 min'][i]}</p></div><span className={i===2?'auth-preview-now':'auth-preview-done'}>{i===2?'Up next':'Done'}</span></div>)}<div className="tour-progress"><span /></div></div>}
        {sceneStep === 2 && <div className="tour-resume"><div className="tour-scene-heading"><span>Resume → Backend Engineer</span><span>Sample analysis</span></div><div className="tour-match"><strong>72<span>%</span></strong><div><h3>A stronger match starts here.</h3><p>Clear strengths. Actionable gaps.</p></div></div><div className="tour-insight"><Check size={14}/><span>Python & REST APIs</span><small>Matched</small></div><div className="tour-insight"><span className="tour-gap-dot"/><span>Container deployment</span><small>Needs evidence</small></div><div className="tour-task-suggestion"><span>YOUR NEXT PREPARATION TASK</span><p>Containerize your API <ArrowRight size={12}/></p></div></div>}
      </div>)}
      </div>
    </div>
    <div className="auth-tour-caption" aria-live={paused ? 'polite' : 'off'}>{steps.map((scene, index) => <div key={scene.name} className={`auth-tour-caption-slide ${step === index ? 'is-active' : ''}`} aria-hidden={step !== index}><p><span>0{index + 1}</span> {scene.title}</p><span>{scene.description}</span></div>)}</div>
    <div className="auth-tour-controls"><div className="auth-tour-dots" role="group" aria-label="Choose walkthrough step">{steps.map((item,i)=><button key={item.name} type="button" onClick={()=>select(i)} aria-label={`Show ${item.name}`} aria-pressed={step===i}><span /></button>)}</div><div><button type="button" aria-label="Previous preview" onClick={()=>select(step-1)}><ChevronLeft size={15}/></button>{!reduced && <button type="button" aria-label={paused?'Play walkthrough':'Pause walkthrough'} onClick={()=>setPaused(value=>!value)}>{paused?<Play size={13}/>:<Pause size={13}/>}</button>}<button type="button" aria-label="Next preview" onClick={()=>select(step+1)}><ChevronRight size={15}/></button></div></div>
  </div>
}
