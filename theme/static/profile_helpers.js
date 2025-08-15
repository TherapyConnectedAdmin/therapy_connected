// Profile Helpers: shared Alpine component factories for profile modal, edit page, and public view.
// Keeps large inline scripts out of templates for better caching and maintainability.
(function(window){
  // Progress Tracker Component
  window.profileProgressTracker = function(){
    return {
      sections: [
        { id:'section-general', label:'General', fields:['first_name','last_name','license_type','license_number','license_state','intro_statement','profile_photo_url'] },
        { id:'section-identity', label:'My Identity', fields:['gender','race_ethnicities','faiths','lgbtqia_identities','other_identities'] },
        { id:'section-about', label:'About Me', fields:['personal_statement_01','personal_statement_q2','personal_statement_q3','intro_note'] },
        { id:'section-locations', label:'Locations', fields:['locations','city','state'] },
        { id:'section-therapy', label:'Therapy & Specialties', fields:['therapy_types','specialties','therapy_types_note','top_specialties'] },
        { id:'section-fees', label:'Fees & Insurance', fields:['individual_session_cost','couples_session_cost','insurance_details','finance_note','accepted_payment_methods','sliding_scale_pricing_available'] },
        { id:'section-client-focus', label:'Client Focus', fields:['participant_types','age_groups'] },
        { id:'section-contact', label:'Contact & Web', fields:['phone_number','practice_email','practice_website_url','facebook_url','instagram_url','linkedin_url'] },
        { id:'section-qualifications', label:'Qualifications', fields:['license_type','license_number','license_state','educations','additional_credentials','year_started_practice'] }
      ].map(s => ({...s, percent:0, active:false})),
  overall:{completedSections:0,totalSections:0,completedFields:0,totalFields:0,percent:0},
  // Dual-track completion
  dual:{ min:{filled:0,total:0,percent:0}, full:{filled:0,total:0,percent:0} },
  minMissing:[],
  submitting:false, submitError:'',
      observer:null,
      mobileInjected:false,
      injectMobile(){ if(this.mobileInjected) return; const targets=['#mobile-menu','.mobile-menu','#site-mobile-menu']; let container=null; for(const sel of targets){ const el=document.querySelector(sel); if(el){ container=el; break; } } if(!container){ setTimeout(()=> this.injectMobile(), 1200); return; } const wrap=document.createElement('div'); wrap.className='mt-4 px-4 py-3 border-t border-[#BEE3DB]/50'; wrap.innerHTML='<div class="text-xs font-semibold text-[#116466] mb-2">Profile Progress</div>' + '<ul class="space-y-1 text-[11px]" data-mobile-progress></ul>'; container.appendChild(wrap); this.mobileInjected=true; this.renderMobile(); },
      renderMobile(){ if(!this.mobileInjected) return; const list=document.querySelector('[data-mobile-progress]'); if(!list) return; list.innerHTML=''; this.sections.forEach(sec=>{ const li=document.createElement('li'); const done = (sec.completed||0)===(sec.total||0) && sec.total>0; li.innerHTML = `<button type="button" data-goto="${sec.id}" class="w-full flex items-center justify-between gap-2 px-2 py-1 rounded ${done?'bg-[#E5F4F2] text-[#116466]':'bg-white text-[#555B6E]'} ring-1 ring-[#BEE3DB] text-left"> <span class="truncate">${sec.label}</span> <span class="text-[10px] tabular-nums">${(sec.completed||0)}/${(sec.total||0)}</span></button>`; list.appendChild(li); }); list.querySelectorAll('button[data-goto]').forEach(btn=> btn.addEventListener('click', e=>{ const id=e.currentTarget.getAttribute('data-goto'); this.scrollTo(id); (window.closeMobileMenu && window.closeMobileMenu()); })); },
      compute(){
  const t = (window.Alpine && Alpine.store('profileModal') && Alpine.store('profileModal').therapist) || {};
        // Per-section full progress
        let completedSections=0,totalSections=0, totalFields=0, completedFields=0;
        this.sections.forEach(sec=>{
          let filled=0; const need=sec.fields.length;
          sec.fields.forEach(f=>{ const v=t[f]; if(Array.isArray(v)) { if(v.length) filled++; } else if(typeof v==='string') { if((v||'').trim().length) filled++; } else if(v) { filled++; } });
          sec.completed = filled; sec.total = need; sec.percent = need ? Math.round((filled/need)*100) : 0;
          if(filled===need && need>0) completedSections++; totalSections++; totalFields += need; completedFields += filled;
        });
        const percent = totalFields ? (completedFields/totalFields)*100 : 0;
        this.overall={completedSections,totalSections,completedFields,totalFields,percent};
        // Minimal required set mirrors server-side ESSENTIAL_FIELDS + relations in compute_profile_completion
        const minFields = ['profile_photo_url','therapy_delivery_method','license_type','first_name','last_name','accepting_new_clients','intro_note','personal_statement_01'];
        const labelMap = {
          profile_photo_url:'Profile photo', therapy_delivery_method:'Delivery method', license_type:'License type', first_name:'First name', last_name:'Last name', accepting_new_clients:'Client availability', intro_note:'Intro blurb', personal_statement_01:'About me',
          rel_locations:'At least one location', rel_specialties:'At least one specialty',
        };
        const minRels = [
          { key:'rel_locations', ok: () => Array.isArray(t.locations) && t.locations.length>0 },
          { key:'rel_specialties', ok: () => Array.isArray(t.specialties) && t.specialties.length>0 },
        ];
        let minFilled=0, minTotal= minFields.length + minRels.length; const missing=[];
        minFields.forEach(f=>{ const v=t[f]; let ok=false; if(Array.isArray(v)) { ok = v.length>0; } else if(typeof v==='string') { ok = (v||'').trim().length>0; } else if(v) { ok=true; } if(ok) { minFilled++; } else { missing.push(labelMap[f]||f); } });
        minRels.forEach(o=>{ try{ if(o.ok()) { minFilled++; } else { missing.push(labelMap[o.key]||o.key); } }catch(e){ missing.push(labelMap[o.key]||o.key); } });
        const minPercent = minTotal ? Math.round((minFilled/minTotal)*100) : 0;
        const fullPercent = Math.round(percent);
        this.dual={ min:{filled:minFilled,total:minTotal,percent:minPercent}, full:{filled:completedFields,total:totalFields,percent:fullPercent} };
        this.minMissing = missing;
        this.renderMobile();
      },
      canSubmit(){ return (this.dual.min.percent>=100); },
      submitProfile(){ if(this.submitting||!this.canSubmit()) return; this.submitting=true; this.submitError=''; const csrf=window.TC_CSRF; fetch('/users/api/profile/submit/', { method:'POST', headers:{ 'X-CSRFToken': csrf } }).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.submitError=d.error||'Submit failed'; return; } const url=d.redirect||'/users/dashboard/'; window.location.href=url; }).catch(()=>{ this.submitError='Network error'; }).finally(()=> this.submitting=false); },
      scrollTo(id){ const el=document.getElementById(id); if(!el) return; window.scrollTo({top: el.getBoundingClientRect().top + window.scrollY - 80, behavior:'smooth'}); },
      focusFirstIncomplete(){ const target=this.sections.find(s=>s.percent<100); if(target) this.scrollTo(target.id); },
      watchData(){ const handler=()=>{ this.compute(); }; document.addEventListener('tc-profile-updated', handler); this.compute(); },
      init(){ this.compute(); this.watchData(); this.setupSpy(); if(window.innerWidth < 1024){ setTimeout(()=> this.injectMobile(), 600); } },
      setupSpy(){ const opts={root:null, rootMargin:'-40% 0px -50% 0px', threshold:[0,0.25,0.5,0.75,1]}; this.observer=new IntersectionObserver((entries)=>{ entries.forEach(e=>{ const id=e.target.id; const s=this.sections.find(x=>x.id===id); if(s){ if(e.isIntersecting){ this.sections.forEach(x=> x.active = (x.id===id)); } } }); }, opts); this.sections.forEach(s=>{ const el=document.getElementById(s.id); if(el) this.observer.observe(el); }); }
    };
  };

  // Qualifications Manager Component
  window.qualificationsManager = function(){
    const csrf = window.TC_CSRF;
    return {
      addingEducation:false, addingCredential:false, saving:false, error:'',
  eduForm:{ id:null, school:'', degree_diploma:'', year_graduated:'' },
      credForm:{ id:null, type:'', organization_name:'', id_number:'', year_issued:'' },
      init(){ /* no-op */ },
      startAddEducation(){ this.resetEdu(); this.addingEducation=true; this.addingCredential=false; },
      startAddCredential(){ this.resetCred(); this.addingCredential=true; this.addingEducation=false; },
  editEducation(e){ if(!e) return; this.eduForm={ id:e.id, school:e.school, degree_diploma:e.degree_diploma, year_graduated:e.year_graduated }; this.addingEducation=true; this.addingCredential=false; },
      editCredential(c){ if(!c) return; this.credForm={ id:c.id, type:c.type, organization_name:c.organization_name, id_number:c.id_number||'', year_issued:c.year_issued }; this.addingCredential=true; this.addingEducation=false; },
      cancelEducation(){ this.addingEducation=false; this.error=''; },
      cancelCredential(){ this.addingCredential=false; this.error=''; },
  resetEdu(){ this.eduForm={ id:null, school:'', degree_diploma:'', year_graduated:'' }; },
      resetCred(){ this.credForm={ id:null, type:'', organization_name:'', id_number:'', year_issued:'' }; },
      deleteEducation(e){ if(!e||!e.id) return; if(!confirm('Delete education?')) return; fetch(`/users/api/profile/educations/${e.id}/`, {method:'DELETE', headers:{'X-CSRFToken':csrf}}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Delete failed'; return; } const s=Alpine.store('profileModal'); if(s&&s.therapist){ s.therapist.educations=d.educations; } }).catch(()=> this.error='Network error'); },
      deleteCredential(c){ if(!c||!c.id) return; if(!confirm('Delete credential?')) return; fetch(`/users/api/profile/credentials/${c.id}/`, {method:'DELETE', headers:{'X-CSRFToken':csrf}}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Delete failed'; return; } const s=Alpine.store('profileModal'); if(s&&s.therapist){ s.therapist.additional_credentials=d.additional_credentials; } }).catch(()=> this.error='Network error'); },
  saveEducation(){ if(this.saving) return; this.error=''; const f=this.eduForm; if(!f.school||!f.degree_diploma||!f.year_graduated){ this.error='All required fields'; return; } this.saving=true; const payload={ school:f.school, degree_diploma:f.degree_diploma, year_graduated:f.year_graduated }; const url = f.id? `/users/api/profile/educations/${f.id}/` : '/users/api/profile/educations/create/'; const method = f.id? 'PATCH':'POST'; fetch(url,{method, headers:{'Content-Type':'application/json','X-CSRFToken':csrf}, body:JSON.stringify(payload)}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Save failed'; return; } const s=Alpine.store('profileModal'); if(s&&s.therapist){ s.therapist.educations=d.educations; } this.addingEducation=false; this.resetEdu(); if(window.__profileEdit){ window.__profileEdit.applyData(d); window.__profileEdit.notify('Saved'); } }).catch(()=> this.error='Network error').finally(()=> this.saving=false); },
      saveCredential(){ if(this.saving) return; this.error=''; const f=this.credForm; if(!f.organization_name||!f.year_issued){ this.error='Org & Year required'; return; } this.saving=true; const payload={ type:f.type, organization_name:f.organization_name, id_number:f.id_number, year_issued:f.year_issued }; const url = f.id? `/users/api/profile/credentials/${f.id}/` : '/users/api/profile/credentials/create/'; const method = f.id? 'PATCH':'POST'; fetch(url,{method, headers:{'Content-Type':'application/json','X-CSRFToken':csrf}, body:JSON.stringify(payload)}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Save failed'; return; } const s=Alpine.store('profileModal'); if(s&&s.therapist){ s.therapist.additional_credentials=d.additional_credentials; } this.addingCredential=false; this.resetCred(); if(window.__profileEdit){ window.__profileEdit.applyData(d); window.__profileEdit.notify('Saved'); } }).catch(()=> this.error='Network error').finally(()=> this.saving=false); }
    };
  };
})(window);
