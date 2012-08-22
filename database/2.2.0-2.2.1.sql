-- add skin to tourneys_schedule and tourneys
ALTER TABLE  `tourneys_schedule` ADD  `skin` VARCHAR( 255 ) NOT NULL DEFAULT  'default' AFTER  `betting_structure`;
ALTER TABLE  `tourneys` ADD  `skin` VARCHAR( 255 ) NOT NULL DEFAULT  'default' AFTER  `betting_structure`;
