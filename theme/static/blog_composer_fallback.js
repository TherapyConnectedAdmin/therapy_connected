(function(){
  // If main composer is present or already initializing, do nothing
  try { if (window._blogComposerInitStarted || window._blogComposerDone) return; } catch(_) {}
  try { console.log('[blog-fallback] loading'); } catch(_){ }
  var modal = document.getElementById('blog-composer');
  if(!modal) return;
  // Modal open/close
  var openBtn = document.getElementById('open-blog-composer');
  var closeBtn = document.getElementById('blog-close');
  var cancelBtn = document.getElementById('blog-cancel');
  function open(){ modal.classList.remove('hidden'); }
  function close(){ modal.classList.add('hidden'); }
  openBtn && openBtn.addEventListener('click', open);
  closeBtn && closeBtn.addEventListener('click', close);
  cancelBtn && cancelBtn.addEventListener('click', close);

  // Emoji (simple prompt)
  var emojiButtons = document.querySelectorAll('.emoji-btn');
  for(var i=0;i<emojiButtons.length;i++){
    emojiButtons[i].addEventListener('click', function(ev){
      if (window._blogComposerDone || window._blogComposerInitStarted) return;
      ev.preventDefault();
      var sel = this.getAttribute('data-emoji-target');
      var input = sel ? document.querySelector(sel) : null;
      if(!input) return;
      var ch = window.prompt('Insert emoji (paste one):','😊');
      if(!ch) return; input.value = (input.value||'') + ch;
    });
  }

  // Upload binding
  var btnUpload = document.getElementById('blog-btn-upload');
  var mediaInput = document.getElementById('blog-media');
  var preview = document.getElementById('blog-preview');
  var items = [];
  function addPreview(file){
    var url = (window.URL||window.webkitURL).createObjectURL(file);
    var c = document.createElement('div'); c.className='relative border border-emerald-100 rounded overflow-hidden'; c.style.height='110px';
    if((file.type||'').indexOf('video/')===0){ c.innerHTML='<video src="'+url+'" class="w-full h-full object-cover" muted></video>'; }
    else { c.innerHTML='<img src="'+url+'" class="w-full h-full object-cover" alt=""/>'; }
    preview && preview.appendChild(c);
  }
  btnUpload && btnUpload.addEventListener('click', function(){ mediaInput && mediaInput.click(); });
  mediaInput && mediaInput.addEventListener('change', function(){
    var list = Array.prototype.slice.call(mediaInput.files||[]);
    for(var i=0;i<list.length;i++){ items.push(list[i]); addPreview(list[i]); if(items.length>=8) break; }
  });

  // Camera: fallback to native file input capture when available
  var btnCamera = document.getElementById('blog-btn-camera');
  var cameraInput = document.getElementById('blog-camera');
  btnCamera && btnCamera.addEventListener('click', function(){ if(cameraInput) cameraInput.click(); });
  cameraInput && cameraInput.addEventListener('change', function(){
    var f = cameraInput.files && cameraInput.files[0]; if(f){ items.push(f); addPreview(f); }
  });

  // Stock search: basic fetch + attach
  var stockBtn = document.getElementById('blog-stock-search');
  var stockQ = document.getElementById('blog-stock-q');
  var stockResults = document.getElementById('blog-stock-results');
  var stockStatus = document.getElementById('blog-stock-status');
  function setStatus(t){ if(stockStatus) stockStatus.textContent=t||''; }
  function render(results){ if(!stockResults) return; stockResults.innerHTML='';
    for(var i=0;i<results.length;i++){
      (function(it){
        var b=document.createElement('button'); b.type='button'; b.className='relative group border border-emerald-100 rounded overflow-hidden'; b.style.height='110px';
        b.innerHTML = '<img src="'+it.thumb_url+'" class="w-full h-full object-cover"/>';
        b.addEventListener('click', function(){
          setStatus('Attaching image…'); b.disabled=true;
          fetch(it.full_url).then(function(r){ return r.blob(); }).then(function(blob){
            var file = new File([blob], (it.provider||'stock')+'-'+(it.id||Date.now())+'.jpg', {type: blob.type||'image/jpeg'});
            items.push(file); addPreview(file); setStatus(''); b.disabled=false;
          }).catch(function(){ setStatus('Failed to attach'); b.disabled=false; });
        });
        stockResults.appendChild(b);
      })(results[i]);
    }
  }
  stockBtn && stockBtn.addEventListener('click', function(){
    var q = (stockQ && stockQ.value || '').trim(); if(!q) return;
    setStatus('Searching…');
    var u = new URL(window.location.origin + '/users/api/feed/stock_images/');
    u.searchParams.set('q', q); u.searchParams.set('page','1'); u.searchParams.set('per_page','18');
    fetch(u.toString()).then(function(r){ return r.json(); }).then(function(d){ render(d.results||[]); setStatus(''); }).catch(function(){ setStatus('Unable to fetch images.'); });
  });
})();
