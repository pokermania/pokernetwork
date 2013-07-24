******************
   First Steps
******************

Connect to the Pokerserver
==========================

Typical Start
~~~~~~~~~~~~~

1. handshake
2. authenticate
3. get tables
4. user actions

Handshake
~~~~~~~~~

Open a TCP connection to the poker service. You will receive a line like `CGI 002.200\\n`. You have to respond with your protocol version number with the same format `CGI <major>.<minor>\\n`. If the versions differ the connection is closed immediately. After the connection is opend you must not use any delimiter for the packets.

It is a standard TCP connection.

The Packets that will be sent are C-Structs. For information about the packet byte order or size you should take a look at **Packet.format_info** from `packets.py <https://github.com/pokermania/poker-network/blob/master/poker-packets/pokerpackets/packets.py#L412>`_. Here you will get the information how the **Packet.info** tuple transformed to the standard C-Struct representation (see `python docu <http://docs.python.org/2/library/struct.html#byte-order-size-and-alignment>` for more information)

For example: ``('game_id', 0, 'I'),`` means *game_id* is an Integer. Given the Packet.format_info from the packets.py:
::

    'I': {'pack': lambda data: pack('!I', data),
          'unpack': lambda block: ( block[4:], int(unpack('!I', block[:4])[0]) ),
          'calcsize': lambda data: 4,
          },

You can see it is packed as an unsigned integer in network (big-endian) byte order with a size of 4 byte.

Authenticate
~~~~~~~~~~~~

The Login must be done with the `Social-API`. There you will get the auth token. 
Then you need to send a :class:`PACKET_POKER_AUTH <pokerpackets.packets.PacketAuth>`.

Get tables
~~~~~~~~~~

This list will include all basic information about the tables (including names, free seats, ...)

Send a :class:`PACKET_POKER_TABLE_SELECT <pokerpackets.clientpackets.PacketPokerTableSelect>` to get :class:`PACKET_POKER_TABLE_LIST <pokerpackets.clientpackets.PacketPokerTableList>` which contains a list of  :class:`PACKET_POKER_TABLE <pokerpackets.clientpackets.PacketPokerTable>`.

You can get the buy in for the table from the betting structure.


User Actions
~~~~~~~~~~~~

Set your ``roles`` to ``PLAY`` with a :class:`PacketPokerSetRole <pokerpackets.networkpackets.PacketPokerSetRole>`.

After you chose a table and want to sit down, check the FAQ section :ref:`How to sit at a cash game table ? <sit>`.

During a hand are :ref:`this packets <hand>` possible.

Explain or no explain
~~~~~~~~~~~~~~~~~~~~~

Theoretically it is possible to ask the pokerserver for more packages. Therfore you could send an :class:`PACKET_POKER_EXPLAIN <pokerpackets.networkpackets.PacketPokerExplain>`. 

It would be much better if the client could work without explains since it reduces the performance impact to the server.

Look at the `implementation <https://github.com/pokermania/poker-network/blob/master/poker-network/pokernetwork/pokerexplain.py#L270>`_ on github for an idea how it could be done.

FAQ.
====

When the client send packets, the reply packets sent by the
server are listed in the packet documentation.

Cash Games
~~~~~~~~~~

How to tell the server that the client is alive every 10 seconds ?
------------------------------------------------------------------

|   If and only if the client does not send any packet during
   more than 10 sec, you must send a :class:`PACKET_PING <pokerpackets.packets.PacketPing>`
|
| :class:`PACKET_PING <pokerpackets.packets.PacketPing>`

How to cash in ?
----------------

:class:`POKER_CASH_IN <pokerpackets.networkpackets.PacketPokerCashIn>`


.. _sit:

How to sit at a cash game table ?
---------------------------------
Send:

| :class:`PACKET_POKER_TABLE_JOIN <pokerpackets.networkpackets.PacketPokerTableJoin>`


if it was successfull you will get:

| :class:`POKER_TABLE <pokerpackets.networkpackets.PacketPokerTable>`
| :class:`POKER_BUY_IN_LIMITS <pokerpackets.networkpackets.PacketPokerBuyInLimits>`
| :class:`POKER_BATCH_MODE <pokerpackets.networkpackets.PacketPokerBatchMode>`
| :class:`POKER_SEATS <pokerpackets.networkpackets.PacketPokerSeats>`
| ... and anything that happend during this hand allready
| :class:`POKER_STREAM_MODE <pokerpackets.networkpackets.PacketPokerStreamMode>`

After that you need to choose a seat, pay your buy in. It is recommended that you activate auto blind ante, since the player has to pay them. If you want to manage the blind by yourself you need to watch for PACKET_POKER_BUY_IN_REQUEST packets. And last but not least you have to sit to indicate that you are ready to play.

| :class:`PACKET_POKER_SEAT <pokerpackets.networkpackets.PacketPokerSeat>`
| :class:`PACKET_POKER_BUY_IN <pokerpackets.networkpackets.PacketPokerBuyIn>`
| :class:`PACKET_POKER_AUTO_BLIND_ANTE <pokerpackets.networkpackets.PacketPokerAutoBlindAnte>` (optional)
| :class:`PACKET_POKER_SIT <pokerpackets.networkpackets.PacketPokerSit>`

How to quickly get to a cash game table that fits certain criteria?
-------------------------------------------------------------------

| :class:`PACKET_POKER_TABLE_PICKER <pokerpackets.networkpackets.PacketPokerTablePicker>`

How to leave a cash game table ?
--------------------------------

| :class:`PACKET_POKER_TABLE_QUIT <pokerpackets.networkpackets.PacketPokerTableQuit>`

What to expect when watching a table ? 
--------------------------------------

| :class:`PACKET_POKER_PLAYER_ARRIVE <pokerpackets.networkpackets.PacketPokerPlayerArrive>`
| :class:`PACKET_POKER_PLAYER_STATS <pokerpackets.networkpackets.PacketPokerPlayerStats>`
| :class:`PACKET_POKER_PLAYER_CHIPS <pokerpackets.networkpackets.PacketPokerPlayerChips>`
| :class:`PACKET_POKER_SIT <pokerpackets.networkpackets.PacketPokerSit>`
| :class:`PACKET_POKER_SIT_OUT <pokerpackets.networkpackets.PacketPokerSitOut>`
| :class:`PACKET_POKER_CHAT <pokerpackets.networkpackets.PacketPokerChat>`
| :class:`PACKET_POKER_PLAYER_LEAVE <pokerpackets.networkpackets.PacketPokerPlayerLeave>`
| PACKET_POKER_REBUY

What to expect at all times ?
-----------------------------

| :class:`PACKET_POKER_MESSAGE <pokerpackets.networkpackets.PacketPokerMessage>`

How do I get the list of tournaments ?
--------------------------------------

| :class:`PACKET_POKER_TOURNEY_SELECT <pokerpackets.networkpackets.PacketPokerTourneySelect>`

How do I get the list of players registered in a tournament ?
-------------------------------------------------------------

| :class:`PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST <pokerpackets.networkpackets.PacketPokerTourneyRequestPlayersList>`


.. _hand:

What to expect while a hand is being played ?
---------------------------------------------

| :class:`PACKET_POKER_IN_GAME <pokerpackets.networkpackets.PacketPokerInGame>`
| :class:`PACKET_POKER_DEALER <pokerpackets.networkpackets.PacketPokerDealer>`
| :class:`PACKET_POKER_START <pokerpackets.networkpackets.PacketPokerStart>`
| :class:`PACKET_POKER_CANCELED <pokerpackets.networkpackets.PacketPokerCanceled>`
| :class:`PACKET_POKER_STATE <pokerpackets.networkpackets.PacketPokerState>`
| :class:`PACKET_POKER_POSITION <pokerpackets.networkpackets.PacketPokerPosition>`
| :class:`PACKET_POKER_BLIND <pokerpackets.networkpackets.PacketPokerBlind>`
| :class:`PACKET_POKER_ANTE <pokerpackets.networkpackets.PacketPokerAnte>`
| :class:`PACKET_POKER_CALL <pokerpackets.networkpackets.PacketPokerCall>`
| :class:`PACKET_POKER_RAISE <pokerpackets.networkpackets.PacketPokerRaise>`
| :class:`PACKET_POKER_FOLD <pokerpackets.networkpackets.PacketPokerFold>`
| :class:`PACKET_POKER_CHECK <pokerpackets.networkpackets.PacketPokerCheck>`
| :class:`PACKET_POKER_RAKE <pokerpackets.networkpackets.PacketPokerRake>`
| :class:`PACKET_POKER_WIN <pokerpackets.networkpackets.PacketPokerWin>`

What to expect while participating in a hand ?
----------------------------------------------

| :class:`PACKET_POKER_BLIND_REQUEST <pokerpackets.networkpackets.PacketPokerBlindRequest>`
| :class:`PACKET_POKER_ANTE_REQUEST <pokerpackets.networkpackets.PacketPokerAnteRequest>`
| :class:`PACKET_POKER_MUCK_REQUEST <pokerpackets.networkpackets.PacketPokerMuckRequest>`
| :class:`PACKET_POKER_SELF_IN_POSITION <pokerpackets.clientpackets.PacketPokerSelfInPosition>`
| :class:`PACKET_POKER_SELF_LOST_POSITION <pokerpackets.clientpackets.PacketPokerSelfLostPosition>`



What to send after receiving :class:`PACKET_POKER_SELF_IN_POSITION <pokerpackets.clientpackets.PacketPokerSelfInPosition>` (only in Explainmode)?
-------------------------------------------------------------------------------------------------------------------------------------------------------------

| :class:`PACKET_POKER_CALL <pokerpackets.networkpackets.PacketPokerCall>`
| :class:`PACKET_POKER_RAISE <pokerpackets.networkpackets.PacketPokerRaise>`
| :class:`PACKET_POKER_FOLD <pokerpackets.networkpackets.PacketPokerFold>`
| :class:`PACKET_POKER_CHECK <pokerpackets.networkpackets.PacketPokerCheck>`

What to send after receiving :class:`PACKET_POKER_MUCK_REQUEST <pokerpackets.networkpackets.PacketPokerMuckRequest>` ?
-------------------------------------------------------------------------------------------------------------------------------------

| :class:`PACKET_POKER_MUCK_ACCEPT <pokerpackets.networkpackets.PacketPokerMuckAccept>` or
| :class:`PACKET_POKER_MUCK_DENY <pokerpackets.networkpackets.PacketPokerMuckDeny>`

Tournaments
~~~~~~~~~~~

How to list tournaments ?
-------------------------

| :class:`PACKET_POKER_TOURNEY_SELECT <pokerpackets.networkpackets.PacketPokerTourneySelect>`

What to expect in response to :class:`PACKET_POKER_TOURNEY_SELECT <pokerpackets.networkpackets.PacketPokerTourneySelect>` ? 
---------------------------------------------------------------------------------------------------------------------------------------

| :class:`PACKET_POKER_TOURNEY_LIST <pokerpackets.networkpackets.PacketPokerTourneyList>` containing
  :class:`PACKET_POKER_TOURNEY <pokerpackets.networkpackets.PacketPokerTourney>` packets

How to list players registered in a tournament ? 
------------------------------------------------

| :class:`PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST <pokerpackets.networkpackets.PacketPokerTourneyRequestPlayersList>`

What to expect in response to :class:`PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST <pokerpackets.networkpackets.PacketPokerTourneyRequestPlayersList>` ? 
------------------------------------------------------------------------------------------------------------------------------------------------------------------

| :class:`PACKET_POKER_TOURNEY_PLAYERS_LIST <pokerpackets.networkpackets.PacketPokerTourneyPlayersList>`
  
How to register to a tournament ?
---------------------------------

| :class:`PACKET_POKER_TOURNEY_REGISTER <pokerpackets.networkpackets.PacketPokerTourneyRegister>`

What to expect in response to :class:`PACKET_POKER_TOURNEY_REGISTER <pokerpackets.networkpackets.PacketPokerTourneyRegister>` ? 
-----------------------------------------------------------------------------------------------------------------------------------------

| :class:`PACKET_POKER_TOURNEY_REGISTER <pokerpackets.networkpackets.PacketPokerTourneyRegister>` if success (the same that was sent)
| :class:`PACKET_ERROR <pokerpackets.packets.PacketError>` if failure

How to unregister to a tournament ?
-----------------------------------

| :class:`PACKET_POKER_TOURNEY_UNREGISTER <pokerpackets.networkpackets.PacketPokerTourneyUnregister>`

What to expect in response to :class:`PACKET_POKER_TOURNEY_UNREGISTER <pokerpackets.networkpackets.PacketPokerTourneyUnregister>` ? 
-------------------------------------------------------------------------------------------------------------------------------------------

| :class:`PACKET_POKER_TOURNEY_UNREGISTER <pokerpackets.networkpackets.PacketPokerTourneyUnregister>` if success (the same that was sent)
| :class:`PACKET_ERROR <pokerpackets.packets.PacketError>` if failure

What is sent to the tournament player that was busted out of a tournament (or is the winner) ? 
----------------------------------------------------------------------------------------------

| :class:`PACKET_POKER_TOURNEY_RANK <pokerpackets.networkpackets.PacketPokerTourneyRank>`

What is sent to the player when the tournament starts ? 
-------------------------------------------------------

#TODO

What should the client expect when moved to another table during a tournament ?
-------------------------------------------------------------------------------

| :class:`PACKET_POKER_TABLE_MOVE <pokerpackets.networkpackets.PacketPokerTableMove>` (or :class:`PACKET_POKER_PLAYER_LEAVE <pokerpackets.networkpackets.PacketPokerPlayerLeave>` if explain mode)
| (and :class:`PACKET_POKER_SEATS <pokerpackets.networkpackets.PacketPokerSeats>` if explain mode)

How to instruct the server to wait for the client before dealing the next hand ? 
--------------------------------------------------------------------------------

| :class:`PACKET_POKER_PROCESSING_HAND <pokerpackets.networkpackets.PacketPokerProcessingHand>`

How to tell the server that the client has finished displaying the current hand and can deal the next one ?
-----------------------------------------------------------------------------------------------------------

| :class:`PACKET_POKER_READY_TO_PLAY <pokerpackets.networkpackets.PacketPokerReadyToPlay>`
 
What should the client expect when a tournament break begins/ends?
-------------------------------------------------------------------

| :class:`POKER_TABLE_TOURNEY_BREAK_BEGIN <pokerpackets.networkpackets.PacketPokerTableTourneyBreakBegin>`
| :class:`POKER_TABLE_TOURNEY_BREAK_DONE <pokerpackets.networkpackets.PacketPokerTableTourneyBreakDone>`

What are the values that the currency_serial can contain?
----------------------------------------------------------

=============== ====================================
currency_serial description
=============== ====================================
       1        User Chips
       2        Tourney Chips (bank roll of with 
                this serial should be hidden from
                the player.)
       3        User Gold
=============== ====================================

How can I get the blinds / buy-ins for cashgames?
-------------------------------------------------

You can look at the name of the betting structure. The betting_structure has a naming convention::

    <small blind>-<big_blind>_<min buy_in>-<max buy_in>_<something>


What to do after a PacketPokerBlindRequest?
-------------------------------------------

When you get a :class:`PACKET_POKER_BLIND_REQUEST <pokerpackets.networkpackets.PacketPokerBlindRequest>` you get all the information how much you should pay. It is possible, that you need to pay a **blind** and a **dead**. Both values are just for your information. You should answer with a :class:`PACKET_POKER_BLIND <pokerpackets.networkpackets.PacketPokerBlind>` with just your serial filled. The server will know the correckt values and will charge you those. After this every one on this table get a :class:`PACKET_POKER_BLIND <pokerpackets.networkpackets.PacketPokerBlind>` with the **blind** amount and maybe a **dead** amount.

What is a dead amount in PacketPokerBlind?
------------------------------------------

After you joining a table it is possible a user would have to wait till the big blind is moving to his place before he can actually play. The default behaviour is to pay a late blind instead and you can usualy play the next round (Except your seat is between the dealer and the big blind). It is possible to wait for big blind if a :class:`POKER_WAIT_BIG_BLIND <pokerpackets.networkpackets.PacketPokerWaitBigBlind>` is sent. 

If the table is too full the player is forced to pay a **dead** amount directly into the pot and the normal **blind** to his bet.

======= ========== ====== ====== =====
  Big    Late Dead        Small
User A  User B     User C User D Pot
   100         100      0     50    50
======= ========== ====== ====== =====

Remember the dead blind goes directly to the pot so *Player C* would still have to call 100 not 150.
