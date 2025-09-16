// static/js/profile.js
(async function(){
  const btn = document.getElementById('save-name');
  if(!btn) return;
  btn.addEventListener('click', async () => {
    const name = (document.getElementById('name')||{}).value || '';
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
    const r = await fetch('/api/profile/change-name', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
      credentials:'include',
      body: JSON.stringify({ name })
    });
    const data = await r.json().catch(()=>({}));
    if (r.ok && !data.error) {
      location.reload();
    } else {
      alert(data.error || 'Failed to update name');
    }
  });
})();