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

poker_service = None

def refund_kick(serial, service=None):
    """
    Refunds money+bet and then kicks each player.
    
    serial: the serial of the table to refund and kick
    service: the service to use (default: poker_service)
    """
    if service is None:
        service = poker_service
    cursor = service.db.cursor()
    try:
        blocking_table = service.tables[serial]
        # kick everyone
        for serial in blocking_table.avatar_collection.serial2avatars.keys():
            service.leavePlayer(serial, blocking_table.game.id, 1)
        # refund players remaining in sql
        cursor.execute(
            """ UPDATE user2money AS u2m
                LEFT JOIN user2table AS u2t
                    ON u2t.user_serial = u2m.user_serial
                LEFT JOIN tables AS t
                    ON t.serial = u2t.table_serial
                LEFT JOIN tableconfigs AS c
                    ON c.serial = t.tableconfig_serial
                SET
                    u2m.amount = u2m.amount + COALESCE(u2t.money, 0) + COALESCE(u2t.bet, 0),
                    u2t.money = 0,
                    u2t.bet = 0
                WHERE t.serial = %s AND u2m.currency_serial = 1 AND c.currency_serial = 1
            """,
            serial
        )
        # cleanup sql
        cursor.execute("DELETE FROM user2table WHERE table_serial = %s", (serial,))
    finally:
        cursor.close()

def filter_tables(function, service=None):
    """
    filter_tables(lambda t: t.listPlayers() != []) -> list of tables matching function
    
    function: the filter to apply on all tables
    service: the service to look in (default: poker_service)
    """
    if service is None:
        service = poker_service
    return [t for t in service.tables.itervalues() if function(t)]

def filter_games(function, service=None):
    """
    filter_tables(lambda t: t.listPlayers() != []) -> list of games matching function
    
    function: the filter to apply on all games
    service: the service to look in (default: poker_service)
    """
    if service is None:
        service = poker_service
    return [t.game for t in service.tables.itervalues() if function(t.game)]

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
        'refund_kick': refund_kick,
        'filter_tables': filter_tables,
        'filter_games': filter_games,
        'pp': pp,
        'namespace': namespace
    })
    global poker_service
    poker_service = namespace['poker_service']

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
