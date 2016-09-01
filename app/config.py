class GandalfConfiguration:
    def __init__(self, proxy_host, db_adapter, allowed_hosts, signing_secret=''):
        self.proxy_host = proxy_host
        self.db_adapter = db_adapter
        self.allowed_hosts = allowed_hosts
        self.signing_secret = signing_secret
