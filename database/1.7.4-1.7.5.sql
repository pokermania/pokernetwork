UPDATE server SET version = '1.7.5';
--
-- different currencies for buyin and prizes
--
ALTER TABLE `tourneys_schedule` ADD `via_satellite` TINYINT DEFAULT 0;
ALTER TABLE `tourneys_schedule` ADD `satellite_of` INT UNSIGNED DEFAULT 0;
ALTER TABLE `tourneys_schedule` ADD `satellite_player_count` INT UNSIGNED DEFAULT 0;
ALTER TABLE `tourneys` ADD `via_satellite` TINYINT DEFAULT 0;
ALTER TABLE `tourneys` ADD `satellite_of` INT UNSIGNED DEFAULT 0;
ALTER TABLE `tourneys` ADD `satellite_player_count` INT UNSIGNED DEFAULT 0;
