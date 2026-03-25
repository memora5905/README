-- ============================================================
-- Bike Sales Analysis — Mauricio Morales
-- Dataset: AdventureWorks-style sales data (2017)
-- Tools: SQLite
-- ============================================================

-- ============================================================
-- 1. DATABASE SETUP
-- ============================================================

CREATE TABLE IF NOT EXISTS sales (
    order_id       TEXT PRIMARY KEY,
    item_cost      REAL,
    item_price     REAL,
    order_date     TEXT,
    ship_date      TEXT,
    days_to_ship   INTEGER,
    customer_name  TEXT,
    city           TEXT,
    state_province TEXT,
    country        TEXT,
    sub_category   TEXT,
    product_name   TEXT,
    color          TEXT,
    model          TEXT,
    order_qty      INTEGER,
    revenue        REAL,
    net_revenue    REAL,
    margin_pct     REAL
);

-- ============================================================
-- 2. BASIC EXPLORATION
-- ============================================================

-- Total number of orders
SELECT COUNT(*) AS total_orders
FROM sales;

-- Date range of the dataset
SELECT 
    MIN(order_date) AS earliest_order,
    MAX(order_date) AS latest_order
FROM sales;

-- Distinct countries in the dataset
SELECT DISTINCT country
FROM sales
ORDER BY country;

-- ============================================================
-- 3. REVENUE ANALYSIS BY COUNTRY
-- ============================================================

SELECT
    country,
    COUNT(*)                          AS total_orders,
    SUM(order_qty)                    AS total_units,
    ROUND(SUM(revenue), 2)            AS total_revenue,
    ROUND(SUM(net_revenue), 2)        AS total_net_revenue,
    ROUND(AVG(revenue), 2)            AS avg_order_value,
    ROUND(SUM(revenue) * 100.0 /
        (SELECT SUM(revenue) FROM sales), 2) AS revenue_share_pct
FROM sales
GROUP BY country
ORDER BY total_revenue DESC;

-- ============================================================
-- 4. REVENUE ANALYSIS BY PRODUCT MODEL
-- ============================================================

SELECT
    model,
    COUNT(*)                          AS total_orders,
    SUM(order_qty)                    AS total_units,
    ROUND(SUM(revenue), 2)            AS total_revenue,
    ROUND(SUM(net_revenue), 2)        AS total_net_revenue,
    ROUND(AVG(margin_pct) * 100, 2)   AS avg_margin_pct
FROM sales
GROUP BY model
ORDER BY total_revenue DESC;

-- ============================================================
-- 5. SHIPPING PERFORMANCE
-- ============================================================

-- Overall shipping stats
SELECT
    ROUND(AVG(days_to_ship), 1)  AS avg_days_to_ship,
    MIN(days_to_ship)            AS fastest_shipment,
    MAX(days_to_ship)            AS slowest_shipment
FROM sales;

-- Shipping performance by country
SELECT
    country,
    ROUND(AVG(days_to_ship), 1) AS avg_days_to_ship,
    MIN(days_to_ship)           AS fastest,
    MAX(days_to_ship)           AS slowest
FROM sales
GROUP BY country
ORDER BY avg_days_to_ship ASC;

-- Orders that shipped in 3 days or less (fast fulfillment)
SELECT
    order_id,
    customer_name,
    country,
    order_date,
    ship_date,
    days_to_ship
FROM sales
WHERE days_to_ship <= 3
ORDER BY days_to_ship ASC;

-- ============================================================
-- 6. MARGIN ANALYSIS
-- ============================================================

-- Overall margin stats
SELECT
    ROUND(AVG(margin_pct) * 100, 2) AS avg_margin_pct,
    ROUND(MIN(margin_pct) * 100, 2) AS min_margin_pct,
    ROUND(MAX(margin_pct) * 100, 2) AS max_margin_pct
FROM sales;

-- Margin by product model
SELECT
    model,
    ROUND(AVG(margin_pct) * 100, 2) AS avg_margin_pct,
    ROUND(SUM(net_revenue), 2)      AS total_profit
FROM sales
GROUP BY model
ORDER BY avg_margin_pct DESC;

-- ============================================================
-- 7. TOP CUSTOMERS BY REVENUE
-- ============================================================

SELECT
    customer_name,
    country,
    COUNT(*)                   AS orders,
    SUM(order_qty)             AS total_units,
    ROUND(SUM(revenue), 2)     AS total_revenue
FROM sales
GROUP BY customer_name, country
ORDER BY total_revenue DESC
LIMIT 10;

-- ============================================================
-- 8. MONTHLY SALES TREND
-- ============================================================

SELECT
    SUBSTR(order_date, 1, 7)      AS year_month,
    COUNT(*)                      AS total_orders,
    SUM(order_qty)                AS total_units,
    ROUND(SUM(revenue), 2)        AS total_revenue,
    ROUND(SUM(net_revenue), 2)    AS total_profit
FROM sales
GROUP BY year_month
ORDER BY year_month ASC;

-- ============================================================
-- 9. WINDOW FUNCTIONS — Running Totals & Rankings
-- ============================================================

-- Running revenue total by order date
SELECT
    order_date,
    order_id,
    revenue,
    ROUND(SUM(revenue) OVER (ORDER BY order_date, order_id), 2) AS running_total_revenue
FROM sales
ORDER BY order_date, order_id;

-- Rank countries by total revenue
SELECT
    country,
    ROUND(SUM(revenue), 2) AS total_revenue,
    RANK() OVER (ORDER BY SUM(revenue) DESC) AS revenue_rank
FROM sales
GROUP BY country;

-- Each order's revenue vs country average
SELECT
    order_id,
    customer_name,
    country,
    revenue,
    ROUND(AVG(revenue) OVER (PARTITION BY country), 2) AS country_avg_revenue,
    ROUND(revenue - AVG(revenue) OVER (PARTITION BY country), 2) AS diff_from_country_avg
FROM sales
ORDER BY country, diff_from_country_avg DESC;

-- ============================================================
-- 10. SUBQUERY — Countries above average revenue
-- ============================================================

SELECT
    country,
    ROUND(SUM(revenue), 2) AS total_revenue
FROM sales
GROUP BY country
HAVING SUM(revenue) > (
    SELECT AVG(country_total)
    FROM (
        SELECT SUM(revenue) AS country_total
        FROM sales
        GROUP BY country
    )
)
ORDER BY total_revenue DESC;
