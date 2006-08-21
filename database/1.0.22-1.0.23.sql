-- Avoid stupid errors by making serial unique
ALTER TABLE `currencies` ADD UNIQUE `serial01` ( `serial` );
