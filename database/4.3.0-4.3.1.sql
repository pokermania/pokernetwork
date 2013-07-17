-- increased possible betting_structure file name length
ALTER TABLE `tourneys_schedule` CHANGE COLUMN `betting_structure` `betting_structure` VARCHAR(255) NOT NULL COMMENT 'Betting structure (level-001, level-10-15-pot-limit, level-10-20_200-2000_no-limit, level-15-30-no-limit, level-1-2_20-200_limit)'  ;
ALTER TABLE `tourneys` CHANGE COLUMN `betting_structure` `betting_structure` VARCHAR(255) NOT NULL  ;
