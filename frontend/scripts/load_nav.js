// Loads shared navbar HTML into element with id 'site-nav'
(async function(){
  try{
    const resp = await fetch('navbar.html');
    if(!resp.ok) return;
    const html = await resp.text();
    const target = document.getElementById('site-nav');
    if(target){
      target.innerHTML = html;
      // attach logout if present
      const logout = document.getElementById('navLogout');
      if(logout){
        logout.addEventListener('click', (e)=>{e.preventDefault(); sessionStorage.clear(); window.location.href='login.html';});
      }
    }
  }catch(e){ console.warn('Navbar load failed', e); }
})();