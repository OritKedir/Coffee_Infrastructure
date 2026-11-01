CREATE DATABASE IF NOT EXISTS coffee_trade;
USE coffee_trade;

CREATE TABLE IF NOT EXISTS raw_trade (
    area_code INT,
    area_code_m49 VARCHAR(50),
    area VARCHAR(255),
    item_code INT,
    item_code_cpc VARCHAR(50),
    item VARCHAR(255),
    element_code INT,
    element VARCHAR(100),
    year_code INT,
    year INT,
    unit VARCHAR(50),
    value DECIMAL(15, 2),
    flag VARCHAR(10),
    note TEXT
);