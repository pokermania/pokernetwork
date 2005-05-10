--
-- Copyright (C) 2004 Mekensleep
--
-- Mekensleep
-- 24 rue vieille du temple
-- 75004 Paris
--       licensing@mekensleep.com
--
-- This program is free software; you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation; either version 2 of the License, or
-- (at your option) any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with this program; if not, write to the Free Software
-- Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
--
-- Authors:
--  Loic Dachary <loic@gnu.org>
--
drop table if exists users;

create table users (
	serial int unsigned not null auto_increment,
	name varchar(32),
	skin_url varchar(32) default "default",
	skin_outfit text,
	password varchar(32),
	privilege int default 1,

	play_money int default 5000,
  real_money int default 0,
	point_money int default 5000,

	rating int default 1000,
	future_rating float default 1000,
	games_count int default 0,
	
	primary key (serial)
);

drop table if exists users_private;

create table users_private (
	serial int unsigned not null,
	email varchar(128) default "",
	addr_street varchar(255) default "",
	addr_zip varchar(64) default "",
	addr_town varchar(64) default "",
	addr_state varchar(128) default "",
	addr_country varchar(64) default "",
	phone varchar(64) default "",

	primary key (serial)
);

drop table if exists user2table;

create table user2table (
	user_serial int unsigned not null,
	table_serial int unsigned not null,
	money int default 0 not null,
	bet int default 0 not null,
  real_money char default 'n',

	primary key (user_serial,table_serial)
);

drop table if exists pokertables;

create table pokertables (
	serial int unsigned not null auto_increment,
	name varchar(32),
  real_money char default 'n',

	primary key (serial)
);

drop table if exists hands;

create table hands (
	serial int unsigned not null auto_increment,
	name varchar(32),
	description text not null,

	primary key (serial)
);

drop table if exists user2hand;

create table user2hand (
	user_serial int not null,
	hand_serial int not null,

	primary key (user_serial, hand_serial)
);

drop table if exists tourneys_schedule;

create table tourneys_schedule (
	serial int unsigned not null auto_increment,
  name varchar(32),
  description_short varchar(64),
  description_long text,
  players_quota int default 10,
  variant varchar(32),
  betting_structure varchar(32),
  seats_per_game int default 10,
  real_money char default 'n',
  buy_in int,
  rake int,
  sit_n_go char default 'y',
  breaks_interval int default 60,
  rebuy_delay int default 0,
  add_on int default 0,
  add_on_delay int default 60,
  start_time int default 0,

  register_time int default 0,
  respawn char default 'n',
  respawn_interval int default 0,

	primary key (serial)
);

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo2', 'Sit and Go 2 players', 'Sit and Go 2 players', '2', 'holdem', 'level-15-30-no-limit', '2', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo3', 'Sit and Go 3 players', 'Sit and Go 3 players', '3', 'holdem', 'level-15-30-no-limit', '3', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo4', 'Sit and Go 4 players', 'Sit and Go 4 players', '4', 'holdem', 'level-15-30-no-limit', '4', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo5', 'Sit and Go 5 players', 'Sit and Go 5 players', '5', 'holdem', 'level-15-30-no-limit', '5', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo6', 'Sit and Go 6 players', 'Sit and Go 6 players', '6', 'holdem', 'level-15-30-no-limit', '6', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo7', 'Sit and Go 7 players', 'Sit and Go 7 players', '7', 'holdem', 'level-15-30-no-limit', '7', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo8', 'Sit and Go 8 players', 'Sit and Go 8 players', '8', 'holdem', 'level-15-30-no-limit', '8', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo9', 'Sit and Go 9 players', 'Sit and Go 9 players', '9', 'holdem', 'level-15-30-no-limit', '9', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo10', 'Sit and Go 10 players', 'Sit and Go single table', '10', 'holdem', 'level-15-30-no-limit', '10', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo20', 'Sit and Go 2 tables', 'Sit and Go 2 tables', '20', 'holdem', 'level-15-30-no-limit', '10', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo30', 'Sit and Go 3 tables', 'Sit and Go 3 tables', '30', 'holdem', 'level-15-30-no-limit', '10', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

INSERT INTO `tourneys_schedule` ( `name`, `description_short` , `description_long` , `players_quota` , `variant` , `betting_structure` , `seats_per_game` , `real_money` , `buy_in` , `rake` , `sit_n_go` , `start_time` , `register_time` , `respawn` , `respawn_interval` )
VALUES ( 'sitngo50', 'Sit and Go 5 tables', 'Sit and Go 5 tables', '50', 'holdem', 'level-15-30-no-limit', '10', 'n', '3000', '0', 'y', '0', '0', 'y', '0' );

drop table if exists tourneys;

create table tourneys (
	serial int unsigned not null auto_increment,
  name varchar(32),
  description_short varchar(64),
  description_long text,
  players_quota int default 10,
  variant varchar(32),
  betting_structure varchar(32),
  seats_per_game int default 10,
  real_money char default 'n',
  buy_in int,
  rake int,
  sit_n_go char default 'y',
  breaks_interval int default 60,
  rebuy_delay int default 0,
  add_on int default 0,
  add_on_delay int default 60,
  start_time int default 0,

  finish_time int default 0,
  state varchar(32) default "registering",
  schedule_serial int,

	primary key (serial)
);

drop table if exists user2tourney;

create table user2tourney (
	user_serial int not null,
	tourney_serial int not null,
  table_serial int,
  rank int default -1,

	primary key (user_serial, tourney_serial)
);

-- Edit the following with phpmyadmin
-- Dump with
--  mysqldump --where 'name is not null' --no-create-info -u poker3d -p poker3d hands

INSERT INTO hands VALUES (1,'Odd chip','[(\'game\',\n  1,\n  1,\n  0,\n  1091628503.714052,\n  \'holdem\',\n  \'15-30-no-limit\',\n  [6, 7, 8, 9, 10],\n  0,\n  {6: [5, 3, 1, 3, 2, 5, 3, 1, 0, 0, 0],\n   7: [5, 3, 1, 3, 2, 5, 3, 1, 0, 0, 0],\n   8: [5, 3, 1, 3, 2, 5, 3, 1, 0, 0, 0],\n   9: [5, 3, 1, 3, 2, 5, 3, 1, 0, 0, 0],\n   10: [5, 3, 1, 3, 2, 5, 3, 1, 0, 0, 0],\n   \'values\': [5, 10, 20, 25, 50, 100, 250, 500, 1000, 2000, 5000]}),\n (\'round\',\n  \'pre-flop\',\n  PokerCards([]),\n  {9: PokerCards([\'7h\', \'3s\']),\n   10: PokerCards([\'As\', \'2s\']),\n   6: PokerCards([\'Ah\', \'2h\']),\n   7: PokerCards([\'Ac\', \'2c\']),\n   8: PokerCards([\'Ad\', \'2d\'])}),\n (\'call\', 9L, 15),\n (\'call\', 10L, 15),\n (\'call\', 6L, 15),\n (\'call\', 7L, 5),\n (\'check\', 8L),\n (\'round\', \'flop\', PokerCards([\'Qh\', \'Qs\', \'Qc\']), None),\n (\'check\', 7L),\n (\'check\', 8L),\n (\'fold\', 9L),\n (\'check\', 10L),\n (\'check\', 6L),\n (\'round\', \'turn\', PokerCards([\'Qh\', \'Qs\', \'Qc\', \'Jh\']), None),\n (\'check\', 7L),\n (\'check\', 8L),\n (\'check\', 10L),\n (\'check\', 6L),\n (\'round\', \'river\', PokerCards([\'Qh\', \'Qs\', \'Qc\', \'Jh\', \'Jc\']), None),\n (\'check\', 7L),\n (\'check\', 8L),\n (\'check\', 10L),\n (\'check\', 6L),\n (\'showdown\', None, None),\n (\'end\', [8, 10, 6, 7], {}, [])]');

INSERT INTO hands VALUES (2,'All In','[(\'game\',\n  1,\n  1,\n  0,\n  1091628503.714052,\n  \'holdem\',\n  \'15-30-no-limit\',\n  [6, 7, 8, 9, 10],\n  0,\n  {6: [20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],\n   7: [40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],\n   8: [60, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],\n   9: [80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],\n   10: [90, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],\n   \'values\': [5, 10, 20, 25, 50, 100, 250, 500, 1000, 2000, 5000]}),\n (\'round\',\n  \'pre-flop\',\n  PokerCards([]),\n  {10: PokerCards([\'3h\', \'3s\']),\n   9: PokerCards([\'4h\', \'4s\']),\n   8: PokerCards([\'5h\', \'5s\']),\n   7: PokerCards([\'6h\', \'6s\']),\n   6: PokerCards([\'7h\', \'7s\'])}),\n (\'raise\', 9L, [40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),\n (\'call\', 10L, None),\n (\'call\', 6L, None),\n (\'call\', 7L, None),\n (\'call\', 8L, None),\n (\'round\', \'flop\', PokerCards([\'Ah\', \'Kc\', \'8s\']), None),\n (\'raise\', 8L, [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),\n (\'call\', 9L, None),\n (\'call\', 10L, None),\n (\'round\', \'turn\', PokerCards([\'Ah\', \'Kc\', \'8s\', \'Jh\']), None),\n (\'check\', 8L),\n (\'check\', 9L),\n (\'check\', 10L),\n (\'round\', \'river\', PokerCards([\'Ah\', \'Kc\', \'8s\', \'Jh\', \'9c\']), None),\n (\'check\', 8L),\n (\'check\', 9L),\n (\'check\', 10L),\n (\'showdown\', None, None),\n (\'end\', [6, 7, 8], {}, [])]');

INSERT INTO `hands` VALUES (3, 'Straight Flush Omaha8', '[(\'game\',\n  1,\n  24074,\n  1,\n  1095434064.7536609,\n  \'omaha8\',\n  \'10-15-pot-limit\',\n  [2996, 2993, 1051L, 2982L],\n  1,\n  {1051L: [18, 21, 17, 0, 0, 0, 0, 0, 0],\n   2982L: [56, 56, 42, 0, 0, 0, 0, 0, 0],\n   2993: [56, 56, 42, 0, 0, 0, 0, 0, 0],\n   2996: [34, 33, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0],\n   \'values\': [5, 10, 20, 25, 50, 100, 250, 500, 5000]}),\n (\'position\', 2),\n (\'blind\', 1051L, 5, 0),\n (\'position\', 3),\n (\'blind\', 2982L, 10, 0),\n (\'position\', 0),\n (\'blind\', 2996, 10, 0),\n (\'round\',\n  \'pre-flop\',\n  PokerCards([]),\n  {1051L: PokerCards([216, 210, 234, 202]),\n   2982L: PokerCards([215, 198, 206, 226]),\n   2993: PokerCards([218, 230, 195, 212]),\n   2996: PokerCards([194, 231, 205, 211])}),\n (\'check\', 2996L),\n (\'call\', 2993L, 10),\n (\'fold\', 1051L),\n (\'check\', 2982L),\n (\'round\',\n  \'flop\',\n  PokerCards([35, 28, 27]),\n  {2982L: PokerCards([215, 198, 206, 226]),\n   2993: PokerCards([218, 230, 195, 212]),\n   2996: PokerCards([194, 231, 205, 211])}),\n (\'check\', 2982L),\n (\'check\', 2996L),\n (\'raise\', 2993L, [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),\n (\'call\', 2982L, 10),\n (\'call\', 2996L, 10),\n (\'round\', \'turn\', PokerCards([35, 28, 27, 29]), None),\n (\'raise\', 2982L, [3, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]),\n (\'fold\', 2996L),\n (\'raise\', 2993L, [6, 4, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0]),\n (\'call\', 2982L, 65),\n (\'round\',\n  \'river\',\n  PokerCards([35, 28, 27, 29, 33]),\n  {2982L: PokerCards([215, 198, 206, 226]),\n   2993: PokerCards([218, 230, 195, 212])}),\n (\'raise\', 2982L, [11, 11, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0]),\n (\'raise\', 2993L, [22, 22, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0]),\n (\'raise\', 2982L, [41, 40, 30, 0, 0, 0, 0, 0, 0, 0, 0, 0]),\n (\'call\', 2993L, 880),\n (\'showdown\',\n  None,\n  {2993: PokerCards([26, 38, 3, 20]), 2982L: PokerCards([23, 6, 14, 34])}),\n (\'end\', [2993], {2993: 3380, 1051L: 5}, []),\n (\'sitOut\', 2982L)]');

--
-- Default admin user
--
INSERT INTO users VALUES (0,'admin','default','default','fakefake',2,500000,200,500000,1000,1000,0);
