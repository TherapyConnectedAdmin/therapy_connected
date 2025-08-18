(function(){
  // Mark that init started; the fallback will only stop if `_blogComposerDone === true` later.
  try { window._blogComposerInitStarted = 1; } catch(_){ }
  try { console.log('[blog] composer init'); } catch(_){ }
  const modal = document.getElementById('blog-composer');
  const openBtn = document.getElementById('open-blog-composer');
  const closeBtn = document.getElementById('blog-close');
  const cancelBtn = document.getElementById('blog-cancel');
  const formEl = document.getElementById('blog-composer-form');
  const contentEl = document.getElementById('blog-content');
  const preview = document.getElementById('blog-preview');
  const mediaInput = document.getElementById('blog-media');
  const coverInput = document.getElementById('blog-cover');
  const mediaMetaField = document.getElementById('blog-media-meta');
  const btnUpload = document.getElementById('blog-btn-upload');
  const btnCamera = document.getElementById('blog-btn-camera');
  const camModal = document.getElementById('blog-camera-modal');
  const camVideo = document.getElementById('blog-camera-video');
  const camClose = document.getElementById('blog-camera-close');
  const camCancel = document.getElementById('blog-camera-cancel');
  const camCapture = document.getElementById('blog-camera-capture');
  const camRetake = document.getElementById('blog-camera-retake');
  const camUse = document.getElementById('blog-camera-use');
  const camStatus = document.getElementById('blog-camera-status');
  const camUpload = document.getElementById('blog-camera-upload');
  const cameraInput = document.getElementById('blog-camera');
  const stockQ = document.getElementById('blog-stock-q');
  const stockBtn = document.getElementById('blog-stock-search');
  const stockResults = document.getElementById('blog-stock-results');
  const stockStatus = document.getElementById('blog-stock-status');
  const visInput = document.getElementById('blog-visibility');
  const visSummary = document.getElementById('blog-visibility-summary');

  function open(){ modal && modal.classList.remove('hidden'); }
  function close(){ modal && modal.classList.add('hidden'); }
  openBtn && openBtn.addEventListener('click', open);
  closeBtn && closeBtn.addEventListener('click', close);
  cancelBtn && cancelBtn.addEventListener('click', close);

  // Styled visibility dropdown (robust iteration for older browsers)
  function bindVisibility(){
    var visNodes = document.querySelectorAll('[data-vis]');
    for (var i = 0; i < visNodes.length; i++){
      (function(btn){
        btn.addEventListener('click', function(){
          var v = btn.getAttribute('data-vis');
          if (visInput) visInput.value = v;
          if (visSummary && visSummary.firstChild) visSummary.firstChild.nodeValue = (v === 'both' ? 'Everywhere' : (v.charAt(0).toUpperCase()+v.slice(1)));
          var det = btn.closest ? btn.closest('details') : null;
          if (det) det.removeAttribute('open');
        });
      })(visNodes[i]);
  
  }
  }
  bindVisibility();

  // Media state
  let mediaItems = []; // [{file, type: 'image'|'video', name, cover:boolean}]
  let camStream = null;
  let mediaMeta = {}; // filename -> meta
  function syncMeta(){ if (mediaMetaField) mediaMetaField.value = JSON.stringify(mediaMeta); }
  function setStatus(msg){ if (stockStatus) stockStatus.textContent = msg || ''; }
  function isVideo(f){ return (f.type||'').indexOf('video/')===0; }
  function clamp8(){ if (mediaItems.length > 8) mediaItems = mediaItems.slice(0,8); }
  function refreshPreview(){
    if (!preview) return;
    preview.innerHTML = '';
    mediaItems.forEach((it, idx)=>{
      const url = (window.URL||window.webkitURL).createObjectURL(it.file);
      const card = document.createElement('div');
      card.className = 'relative border border-emerald-100 rounded overflow-hidden';
      card.style.height = '110px';
      card.innerHTML = (it.type==='video') ? '<video src="'+url+'" class="w-full h-full object-cover" muted></video>' : '<img src="'+url+'" class="w-full h-full object-cover" alt=""/>';
      // Controls overlay
      const bar = document.createElement('div');
      bar.className = 'absolute bottom-0 left-0 right-0 bg-black/40 text-white text-[11px] flex items-center justify-between px-1 py-0.5';
      bar.innerHTML = ''+
        '<div class="flex items-center gap-1">' +
        '  <label class="inline-flex items-center gap-1 cursor-pointer">' +
        '    <input type="checkbox" '+(it.cover?'checked':'')+' /> Cover' +
        '  </label>' +
        '  <button type="button" class="px-1 py-0.5 rounded bg-black/30 hover:bg-black/50" data-insert>Insert</button>' +
        '</div>' +
        '<div class="flex items-center gap-1">' +
        '  <button type="button" class="px-1 py-0.5 rounded bg-black/30 hover:bg-black/50" data-up>↑</button>' +
        '  <button type="button" class="px-1 py-0.5 rounded bg-black/30 hover:bg-black/50" data-down>↓</button>' +
        '  <button type="button" class="px-1 py-0.5 rounded bg-red-600/80 hover:bg-red-600" data-remove>×</button>' +
        '</div>';
      // Wire controls
      const chk = bar.querySelector('input[type=checkbox]');
      chk.addEventListener('change', ()=>{ mediaItems.forEach(m=>m.cover=false); it.cover = chk.checked; syncCoverFile(); refreshPreview(); });
      bar.querySelector('[data-insert]').addEventListener('click', ()=> insertTokenAtCursor(idx+1));
      bar.querySelector('[data-up]').addEventListener('click', ()=>{ if (idx>0){ const t=mediaItems[idx]; mediaItems[idx]=mediaItems[idx-1]; mediaItems[idx-1]=t; refreshPreview(); } });
      bar.querySelector('[data-down]').addEventListener('click', ()=>{ if (idx<mediaItems.length-1){ const t=mediaItems[idx]; mediaItems[idx]=mediaItems[idx+1]; mediaItems[idx+1]=t; refreshPreview(); } });
      bar.querySelector('[data-remove]').addEventListener('click', ()=>{ mediaItems.splice(idx,1); if (!mediaItems.some(m=>m.cover)) clearCoverFile(); refreshPreview(); });
      card.appendChild(bar);
      preview.appendChild(card);
    });
  }
  function insertTokenAtCursor(n){
    const el = contentEl; if (!el) return;
    try{
      el.focus();
      const token = '[[media:'+n+']]';
      const start = el.selectionStart||0, end = el.selectionEnd||0;
      const val = el.value||''; el.value = val.slice(0,start) + token + val.slice(end);
      const pos = start + token.length; el.setSelectionRange && el.setSelectionRange(pos, pos);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }catch(e){}
  }
  function clearCoverFile(){ try{ if (coverInput){ coverInput.value = ''; } }catch(e){}
  function syncCoverFile(){
    try{
      if (!coverInput) return;
      const sel = mediaItems.find(function(m){ return m.cover && m.type==='image'; });
      if (!sel){ coverInput.value=''; return; }
      const dt = new DataTransfer();
      dt.items.add(new File([sel.file], sel.file.name || 'cover.jpg', { type: sel.file.type || 'image/jpeg' }));
      coverInput.files = dt.files;
    }catch(e){ }
  }
  function addFile(file, meta){
    if (!file) return;
    const item = { file, type: isVideo(file) ? 'video' : 'image', name: file.name || ('blob-'+Date.now()), cover:false };
    mediaItems.push(item); clamp8();
    if (meta){ mediaMeta[item.name] = meta; syncMeta(); }
    refreshPreview();
  }
  // Upload button -> native input
  btnUpload && btnUpload.addEventListener('click', ()=> { try{ console.log('[blog] upload click'); }catch(_){} mediaInput && mediaInput.click(); });
  mediaInput && mediaInput.addEventListener('change', ()=>{ try{ console.log('[blog] media change count', (mediaInput.files||[]).length); }catch(_){} const list = Array.from(mediaInput.files||[]); list.forEach(f=> addFile(f)); refreshPreview(); });

  // Stock search/attach (adds to list, not replace)
  async function fetchStock(query, page){
    page = page || 1;
    const u = new URL(window.location.origin + '/users/api/feed/stock_images/');
    u.searchParams.set('q', query); u.searchParams.set('page', page); u.searchParams.set('per_page', 18);
    try{ const res = await fetch(u.toString()); if(!res.ok) return {results:[], total:0, error:'http'}; return await res.json(); }catch(e){ return {results:[], total:0, error:'network'}; }
  }
  function renderStock(items){
    if (!stockResults) return; stockResults.innerHTML='';
    items.forEach(it=>{
      const btn = document.createElement('button'); btn.type='button'; btn.className='relative group border border-emerald-100 rounded overflow-hidden'; btn.style.height='110px';
      btn.title = (it.attribution||'') + (it.provider?' • '+it.provider:'');
      btn.innerHTML = '\n        <img src="'+it.thumb_url+'" alt="" class="w-full h-full object-cover" />\n        <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition"></div>\n      ';
      btn.addEventListener('click', async ()=>{
        setStatus('Attaching image…'); btn.disabled = true;
        try{
          const r = await fetch(it.full_url); const blob = await r.blob();
          const fname = (it.provider||'stock')+'-'+(it.id||Date.now())+'.jpg';
          const file = new File([blob], fname, { type: blob.type||'image/jpeg' });
          addFile(file, {
            provider: it.provider, attribution: it.attribution, attribution_url: it.attribution_url,
            license: it.license, license_url: it.license_url, thumb_url: it.thumb_url
          });
        } finally { btn.disabled=false; setStatus(''); }
      });
      stockResults.appendChild(btn);
    });
  }
  stockBtn && stockBtn.addEventListener('click', async ()=>{
    const q = ((stockQ && stockQ.value) || '').trim(); if (!q) return;
    try{ console.log('[blog] stock search', q); }catch(_){}
    stockBtn.disabled = true; const old = stockBtn.textContent; stockBtn.textContent = 'Searching…'; setStatus('');
    try{ const data = await fetchStock(q,1); if (data.error){ setStatus('Unable to fetch images.'); return; }
      const items = data.results||[]; if (!items.length) setStatus('No results.'); renderStock(items); }
    finally{ stockBtn.disabled=false; stockBtn.textContent = old || 'Search'; }
  });
  stockQ && stockQ.addEventListener('keydown', (e)=>{ if (e.key==='Enter'){ e.preventDefault(); stockBtn && stockBtn.click(); }});

  // Camera handling
  function isMobile(){ try { return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent||''); } catch(e){ return false; } }
  async function openCam(){
    if (!camModal) return;
    camModal.classList.remove('hidden');
    // Reset UI
    camRetake && camRetake.classList.add('hidden');
    camUse && camUse.classList.add('hidden');
    camCapture && camCapture.classList.remove('hidden');
    if (camStatus) camStatus.textContent = 'Grant camera permission if prompted. Works on localhost or HTTPS.';
    if (camUpload) camUpload.classList.add('hidden');
    try{
      if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) throw new Error('getUserMedia unsupported');
  const constraints = { video: { facingMode: isMobile()? { ideal:'environment' } : 'user' } };
      camStream = await navigator.mediaDevices.getUserMedia(constraints);
      if (camVideo) camVideo.srcObject = camStream;
    }catch(e){
      // Keep modal open; show guidance and offer explicit upload option
      try { console.warn('[blog] getUserMedia failed:', e && (e.name+': '+e.message) || e); } catch(_){}
      if (camStatus) camStatus.textContent = 'Camera unavailable (' + (e && e.name ? e.name : 'error') + '). You can still use file upload.';
      if (camUpload) camUpload.classList.remove('hidden');
    }
  }
  function stopCam(){ try{ if (camStream){ camStream.getTracks().forEach(t=>t.stop()); camStream=null; } if (camVideo) camVideo.srcObject=null; }catch(e){} }
  function closeCam(){ if (camModal) camModal.classList.add('hidden'); stopCam(); }
  btnCamera && btnCamera.addEventListener('click', (ev)=>{
    if(ev && ev.preventDefault) ev.preventDefault();
    if(ev && ev.stopPropagation) ev.stopPropagation();
    if(ev && ev.stopImmediatePropagation) ev.stopImmediatePropagation();
    try{ console.log('[blog] camera open'); }catch(_){}
    const test = document.createElement('input'); test.type='file';
    const supportsNative = ('capture' in test) && isMobile();
    if (supportsNative && cameraInput) return cameraInput.click();
    return openCam();
  });
  camClose && camClose.addEventListener('click', closeCam);
  camCancel && camCancel.addEventListener('click', closeCam);
  camModal && camModal.addEventListener('click', (e)=>{ if (e.target===camModal) closeCam(); });
  camCapture && camCapture.addEventListener('click', async ()=>{
    try{ console.log('[blog] camera capture'); }catch(_){}
    try{ const v = camVideo; if (!v) return; const canvas=document.createElement('canvas'); const w=v.videoWidth||1280, h=v.videoHeight||720; canvas.width=w; canvas.height=h; const ctx=canvas.getContext('2d'); ctx.drawImage(v,0,0,w,h);
      canvas.toBlob(function(blob){ if (!blob) return; const file = new File([blob], 'camera-'+Date.now()+'.jpg', { type:'image/jpeg' }); addFile(file); camCapture.classList.add('hidden'); camRetake.classList.remove('hidden'); camUse.classList.remove('hidden'); }, 'image/jpeg', 0.9);
    }catch(e){}
  });
  camRetake && camRetake.addEventListener('click', ()=>{ camRetake.classList.add('hidden'); camUse && camUse.classList.add('hidden'); camCapture && camCapture.classList.remove('hidden'); });
  camUse && camUse.addEventListener('click', closeCam);
  camUpload && camUpload.addEventListener('click', function(){ if (cameraInput) cameraInput.click(); closeCam(); });
  cameraInput && cameraInput.addEventListener('change', ()=>{ const f = cameraInput.files && cameraInput.files[0]; if (f) addFile(f); });

  // Hide camera button on devices that don't support capture (desktop browsers), similar to feed
  function maybeHideCamera(){
    try{
      var test = document.createElement('input'); test.type='file';
      var mobile = isMobile();
      var supportsNativeCapture = ('capture' in test) || mobile;
      var supportsGUM = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
      if (!supportsNativeCapture && !supportsGUM && btnCamera) { btnCamera.style.display = 'none'; }
    }catch(_){ /* ignore */ }
  }
  maybeHideCamera();

  // Emoji picker (match feed behavior: fixed popover appended to body)
  (function initEmojiPicker(){
    var POP = null; var activeInput = null;
    var EMOJIS = ['😀','😁','😂','🤣','😅','😊','🙂','😉','😍','😘','🤗','🤔','🤩','😎','😇','🙌','👍','👏','💯','🔥','🌟','🎉','✅','❌','⚠️','❤️','🧡','💛','💚','💙','💜','🤍','🤎','🖤','💪','🙏','🤝','💡','📣','📝','📅','📍','📈','💬','🧘','🩺','🧠','🌿','🌈','☀️','⭐','☕','🍎'];
    function createPopover(){ var d=document.createElement('div'); d.className='emoji-popover'; var g=document.createElement('div'); g.className='emoji-grid'; EMOJIS.forEach(function(e){ var c=document.createElement('button'); c.type='button'; c.className='emoji-cell'; c.textContent=e; c.addEventListener('click', function(){ insertEmoji(e); close(); }); g.appendChild(c); }); d.appendChild(g); document.body.appendChild(d); return d; }
    function open(btn, input){
      activeInput = input||null; if (!activeInput) return;
      if (!POP) POP = createPopover();
      var r = btn.getBoundingClientRect();
      // If inside the fixed blog modal, use viewport coords (no scroll). Otherwise, include page scroll.
      var insideFixed = !!(btn.closest && btn.closest('#blog-composer'));
      // Temporarily show to measure and clamp
      POP.style.visibility = 'hidden'; POP.style.display = 'block';
      var pw = POP.offsetWidth || 260; var ph = POP.offsetHeight || 200;
      var left = insideFixed ? r.left : (r.left + window.scrollX);
      var top = insideFixed ? (r.bottom + 8) : (r.bottom + 8 + window.scrollY);
      // Clamp within viewport
      var maxLeft = (insideFixed ? window.innerWidth : document.documentElement.clientWidth) - pw - 8;
      if (left < 8) left = 8; if (left > maxLeft) left = Math.max(8, maxLeft);
      var maxBottom = (insideFixed ? window.innerHeight : document.documentElement.clientHeight) - 8;
      if (top + ph > maxBottom) { top = Math.max(8, (insideFixed ? r.top - ph - 8 : (r.top - ph - 8 + window.scrollY))); }
      POP.style.top = top + 'px';
      POP.style.left = left + 'px';
      POP.style.visibility = 'visible';
      setTimeout(function(){ document.addEventListener('click', onDoc, { once: true }); }, 0);
    }
    function close(){ if (POP) POP.style.display='none'; }
    function onDoc(ev){ if (!POP) return; if (ev && POP.contains(ev.target)) return; close(); }
    function insertEmoji(ch){ try{ var el=activeInput; if (!el) return; el.focus(); var s=el.selectionStart||0, e=el.selectionEnd||0; var v=el.value||''; el.value=v.slice(0,s)+ch+v.slice(e); var pos=s+ch.length; el.setSelectionRange && el.setSelectionRange(pos,pos); el.dispatchEvent(new Event('input',{bubbles:true})); }catch(e){} }
    document.addEventListener('click', function(ev){
      var t = ev.target; if (!t) return;
      // Normalize Safari Text node target to an element
      var el = (t.nodeType === 1) ? t : t.parentElement; if (!el) return;
      var btn = el.closest && el.closest('.emoji-btn'); if (!btn) return;
      ev.preventDefault && ev.preventDefault();
      var sel = btn.getAttribute('data-emoji-target');
      var input = sel ? document.querySelector(sel) : null;
      if (input) open(btn, input);
    });
    document.addEventListener('keydown', function(e){ if (POP && POP.style.display==='block' && e.key==='Escape') close(); });
  })();

  // Build ordered submission
  formEl && formEl.addEventListener('submit', function(e){
    e.preventDefault();
    try{ console.log('[blog] submit'); }catch(_){}
    const fd = new FormData(formEl);
    mediaItems.forEach(it=>{ fd.append('media', it.file, it.file.name); });
    syncMeta();
    fetch(formEl.action, { method:'POST', body: fd }).then(r=>{ if (r.ok) window.location.href = formEl.getAttribute('action-success') || window.location.href; });
  });

  // end of main init scope
  try { window._blogComposerDone = true; } catch(_){ }

}

})();
