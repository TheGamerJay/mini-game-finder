# Add after the login/register routes in app.py

@app.get("/settings/password")
def password_form():
    if not session.get("user_id"): 
        return redirect("/login")
    return """
<!doctype html><meta charset="utf-8">
<title>Change Password</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;margin:40px}
  .card{max-width:480px;margin:auto;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 1px 6px rgba(0,0,0,.08)}
  .row{display:flex;gap:8px;align-items:center}
  .btn{padding:8px 12px;border:1px solid #d1d5db;border-radius:10px;background:#fff;cursor:pointer}
  input{padding:10px;border:1px solid #d1d5db;border-radius:10px;width:100%}
  label{font-size:14px;color:#374151}
</style>
<div class="card">
  <h2>Change Password</h2>
  <form method="post" action="/settings/password" onsubmit="return checkMatch()">
    <label>Current password</label>
    <div class="row">
      <input id="cpw" name="current" type="password" placeholder="Current password" required />
      <button type="button" class="btn" aria-pressed="false" onclick="togglePw('cpw', this)">👁</button>
    </div>

    <label style="margin-top:8px;">New password</label>
    <div class="row">
      <input id="npw" name="new" type="password" placeholder="New password" required />
      <button type="button" class="btn" aria-pressed="false" onclick="togglePw('npw', this)">👁</button>
    </div>

    <label style="margin-top:8px;">Confirm new password</label>
    <div class="row">
      <input id="npw2" name="confirm" type="password" placeholder="Repeat new password" required />
      <button type="button" class="btn" aria-pressed="false" onclick="togglePw('npw2', this)">👁</button>
    </div>

    <div class="row" style="margin-top:12px;justify-content:space-between">
      <button class="btn" type="submit">Update</button>
      <a class="btn" href="/profile/""" + str(session.get("user_id")) + """">Back to profile</a>
    </div>
  </form>
</div>
<script>
function togglePw(id, btn){
  const i = document.getElementById(id);
  const show = i.type === 'password';
  i.type = show ? 'text' : 'password';
  btn.setAttribute('aria-pressed', show ? 'true' : 'false');
  btn.textContent = show ? '🙈' : '👁';
}
function checkMatch(){
  const a = document.getElementById('npw').value;
  const b = document.getElementById('npw2').value;
  if(a !== b){ alert('New passwords do not match'); return false; }
  return true;
}
</script>
"""

@app.post("/settings/password")
def password_change():
    uid = session.get("user_id")
    if not uid: 
        return redirect("/login")
        
    user = User.query.get(uid)
    cur = request.form.get("current") or ""
    new = request.form.get("new") or ""
    conf = request.form.get("confirm") or ""
    
    if not user.check_password(cur):
        return "Wrong current password", 400
    if not new or new != conf:
        return "New passwords do not match", 400
        
    user.set_password(new)
    db.session.commit()
    return redirect(f"/profile/{user.id}")
