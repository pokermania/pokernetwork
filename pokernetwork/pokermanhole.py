# -*- coding: utf-8 *-*

from twisted.conch.manhole import ColoredManhole
from twisted.conch.insults import insults
from twisted.conch.manhole_ssh import ConchFactory, TerminalRealm
from twisted.application import internet
from twisted.cred import checkers, portal
from zope.interface import implements
from twisted.cred import credentials
from twisted.internet import defer
from pprint import pprint as pp

def unblock_table(service, serial, destroy=False):
    """Kick everyone from the table, refund money+bet, cleanup sql, set game to end state and if destory=True destory the table"""
    cursor = service.db.cursor()
    try:
        blocking_table = service.tables[serial]
        # kick everyone
        for serial in blocking_table.avatar_collection.serial2avatars.keys():
            service.leavePlayer(serial, blocking_table.game.id, 1)
        # refund players remaining in sql
        cursor.execute("update user2table as u2t join pokertables as t on t.serial = u2t.table_serial join user2money as u2m on u2m.user_serial = u2t.user_serial set u2m.amount = u2m.amount + u2t.money + u2t.bet, u2t.money = 0, u2t.bet = 0 where u2t.table_serial = %s and t.currency_serial = 1;", (serial))
        # cleanup sql
        cursor.execute("delete from user2table where table_serial = %s;""", (serial))
        # game state muck -> end
        blocking_table.game.endState()
        # beat it to death for failing
        if destroy:
            blocking_table.destroy()
    finally:
        cursor.close()

def find_muck_games(service):
    """Find games in muck state and print them"""
    for table in service.tables.itervalues():
        if table.game.state == 'muck':
            yield table.game.id

class AllowAnyAccess():
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (
        credentials.IUsernamePassword,
        credentials.IUsernameHashedPassword
    )

    def requestAvatarId(self, credentials):
        return defer.succeed(credentials.username)

def makeService(port, namespace):
    namespace.update({
        'unblock_tables': unblock_table,
        'find_muck_games': find_muck_games,
        'pp': pp
    })

    def chainProtocolFactory():
        return insults.ServerProtocol(
            ColoredManhole,
            namespace
        )

    realm = TerminalRealm()
    realm.chainedProtocolFactory = chainProtocolFactory
    manhole_portal = portal.Portal(realm, [AllowAnyAccess()])
    factory = ConchFactory(manhole_portal)
    return internet.TCPServer(port, factory, interface="127.0.0.1")
