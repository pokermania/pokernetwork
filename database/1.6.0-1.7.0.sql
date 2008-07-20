UPDATE server SET version = '1.7.0';
--
-- Larger field for skin url 
--
ALTER TABLE `users` CHANGE COLUMN `skin_url` `skin_url` VARCHAR(128);
