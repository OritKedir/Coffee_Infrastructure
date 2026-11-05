
-- GIULIA: EUROPEAN COFFEE TRADE ANALYSIS
-- Dataset: FAOSTAT - Coffee, green
-- Units: tonnes (t)
-- Net trade = Exports - Imports

-- 1. Identify the latest available year
SET @latest_year = (
    SELECT MAX(year)
    FROM raw_trade
    WHERE item = 'Coffee, green'
      AND element_code IN (5610, 5910)
      AND unit = 't'
);

-- 2. Create a temporary European country list
-- Geographic classification: UN M49
CREATE TEMPORARY TABLE europe_m49 (
    code INT PRIMARY KEY
);

INSERT INTO europe_m49 (code) VALUES
(112),(100),(203),(348),(616),(498),(642),(643),(703),(804),
(248),(208),(233),(234),(246),(831),(352),(372),(833),(832),
(428),(440),(578),(744),(752),(826),
(8),(20),(70),(191),(292),(300),(336),(380),(470),(499),
(807),(620),(674),(688),(705),(724),
(40),(56),(250),(276),(438),(442),(492),(528),(756);

-- 3. European top 5 net exporters and importers
WITH country_totals AS (
    SELECT
        area,
        SUM(CASE WHEN element_code = 5910
                 THEN value ELSE 0 END) AS exports_t,
        SUM(CASE WHEN element_code = 5610
                 THEN value ELSE 0 END) AS imports_t
    FROM raw_trade
    WHERE item = 'Coffee, green'
      AND unit = 't'
      AND element_code IN (5610, 5910)
      AND year BETWEEN @latest_year - 9 AND @latest_year
      AND CAST(REPLACE(area_code_m49, CHAR(39), '')
               AS UNSIGNED) IN (SELECT code FROM europe_m49)
    GROUP BY area
),
ranked AS (
    SELECT
        area,
        exports_t - imports_t AS net_trade_t,
        ROW_NUMBER() OVER (
            ORDER BY exports_t - imports_t DESC
        ) AS export_rank,
        ROW_NUMBER() OVER (
            ORDER BY exports_t - imports_t ASC
        ) AS import_rank
    FROM country_totals
)
SELECT 'Exporter' AS category,
       export_rank AS position,
       area,
       ROUND(net_trade_t, 2) AS net_trade_t
FROM ranked
WHERE export_rank <= 5 AND net_trade_t > 0

UNION ALL

SELECT 'Importer' AS category,
       import_rank AS position,
       area,
       ROUND(net_trade_t, 2) AS net_trade_t
FROM ranked
WHERE import_rank <= 5 AND net_trade_t < 0
ORDER BY category, position;

-- 4. Ten-year trajectory for European countries
SELECT
    area,
    year,
    SUM(CASE WHEN element_code = 5910
             THEN value ELSE 0 END) AS exports_t,
    SUM(CASE WHEN element_code = 5610
             THEN value ELSE 0 END) AS imports_t,
    SUM(CASE
        WHEN element_code = 5910 THEN value
        WHEN element_code = 5610 THEN -value
        ELSE 0
    END) AS net_trade_t
FROM raw_trade
WHERE item = 'Coffee, green'
  AND unit = 't'
  AND element_code IN (5610, 5910)
  AND year BETWEEN @latest_year - 9 AND @latest_year
  AND REPLACE(area_code_m49, CHAR(39), '') IN (
    SELECT LPAD(CAST(code AS CHAR), 3, '0')
    FROM europe_m49
)
GROUP BY area, year
ORDER BY area, year;

