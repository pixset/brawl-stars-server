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


class LoginFailedMessage(Writer):
    def __init__(self, client, player, errorInfo, fingerprint=None):
        super().__init__(client)
        self.id = 20103
        self.client = client
        self.player = player
        self.errorInfo = errorInfo
        self.fingerprint = fingerprint
        self.cndUrl = _get_cdn_url() if fingerprint is not None else None

    def encode(self):
        self.writeInt(self.errorInfo['ErrorID'])
        self.writeString(self.fingerprint)
        self.writeString()
        self.writeString(self.cndUrl)
        self.writeString()
        self.writeString(self.errorInfo['Message'])
        self.writeInt(0)
        self.writeBoolean(False)
        self.writeBytes(b'')
        self.writeInt(0)
        self.writeInt(0)
        self.writeInt(0)
        self.writeString()
        self.writeInt(0)
        self.writeByte(3)
        self.writeStringReference()
        self.writeVint(0)
        self.writeStringReference()
        self.writeBoolean(False)
