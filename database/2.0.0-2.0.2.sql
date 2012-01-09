-- support big bets
ALTER TABLE user2table CHANGE money money BIGINT NOT NULL DEFAULT 0;
ALTER TABLE user2table CHANGE bet bet BIGINT NOT NULL DEFAULT 0;