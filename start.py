"""
start.py — главная точка запуска BSDS
Запускает:
  • TCP game server  → порт 9339
  • HTTP CDN + admin → PORT env (default 8080)
"""

import os
import sys
import json
import shutil
import socket
import threading
import time
import traceback

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)

# ──────────────────────────────────────────────
#  Подготовка fingerprint в Update-папке
# ──────────────────────────────────────────────

def setup_fingerprint():
    lastver_path = os.path.join(_ROOT, 'ContentUpdater', 'lastversion.txt')
    if not os.path.isfile(lastver_path):
        print('[Setup] lastversion.txt not found — skipping fingerprint setup')
        return

    content = open(lastver_path, 'r').read().strip()
    parts = content.split('...')
    if len(parts) < 2:
        print('[Setup] lastversion.txt has unexpected format')
        return

    sha = parts[1]
    update_dir = os.path.join(_ROOT, 'ContentUpdater', 'Update', sha)
    fp_target  = os.path.join(update_dir, 'fingerprint.json')

    if os.path.isfile(fp_target):
        print(f'[Setup] fingerprint.json already in place for sha={sha}')
        return

    os.makedirs(update_dir, exist_ok=True)

    # Try to copy from Content/assets
    fp_source = os.path.join(_ROOT, 'ContentUpdater', 'Content', 'assets', 'fingerprint.json')
    if os.path.isfile(fp_source):
        # Load, inject sha field, save
        data = json.loads(open(fp_source, 'r').read())
        data['sha'] = sha
        with open(fp_target, 'w') as f:
            json.dump(data, f)
        print(f'[Setup] Created fingerprint.json for sha={sha}')
    else:
        # Create minimal fingerprint so server won't crash
        minimal = {'files': [], 'sha': sha, 'version': parts[0]}
        with open(fp_target, 'w') as f:
            json.dump(minimal, f)
        print(f'[Setup] Created minimal fingerprint.json for sha={sha}')


# ──────────────────────────────────────────────
#  TCP Game Server (порт 9339)
# ──────────────────────────────────────────────

def run_game_server():
    from Logic.Client.ClientsManager import ClientsManager
    from Logic.Client.PlayerManager import Players
    from Logic.Data.PacketsHandler import PacketsHandler
    from Messaging.Packets.Server.Home.LobbyInfoMessage import LobbyInfoMessage

    class ConnectionThread(threading.Thread):
        def __init__(self, client, address):
            super().__init__(daemon=True)
            self.address = address
            self.client  = client
            self.player  = Players()
            self.timeout = time.time()
            LobbyInfoMessageThread(self.client).start()

        def run(self):
            try:
                while True:
                    time.sleep(0.1)
                    PacketsHandler.ReadHeader(self)
                    if time.time() - self.timeout > 7:
                        print(f'[Game] Client {self.address[0]} timed out')
                        ClientsManager.RemoveSocket(self.player.LowID)
                        self.client.close()
                        return
            except (ConnectionError, OSError):
                print(f'[Game] Client {self.address[0]} disconnected')
                ClientsManager.RemoveSocket(self.player.LowID)
                self.client.close()
            except Exception:
                print(traceback.format_exc())

    class LobbyInfoMessageThread(threading.Thread):
        def __init__(self, client):
            super().__init__(daemon=True)
            self.client = client
            self.player = Players

        def run(self):
            timeout = time.time()
            try:
                while True:
                    time.sleep(0.1)
                    if time.time() >= timeout + 1:
                        LobbyInfoMessage(self.client, self.player).send(self.client)
                        timeout = time.time()
            except Exception:
                pass

    port = int(os.environ.get('GAME_PORT', 9339))
    srv  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(('0.0.0.0', port))
    except OSError as e:
        print(f'[Game] FATAL: не удалось занять порт {port}: {e}')
        print(f'[Game] Скорее всего PORT и GAME_PORT совпадают. '
              f'HTTP-порт (PORT) и игровой (GAME_PORT) должны быть РАЗНЫМИ.')
        return
    print(f'[Game] TCP server listening on port {port}')
    while True:
        srv.listen()
        client_sock, address = srv.accept()
        print(f'[Game] New connection: {address[0]}')
        ConnectionThread(client_sock, address).start()


# ──────────────────────────────────────────────
#  HTTP Admin + CDN (PORT env, default 8080)
# ──────────────────────────────────────────────

def run_admin_server():
    from admin_server import app
    port = int(os.environ.get('PORT', 8080))
    print(f'[Admin] HTTP server on port {port}')
    print(f'[Admin] Panel → http://0.0.0.0:{port}/admin')
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────

if __name__ == '__main__':
    print('=' * 55)
    print('  BSDS Private Server — Starting up')
    print('=' * 55)

    setup_fingerprint()

    # Проверка конфликта портов: HTTP (PORT) и игровой (GAME_PORT) обязаны различаться
    http_port = int(os.environ.get('PORT', 8080))
    game_port = int(os.environ.get('GAME_PORT', 9339))
    if http_port == game_port:
        print('=' * 55)
        print(f'  ВНИМАНИЕ: PORT и GAME_PORT оба = {http_port}!')
        print('  HTTP-сервер (CDN/админка) и игровой TCP-сервер не могут')
        print('  слушать один порт. Игра не запустится.')
        print(f'  Исправь в Railway: убери PORT=9339 (или поставь PORT=8080),')
        print(f'  оставь GAME_PORT=9339 и настрой на него TCP Proxy.')
        print('=' * 55)

    # Game server in background thread
    game_thread = threading.Thread(target=run_game_server, daemon=True, name='GameServer')
    game_thread.start()

    # Admin/CDN server — blocks main thread (Railway health checks need HTTP)
    run_admin_server()
