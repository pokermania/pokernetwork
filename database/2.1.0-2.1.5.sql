-- add not null to relevant columns
ALTER TABLE `affiliates` 
MODIFY COLUMN `users_count` int(10) unsigned NOT NULL DEFAULT '0' AFTER `created`, 
MODIFY COLUMN `users_rake` int(10) unsigned NOT NULL DEFAULT '0' AFTER `users_count`, 
MODIFY COLUMN `users_points` int(10) unsigned NOT NULL DEFAULT '0' AFTER `users_rake`, 
MODIFY COLUMN `share` int(10) unsigned NOT NULL DEFAULT '0' AFTER `users_points`, 
MODIFY COLUMN `companyname` varchar(255) NOT NULL DEFAULT '' AFTER `share`, 
MODIFY COLUMN `firstname` varchar(255) NOT NULL DEFAULT '' AFTER `companyname`, 
MODIFY COLUMN `lastname` varchar(255) NOT NULL DEFAULT '' AFTER `firstname`, 
MODIFY COLUMN `addr_street` varchar(255) NOT NULL DEFAULT '' AFTER `lastname`, 
MODIFY COLUMN `addr_street2` varchar(255) NOT NULL DEFAULT '' AFTER `addr_street`, 
MODIFY COLUMN `addr_zip` varchar(64) NOT NULL DEFAULT '' AFTER `addr_street2`, 
MODIFY COLUMN `addr_town` varchar(64) NOT NULL DEFAULT '' AFTER `addr_zip`, 
MODIFY COLUMN `addr_state` varchar(128) NOT NULL DEFAULT '' AFTER `addr_town`, 
MODIFY COLUMN `addr_country` varchar(64) NOT NULL DEFAULT '' AFTER `addr_state`, 
MODIFY COLUMN `phone` varchar(64) NOT NULL DEFAULT '' AFTER `addr_country`, 
MODIFY COLUMN `url` text NOT NULL AFTER `phone`, 
MODIFY COLUMN `notes` text NOT NULL AFTER `url`;

ALTER TABLE `chat_messages` 
MODIFY COLUMN `message` text NOT NULL AFTER `game_id`;

ALTER TABLE `currencies` 
MODIFY COLUMN `symbol` char(8) NOT NULL AFTER `url`, 
MODIFY COLUMN `name` char(32) NOT NULL AFTER `symbol`;

ALTER TABLE `hands` 
MODIFY COLUMN `name` varchar(32) NOT NULL AFTER `created`;

ALTER TABLE `messages` 
MODIFY COLUMN `message` text NOT NULL AFTER `send_date`;

ALTER TABLE `resthost` 
MODIFY COLUMN `name` varchar(255) NOT NULL AFTER `serial`, 
MODIFY COLUMN `host` varchar(255) NOT NULL AFTER `name`, 
MODIFY COLUMN `port` int(10) unsigned NOT NULL AFTER `host`, 
MODIFY COLUMN `path` varchar(255) NOT NULL AFTER `port`;

ALTER TABLE `route` 
MODIFY COLUMN `table_serial` int(10) unsigned NOT NULL FIRST, 
MODIFY COLUMN `tourney_serial` int(10) unsigned NOT NULL AFTER `table_serial`, 
MODIFY COLUMN `modified` int(10) unsigned NOT NULL AFTER `tourney_serial`, 
MODIFY COLUMN `resthost_serial` int(10) unsigned NOT NULL AFTER `modified`;

ALTER TABLE `session` 
MODIFY COLUMN `started` int(11) NOT NULL DEFAULT '0' AFTER `user_serial`, 
MODIFY COLUMN `ended` int(11) NOT NULL DEFAULT '0' AFTER `started`, 
MODIFY COLUMN `ip` varchar(16) NOT NULL AFTER `ended`;

ALTER TABLE `session_history` 
MODIFY COLUMN `started` int(11) NOT NULL DEFAULT '0' AFTER `user_serial`, 
MODIFY COLUMN `ended` int(11) NOT NULL DEFAULT '0' AFTER `started`, 
MODIFY COLUMN `ip` varchar(16) NOT NULL AFTER `ended`;

ALTER TABLE `tourneys` 
MODIFY COLUMN `name` varchar(200) NOT NULL AFTER `resthost_serial`, 
MODIFY COLUMN `description_short` varchar(64) NOT NULL AFTER `name`, 
MODIFY COLUMN `description_long` text NOT NULL AFTER `description_short`, 
MODIFY COLUMN `players_quota` int(11) NOT NULL DEFAULT '10' AFTER `description_long`, 
MODIFY COLUMN `players_min` int(11) NOT NULL DEFAULT '2' AFTER `players_quota`, 
MODIFY COLUMN `variant` varchar(32) NOT NULL AFTER `players_min`, 
MODIFY COLUMN `betting_structure` varchar(32) NOT NULL AFTER `variant`, 
MODIFY COLUMN `seats_per_game` int(11) NOT NULL DEFAULT '10' AFTER `betting_structure`, 
MODIFY COLUMN `player_timeout` int(11) NOT NULL DEFAULT '60' AFTER `seats_per_game`, 
MODIFY COLUMN `currency_serial` int(11) NOT NULL AFTER `player_timeout`, 
MODIFY COLUMN `prize_currency` int(10) unsigned NOT NULL DEFAULT '0' AFTER `currency_serial`, 
MODIFY COLUMN `prize_min` int(11) NOT NULL DEFAULT '0' AFTER `prize_currency`, 
MODIFY COLUMN `bailor_serial` int(11) NOT NULL DEFAULT '0' AFTER `prize_min`, 
MODIFY COLUMN `buy_in` int(11) NOT NULL DEFAULT '0' AFTER `bailor_serial`, 
MODIFY COLUMN `rake` int(11) NOT NULL DEFAULT '0' AFTER `buy_in`, 
MODIFY COLUMN `sit_n_go` char(1) NOT NULL DEFAULT 'y' AFTER `rake`, 
MODIFY COLUMN `breaks_first` int(11) NOT NULL DEFAULT '7200' AFTER `sit_n_go`, 
MODIFY COLUMN `breaks_interval` int(11) NOT NULL DEFAULT '3600' AFTER `breaks_first`, 
MODIFY COLUMN `breaks_duration` int(11) NOT NULL DEFAULT '300' AFTER `breaks_interval`, 
MODIFY COLUMN `rebuy_delay` int(11) NOT NULL DEFAULT '0' AFTER `breaks_duration`, 
MODIFY COLUMN `add_on` int(11) NOT NULL DEFAULT '0' AFTER `rebuy_delay`, 
MODIFY COLUMN `add_on_delay` int(11) NOT NULL DEFAULT '60' AFTER `add_on`, 
MODIFY COLUMN `start_time` int(11) NOT NULL DEFAULT '0' AFTER `add_on_delay`, 
MODIFY COLUMN `satellite_of` int(10) unsigned NOT NULL DEFAULT '0' AFTER `start_time`, 
MODIFY COLUMN `via_satellite` tinyint(4) NOT NULL DEFAULT '0' AFTER `satellite_of`, 
MODIFY COLUMN `satellite_player_count` int(10) unsigned NOT NULL DEFAULT '0' AFTER `via_satellite`, 
MODIFY COLUMN `finish_time` int(11) NOT NULL DEFAULT '0' AFTER `satellite_player_count`, 
MODIFY COLUMN `state` varchar(16) NOT NULL DEFAULT 'registering' AFTER `finish_time`, 
MODIFY COLUMN `schedule_serial` int(11) NOT NULL AFTER `state`, 
MODIFY COLUMN `add_on_count` int(11) NOT NULL DEFAULT '0' AFTER `schedule_serial`, 
MODIFY COLUMN `rebuy_count` int(11) NOT NULL DEFAULT '0' AFTER `add_on_count`;

ALTER TABLE `tourneys_schedule` 
MODIFY COLUMN `name` varchar(200) NOT NULL AFTER `resthost_serial`, 
MODIFY COLUMN `description_short` varchar(64) NOT NULL AFTER `name`, 
MODIFY COLUMN `description_long` text NOT NULL AFTER `description_short`, 
MODIFY COLUMN `players_quota` int(11) NOT NULL DEFAULT '10' AFTER `description_long`, 
MODIFY COLUMN `players_min` int(11) NOT NULL DEFAULT '2' AFTER `players_quota`, 
MODIFY COLUMN `variant` varchar(32) NOT NULL AFTER `players_min`, 
MODIFY COLUMN `betting_structure` varchar(32) NOT NULL AFTER `variant`, 
MODIFY COLUMN `seats_per_game` int(11) NOT NULL DEFAULT '10' AFTER `betting_structure`, 
MODIFY COLUMN `player_timeout` int(11) NOT NULL DEFAULT '60' AFTER `seats_per_game`, 
MODIFY COLUMN `currency_serial` int(11) NOT NULL AFTER `player_timeout`, 
MODIFY COLUMN `prize_currency` int(10) unsigned NOT NULL DEFAULT '0' AFTER `currency_serial`, 
MODIFY COLUMN `prize_min` int(11) NOT NULL DEFAULT '0' AFTER `prize_currency`, 
MODIFY COLUMN `bailor_serial` int(11) NOT NULL DEFAULT '0' AFTER `prize_min`, 
MODIFY COLUMN `buy_in` int(11) NOT NULL DEFAULT '0' AFTER `bailor_serial`, 
MODIFY COLUMN `rake` int(11) NOT NULL DEFAULT '0' AFTER `buy_in`, 
MODIFY COLUMN `sit_n_go` char(1) NOT NULL DEFAULT 'y' AFTER `rake`, 
MODIFY COLUMN `breaks_first` int(11) NOT NULL DEFAULT '7200' AFTER `sit_n_go`, 
MODIFY COLUMN `breaks_interval` int(11) NOT NULL DEFAULT '3600' AFTER `breaks_first`, 
MODIFY COLUMN `breaks_duration` int(11) NOT NULL DEFAULT '300' AFTER `breaks_interval`, 
MODIFY COLUMN `rebuy_delay` int(11) NOT NULL DEFAULT '0' AFTER `breaks_duration`, 
MODIFY COLUMN `add_on` int(11) NOT NULL DEFAULT '0' AFTER `rebuy_delay`, 
MODIFY COLUMN `add_on_delay` int(11) NOT NULL DEFAULT '60' AFTER `add_on`, 
MODIFY COLUMN `start_time` int(11) NOT NULL DEFAULT '0' AFTER `add_on_delay`, 
MODIFY COLUMN `register_time` int(11) NOT NULL DEFAULT '0' AFTER `start_time`, 
MODIFY COLUMN `active` char(1) NOT NULL DEFAULT 'y' AFTER `register_time`, 
MODIFY COLUMN `respawn` char(1) NOT NULL DEFAULT 'n' AFTER `active`, 
MODIFY COLUMN `respawn_interval` int(11) NOT NULL DEFAULT '0' AFTER `respawn`, 
MODIFY COLUMN `satellite_of` int(10) unsigned NOT NULL DEFAULT '0' AFTER `prize_currency_from_date_format`, 
MODIFY COLUMN `via_satellite` tinyint(4) NOT NULL DEFAULT '0' AFTER `satellite_of`, 
MODIFY COLUMN `satellite_player_count` int(10) unsigned NOT NULL DEFAULT '0' AFTER `via_satellite`;

ALTER TABLE `user2table` 
MODIFY COLUMN `money` bigint(20) NOT NULL DEFAULT '0' AFTER `table_serial`;

ALTER TABLE `user2tourney` 
MODIFY COLUMN `rank` int(11) NOT NULL DEFAULT '-1' AFTER `table_serial`;

ALTER TABLE `users` 
MODIFY COLUMN `name` varchar(64) NOT NULL AFTER `created`, 
MODIFY COLUMN `affiliate` int(10) unsigned NOT NULL DEFAULT '0' AFTER `email`, 
MODIFY COLUMN `skin_url` varchar(255) NOT NULL DEFAULT 'random' AFTER `affiliate`, 
MODIFY COLUMN `skin_outfit` text AFTER `skin_url`, 
MODIFY COLUMN `skin_image` text AFTER `skin_outfit`, 
MODIFY COLUMN `password` varchar(32) NOT NULL AFTER `skin_image_type`, 
MODIFY COLUMN `privilege` int(11) NOT NULL DEFAULT '1' AFTER `password`, 
MODIFY COLUMN `locale` varchar(32) NOT NULL DEFAULT 'en_US' AFTER `privilege`, 
MODIFY COLUMN `rating` int(11) NOT NULL DEFAULT '1000' AFTER `locale`, 
MODIFY COLUMN `future_rating` float NOT NULL DEFAULT '1000' AFTER `rating`, 
MODIFY COLUMN `games_count` int(11) NOT NULL DEFAULT '0' AFTER `future_rating`;

ALTER TABLE `users_private` 
MODIFY COLUMN `firstname` varchar(255) NOT NULL DEFAULT '' AFTER `serial`, 
MODIFY COLUMN `lastname` varchar(255) NOT NULL DEFAULT '' AFTER `firstname`, 
MODIFY COLUMN `addr_street` varchar(255) NOT NULL DEFAULT '' AFTER `lastname`, 
MODIFY COLUMN `addr_street2` varchar(255) NOT NULL DEFAULT '' AFTER `addr_street`, 
MODIFY COLUMN `addr_zip` varchar(64) NOT NULL DEFAULT '' AFTER `addr_street2`, 
MODIFY COLUMN `addr_town` varchar(64) NOT NULL DEFAULT '' AFTER `addr_zip`, 
MODIFY COLUMN `addr_state` varchar(128) NOT NULL DEFAULT '' AFTER `addr_town`, 
MODIFY COLUMN `addr_country` varchar(64) NOT NULL DEFAULT '' AFTER `addr_state`, 
MODIFY COLUMN `phone` varchar(64) NOT NULL DEFAULT '' AFTER `addr_country`, 
MODIFY COLUMN `gender` char(1) NOT NULL DEFAULT '' AFTER `phone`, 
MODIFY COLUMN `verified` char(1) NOT NULL DEFAULT 'n' AFTER `birthdate`, 
MODIFY COLUMN `verified_time` int(11) NOT NULL DEFAULT '0' AFTER `verified`;

ALTER TABLE `users_transactions` 
MODIFY COLUMN `amount` int(11) NOT NULL DEFAULT '0' AFTER `modified`, 
MODIFY COLUMN `status` char(1) NOT NULL DEFAULT 'n' AFTER `currency_serial`, 
MODIFY COLUMN `notes` text NOT NULL AFTER `status`;

