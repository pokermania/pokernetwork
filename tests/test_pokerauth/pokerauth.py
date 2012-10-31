class PokerAuth:
    def __init__(self, db, memcache, settings):
        self.gotcha = True

def get_auth_instance(db, memcache, settings):
    return PokerAuth(db, memcache, settings)
