# -*- coding: utf-8 *-*

from twisted.conch.manhole import ColoredManhole
from twisted.conch.insults import insults
from twisted.conch.manhole_ssh import ConchFactory, TerminalRealm
from twisted.application import internet
from twisted.cred import checkers, portal
from pprint import pprint as pp
import gc, types
import pokernetwork


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
            print table.game.id

def ureload(module, updatables=None):
    """
    Reload module and update its contents. Returns new module or None if there are no updatables

    if updatables is None the function will search for a _update or _dont_update list
    in the module. _dont_update is subtracted from the module.__dict__.

    the new updatable list is stored in the new module in an _update attribute.
    _dont_update gets deleted

    If a class is in updatables it's instances __class__ attributes are set to
    the same class in the new module. Other objects are just copied to the new module

    >>> ureload(pokernetwork.pokertable)
    <module 'pokernetwork.pokertable' from '../pokernetwork/pokertable.py'>

    >>> ureload(pokernetwork.pokertable, ['PokerTable'])
    <module 'pokernetwork.pokertable' from '../pokernetwork/pokertable.py'>
    """

    # calc list of items to update
    if not updatables:
        updatables = module.__dict__.get('_update', None)
    if not updatables and module.__dict__.get('_dont_update'):
        updatables = [name for name in module.__dict__.keys() if name not in module._dont_update]
    if not updatables:
        print "no updatable items found"
        return

    print "updating:\n  ", "\n   ".join(updatables)

    # get list of class instances to update
    _updates_instances = []

    # get list of globals to copy to new module
    _updates_globals = []

    for name, obj in [(name, module.__dict__[name],) for name in updatables]:
        if isinstance(obj, (type, types.ClassType)):
            _updates_instances.extend([
                (name, ref,) for ref in gc.get_referrers(obj)
                if ref.__class__ is obj
            ])
        else:
            _updates_globals.append((name, obj,))

    # reload module, garbage collector will behave different after this,
    # so we had to get lists of object before.
    module = reload(module)

    # update class instances
    for cls_name, ref in _updates_instances:
        ref.__class__ = module.__dict__[cls_name]

    # update globals
    for gl_name, gl_obj in _updates_globals:
        module.__dict__[gl_name] = gl_obj

    # set _update
    module._update = updatables

    # end
    return module

def makeService(port, namespace):
    checker = checkers.InMemoryUsernamePasswordDatabaseDontUse(root="")
    namespace.update({
        'unblock_tables': unblock_table,
        'find_muck_games': find_muck_games,
        'pokernetwork': pokernetwork,
        'ureload': ureload,
        'pp': pp
    })

    def chainProtocolFactory():
        return insults.ServerProtocol(
            ColoredManhole,
            namespace
        )

    realm = TerminalRealm()
    realm.chainedProtocolFactory = chainProtocolFactory
    manhole_portal = portal.Portal(realm, [checker])
    factory = ConchFactory(manhole_portal)
    return internet.TCPServer(port, factory, interface="127.0.0.1")
