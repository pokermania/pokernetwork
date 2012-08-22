-- add skin to tourneys_schedule and tourneys
ALTER TABLE  `tourneys_schedule` ADD  `skin` VARCHAR( 255 ) NOT NULL DEFAULT  'default' AFTER  `betting_structure`;
ALTER TABLE  `tourneys` ADD  `skin` VARCHAR( 255 ) NOT NULL DEFAULT  'default' AFTER  `betting_structure`;

-- change skin_url default to ''
ALTER TABLE  `users` CHANGE  `skin_url`  `skin_url` VARCHAR( 255 ) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL DEFAULT  '';
