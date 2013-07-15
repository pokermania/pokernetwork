-- add inactive_delay column to tourneys and tourneys_schedule
ALTER TABLE `tourneys_schedule` ADD COLUMN `inactive_delay` INT(11) NOT NULL DEFAULT '0' AFTER `add_on_delay`;
ALTER TABLE `tourneys` ADD COLUMN `inactive_delay` INT(11) NOT NULL DEFAULT '0' AFTER `add_on_delay`;
