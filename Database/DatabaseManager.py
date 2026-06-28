import json
import sqlite3
import traceback
import os

# Путь к базе. На Railway укажи DB_PATH на смонтированный Volume,
# например /data/player.sqlite — иначе база стирается при каждом редеплое.
_LOCAL_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'player.sqlite')


def _resolve_db_path():
    """Выбираем рабочий путь к базе. Если заданный DB_PATH недоступен для
    записи (например Volume не примонтирован) — откатываемся на локальный
    файл, чтобы сервер не падал в 500, и громко сообщаем об этом."""
    wanted = os.environ.get('DB_PATH', '').strip()
    if not wanted:
        return _LOCAL_DB

    db_dir = os.path.dirname(wanted) or '.'
    try:
        os.makedirs(db_dir, exist_ok=True)
        # Проверяем, что директория реально доступна для записи
        probe = os.path.join(db_dir, '.write_test')
        with open(probe, 'w') as f:
            f.write('ok')
        os.remove(probe)
        print(f'[DB] Используется база: {wanted}')
        return wanted
    except Exception as e:
        print(f'[DB] WARNING: путь {wanted} недоступен для записи ({e}).')
        print(f'[DB] Откат на локальную базу {_LOCAL_DB} — данные НЕ переживут редеплой!')
        print(f'[DB] Проверь, что в Railway создан Volume с Mount path = {db_dir}')
        return _LOCAL_DB


DB_PATH = _resolve_db_path()


class DatabaseManager():
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        try:
            self.cursor.execute("""CREATE TABLE main (LowID integer, Token text, Data json)""")
            self.conn.commit()
        except:
            pass

    def createAccount(self, lowID, token, data):
        try:
            self.cursor.execute("INSERT INTO main (LowID, Token, Data) VALUES (?, ?, ?)",
                                (lowID, token, json.dumps(data, ensure_ascii=0)))
            self.conn.commit()
        except Exception:
            print(traceback.format_exc())

    def GetAllDb(self):
        self.playersId = []
        try:
            self.cursor.execute("SELECT * from main")
            self.db = self.cursor.fetchall()
            for i in range(len(self.db)):
                self.playersId.append(self.db[i][0])
            return self.playersId
        except Exception:
            print(traceback.format_exc())

    def getPlayerWithLowID(self, low):
        try:
            self.cursor.execute("SELECT * from main where LowID=?", (low,))
            return self.cursor.fetchall()
        except Exception:
            print(traceback.format_exc())

    def LoadAccount(self, low, player):
        try:
            self.player = player
            self.cursor.execute("SELECT * from main where LowID=?", (low,))
            playersdata = self.cursor.fetchall()
            self.players = json.loads(playersdata[0][2])
            self.player.Name = self.players['name']
            self.player.Token = playersdata[0][1]
            self.player.isRegistred = self.players['IsRegistred']
            self.player.level = self.players['level']
            self.player.doNotDisturb = self.players['DoNotDisturb']
            self.player.friends = self.players['friend']
            self.player.highestTrophies = self.players['highestTrophies']
            self.player.brawlerID = self.players['brawlerID']
            self.player.skinID = self.players['skinID']
            self.player.selectedSkin = self.players['selectedSkin']
            self.player.brawlerState = self.players['brawlerState']
            self.player.brawlersTrophies = self.players['brawlersTrophies']
            self.player.selectedRandomSkin = self.players['selectedRandomSkin']
            self.player.starpowerID = self.players['starpowerID']
            self.player.thumbnail = self.players['playericon']
            self.player.nameColor = self.players['namecolor']
            self.player.region = self.players['region']
            self.player.trophies = self.players['trophies']
            self.player.experience = self.players['experience']
            self.player.room_id = self.players['gameroomID']
            self.player.roomInfo = self.players['roomInfo']
            self.player.allianceID = self.players['allianceID']
            self.player.isBanned = self.players['isBanned']
            self.player.gems = self.players['gems']
            self.player.coins = self.players['coins']
            self.player.clubMailInbox = self.players['clubMailInbox']
        except Exception:
            print(traceback.format_exc())

    def updatePlayerData(self, data, lowID):
        try:
            self.cursor.execute("UPDATE main SET Data=? WHERE LowID=?",
                                (json.dumps(data, ensure_ascii=0), lowID))
            self.conn.commit()
        except Exception:
            print(traceback.format_exc())

    # ──────────────────────────── ADMIN METHODS ────────────────────────────

    def getAllPlayersData(self):
        """Return summary list of all players for admin panel."""
        try:
            self.cursor.execute("SELECT LowID, Data FROM main")
            rows = self.cursor.fetchall()
            players = []
            for row in rows:
                try:
                    d = json.loads(row[1])
                    players.append({
                        'lowID':    row[0],
                        'name':     d.get('name', 'Unknown'),
                        'trophies': d.get('trophies', 0),
                        'gems':     d.get('gems', 0),
                        'coins':    d.get('coins', 0),
                        'level':    d.get('level', 1),
                    })
                except Exception:
                    pass
            return players
        except Exception:
            print(traceback.format_exc())
            return []

    def getPlayerData(self, lowID):
        """Return full player data dict or None."""
        try:
            self.cursor.execute("SELECT Data FROM main WHERE LowID=?", (lowID,))
            row = self.cursor.fetchone()
            if not row:
                return None
            return json.loads(row[0])
        except Exception:
            print(traceback.format_exc())
            return None

    def adminSetField(self, lowID, field, value):
        """Set a top-level field in player JSON. Returns (ok, message)."""
        try:
            data = self.getPlayerData(lowID)
            if data is None:
                return False, f"Player {lowID} not found"
            data[field] = value
            self.cursor.execute("UPDATE main SET Data=? WHERE LowID=?",
                                (json.dumps(data, ensure_ascii=0), lowID))
            self.conn.commit()
            return True, data
        except Exception as e:
            print(traceback.format_exc())
            return False, str(e)

    def adminSetBrawlerTrophies(self, lowID, brawler_id, amount):
        """Set trophies for a specific brawler and recalculate total."""
        try:
            data = self.getPlayerData(lowID)
            if data is None:
                return False, f"Player {lowID} not found"

            trophies = data.get('brawlersTrophies', {})

            # keys may be int or str depending on how they were stored
            int_key  = int(brawler_id)
            str_key  = str(brawler_id)

            if int_key in trophies:
                trophies[int_key] = int(amount)
            elif str_key in trophies:
                trophies[str_key] = int(amount)
            else:
                return False, f"Brawler {brawler_id} not found in player data"

            data['brawlersTrophies'] = trophies
            data['trophies'] = sum(int(v) for v in trophies.values())
            if data['trophies'] > data.get('highestTrophies', 0):
                data['highestTrophies'] = data['trophies']

            self.cursor.execute("UPDATE main SET Data=? WHERE LowID=?",
                                (json.dumps(data, ensure_ascii=0), lowID))
            self.conn.commit()
            return True, data
        except Exception as e:
            print(traceback.format_exc())
            return False, str(e)

    def adminSetAllBrawlerTrophies(self, lowID, amount):
        """Set trophies for every brawler and recalculate total."""
        try:
            data = self.getPlayerData(lowID)
            if data is None:
                return False, f"Player {lowID} not found"

            trophies = data.get('brawlersTrophies', {})
            trophies = {k: int(amount) for k in trophies}
            data['brawlersTrophies'] = trophies
            data['trophies'] = sum(trophies.values())
            if data['trophies'] > data.get('highestTrophies', 0):
                data['highestTrophies'] = data['trophies']

            self.cursor.execute("UPDATE main SET Data=? WHERE LowID=?",
                                (json.dumps(data, ensure_ascii=0), lowID))
            self.conn.commit()
            return True, data
        except Exception as e:
            print(traceback.format_exc())
            return False, str(e)
