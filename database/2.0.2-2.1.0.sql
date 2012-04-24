-- add state for resthost (0=offline,1=online,2=shutting_down)
ALTER TABLE resthost ADD state INT UNSIGNED NOT NULL DEFAULT '0';

