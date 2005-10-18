--
-- Money units are now cents
--
ALTER TABLE `users` CHANGE `play_money` `play_money` INT( 11 ) NULL DEFAULT '100000000';
update users set play_money = play_money * 100;
update tourneys_schedule set buy_in = buy_in * 100, rake = rake * 100;
