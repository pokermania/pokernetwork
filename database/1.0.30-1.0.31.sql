ALTER TABLE `user2money` CHANGE COLUMN `amount` `amount` BIGINT not null;
ALTER TABLE `user2money` CHANGE COLUMN `rake` `rake` BIGINT default 0 not null;
ALTER TABLE `user2money` CHANGE COLUMN `points` `points` BIGINT default 0 not null;
ALTER TABLE `safe` CHANGE COLUMN `value` `value` BIGINT not null;
ALTER TABLE `counter` CHANGE COLUMN `value` `value` BIGINT not null;
