-- add null back and some more changes

ALTER TABLE `currencies` 
MODIFY COLUMN `url` varchar(255) NOT NULL UNIQUE AFTER `serial`, 
MODIFY COLUMN `symbol` varchar(8) DEFAULT '' NOT NULL AFTER `url`, 
MODIFY COLUMN `name` varchar(32) DEFAULT '' NOT NULL AFTER `symbol`,
MODIFY COLUMN `cash_out` int(11) DEFAULT '0' NOT NULL AFTER `name`;
