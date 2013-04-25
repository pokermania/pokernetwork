from pokerengine.pokercards import PokerCards
from pokerpackets.packets import *
from pokerpackets.networkpackets import *

def createCache():
    return {"board": PokerCards(), "pockets": {}}

def history2packets(history, game_id, previous_dealer, cache):
    packets = []
    errors = []
    for event in history:
        event_type = event[0]
        if event_type == "game":
            level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips = event[1:]  # @UnusedVariable
            if len(serial2chips) > 1:
                for (serial, chips) in serial2chips.iteritems():
                    if serial == 'values':
                        continue
                    packets.append(PacketPokerPlayerChips(
                        game_id = game_id,
                        serial = serial,
                        bet = 0,
                        money = chips
                    ))
            packets.append(PacketPokerInGame(
                game_id = game_id,
                players = player_list
            ))
            #
            # this may happen, for instance, if a turn is canceled
            if previous_dealer == dealer:
                previous_dealer = -1
            packets.append(PacketPokerDealer(
                game_id = game_id,
                dealer = dealer,
                previous_dealer = previous_dealer
            ))
            previous_dealer = dealer
            packets.append(PacketPokerStart(
                game_id = game_id,
                hand_serial = hand_serial,
                hands_count = hands_count,
                time = int(time),
                level = level
            ))

        elif event_type == "wait_for":
            serial, reason = event[1:]
            packets.append(PacketPokerWaitFor(
                game_id = game_id,
                serial = serial,
                reason = reason
            ))

        elif event_type == "player_list":
            player_list = event[1]
            packets.append(PacketPokerInGame(
                game_id = game_id,
                players = player_list
            ))

        elif event_type == "round":
            name, board, pockets = event[1:]
            packets.extend(cards2packets(game_id, board, pockets, cache))
            packets.append(PacketPokerState(
                game_id = game_id,
                string = name
            ))
            
        elif event_type == "bet_limits":
            min_bet, max_bet, step = event[1:]
            print min_bet, max_bet, step
            
        elif event_type == "position":
            position = event[1]
            serial = event[2] if event[2] is not None else 0
            packets.append(PacketPokerPosition(
                game_id = game_id,
                serial = serial,
                position = position
            ))

        elif event_type == "showdown":
            board, pockets = event[1:]
            packets.extend(cards2packets(game_id, board, pockets, cache))

        elif event_type == "blind_request":
            serial, amount, dead, state = event[1:]
            packets.append(PacketPokerBlindRequest(
                game_id = game_id,
                serial = serial,
                amount = amount,
                dead = dead,
                state = state
            ))

        elif event_type == "wait_blind":
            pass

        elif event_type == "blind":
            serial, amount, dead = event[1:]
            packets.append(PacketPokerBlind(
                game_id = game_id,
                serial = serial,
                amount = amount,
                dead = dead
            ))

        elif event_type == "ante_request":
            serial, amount = event[1:]
            packets.append(PacketPokerAnteRequest(
                game_id = game_id,
                serial = serial,
                amount = amount
            ))

        elif event_type == "ante":
            serial, amount = event[1:]
            packets.append(PacketPokerAnte(
                game_id = game_id,
                serial = serial,
                amount = amount
            ))

        elif event_type == "all-in":
            pass

        elif event_type == "call":
            serial, amount = event[1:]
            packets.append(PacketPokerCall(
                game_id = game_id,
                serial = serial
            ))

        elif event_type == "check":
            serial = event[1]
            packets.append(PacketPokerCheck(
                game_id = game_id,
                serial = serial
            ))

        elif event_type == "fold":
            serial = event[1]
            packets.append(PacketPokerFold(
                game_id = game_id,
                serial = serial
            ))

        elif event_type == "raise":
            serial, amount = event[1:]
            packets.append(PacketPokerRaise(
                game_id = game_id,
                serial = serial,
                amount = amount
            ))

        elif event_type == "canceled":
            serial, amount = event[1:]
            packets.append(PacketPokerCanceled(
                game_id = game_id,
                serial = serial,
                amount = amount
            ))

        elif event_type == "muck":
            muckable_serials = event[1]
            packets.append(PacketPokerMuckRequest(
                game_id = game_id,
                muckable_serials = muckable_serials
            ))

        elif event_type == "rake":
            amount = event[1]
            packets.append(PacketPokerRake(
                game_id = game_id,
                value = amount
            ))

        elif event_type == "end":
            winners = event[1]
            showdown_stack = event[2]
            packets.append(PacketPokerState(
                game_id = game_id,
                string = "end"
            ))
            packets.append(PacketPokerWin(
                game_id = game_id,
                serials = winners
            ))
            if len(showdown_stack) == 0:
                showdown_stack = [{}]
            for serial, chips in showdown_stack[0].get("serial2money",{}).iteritems():
                packets.append(PacketPokerPlayerChips(
                    game_id = game_id,
                    serial = serial,
                    bet = 0,
                    money = chips
                ))

        elif event_type == "sitOut":
            serial = event[1]
            packets.append(PacketPokerSitOut(
                game_id = game_id,
                serial = serial
            ))

        elif event_type == "sit":
            pass

        elif event_type == "rebuy":
            serial, amount = event[1:]
            packets.append(PacketPokerRebuy(
                game_id = game_id,
                serial = serial,
                amount = amount
            ))

        elif event_type == "leave":
            quitters = event[1]
            for (serial, seat) in quitters:
                packets.append(PacketPokerPlayerLeave(
                    game_id = game_id,
                    serial = serial,
                    seat = seat
                ))

        elif event_type == "finish":
            pass
        
        else:
            errors.append("history2packets: unknown history type %s " % event_type)
    return (packets, previous_dealer, errors)


def cards2packets(game_id, board, pockets, cache):
    packets = []
    #
    # If no pockets or board specified (different from empty pockets),
    # ignore and keep the cached values
    if board != None:
        if board != cache["board"]:
            packets.append(PacketPokerBoardCards(
                game_id = game_id,
                cards = board.tolist(False)
            ))
            cache["board"] = board.copy()

    if pockets != None:
        #
        # send new pockets or pockets that changed
        for (serial, pocket) in pockets.iteritems():
            if serial not in cache["pockets"] or cache["pockets"][serial] != pocket:
                packets.append(PacketPokerPlayerCards(
                    game_id = game_id,
                    serial = serial,
                    cards = pocket.toRawList()
                ))
                cache["pockets"][serial] = pocket.copy()
    return packets

def private2public(packet, serial):
    #
    # cards private to each player are shown only to the player
    if packet.type == PACKET_POKER_PLAYER_CARDS and packet.serial != serial:
        return PacketPokerPlayerCards(
            game_id = packet.game_id,
            serial = packet.serial,
            cards = PokerCards(packet.cards).tolist(False)
        )
    else:
        return packet

