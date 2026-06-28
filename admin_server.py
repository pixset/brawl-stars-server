"""
admin_server.py — CDN file server + Admin panel (Flask)
Runs on PORT env var (default 8080)
"""

import os
import sys
import json

# Make sure project root is on path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, abort, redirect, Response

from Database.DatabaseManager import DatabaseManager

app = Flask(__name__)

CDN_DIR = os.path.join(_ROOT, 'ContentUpdater', 'Update')

# Пароль на админку. Задаётся переменной окружения ADMIN_PASSWORD.
# Если не задан — панель открыта (как и раньше), но в логах будет предупреждение.
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '').strip()
if not ADMIN_PASSWORD:
    print('[Admin] WARNING: ADMIN_PASSWORD не задан — панель открыта всем!')


def require_auth(fn):
    """Basic-Auth защита для /admin и /admin/api/*. Логин любой, пароль = ADMIN_PASSWORD."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if ADMIN_PASSWORD:
            auth = request.authorization
            if not auth or auth.password != ADMIN_PASSWORD:
                return Response(
                    'Auth required', 401,
                    {'WWW-Authenticate': 'Basic realm="BSDS Admin"'})
        return fn(*args, **kwargs)
    return wrapper


@app.route('/')
def root():
    """Голый домен → сразу в админку (вместо 404 от CDN-роута)."""
    return redirect('/admin')

# ══════════════════════════════════════════════════════════
#  CDN — serves game asset files (fingerprint, resources)
# ══════════════════════════════════════════════════════════

@app.route('/<path:filepath>')
def cdn_serve(filepath):
    """Serve any file from ContentUpdater/Update/"""
    full = os.path.join(CDN_DIR, filepath)
    if not os.path.isfile(full):
        abort(404)
    directory = os.path.dirname(full)
    filename  = os.path.basename(full)
    return send_from_directory(directory, filename)


# ══════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


# ══════════════════════════════════════════════════════════
#  ADMIN API
# ══════════════════════════════════════════════════════════

@app.route('/admin/api/players')
@require_auth
def api_players():
    db = DatabaseManager()
    return jsonify(db.getAllPlayersData())


@app.route('/admin/api/player/<int:low_id>')
@require_auth
def api_player(low_id):
    db = DatabaseManager()
    data = db.getPlayerData(low_id)
    if data is None:
        return jsonify({'error': 'Player not found'}), 404
    return jsonify(data)


@app.route('/admin/api/gems', methods=['POST'])
@require_auth
def api_gems():
    body = request.get_json(force=True)
    low_id = int(body.get('player_id', 0))
    amount = int(body.get('amount', 0))
    if not low_id:
        return jsonify({'error': 'player_id required'}), 400

    db = DatabaseManager()
    data = db.getPlayerData(low_id)
    if data is None:
        return jsonify({'error': 'Player not found'}), 404

    new_gems = data.get('gems', 0) + amount
    ok, result = db.adminSetField(low_id, 'gems', new_gems)
    if not ok:
        return jsonify({'error': result}), 500
    return jsonify({'success': True, 'gems': new_gems})


@app.route('/admin/api/gems/set', methods=['POST'])
@require_auth
def api_gems_set():
    body = request.get_json(force=True)
    low_id = int(body.get('player_id', 0))
    amount = int(body.get('amount', 0))
    if not low_id:
        return jsonify({'error': 'player_id required'}), 400

    db = DatabaseManager()
    ok, result = db.adminSetField(low_id, 'gems', amount)
    if not ok:
        return jsonify({'error': result}), 500
    return jsonify({'success': True, 'gems': amount})


@app.route('/admin/api/trophies', methods=['POST'])
@require_auth
def api_trophies():
    """
    Set trophies.
    Body: { player_id, amount, brawler_id? }
    If brawler_id is omitted or "all" → set all brawlers.
    """
    body = request.get_json(force=True)
    low_id    = int(body.get('player_id', 0))
    amount    = int(body.get('amount', 0))
    brawler   = body.get('brawler_id', 'all')

    if not low_id:
        return jsonify({'error': 'player_id required'}), 400

    db = DatabaseManager()

    if brawler == 'all' or brawler is None:
        ok, result = db.adminSetAllBrawlerTrophies(low_id, amount)
    else:
        ok, result = db.adminSetBrawlerTrophies(low_id, int(brawler), amount)

    if not ok:
        return jsonify({'error': result}), 500

    return jsonify({'success': True, 'trophies': result.get('trophies', 0)})


@app.route('/admin/api/coins', methods=['POST'])
@require_auth
def api_coins():
    body = request.get_json(force=True)
    low_id = int(body.get('player_id', 0))
    amount = int(body.get('amount', 0))
    if not low_id:
        return jsonify({'error': 'player_id required'}), 400
    db = DatabaseManager()
    data = db.getPlayerData(low_id)
    if data is None:
        return jsonify({'error': 'Player not found'}), 404
    new_val = data.get('coins', 0) + amount
    ok, result = db.adminSetField(low_id, 'coins', new_val)
    if not ok:
        return jsonify({'error': result}), 500
    return jsonify({'success': True, 'coins': new_val})


# ══════════════════════════════════════════════════════════
#  ADMIN WEB UI
# ══════════════════════════════════════════════════════════

BRAWLERS = [
    {"id": 0,  "name": "Shelly"},    {"id": 1,  "name": "Colt"},
    {"id": 2,  "name": "Bull"},      {"id": 3,  "name": "Brock"},
    {"id": 4,  "name": "Dynamike"},  {"id": 5,  "name": "Bo"},
    {"id": 6,  "name": "El Primo"},  {"id": 7,  "name": "Barley"},
    {"id": 8,  "name": "Poco"},      {"id": 9,  "name": "Rico"},
    {"id": 10, "name": "Darryl"},    {"id": 11, "name": "Penny"},
    {"id": 12, "name": "Piper"},     {"id": 13, "name": "Pam"},
    {"id": 14, "name": "Frank"},     {"id": 15, "name": "Mortis"},
    {"id": 16, "name": "Tara"},      {"id": 17, "name": "Gene"},
    {"id": 18, "name": "Tick"},      {"id": 19, "name": "Leon"},
    {"id": 20, "name": "Rosa"},      {"id": 21, "name": "Carl"},
    {"id": 22, "name": "Bibi"},      {"id": 23, "name": "8-Bit"},
    {"id": 24, "name": "Sandy"},     {"id": 25, "name": "Bea"},
    {"id": 26, "name": "Emz"},       {"id": 27, "name": "Mr. P"},
    {"id": 28, "name": "Max"},       {"id": 29, "name": "Jacky"},
    {"id": 30, "name": "Gale"},      {"id": 31, "name": "Nani"},
    {"id": 32, "name": "Sprout"},    {"id": 34, "name": "Surge"},
    {"id": 35, "name": "Colette"},   {"id": 36, "name": "Amber"},
    {"id": 37, "name": "Lou"},       {"id": 38, "name": "Byron"},
    {"id": 39, "name": "Edgar"},     {"id": 40, "name": "Colonel Ruffs"},
    {"id": 41, "name": "Stu"},       {"id": 42, "name": "Belle"},
    {"id": 43, "name": "Squeak"},    {"id": 44, "name": "Grom"},
    {"id": 45, "name": "Buzz"},      {"id": 46, "name": "Griff"},
    {"id": 47, "name": "Ash"},       {"id": 49, "name": "Meg"},
    {"id": 50, "name": "Lola"},      {"id": 51, "name": "Eve"},
    {"id": 52, "name": "Janet"},     {"id": 53, "name": "Bonnie"},
]

ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BSDS Admin Panel</title>
<style>
  :root {
    --bg:      #0d0f1a;
    --card:    #161927;
    --border:  #252840;
    --accent:  #f7c948;
    --accent2: #ff5c5c;
    --green:   #3dd68c;
    --text:    #e8eaf6;
    --muted:   #8b90b8;
    --input:   #1e2235;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }

  header {
    background: linear-gradient(135deg, #1a1f35 0%, #111827 100%);
    border-bottom: 1px solid var(--border);
    padding: 18px 32px;
    display: flex; align-items: center; gap: 14px;
  }
  header h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: .5px; }
  header span { font-size: 2rem; }
  .tag { background: var(--accent); color: #000; font-size: .65rem; font-weight: 800;
         padding: 2px 8px; border-radius: 20px; letter-spacing: 1px; text-transform: uppercase; }

  main { max-width: 1100px; margin: 0 auto; padding: 32px 20px; display: grid;
         grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:720px) { main { grid-template-columns: 1fr; } }

  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
  }
  .card.full { grid-column: 1 / -1; }
  .card h2 { font-size: 1rem; font-weight: 700; color: var(--accent); margin-bottom: 18px;
             display: flex; align-items: center; gap: 8px; }
  .card h2 .ico { font-size: 1.2rem; }

  label { display: block; font-size: .78rem; color: var(--muted); margin-bottom: 6px; margin-top: 14px; }
  label:first-of-type { margin-top: 0; }

  input, select {
    width: 100%; padding: 10px 14px; border-radius: 8px;
    background: var(--input); border: 1px solid var(--border);
    color: var(--text); font-size: .9rem; outline: none;
    transition: border-color .2s;
  }
  input:focus, select:focus { border-color: var(--accent); }

  .btn {
    display: inline-block; margin-top: 16px; padding: 11px 22px;
    border-radius: 9px; border: none; cursor: pointer;
    font-weight: 700; font-size: .9rem; transition: opacity .15s, transform .1s;
  }
  .btn:active { transform: scale(.97); }
  .btn-gold  { background: var(--accent);  color: #000; }
  .btn-red   { background: var(--accent2); color: #fff; }
  .btn-green { background: var(--green);   color: #000; }
  .btn-gray  { background: var(--border);  color: var(--text); }
  .btn:hover { opacity: .88; }

  .msg { margin-top: 14px; padding: 11px 14px; border-radius: 9px;
         font-size: .85rem; display: none; }
  .msg.ok  { background: #1a3d2b; border: 1px solid #2a6644; color: var(--green); }
  .msg.err { background: #3d1a1a; border: 1px solid #663333; color: var(--accent2); }

  /* Players table */
  .table-wrap { overflow-x: auto; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { text-align: left; color: var(--muted); font-weight: 600; padding: 8px 12px;
       border-bottom: 1px solid var(--border); font-size: .75rem; text-transform: uppercase; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e2235; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #1b1f30; }
  .badge { background: var(--input); border-radius: 6px; padding: 2px 8px;
           font-size: .75rem; font-weight: 600; }
  .badge-gold  { color: var(--accent); }
  .badge-green { color: var(--green); }

  .use-btn { background: #252840; border: none; color: var(--text); padding: 5px 12px;
             border-radius: 6px; cursor: pointer; font-size: .8rem; }
  .use-btn:hover { background: var(--border); }

  #playerDetail pre { background: var(--input); border-radius: 8px; padding: 14px;
                      font-size: .75rem; overflow-x: auto; color: #a8d8b0;
                      border: 1px solid var(--border); margin-top: 10px; }
  .search-row { display: flex; gap: 10px; }
  .search-row input { flex: 1; }
  .search-row .btn { margin-top: 0; }
</style>
</head>
<body>
<header>
  <span>🎮</span>
  <h1>BSDS Admin Panel</h1>
  <span class="tag">v40</span>
</header>
<main>

  <!-- ── Gems ── -->
  <div class="card">
    <h2><span class="ico">💎</span> Give Gems</h2>
    <label>Player Low ID</label>
    <input id="g-pid" type="number" placeholder="e.g. 12345678">
    <label>Amount (negative to subtract)</label>
    <input id="g-amt" type="number" placeholder="e.g. 500" value="500">
    <label>Mode</label>
    <select id="g-mode">
      <option value="add">Add to current</option>
      <option value="set">Set exact value</option>
    </select>
    <button class="btn btn-gold" onclick="doGems()">Give Gems 💎</button>
    <div class="msg" id="g-msg"></div>
  </div>

  <!-- ── Trophies ── -->
  <div class="card">
    <h2><span class="ico">🏆</span> Set Trophies</h2>
    <label>Player Low ID</label>
    <input id="t-pid" type="number" placeholder="e.g. 12345678">
    <label>Trophies per brawler</label>
    <input id="t-amt" type="number" placeholder="e.g. 1250" value="1250">
    <label>Brawler</label>
    <select id="t-brawler">
      <option value="all">🌟 All Brawlers</option>
      __BRAWLER_OPTIONS__
    </select>
    <button class="btn btn-gold" onclick="doTrophies()">Set Trophies 🏆</button>
    <div class="msg" id="t-msg"></div>
  </div>

  <!-- ── Coins ── -->
  <div class="card">
    <h2><span class="ico">🪙</span> Give Coins</h2>
    <label>Player Low ID</label>
    <input id="c-pid" type="number" placeholder="e.g. 12345678">
    <label>Amount</label>
    <input id="c-amt" type="number" placeholder="e.g. 99999" value="99999">
    <button class="btn btn-gold" onclick="doCoins()">Give Coins 🪙</button>
    <div class="msg" id="c-msg"></div>
  </div>

  <!-- ── Player Lookup ── -->
  <div class="card">
    <h2><span class="ico">🔍</span> Player Lookup</h2>
    <div class="search-row">
      <input id="lk-pid" type="number" placeholder="Low ID">
      <button class="btn btn-gray" onclick="doLookup()" style="margin-top:0">Search</button>
    </div>
    <div id="playerDetail"></div>
  </div>

  <!-- ── Players Table ── -->
  <div class="card full">
    <h2><span class="ico">👥</span> All Players <button class="btn btn-gray" onclick="loadPlayers()" style="margin-top:0;padding:6px 14px;font-size:.8rem">Refresh</button></h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Low ID</th><th>Name</th><th>Level</th><th>Trophies</th><th>Gems</th><th>Coins</th><th></th>
          </tr>
        </thead>
        <tbody id="players-tbody">
          <tr><td colspan="7" style="color:var(--muted);padding:20px">Loading…</td></tr>
        </tbody>
      </table>
    </div>
  </div>

</main>

<script>
const brawlerOptions = document.getElementById('t-brawler');

async function api(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  return r.json();
}

function showMsg(id, ok, text) {
  const el = document.getElementById(id);
  el.className = 'msg ' + (ok ? 'ok' : 'err');
  el.textContent = ok ? '✅ ' + text : '❌ ' + text;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 4000);
}

async function doGems() {
  const pid  = document.getElementById('g-pid').value;
  const amt  = parseInt(document.getElementById('g-amt').value);
  const mode = document.getElementById('g-mode').value;
  if (!pid) return showMsg('g-msg', false, 'Enter Player ID');
  const url = mode === 'set' ? '/admin/api/gems/set' : '/admin/api/gems';
  const r = await api(url, {player_id: pid, amount: amt});
  if (r.success) showMsg('g-msg', true, `Gems set to ${r.gems.toLocaleString()}`);
  else showMsg('g-msg', false, r.error);
  loadPlayers();
}

async function doTrophies() {
  const pid = document.getElementById('t-pid').value;
  const amt = parseInt(document.getElementById('t-amt').value);
  const brl = document.getElementById('t-brawler').value;
  if (!pid) return showMsg('t-msg', false, 'Enter Player ID');
  const r = await api('/admin/api/trophies', {player_id: pid, amount: amt, brawler_id: brl});
  if (r.success) showMsg('t-msg', true, `Total trophies: ${r.trophies.toLocaleString()}`);
  else showMsg('t-msg', false, r.error);
  loadPlayers();
}

async function doCoins() {
  const pid = document.getElementById('c-pid').value;
  const amt = parseInt(document.getElementById('c-amt').value);
  if (!pid) return showMsg('c-msg', false, 'Enter Player ID');
  const r = await api('/admin/api/coins', {player_id: pid, amount: amt});
  if (r.success) showMsg('c-msg', true, `Coins: ${r.coins.toLocaleString()}`);
  else showMsg('c-msg', false, r.error);
  loadPlayers();
}

async function doLookup() {
  const pid = document.getElementById('lk-pid').value;
  if (!pid) return;
  const r = await fetch('/admin/api/player/' + pid);
  const data = await r.json();
  const el = document.getElementById('playerDetail');
  if (data.error) {
    el.innerHTML = '<div class="msg err" style="display:block">❌ ' + data.error + '</div>';
  } else {
    el.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
  }
}

async function loadPlayers() {
  const r = await fetch('/admin/api/players');
  const players = await r.json();
  const tbody = document.getElementById('players-tbody');
  if (!players.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);padding:20px">No players yet</td></tr>';
    return;
  }
  tbody.innerHTML = players.map(p => `
    <tr>
      <td><span class="badge">${p.lowID}</span></td>
      <td><b>${escHtml(p.name)}</b></td>
      <td>${p.level}</td>
      <td><span class="badge badge-gold">🏆 ${p.trophies.toLocaleString()}</span></td>
      <td><span class="badge badge-green">💎 ${p.gems.toLocaleString()}</span></td>
      <td>🪙 ${p.coins.toLocaleString()}</td>
      <td>
        <button class="use-btn" onclick="fillPid(${p.lowID})">Use ID</button>
      </td>
    </tr>
  `).join('');
}

function fillPid(id) {
  ['g-pid','t-pid','c-pid','lk-pid'].forEach(k => document.getElementById(k).value = id);
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

loadPlayers();
</script>
</body>
</html>"""


@app.route('/admin')
@app.route('/admin/')
@require_auth
def admin_panel():
    brawler_opts = '\n'.join(
        f'<option value="{b["id"]}">{b["name"]}</option>'
        for b in BRAWLERS
    )
    html = ADMIN_HTML.replace('__BRAWLER_OPTIONS__', brawler_opts)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f'[Admin] Starting on port {port}')
    app.run(host='0.0.0.0', port=port, debug=False)
