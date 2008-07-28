UPDATE server SET version = '1.7.0';
--
-- Larger field for skin url 
--
ALTER TABLE `users` CHANGE COLUMN `skin_url` `skin_url` VARCHAR(128);
--
-- Server side, per user locale
-- 
ALTER TABLE `users` ADD COLUMN `locale` VARCHAR(32) DEFAULT "en";
--
-- History of monitor events
--
CREATE TABLE monitor (
  serial INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  event TINYINT NOT NULL,
  param1 BIGINT NOT NULL,
  param2 BIGINT NOT NULL,

  PRIMARY KEY (serial, created)
) ENGINE=MyISAM;
--
-- A table that belongs to a tourney is marked as such
--
ALTER TABLE `pokertables` ADD COLUMN tourney_serial INT UNSIGNED DEFAULT 0 NOT NULL;
