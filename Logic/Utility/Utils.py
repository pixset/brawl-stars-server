import json
import time
import random
import os

# Project root — works regardless of CWD
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Utils:
    def getTime():
        return time.strftime("%H:%M:%S")

    def getRandomID():
        id = []
        id.append(int(''.join([str(random.randint(0, 9)) for _ in range(2)])))
        id.append(int(''.join([str(random.randint(0, 9)) for _ in range(8)])))
        return id

    def isPromoting(currentRole, newRole):
        if newRole == 2:
            return True
        elif newRole == 4:
            if currentRole == 2:
                return False
            else:
                return True
        elif newRole == 3:
            if currentRole == 4:
                return False
            else:
                return True
        elif newRole == 1:
            return False

    def getContentUpdaterInfo():
        path = os.path.join(_BASE, 'ContentUpdater', 'lastversion.txt')
        return open(path, 'r').read().split('...')

    def getFingerprintData(resourceSha):
        path = os.path.join(_BASE, 'ContentUpdater', 'Update', resourceSha, 'fingerprint.json')
        return json.dumps(json.loads(open(path, 'r').read()))
