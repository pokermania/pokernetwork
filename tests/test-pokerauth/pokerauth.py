class PokerAuth:
    def __init__(self, db, memcache, settings):
        self.gotcha = 1

def get_auth_instance(db, memcache, settings):
    return PokerAuth(db, memcache, settings)
