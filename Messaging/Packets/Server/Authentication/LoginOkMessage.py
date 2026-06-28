import os
import socket

from Logic.Data.DataManager import Writer


def _get_cdn_url():
    # 1) Явно заданный CDN (например свой домен)
    cdn = os.environ.get('CDN_HOST', '').strip()
    if cdn:
        return cdn
    # 2) Публичный домен, который Railway выставляет автоматически
    dom = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '').strip()
    if dom:
        return f'https://{dom}'
    # 3) Локальный фолбэк (только для запуска на своей машине)
    port = os.environ.get('PORT', '8080')
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = '127.0.0.1'
    return f'http://{ip}:{port}'


class LoginOkMessage(Writer):
    def __init__(self, client, player):
        super().__init__(client)
        self.id = 20104
        self.client = client
        self.player = player
        self.version = 1

    def encode(self):
        cdn = _get_cdn_url()

        self.writeLong(self.player.HighID, self.player.LowID)
        self.writeLong(self.player.HighID, self.player.LowID)
        self.writeString(self.player.Token)
        self.writeString()
        self.writeString()
        self.writeInt(40)
        self.writeInt(150)
        self.writeInt(1)
        self.writeString('prod')
        self.writeInt(0)
        self.writeInt(0)
        self.writeInt(0)
        self.writeString()
        self.writeString()
        self.writeString()
        self.writeInt(0)
        self.writeString()
        self.writeString('CA')
        self.writeString()
        self.writeInt(2)
        self.writeString()

        self.writeInt(1)
        self.writeString(cdn)

        self.writeInt(2)
        self.writeString('https://event-assets.brawlstars.com')
        self.writeString('https://24b999e6da07674e22b0-8209975788a0f2469e68e84405ae4fcf.ssl.cf2.rackcdn.com/event-assets')

        self.writeVint(0)
        self.writeCompressedString(b'')
        self.writeBoolean(True)
        self.writeString()
        self.writeString()
        self.writeString()
        self.writeString('https://play.google.com/store/apps/details?id=com.supercell.brawlstars')
        self.writeString()
        self.writeBoolean(False)
