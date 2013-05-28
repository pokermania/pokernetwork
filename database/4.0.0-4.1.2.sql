ALTER TABLE `user2tourney` ADD COLUMN `rebuy_count` INT NOT NULL DEFAULT 0  AFTER `rank` , ADD COLUMN `add_on_count` INT NOT NULL DEFAULT 0  AFTER `rebuy_count`;
