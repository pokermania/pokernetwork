
from nose.twistedtools import reactor, deferred

import sys as _sys
from time import time
import os.path as _path
import pokernetwork.pokerservice as _service
import pokernetwork.pokernetworkconfig as _config
import reflogging as _reflogging
import reflogging.handlers as _handlers
import pokerpackets.networkpackets as _networkpackets
from contextlib import closing

from pokerengine.pokertournament import TOURNAMENT_STATE_CANCELED


_reflogging.root_logger.set_level(10)
_reflogging.root_logger.add_handler(_handlers.StreamHandler(_sys.stdout))

class MockProtocol():

    def __init__(self, id):
        self.id = id

    def sendPacket(self, packet):
        pass # print 'sendPacket to %d: %s' % (self.id, packet)

def join_avatar(service, table, user_id, user_name, user_password):
    a = service.createAvatar()
    a.setProtocol(MockProtocol(user_id))
    a.login((user_id, user_name, user_password))
    table.joinPlayer(a)
    return a

def get_player(table, user_id):
    return table.game.serial2player[user_id]

def play(table, rounds=None):
    game = table.game
    for i in range(rounds):
        user_id = game.getSerialInPosition()
        if user_id == 0:
            table.beginTurn()
        else:
            game.fold(user_id)
        table.update()

def test_cancel():
    def test(play1, update_money, play2, cancel):
        settings = _config.Config([_path.join(_path.dirname(__file__), '.')])
        settings.load('poker.server.additions.xml')
        service = _service.PokerService(settings)
        service.startService()

        tourney_id = service.tourneySelect('Strippoker_175_0')[0]['serial']
        assert service.tourneyRegister(_networkpackets.PacketPokerTourneyRegister(serial=2,
            tourney_serial=tourney_id)) is True, 'registration of admin failed'
        assert service.tourneyRegister(_networkpackets.PacketPokerTourneyRegister(serial=174,
            tourney_serial=tourney_id)) is True, 'registration of bot failed'

        # right amount of tables spawned?
        assert len(service.tables) == 1, 'there should be one spawned table'
        
        # right amount of tables returned?
        table_dicts = service.listTables('mytourneys', 2)
        assert len(table_dicts) == 1, 'listTables should reutrn one table dict'

        # get table
        table_id = table_dicts[0]['serial']
        table = service.tables[table_id]
        table.beginTurn()
        table.update()

        # get tourney
        tourney = service.tourneys[tourney_id]

        # create/join players
        admin = join_avatar(service, table, 2, 'admin', 'holahola')
        bot = join_avatar(service, table, 174, 'BOT174', '1504')

        # check if avatar has table in .tables
        assert [table_id] == admin.tables.keys(), 'there should be table %d in admin.tables: %s' % (table_id, admin.tables)
        assert [table_id] == bot.tables.keys(), 'there should be table %d in bot.tables: %s' % (table_id, bot.tables)

        # play 2 round
        if play1:
            play(table, 2)

        # test updatePlayersMoney
        if update_money:
            assert table.updatePlayersMoney([
                (2, 1500),
                (174, 200)
            ]) is True, 'updatePlayersMoney should return True'
            table.update()

            # check .money
            assert get_player(table, 2).money == 1500, 'player money should be 1500'
            assert get_player(table, 174).money == 200, 'player money should be 200'

            # check database money
            with closing(service.db.cursor()) as c:
                assert 2 == c.execute("SELECT money FROM user2table WHERE table_serial = %s ORDER BY user_serial", (table_id,)), \
                    'there should be 2 rows, not %d in %s' % (c.rowcount, c._executed)
                money = c.fetchone()[0] ; assert money == 1500, 'admin money should be 1500 in db, but is %d' % (money,)
                money = c.fetchone()[0] ; assert money == 200, 'bot money should be 200 in db, but is %d' % (money,)

            # deal next round
            table.beginTurn()
            table.update()
       
        if play2:
            play(table, 2)

        if cancel:
            tourney._kickme_after = time() - 1 # give cancelInactiveTourneys a little hint :)
            service.cancelInactiveTourneys()   # and run it without poll

            # check table destroy
            assert not hasattr(table, 'factory'), 'there should be no factory after destroy'

            # check tourney is canceled and avatars have no tables anymore
            assert tourney.state == 'canceled', 'tourney state should not be %s' % (tourney.state,)
            assert len(admin.tables) == 0, 'admin.tables should be empty'
            assert len(bot.tables) == 0, 'bot.tables should be empty'

            # check db
            with closing(service.db.cursor()) as c:
                # check user2table
                assert 0 == c.execute("SELECT * FROM user2table WHERE user_serial IN (2, 174) AND table_serial = %s", (table_id,)), \
                    'there should be no user2table entries %s' % (c.fetchall(),)

                # check user2tourney
                assert 0 == c.execute("SELECT * FROM user2tourney WHERE user_serial IN (2, 174) AND tourney_serial = %s", (tourney_id,)), \
                    'there should be no user2tourney entries %s' % (c.fetchall(),)

                # check tables
                assert 0 == c.execute("SELECT * FROM tables WHERE serial = %s", (table_id,)), 'there should be no table %s' % (c.fetchone(),)

        # play it out
        # else:
        #     play(table)

        service.stopService()


    # test permutations of play, cancel, play, update_money
    bits = 4
    for i in range(2**bits):
        yield tuple([test]+[bool(2**e & i) for e in range(bits)])

