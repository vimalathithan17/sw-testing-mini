// Toast manager moved to static file so other scripts can call showToast()
(function(){
  function createToastElement(msg, type){
    const el = document.createElement('div');
    el.classList.add('toast', `toast--${type || 'info'}`);
    const inner = document.createElement('div');
    inner.className = 'toast-message';
    inner.textContent = msg;
    const btn = document.createElement('button');
    btn.className = 'toast-close';
    btn.setAttribute('aria-label','dismiss');
    btn.innerHTML = '&times;';
    btn.addEventListener('click', ()=>{ hideToast(el); });
    el.appendChild(inner);
    el.appendChild(btn);
    return el;
  }

  function hideToast(el){
    if(!el) return;
    el.classList.remove('toast-in');
    el.classList.add('toast-out');
    el.addEventListener('animationend', ()=> el.remove(), { once: true });
  }

  function showToast(payload){
    let msg=''; let type='info'; let duration=4000;
    if(typeof payload === 'string') msg = payload;
    else if (payload && typeof payload === 'object'){
      msg = payload.message || JSON.stringify(payload);
      type = payload.type || 'info';
      duration = (typeof payload.duration === 'number') ? payload.duration : duration;
    } else return;

    const container = document.getElementById('toast-container');
    if(!container) return;
    const el = createToastElement(msg, type);
    container.appendChild(el);
    requestAnimationFrame(()=> el.classList.add('toast-in'));
    let timeoutId = setTimeout(()=> hideToast(el), duration);
    el.addEventListener('mouseenter', ()=> clearTimeout(timeoutId));
    el.addEventListener('mouseleave', ()=> { timeoutId = setTimeout(()=> hideToast(el), Math.max(800, duration/3)); });
  }

  // expose globally
  window.showToast = showToast;
  window.hideToast = hideToast;

  // On load, parse JSON from data-toast attribute and show initial toast if present
  window.addEventListener('load', function(){
    try{
      const container = document.getElementById('toast-container');
      const raw = container && container.getAttribute('data-toast');
      let payload = null;
      if (raw && raw !== 'null') payload = JSON.parse(raw);
      if (payload) showToast(payload);
    }catch(e){ console.warn('Failed to parse toast payload', e); }
  });
})();
