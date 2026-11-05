
-- SERENA: WORLD COFFEE TRADE RANKING
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

-- 2. Calculate worldwide net trade by country
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
      -- Exclude known geographic aggregations
      AND area_code < 5000
      AND area_code NOT IN (265, 351)
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

-- 3. Top 5 net exporters
SELECT
    'Exporter' AS category,
    export_rank AS position,
    area,
    ROUND(net_trade_t, 2) AS net_trade_t
FROM ranked
WHERE export_rank <= 5
  AND net_trade_t > 0

UNION ALL

-- 4. Top 5 net importers
SELECT
    'Importer' AS category,
    import_rank AS position,
    area,
    ROUND(net_trade_t, 2) AS net_trade_t
FROM ranked
WHERE import_rank <= 5
  AND net_trade_t < 0

ORDER BY category, position;