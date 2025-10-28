// Auth UI and helpers moved out of templates for clarity.
(function(){
  // Acting user UI: persist to localStorage and expose a getter for other scripts
  (function(){
    const input = document.getElementById('acting-user-id');
    const btn = document.getElementById('acting-set');
    if(!input || !btn) return;
    const key = 'actingUserId';
    input.value = localStorage.getItem(key) || '';
    btn.addEventListener('click', ()=>{
      const v = input.value.trim();
      if(v) localStorage.setItem(key, v); else localStorage.removeItem(key);
      showToast('Acting user id set to: ' + (v || '(none)'), 'info');
    });
    window.getActingUserId = function(){ return localStorage.getItem(key); };
  })();

  // Login form handling and header auth UI
  (function(){
    const idInput = document.getElementById('login-user-id');
    const pwInput = document.getElementById('login-password');
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const headerAvatar = document.getElementById('header-avatar');
    const authToggleLabel = document.getElementById('auth-toggle-label');
    const key = 'authToken';
    function setToken(t){ if(t) localStorage.setItem(key, t); else localStorage.removeItem(key); }

    function parseJwt(token){
      try{
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c){
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
      }catch(e){ return null }
    }

    // Cache helpers
    function readCachedProfile(sub){
      try{
        const raw = localStorage.getItem('authProfile');
        if(!raw) return null;
        const p = JSON.parse(raw);
        if(p && String(p.sub) === String(sub) && p.name) return p;
      }catch(e){ }
      return null;
    }
    function writeCachedProfile(obj){ try{ localStorage.setItem('authProfile', JSON.stringify(obj)); }catch(e){} }

    async function fetchAndSetUsernameFromToken(token){
      if(!token) return;
      const payload = parseJwt(token);
      if(!payload || !payload.sub) return;
      const uid = payload.sub;
      const cached = readCachedProfile(uid);
      if(cached){
        if(authToggleLabel) authToggleLabel.textContent = 'Account · ' + cached.name;
        if(headerAvatar){ headerAvatar.textContent = (cached.name || 'U').split(' ').map(s=>s[0]).slice(0,2).join('').toUpperCase(); headerAvatar.style.display = ''; }
        return;
      }
      try{
        const res = await fetch('/users/' + uid);
        if(!res.ok) return;
        const u = await res.json();
        if(u && u.name){
          writeCachedProfile({ sub: uid, name: u.name });
          if(authToggleLabel) authToggleLabel.textContent = 'Account · ' + u.name;
          if(headerAvatar){ headerAvatar.textContent = (u.name || 'U').split(' ').map(s=>s[0]).slice(0,2).join('').toUpperCase(); headerAvatar.style.display = ''; }
        }
      }catch(e){ /* ignore */ }
    }

    async function handleLogin(){
      const uid = idInput.value.trim(); const pw = pwInput.value;
      if(!uid){ showToast('Enter user id', 'warn'); return; }
      try{
        const res = await fetch('/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({user_id: uid, password: pw || undefined})});
        if(!res.ok){ const j = await res.json().catch(()=>({})); showToast('Login failed: ' + (j.detail||res.statusText), 'error'); return; }
        const j = await res.json(); setToken(j.access_token);
        showToast('Logged in', 'success');
        updateAuthUI();
        await fetchAndSetUsernameFromToken(j.access_token);
      }catch(e){ showToast('Login failed', 'error'); }
    }

    loginBtn && loginBtn.addEventListener('click', function(e){ e.preventDefault(); handleLogin(); });
    logoutBtn && logoutBtn.addEventListener('click', function(e){ e.preventDefault(); setToken(null); localStorage.removeItem('authProfile'); if(headerAvatar){ headerAvatar.style.display='none'; } if(authToggleLabel){ authToggleLabel.textContent = 'Account'; } showToast('Logged out', 'info'); updateAuthUI(); });
    window.getAuthToken = function(){ return localStorage.getItem(key); };
    window.getAuthHeader = function(){ const t = window.getAuthToken(); return t ? {'Authorization':'Bearer '+t} : {}; };

    // On load, if token exists, update UI and try to fetch username
    document.addEventListener('DOMContentLoaded', function(){ updateAuthUI(); const t = window.getAuthToken(); if(t) fetchAndSetUsernameFromToken(t); });
  })();

  // Header auth toggle: show/hide compact auth panel and reflect login state
  (function(){
    window.addEventListener('load', function(){
      const toggle = document.getElementById('auth-toggle-btn');
      const panel = document.getElementById('auth-panel');
      const status = document.getElementById('auth-status');
      const loginBtn = document.getElementById('login-btn');
      const logoutBtn = document.getElementById('logout-btn');
      if(!toggle || !panel) return;

      function setPanelOpen(open){
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        panel.setAttribute('aria-hidden', open ? 'false' : 'true');
        if(open){
          const focusable = panel.querySelectorAll('input,button,a,select,textarea');
          if(focusable && focusable.length) focusable[0].focus();
        }
      }

      function updateAuthUI(){
        const t = (window.getAuthToken && window.getAuthToken());
        if(t){
          if(status) status.textContent = 'Signed in';
          if(loginBtn) loginBtn.style.display = 'none';
          if(logoutBtn) logoutBtn.style.display = '';
        } else {
          if(status) status.textContent = 'Not signed in';
          if(loginBtn) loginBtn.style.display = '';
          if(logoutBtn) logoutBtn.style.display = 'none';
        }
      }

      toggle.addEventListener('click', function(e){ e.stopPropagation(); const isHidden = panel.getAttribute('aria-hidden') === 'true'; setPanelOpen(isHidden); if(isHidden){ panel.addEventListener('keydown', trapKey); } else { panel.removeEventListener('keydown', trapKey); } });
      document.addEventListener('click', function(e){ if(!panel.contains(e.target) && !toggle.contains(e.target)) { setPanelOpen(false); panel.removeEventListener('keydown', trapKey); } });
      window.addEventListener('storage', function(e){ if(e.key === 'authToken'){ localStorage.removeItem('authProfile'); updateAuthUI(); } });

      function trapKey(e){
        if(e.key === 'Escape') { setPanelOpen(false); panel.removeEventListener('keydown', trapKey); toggle.focus(); return; }
        if(e.key !== 'Tab') return;
        const focusable = Array.from(panel.querySelectorAll('input,button,a,select,textarea')).filter(n=>!n.disabled && n.offsetParent !== null);
        if(focusable.length === 0) return;
        const idx = focusable.indexOf(document.activeElement);
        if(e.shiftKey){
          if(idx === 0 || document.activeElement === panel) { focusable[focusable.length-1].focus(); e.preventDefault(); }
        } else {
          if(idx === focusable.length-1) { focusable[0].focus(); e.preventDefault(); }
        }
      }

      updateAuthUI();
    });
  })();
})();
