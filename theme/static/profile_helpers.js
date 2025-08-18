// Profile Helpers: shared Alpine component factories for profile modal, edit page, and public view.
// Keeps large inline scripts out of templates for better caching and maintainability.
(function(window){
  // Video Manager Component (modal and edit use). Provides confirmDelete modal state used by _about_modal_body.html
  window.videoManager = function(){
    const csrf = window.TC_CSRF;
    return {
      video:(window.Alpine && Alpine.store('profileModal') && Alpine.store('profileModal').therapist && (Alpine.store('profileModal').therapist.video_gallery||[])[0]) || null,
      file:null, caption:'', uploading:false, progress:0, error:'',
      recording:false, mediaRecorder:null, chunks:[], stream:null, drag:false,
      chosenType:null, trackFailed:false, previewUrl:null, videoLoadError:false,
      // Delete confirmation state used by template
      confirmDelete:false,
      deleting:false,
      openDelete(){ if(!this.video) return; this.error=''; this.confirmDelete=true; this.deleting=false; },
      cancelDelete(){ if(this.deleting) return; this.confirmDelete=false; },
      confirmDeleteAction(){ if(!this.video || this.deleting) return; this.deleting=true; fetch('/users/api/profile/video/', { method:'DELETE', headers:{'X-CSRFToken': csrf} })
        .then(r=>r.json().then(d=>[r,d]))
        .then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Delete failed'; return; } const s=window.Alpine && Alpine.store('profileModal'); if(s&&s.therapist){ s.therapist.video_gallery=d.video_gallery||[]; } this.video=null; this.confirmDelete=false; })
        .catch(()=> this.error='Network error')
        .finally(()=> this.deleting=false);
      },
      // Backward-compat alias
      remove(){ this.openDelete(); },
      reset(){
        if(this.recording){ this.stopRecording(); }
        this.stopStream();
        if(this.previewUrl){ try{ URL.revokeObjectURL(this.previewUrl); }catch(_){} }
        this.previewUrl=null; this.file=null; this.chunks=[]; this.chosenType=null; this.trackFailed=false;
        this.error=''; this.progress=0; this.caption='';
        if(this.$refs && this.$refs.vidFile) this.$refs.vidFile.value='';
      },
      setFile(f){ if(!f) return; try{ if(this.previewUrl){ URL.revokeObjectURL(this.previewUrl); } }catch(_){} this.file=f; try{ this.previewUrl = URL.createObjectURL(f); }catch(_) { this.previewUrl=null; } },
      onFile(e){ const f=e?.target?.files?.[0]; if(f) this.setFile(f); },
      handleTrackFailure(msg){ if(this.recording){ this.error=msg||'Camera stream ended unexpectedly'; this.trackFailed=true; } },
      startRecording(){
        if(!navigator.mediaDevices?.getUserMedia){ this.error='Recording not supported'; return; }
        this.error=''; this.file=null; this.chunks=[]; this.chosenType=null; this.trackFailed=false;
        navigator.mediaDevices.getUserMedia({video:true,audio:true}).then(str=>{
          this.stream=str;
          if(this.$refs && this.$refs.livePreview){ try{ this.$refs.livePreview.srcObject=str; }catch(_){} }
          const candidates=[
            'video/mp4;codecs=avc1.42E01E,mp4a.40.2', 'video/mp4',
            'video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm'
          ];
          let chosen=null;
          if(window.MediaRecorder && MediaRecorder.isTypeSupported){
            chosen=candidates.find(t=>{ try { return MediaRecorder.isTypeSupported(t); } catch(_) { return false; } })||null;
          }
          this.chosenType=chosen;
          str.getTracks().forEach(tr=>{ tr.addEventListener('ended', ()=> this.handleTrackFailure('Camera stopped (ended)')); });
          try { this.mediaRecorder = chosen ? new MediaRecorder(str,{mimeType:chosen}) : new MediaRecorder(str); }
          catch(e){ try{ this.mediaRecorder=new MediaRecorder(str); } catch(e2){ this.error='Unable to start recorder'; this.stopStream(); return; } }
          this.chunks=[];
          this.mediaRecorder.ondataavailable=ev=>{ if(ev.data?.size>0) this.chunks.push(ev.data); };
          this.mediaRecorder.onstop=()=>{ const type=this.chosenType || (this.mediaRecorder && this.mediaRecorder.mimeType) || 'video/webm'; const ext=/mp4/.test(type)?'mp4':'webm'; const blob=new Blob(this.chunks,{type}); const f=new File([blob],'recording.'+ext,{type}); this.setFile(f); this.stopStream(); };
          try { this.mediaRecorder.start(); } catch(e){ this.error='Recorder start failed'; this.stopStream(); return; }
          this.recording=true;
        }).catch(()=> this.error='Permission denied');
      },
      stopRecording(){ if(this.mediaRecorder && this.recording){ this.mediaRecorder.stop(); this.recording=false; } },
      stopStream(){ if(this.$refs && this.$refs.livePreview){ try{ this.$refs.livePreview.srcObject=null; }catch(_){} } this.stream?.getTracks().forEach(t=>t.stop()); this.stream=null; },
      upload(){ if(!this.file){ this.error='No video selected'; return;} this.error=''; this.uploading=true; const form=new FormData(); form.append('file',this.file); if(this.caption) form.append('caption',this.caption); fetch('/users/api/profile/video/',{method:'POST',headers:{'X-CSRFToken':csrf},body:form}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Upload failed'; return;} const s=Alpine.store('profileModal'); if(s?.therapist) s.therapist.video_gallery=d.video_gallery||[]; this.video=(d.video_gallery||[])[0]||null; this.reset(); }).catch(()=> this.error='Network error').finally(()=> this.uploading=false); },
      updateCaption(){ if(!this.video) return; fetch('/users/api/profile/video/',{method:'PATCH',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({caption:this.video.caption||''})}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Save failed'; return;} const s=Alpine.store('profileModal'); if(s?.therapist) s.therapist.video_gallery=d.video_gallery||[]; this.video=(d.video_gallery||[])[0]||null; }).catch(()=> this.error='Network error'); }
    };
  };

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
  submitProfile(){ if(this.submitting||!this.canSubmit()) return; this.submitting=true; this.submitError=''; const csrf=window.TC_CSRF; fetch('/users/api/profile/submit/', { method:'POST', headers:{ 'X-CSRFToken': csrf } }).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.submitError=d.error||'Submit failed'; return; } const url=d.redirect||'/users/members/feed/'; window.location.href=url; }).catch(()=>{ this.submitError='Network error'; }).finally(()=> this.submitting=false); },
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

  // Therapy Types & Specialties Manager Component
  // Extracted from inline template (therapist_profile_edit.html) so it can be reused by modal/public profile.
  window.therapySpecialtiesManager = function(opts){
    const csrf = window.TC_CSRF;
    return {
      editable: opts && typeof opts.editable !== 'undefined' ? !!opts.editable : false,
      // Therapy Types state
      therapyQuery:'', therapyResults:[], therapyOpen:false, therapyLoading:false, therapySelectedIndex:-1, therapyDebounce:null,
      // Specialties state
      specialtyQuery:'', specialtyResults:[], specialtyOpen:false, specialtyLoading:false, specialtySelectedIndex:-1, specialtyDebounce:null,
      // Save debounce
      saveTimer:null, saving:false, error:'',
      init(){ /* no-op for now; could preload lists if desired */ },
      // Shared helpers
      normalizeName(v){ return (v||'').trim(); },
      caseEq(a,b){ return (a||'').toLowerCase() === (b||'').toLowerCase(); },
      inList(list, name){ return list.some(x => this.caseEq((x.name||x), name)); },
      // Therapy Types logic
      onTherapyInput(){ if(this.therapyDebounce) clearTimeout(this.therapyDebounce); this.therapySelectedIndex=-1; if(!this.therapyQuery){ if(!this.therapyOpen || !this.therapyResults.length){ this.fetchTherapyTypes(true); } return; } this.therapyDebounce=setTimeout(()=> this.fetchTherapyTypes(), 220); },
      onTherapyFocus(){ if(this.therapyQuery) { this.onTherapyInput(); return; } if(!this.therapyResults.length){ this.fetchTherapyTypes(true); } else { this.therapyOpen=true; } },
      fetchTherapyTypes(){ this.therapyLoading=true; fetch('/users/api/lookups/therapy_types/?q='+encodeURIComponent(this.therapyQuery))
        .then(r=>r.json()).then(d=>{ this.therapyResults=d.results||[]; this.therapyOpen=true; })
        .catch(()=>{ this.therapyResults=[]; this.therapyOpen=false; })
        .finally(()=> this.therapyLoading=false); },
      selectTherapy(idx){ const item=this.therapyResults[idx]; if(!item) return; this.therapyQuery=item.name; this.therapyOpen=false; this.therapyResults=[]; this.addTherapyType(); },
      therapyKeydown(e){ if(!this.therapyOpen){ if(e.key==='ArrowDown' && this.therapyResults.length){ this.therapyOpen=true; e.preventDefault(); } else if(e.key==='Enter'){ if(this.therapyQuery.trim()){ e.preventDefault(); this.addTherapyType(); } } return; }
        if(e.key==='ArrowDown'){ e.preventDefault(); this.therapySelectedIndex=(this.therapySelectedIndex+1)%this.therapyResults.length; }
        else if(e.key==='ArrowUp'){ e.preventDefault(); this.therapySelectedIndex=(this.therapySelectedIndex-1+this.therapyResults.length)%this.therapyResults.length; }
        else if(e.key==='Enter'){ e.preventDefault(); if(this.therapySelectedIndex>-1){ this.selectTherapy(this.therapySelectedIndex); } if(this.therapyQuery.trim()){ this.addTherapyType(); } }
        else if(e.key==='Escape'){ this.therapyOpen=false; }
      },
      addTherapyType(){ const name=this.normalizeName(this.therapyQuery); if(!name){ return; } const s=Alpine.store('profileModal'); if(!s||!s.therapist) return; const list = (s.therapist.therapy_types||[]).slice(); if(this.inList(list, name)){ this.therapyQuery=''; this.therapyOpen=false; this.therapyResults=[]; return; } list.push(name); list.sort((a,b)=> a.localeCompare(b)); s.therapist.therapy_types=list; this.therapyQuery=''; this.therapyOpen=false; this.therapyResults=[]; this.scheduleSave(); },
      removeTherapyType(name){ const s=Alpine.store('profileModal'); if(!s||!s.therapist) return; s.therapist.therapy_types=(s.therapist.therapy_types||[]).filter(t=> !this.caseEq(t,name)); this.scheduleSave(); },
      // Specialties logic
      onSpecialtyInput(){ if(this.specialtyDebounce) clearTimeout(this.specialtyDebounce); this.specialtySelectedIndex=-1; if(!this.specialtyQuery){ if(!this.specialtyOpen || !this.specialtyResults.length){ this.fetchSpecialties(true); } return; } this.specialtyDebounce=setTimeout(()=> this.fetchSpecialties(), 220); },
      onSpecialtyFocus(){ if(this.specialtyQuery){ this.onSpecialtyInput(); return; } if(!this.specialtyResults.length){ this.fetchSpecialties(true); } else { this.specialtyOpen=true; } },
      fetchSpecialties(){ this.specialtyLoading=true; fetch('/users/api/lookups/specialties/?q='+encodeURIComponent(this.specialtyQuery))
        .then(r=>r.json()).then(d=>{ this.specialtyResults=d.results||[]; this.specialtyOpen=true; })
        .catch(()=>{ this.specialtyResults=[]; this.specialtyOpen=false; })
        .finally(()=> this.specialtyLoading=false); },
      selectSpecialty(idx){ const item=this.specialtyResults[idx]; if(!item) return; this.specialtyQuery=item.name; this.specialtyOpen=false; this.specialtyResults=[]; this.addSpecialty(); },
      specialtyKeydown(e){ if(!this.specialtyOpen){ if(e.key==='ArrowDown' && this.specialtyResults.length){ this.specialtyOpen=true; e.preventDefault(); } else if(e.key==='Enter'){ if(this.specialtyQuery.trim()){ e.preventDefault(); this.addSpecialty(); } } return; }
        if(e.key==='ArrowDown'){ e.preventDefault(); this.specialtySelectedIndex=(this.specialtySelectedIndex+1)%this.specialtyResults.length; }
        else if(e.key==='ArrowUp'){ e.preventDefault(); this.specialtySelectedIndex=(this.specialtySelectedIndex-1+this.specialtyResults.length)%this.specialtyResults.length; }
        else if(e.key==='Enter'){ e.preventDefault(); if(this.specialtySelectedIndex>-1){ this.selectSpecialty(this.specialtySelectedIndex); } if(this.specialtyQuery.trim()){ this.addSpecialty(); } }
        else if(e.key==='Escape'){ this.specialtyOpen=false; }
      },
      addSpecialty(){ const name=this.normalizeName(this.specialtyQuery); if(!name) return; const s=Alpine.store('profileModal'); if(!s||!s.therapist) return; const list=(s.therapist.specialties||[]).slice(); if(this.inList(list, name)){ this.specialtyQuery=''; this.specialtyOpen=false; this.specialtyResults=[]; return; } list.push({name:name, is_top:false}); list.sort((a,b)=> (a.name||'').localeCompare(b.name||'')); s.therapist.specialties=list; this.specialtyQuery=''; this.specialtyOpen=false; this.specialtyResults=[]; this.syncTopList(); this.scheduleSave(); },
      removeSpecialty(name){ const s=Alpine.store('profileModal'); if(!s||!s.therapist) return; s.therapist.specialties=(s.therapist.specialties||[]).filter(sp=> !this.caseEq(sp.name||sp,name)); s.therapist.top_specialties = (s.therapist.top_specialties||[]).filter(t=> !this.caseEq(t,name)); this.scheduleSave(); },
      toggleTop(name){ const s=Alpine.store('profileModal'); if(!s||!s.therapist) return; const specs=(s.therapist.specialties||[]).slice(); const idx=specs.findIndex(sp=> this.caseEq(sp.name||sp,name)); if(idx===-1) return; const sp=specs[idx]; const currentlyTop=!!sp.is_top; if(!currentlyTop){ const topCount=specs.filter(x=> x.is_top).length; if(topCount>=5){ if(window.__profileEdit){ window.__profileEdit.notify('Max 5 top specialties', true); } return; } }
        sp.is_top = !currentlyTop; specs[idx]=sp; s.therapist.specialties=specs; this.syncTopList(); this.scheduleSave(); },
      syncTopList(){ const s=Alpine.store('profileModal'); if(!s||!s.therapist) return; const tops=(s.therapist.specialties||[]).filter(sp=> sp.is_top).map(sp=> sp.name).slice(0,5); s.therapist.top_specialties=tops; },
      // Saving
      scheduleSave(){ if(this.saveTimer) clearTimeout(this.saveTimer); this.saveTimer=setTimeout(()=> this.saveAll(), 650); },
      saveAll(){ const s=Alpine.store('profileModal'); if(!s||!s.therapist) return; this.saving=true; const therapy=(s.therapist.therapy_types||[]).map(t=> typeof t==='string'? t : (t.name||'')); const specs=(s.therapist.specialties||[]).map(sp=> sp.name || sp); const tops=(s.therapist.top_specialties||[]).slice(0,5); const payload={ therapy_types: therapy, specialties: specs, top_specialties: tops }; fetch('/users/api/profile/update/', {method:'PATCH', headers:{'Content-Type':'application/json','X-CSRFToken':csrf}, body:JSON.stringify(payload)})
        .then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=(d.errors && (d.errors.therapy_types||d.errors.specialties||d.errors.top_specialties)) || d.error || 'Save failed'; if(window.__profileEdit){ window.__profileEdit.notify(this.error,true); } return; } const s2=Alpine.store('profileModal'); if(s2&&s2.therapist){ s2.therapist.therapy_types = d.therapy_types||therapy; s2.therapist.specialties = d.specialties|| (s2.therapist.specialties||[]); s2.therapist.top_specialties = d.top_specialties || (s2.therapist.top_specialties||[]); } if(window.__profileEdit){ window.__profileEdit.applyData(d); window.__profileEdit.notify('Saved'); } })
        .catch(()=>{ this.error='Network error'; if(window.__profileEdit){ window.__profileEdit.notify(this.error,true); } })
        .finally(()=> this.saving=false); },
      clickAwayTherapy(){ this.therapyOpen=false; },
      clickAwaySpecialty(){ this.specialtyOpen=false; }
    };
  };

  // Fees & Insurance Manager Component (extracted for reuse)
  window.feesInsuranceManager = function(){
    const csrf = window.TC_CSRF;
    return {
      editable:true,
      fees:{ individual:'', couples:'' },
      insuranceForm:{ provider:'' },
      insError:'',
      providerQuery:'', providerResults:[], providerLoading:false, providerOpen:false, providerSelectedIndex:-1, providerDebounce:null,
      insuranceSaveTimer:null,
      init(){ const s=Alpine.store('profileModal'); if(s && s.therapist){ this.fees.individual = s.therapist.individual_session_cost || ''; this.fees.couples = s.therapist.couples_session_cost || ''; } },
      fmt(v){ if(v==null||v==='') return ''; const num=parseFloat((''+v).replace(/[^0-9.]/g,'')); if(isNaN(num)) return v; return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:0,maximumFractionDigits:0}).format(num); },
      normalizeCurrency(raw){ if(!raw) return ''; const digits=(''+raw).replace(/[^0-9.]/g,''); if(!digits) return ''; const num=parseFloat(digits); if(isNaN(num)) return ''; return Math.round(num); },
      formatFeeInput(field){ const s=Alpine.store('profileModal'); if(!s||!s.therapist) return ''; const v=s.therapist[field]; if(!v && v!==0) return ''; const num=this.normalizeCurrency(v); return num? ('$'+num):''; },
      onFeeBlur(field,val){ const norm=this.normalizeCurrency(val); if(norm!==''){ this.fees[field.includes('couples')?'couples':'individual'] = '$'+norm; } },
      saveFee(field,val){ const s=Alpine.store('profileModal'); const norm=this.normalizeCurrency(val); window.__tcSaveProfileField(field, norm? norm : ''); if(s && s.therapist){ s.therapist[field] = norm? norm : ''; } },
      toggleSliding(){ const s=Alpine.store('profileModal'); const next = !s.therapist.sliding_scale_pricing_available; window.__tcSaveProfileField('sliding_scale_pricing_available', next); if(s&&s.therapist) s.therapist.sliding_scale_pricing_available=next; },
      setSliding(val){ const s=Alpine.store('profileModal'); if(!s||!s.therapist) return; if(s.therapist.sliding_scale_pricing_available===val) return; window.__tcSaveProfileField('sliding_scale_pricing_available', val); s.therapist.sliding_scale_pricing_available=val; },
      addInsurance(){ const raw=(this.insuranceForm.provider||'').trim(); if(!raw){ this.insError='Provider required'; return; } this.insError=''; const s=Alpine.store('profileModal'); const list=(s.therapist.insurance_details||[]).slice(); if(list.some(i=> (i.provider||'').toLowerCase()===raw.toLowerCase())){ this.insuranceForm.provider=''; this.providerResults=[]; this.providerOpen=false; return; } list.push({ provider: raw, out_of_network:false }); s.therapist.insurance_details=list; this.insuranceForm.provider=''; this.providerResults=[]; this.providerOpen=false; this.providerSelectedIndex=-1; this.scheduleInsuranceSave(); },
      removeInsurance(idx){ const s=Alpine.store('profileModal'); const list=(s.therapist.insurance_details||[]).slice(); list.splice(idx,1); s.therapist.insurance_details=list; this.scheduleInsuranceSave(); },
      toggleOON(idx){ const s=Alpine.store('profileModal'); const list=(s.therapist.insurance_details||[]).slice(); if(list[idx]){ list[idx].out_of_network=!list[idx].out_of_network; } s.therapist.insurance_details=list; this.scheduleInsuranceSave(); },
      saveInsurance(){ const s=Alpine.store('profileModal'); const payload=(s.therapist.insurance_details||[]).map(i=>({provider:i.provider, out_of_network:!!i.out_of_network})); window.__tcSaveProfileField('insurance_details', payload); },
      scheduleInsuranceSave(){ if(this.insuranceSaveTimer) clearTimeout(this.insuranceSaveTimer); this.insuranceSaveTimer=setTimeout(()=> this.saveInsurance(), 600); },
      onProviderInput(){ this.providerQuery = this.insuranceForm.provider; this.providerSelectedIndex=-1; if(this.providerDebounce) clearTimeout(this.providerDebounce); if(!this.providerQuery){ this.providerResults=[]; this.providerOpen=false; return; } this.providerDebounce=setTimeout(()=> this.fetchProviders(), 220); },
      onProviderFocus(){ if(this.insuranceForm.provider && this.insuranceForm.provider.trim()){ this.onProviderInput(); return; } if(this.providerResults.length){ this.providerOpen=true; return; } this.providerLoading=true; fetch('/users/api/lookups/insurance_providers/?q=').then(r=>r.json()).then(d=>{ this.providerResults=(d.results||[]); this.providerOpen=true; }).catch(()=>{ this.providerResults=[]; this.providerOpen=false; }).finally(()=> this.providerLoading=false); },
      fetchProviders(){ this.providerLoading=true; fetch('/users/api/lookups/insurance_providers/?q='+encodeURIComponent(this.providerQuery)).then(r=>r.json()).then(d=>{ this.providerResults=(d.results||[]); this.providerOpen=true; }).catch(()=>{ this.providerResults=[]; this.providerOpen=false; }).finally(()=> this.providerLoading=false); },
      selectProvider(idx){ const item=this.providerResults[idx]; if(!item) return; this.insuranceForm.provider=item.name; this.providerOpen=false; this.providerResults=[]; this.addInsurance(); },
      providerKeydown(e){ if(!this.providerOpen){ if(e.key==='ArrowDown' && this.providerResults.length){ this.providerOpen=true; e.preventDefault(); } else if(e.key==='Enter'){ if(this.insuranceForm.provider.trim()){ e.preventDefault(); this.addInsurance(); } } return; } if(e.key==='ArrowDown'){ e.preventDefault(); this.providerSelectedIndex=(this.providerSelectedIndex+1)%this.providerResults.length; } else if(e.key==='ArrowUp'){ e.preventDefault(); this.providerSelectedIndex=(this.providerSelectedIndex-1+this.providerResults.length)%this.providerResults.length; } else if(e.key==='Enter'){ e.preventDefault(); if(this.providerSelectedIndex>-1){ this.selectProvider(this.providerSelectedIndex); } if(this.insuranceForm.provider.trim()){ this.addInsurance(); } } else if(e.key==='Escape'){ this.providerOpen=false; } },
      clickAway(){ this.providerOpen=false; }
    };
  };

  // Contact & Web Manager Component (extracted)
  window.contactWebManager = function(){
    const csrf = window.TC_CSRF;
    return {
      editing:false, saving:false, success:false, error:'',
      socialFields:[
        {key:'facebook_url', label:'Facebook URL', placeholder:'https://facebook.com/...', type:'url'},
        {key:'instagram_url', label:'Instagram URL', placeholder:'https://instagram.com/...', type:'url'},
        {key:'linkedin_url', label:'LinkedIn URL', placeholder:'https://linkedin.com/in/...', type:'url'},
        {key:'twitter_url', label:'Twitter URL', placeholder:'https://x.com/...', type:'url'},
        {key:'tiktok_url', label:'TikTok URL', placeholder:'https://tiktok.com/@...', type:'url'},
        {key:'youtube_url', label:'YouTube URL', placeholder:'https://youtube.com/@...', type:'url'}
      ],
      form:{ phone_number:'', phone_extension:'', mobile_number:'', practice_email:'', office_email:'', practice_website_url:'',
             receive_calls_from_client:false, receive_texts_from_clients:false, receive_emails_from_clients:false, receive_emails_when_client_calls:false,
             facebook_url:'', instagram_url:'', linkedin_url:'', twitter_url:'', tiktok_url:'', youtube_url:'' },
      init(){ this.load(); },
      load(){ const s=window.Alpine && Alpine.store('profileModal'); if(!s||!s.therapist) return; const t=s.therapist; for(const k in this.form){ this.form[k] = (t[k]!==undefined && t[k]!==null) ? t[k] : (typeof this.form[k]==='boolean'? false : ''); } },
      startEdit(){ this.load(); this.editing=true; this.success=false; this.error=''; },
      cancel(){ if(this.saving) return; this.editing=false; this.error=''; },
      socialList(){ const s=Alpine.store('profileModal'); if(!s||!s.therapist) return []; const map=[['facebook_url','Facebook'],['instagram_url','Instagram'],['linkedin_url','LinkedIn'],['twitter_url','Twitter'],['tiktok_url','TikTok'],['youtube_url','YouTube']]; return map.filter(([k])=> s.therapist[k]).map(([k,l])=> ({key:k,label:l,url:s.therapist[k]})); },
      validate(){ const urlFields=['practice_website_url','facebook_url','instagram_url','linkedin_url','twitter_url','tiktok_url','youtube_url']; const urlRe=/^https?:\/\//i; for(const f of urlFields){ const v=this.form[f]; if(v && !urlRe.test(v)){ this.error=f.replace(/_/g,' ')+' must start with http'; return false; } } return true; },
      buildPayload(){ const p={}; for(const k in this.form){ p[k]=this.form[k]; } return p; },
      save(){ if(this.saving) return; this.error=''; if(!this.validate()) return; this.saving=true; const payload=this.buildPayload(); const s=Alpine.store('profileModal'); const prev={}; if(s&&s.therapist){ for(const k in payload){ prev[k]=s.therapist[k]; s.therapist[k]=payload[k]; } }
        fetch('/users/api/profile/update/', {method:'PATCH', headers:{'Content-Type':'application/json','X-CSRFToken':csrf}, body: JSON.stringify(payload)})
          .then(r=>r.json().then(d=>[r,d]))
          .then(([r,d])=>{ if(!r.ok){ this.error=(d.errors && Object.values(d.errors)[0]) || d.error || 'Save failed'; if(s&&s.therapist){ for(const k in prev){ s.therapist[k]=prev[k]; } } if(window.__profileEdit){ window.__profileEdit.notify(this.error,true); } return; }
            if(s&&s.therapist){ for(const k in d){ if(k in this.form) s.therapist[k]=d[k]; } }
            if(window.__profileEdit){ window.__profileEdit.applyData(d); window.__profileEdit.notify('Saved'); }
            this.success=true; this.editing=false; setTimeout(()=> this.success=false,1800);
          })
          .catch(()=>{ this.error='Network error'; if(s&&s.therapist){ for(const k in prev){ s.therapist[k]=prev[k]; } } })
          .finally(()=> this.saving=false);
      }
    };
  };

  // Location Manager Component (extracted)
  window.locationManager = function(){
    const csrf = window.TC_CSRF;
    return {
      form:{show:false, mode:'add', id:null, practice_name:'', street_address:'', address_line_2:'', city:'', state:'', zip:'', is_primary_address:false},
      saving:false, error:'',
      hoursEdit:{ openFor:null, rows:[], saving:false, error:'' },
      weekdayNames:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
      confirmDelete:{show:false, targetId:null, targetName:''},
      states:[
        {code:'', name:'Select State'},
        {code:'AL', name:'Alabama'},{code:'AK', name:'Alaska'},{code:'AZ', name:'Arizona'},{code:'AR', name:'Arkansas'},
        {code:'CA', name:'California'},{code:'CO', name:'Colorado'},{code:'CT', name:'Connecticut'},{code:'DE', name:'Delaware'},
        {code:'DC', name:'District of Columbia'},{code:'FL', name:'Florida'},{code:'GA', name:'Georgia'},{code:'HI', name:'Hawaii'},
        {code:'ID', name:'Idaho'},{code:'IL', name:'Illinois'},{code:'IN', name:'Indiana'},{code:'IA', name:'Iowa'},
        {code:'KS', name:'Kansas'},{code:'KY', name:'Kentucky'},{code:'LA', name:'Louisiana'},{code:'ME', name:'Maine'},
        {code:'MD', name:'Maryland'},{code:'MA', name:'Massachusetts'},{code:'MI', name:'Michigan'},{code:'MN', name:'Minnesota'},
        {code:'MS', name:'Mississippi'},{code:'MO', name:'Missouri'},{code:'MT', name:'Montana'},{code:'NE', name:'Nebraska'},
        {code:'NV', name:'Nevada'},{code:'NH', name:'New Hampshire'},{code:'NJ', name:'New Jersey'},{code:'NM', name:'New Mexico'},
        {code:'NY', name:'New York'},{code:'NC', name:'North Carolina'},{code:'ND', name:'North Dakota'},{code:'OH', name:'Ohio'},
        {code:'OK', name:'Oklahoma'},{code:'OR', name:'Oregon'},{code:'PA', name:'Pennsylvania'},{code:'RI', name:'Rhode Island'},
        {code:'SC', name:'South Carolina'},{code:'SD', name:'South Dakota'},{code:'TN', name:'Tennessee'},{code:'TX', name:'Texas'},
        {code:'UT', name:'Utah'},{code:'VT', name:'Vermont'},{code:'VA', name:'Virginia'},{code:'WA', name:'Washington'},
        {code:'WV', name:'West Virginia'},{code:'WI', name:'Wisconsin'},{code:'WY', name:'Wyoming'}
      ],
      startAdd(){ this.error=''; this.form={show:true, mode:'add', id:null, practice_name:'', street_address:'', address_line_2:'', city:'', state:'', zip:'', is_primary_address:false}; },
      edit(loc){ this.error=''; this.form={show:true, mode:'edit', id:loc.id, practice_name:loc.practice_name||'', street_address:loc.street_address||'', address_line_2:loc.address_line_2||'', city:loc.city||'', state:loc.state||'', zip:loc.zip||'', is_primary_address: !!loc.is_primary_address}; },
      cancel(){ this.form.show=false; },
      openHours(loc){ if(this.hoursEdit.saving) return; this.hoursEdit.openFor = loc.id; const base=[]; const existing=(loc.office_hours||[]).reduce((m,r)=>{ m[r.weekday]=r; return m; },{}); for(let d=0; d<7; d++){ const r = existing[d] || {weekday:d,is_closed:false,by_appointment_only:false,start_time_1:'',end_time_1:'',start_time_2:'',end_time_2:'',notes:''}; base.push(JSON.parse(JSON.stringify(r))); } this.hoursEdit.rows=base; this.hoursEdit.error=''; },
      closeHours(){ if(this.hoursEdit.saving) return; this.hoursEdit.openFor=null; },
      toggleClosed(row){ row.is_closed=!row.is_closed; if(row.is_closed){ row.by_appointment_only=false; row.start_time_1=row.end_time_1=row.start_time_2=row.end_time_2=''; } },
      toggleAppt(row){ row.by_appointment_only=!row.by_appointment_only; if(row.by_appointment_only){ row.is_closed=false; row.start_time_1=row.end_time_1=row.start_time_2=row.end_time_2=''; } },
      saveHours(){ if(this.hoursEdit.saving || this.hoursEdit.openFor==null) return; this.hoursEdit.saving=true; this.hoursEdit.error=''; const payload={ office_hours: this.hoursEdit.rows.map(r=>({ weekday:r.weekday, is_closed:!!r.is_closed, by_appointment_only:!!r.by_appointment_only, start_time_1:r.start_time_1||'', end_time_1:r.end_time_1||'', start_time_2:r.start_time_2||'', end_time_2:r.end_time_2||'', notes:(r.notes||'').slice(0,64) }))}; fetch('/users/api/profile/locations/'+this.hoursEdit.openFor+'/office_hours/', {method:'PATCH', headers:{'Content-Type':'application/json','X-CSRFToken':csrf}, body:JSON.stringify(payload)}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.hoursEdit.error=d.error||'Save failed'; return; } this.apply(d); const s=window.Alpine && Alpine.store('profileModal'); const updated = s?.therapist?.locations?.find(l=> l.id===this.hoursEdit.openFor); if(updated){ this.openHours(updated); } }).catch(()=> this.hoursEdit.error='Network error').finally(()=> this.hoursEdit.saving=false); },
      save(){ if(this.saving) return; this.error=''; this.saving=true; if(this.form.mode==='add'){ const fd=new FormData(); ['practice_name','street_address','address_line_2','city','state','zip'].forEach(k=> fd.append(k,this.form[k]||'')); if(this.form.is_primary_address) fd.append('is_primary_address','1'); const prevIds=(window.Alpine && Alpine.store('profileModal')?.therapist?.locations||[]).map(l=>l.id); fetch('/users/api/profile/locations/create/', {method:'POST', headers:{'X-CSRFToken':csrf}, body:fd}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Save failed'; return; } this.apply(d); this.form.show=false; const s=window.Alpine && Alpine.store('profileModal'); const newLoc = (s?.therapist?.locations||[]).find(l=> !prevIds.includes(l.id)); if(newLoc){ this.openHours(newLoc); } }).catch(()=> this.error='Network error').finally(()=> this.saving=false); } else { const payload={ practice_name:this.form.practice_name, street_address:this.form.street_address, address_line_2:this.form.address_line_2, city:this.form.city, state:this.form.state, zip:this.form.zip, is_primary_address:this.form.is_primary_address}; fetch('/users/api/profile/locations/'+this.form.id+'/', {method:'PATCH', headers:{'Content-Type':'application/json','X-CSRFToken':csrf}, body:JSON.stringify(payload)}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Update failed'; return; } this.apply(d); this.form.show=false; }).catch(()=> this.error='Network error').finally(()=> this.saving=false); } },
      remove(){ if(!this.form.id) return; this.openDelete({id:this.form.id, practice_name:this.form.practice_name}); },
      openDelete(loc){ if(!loc) return; this.confirmDelete={show:true, targetId:loc.id, targetName: loc.practice_name || 'Location'}; },
      cancelDelete(){ this.confirmDelete={show:false, targetId:null, targetName:''}; },
      confirmDeleteAction(){ const id=this.confirmDelete.targetId; if(!id) return; this.confirmDelete.show=false; fetch('/users/api/profile/locations/'+id+'/', {method:'DELETE', headers:{'X-CSRFToken':csrf}}).then(r=>r.json().then(d=>[r,d])).then(([r,d])=>{ if(!r.ok){ this.error=d.error||'Delete failed'; return; } if(this.hoursEdit.openFor===id){ this.closeHours(); } if(this.form.id===id){ this.form.show=false; } this.apply(d); }).catch(()=> this.error='Network error'); },
      removeLoc(loc){ if(!loc || !loc.id) return; this.openDelete(loc); },
      apply(data){ const s = window.Alpine && Alpine.store('profileModal'); if(s && s.therapist){ s.therapist.locations = data.locations || []; } }
    };
  };
})(window);
