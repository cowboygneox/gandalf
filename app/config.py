HTTP = 1
WEBSOCKET = 2

class GandalfConfiguration:
    def __init__(self, proxy_host, db_adapter, allowed_hosts, signing_secret='', mode=HTTP):
        self.proxy_host = proxy_host
        self.db_adapter = db_adapter
        self.allowed_hosts = allowed_hosts
        self.signing_secret = signing_secret
        self.mode = mode
