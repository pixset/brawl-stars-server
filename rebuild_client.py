"""
rebuild_client.py — пересборка клиента BSDS под адрес твоего сервера.

Меняет вшитый адрес сервера (libprojectbsds.config.so) в APK на нужный
IP:порт, выравнивает (zipalign) и переподписывает APK.

Использование:
    python rebuild_client.py <исходный.apk> <IP> <порт> [выход.apk]

Пример:
    python rebuild_client.py com_projectbsds_v40150-rev1.apk 66.33.22.224 42652

ВАЖНО: address должен быть числовым IP (1.2.3.4), а не доменом —
клиент резолвит его через inet_addr, домены не поддерживаются.
"""

import os
import re
import sys
import json
import shutil
import zipfile
import subprocess

_ROOT = os.path.dirname(os.path.abspath(__file__))

# ── пути к инструментам (Android SDK build-tools + JDK) ──────────────
LOCALAPPDATA = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
BUILD_TOOLS  = os.path.join(LOCALAPPDATA, 'Android', 'Sdk', 'build-tools', '36.1.0')
ZIPALIGN     = os.path.join(BUILD_TOOLS, 'zipalign.exe')
APKSIGNER    = os.path.join(BUILD_TOOLS, 'apksigner.bat')
KEYTOOL      = r'C:\Program Files\Java\jre1.8.0_491\bin\keytool.exe'

KEYSTORE = os.path.join(_ROOT, 'bsds.keystore')
KS_PASS  = 'bsds12345'
KS_ALIAS = 'bsds'

CONFIG_NAME = 'libprojectbsds.config.so'

IP_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')


def make_config(ip, port):
    return json.dumps({
        "interaction": {
            "type": "script",
            "path": "libmeow.js",
            "on_load": "reload",
            "parameters": {"address": ip, "port": int(port)}
        }
    }, indent=2).encode('utf-8')


def repack(src_apk, dst_apk, new_cfg):
    """Копируем все записи APK как есть, подменяя только config.so."""
    replaced = 0
    with zipfile.ZipFile(src_apk, 'r') as zin, \
         zipfile.ZipFile(dst_apk, 'w') as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith(CONFIG_NAME):
                data = new_cfg
                replaced += 1
                print(f'  подменён: {item.filename}')
            # сохраняем оригинальный метод сжатия записи
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zi.internal_attr = item.internal_attr
            zi.create_system = item.create_system
            zout.writestr(zi, data)
    return replaced


def ensure_keystore():
    if os.path.isfile(KEYSTORE):
        return
    print('[*] Создаю keystore для подписи...')
    subprocess.run([
        KEYTOOL, '-genkeypair', '-v',
        '-keystore', KEYSTORE,
        '-alias', KS_ALIAS,
        '-keyalg', 'RSA', '-keysize', '2048',
        '-validity', '10000',
        '-storepass', KS_PASS, '-keypass', KS_PASS,
        '-dname', 'CN=BSDS, OU=Dev, O=Pixset, L=NA, S=NA, C=NA',
    ], check=True)


def run(cmd):
    print('  $', ' '.join(os.path.basename(c) if os.path.sep in c else c for c in cmd))
    subprocess.run(cmd, check=True)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    src = sys.argv[1]
    ip = sys.argv[2]
    port = sys.argv[3]
    out = sys.argv[4] if len(sys.argv) > 4 else \
        os.path.splitext(src)[0] + f'_{ip.replace(".", "-")}_{port}.apk'

    if not IP_RE.match(ip):
        print(f'[!] "{ip}" не похож на IP. Нужен числовой адрес, не домен.')
        sys.exit(1)
    for tool in (ZIPALIGN, APKSIGNER, KEYTOOL):
        if not os.path.isfile(tool):
            print(f'[!] Не найден инструмент: {tool}')
            sys.exit(1)

    tmp_unsigned = out + '.unsigned'
    tmp_aligned  = out + '.aligned'

    print(f'[1/4] Подмена адреса -> {ip}:{port}')
    n = repack(src, tmp_unsigned, make_config(ip, port))
    if n == 0:
        print('[!] config.so не найден в APK — нечего менять.')
        sys.exit(1)

    print('[2/4] zipalign')
    if os.path.exists(tmp_aligned):
        os.remove(tmp_aligned)
    run([ZIPALIGN, '-f', '-p', '4', tmp_unsigned, tmp_aligned])

    print('[3/4] keystore')
    ensure_keystore()

    print('[4/4] подпись (apksigner)')
    run([APKSIGNER, 'sign',
         '--ks', KEYSTORE, '--ks-pass', f'pass:{KS_PASS}',
         '--ks-key-alias', KS_ALIAS, '--key-pass', f'pass:{KS_PASS}',
         '--out', out, tmp_aligned])
    run([APKSIGNER, 'verify', '--print-certs', out])

    for f in (tmp_unsigned, tmp_aligned, out + '.idsig'):
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass

    print('\n[OK] Готовый клиент:')
    print('   ', out)
    print(f'    Сервер: {ip}:{port}')


if __name__ == '__main__':
    main()
