-- ============================================================
-- Auto Loan Portfolio Analysis — Mauricio Morales
-- Dataset: 400 simulated loan applications (2022-2024)
-- Tables: applications, loan_performance
-- Tools: SQLite
-- ============================================================
-- Context: Mirrors the type of analysis performed by a credit
-- analyst reviewing an auto loan portfolio — approval patterns,
-- risk segmentation, default rates, and portfolio health.
-- ============================================================


-- ============================================================
-- SECTION 1: PORTFOLIO OVERVIEW
-- ============================================================

-- Total applications and overall approval rate
SELECT
    COUNT(*)                                                     AS total_applications,
    SUM(CASE WHEN decision = 'Approved' THEN 1 ELSE 0 END)      AS approved,
    SUM(CASE WHEN decision = 'Declined' THEN 1 ELSE 0 END)      AS declined,
    ROUND(AVG(CASE WHEN decision = 'Approved' THEN 1.0 ELSE 0 END) * 100, 1) AS approval_rate_pct
FROM applications;


-- Average applicant profile
SELECT
    ROUND(AVG(credit_score), 0)     AS avg_credit_score,
    ROUND(AVG(annual_income), 0)    AS avg_annual_income,
    ROUND(AVG(loan_amount), 2)      AS avg_loan_amount,
    ROUND(AVG(ltv_ratio), 3)        AS avg_ltv,
    ROUND(AVG(dti_ratio), 3)        AS avg_dti,
    ROUND(AVG(interest_rate), 2)    AS avg_interest_rate
FROM applications
WHERE decision = 'Approved';


-- ============================================================
-- SECTION 2: APPROVAL RATE BY CREDIT TIER
-- ============================================================

SELECT
    credit_tier,
    COUNT(*)                                                              AS total_apps,
    SUM(CASE WHEN decision = 'Approved' THEN 1 ELSE 0 END)               AS approved,
    SUM(CASE WHEN decision = 'Declined' THEN 1 ELSE 0 END)               AS declined,
    ROUND(AVG(CASE WHEN decision = 'Approved' THEN 1.0 ELSE 0 END)*100, 1) AS approval_rate_pct,
    ROUND(AVG(credit_score), 0)                                           AS avg_score,
    ROUND(AVG(interest_rate), 2)                                          AS avg_rate_pct
FROM applications
GROUP BY credit_tier
ORDER BY avg_score DESC;


-- ============================================================
-- SECTION 3: RISK ANALYSIS — LTV AND DTI
-- ============================================================

-- Average LTV and DTI by credit tier (risk exposure)
SELECT
    credit_tier,
    ROUND(AVG(ltv_ratio), 3)        AS avg_ltv,
    ROUND(MAX(ltv_ratio), 3)        AS max_ltv,
    ROUND(AVG(dti_ratio), 3)        AS avg_dti,
    ROUND(MAX(dti_ratio), 3)        AS max_dti,
    COUNT(*)                        AS approved_loans
FROM applications
WHERE decision = 'Approved'
GROUP BY credit_tier
ORDER BY AVG(credit_score) DESC;


-- High-risk applications: LTV > 1.10 AND DTI > 0.40
SELECT
    application_id,
    credit_tier,
    credit_score,
    ROUND(ltv_ratio, 3)     AS ltv,
    ROUND(dti_ratio, 3)     AS dti,
    loan_amount,
    decision
FROM applications
WHERE ltv_ratio > 1.10 AND dti_ratio > 0.40
ORDER BY ltv_ratio DESC;


-- ============================================================
-- SECTION 4: DEFAULT RATE ANALYSIS
-- ============================================================

-- Default rate by credit tier
SELECT
    a.credit_tier,
    COUNT(l.loan_id)                                                          AS funded_loans,
    SUM(CASE WHEN l.status = 'Default' THEN 1 ELSE 0 END)                    AS defaults,
    ROUND(AVG(CASE WHEN l.status = 'Default' THEN 1.0 ELSE 0 END) * 100, 1) AS default_rate_pct,
    ROUND(AVG(a.credit_score), 0)                                             AS avg_score,
    ROUND(AVG(a.interest_rate), 2)                                            AS avg_rate
FROM applications a
JOIN loan_performance l ON a.application_id = l.application_id
GROUP BY a.credit_tier
ORDER BY AVG(a.credit_score) DESC;


-- Default rate by LTV bucket
SELECT
    CASE
        WHEN ltv_ratio < 0.80 THEN 'Under 80%'
        WHEN ltv_ratio < 0.90 THEN '80-89%'
        WHEN ltv_ratio < 1.00 THEN '90-99%'
        WHEN ltv_ratio < 1.10 THEN '100-109%'
        ELSE '110%+'
    END AS ltv_bucket,
    COUNT(l.loan_id) AS loans,
    SUM(CASE WHEN l.status = 'Default' THEN 1 ELSE 0 END) AS defaults,
    ROUND(AVG(CASE WHEN l.status = 'Default' THEN 1.0 ELSE 0 END) * 100, 1) AS default_rate_pct
FROM applications a
JOIN loan_performance l ON a.application_id = l.application_id
GROUP BY ltv_bucket
ORDER BY MIN(a.ltv_ratio);


-- ============================================================
-- SECTION 5: PORTFOLIO HEALTH — DELINQUENCY SNAPSHOT
-- ============================================================

-- Current portfolio status breakdown
SELECT
    status,
    COUNT(*)                                          AS loan_count,
    ROUND(SUM(remaining_balance), 2)                  AS total_exposure,
    ROUND(AVG(remaining_balance), 2)                  AS avg_balance,
    ROUND(COUNT(*) * 100.0 /
        (SELECT COUNT(*) FROM loan_performance), 1)   AS pct_of_portfolio
FROM loan_performance
GROUP BY status
ORDER BY loan_count DESC;


-- Delinquent loans (30+ days past due or default) with full applicant profile
SELECT
    l.loan_id,
    l.status,
    l.days_past_due,
    l.remaining_balance,
    a.credit_tier,
    a.credit_score,
    a.loan_amount,
    ROUND(a.ltv_ratio, 3)   AS ltv,
    ROUND(a.dti_ratio, 3)   AS dti,
    a.state
FROM loan_performance l
JOIN applications a ON l.application_id = a.application_id
WHERE l.days_past_due >= 30 OR l.status = 'Default'
ORDER BY l.days_past_due DESC;


-- ============================================================
-- SECTION 6: INTEREST RATE ANALYSIS
-- ============================================================

-- Revenue potential — projected total interest income by tier
SELECT
    a.credit_tier,
    COUNT(l.loan_id)                                            AS loans,
    ROUND(SUM(l.monthly_payment * a.term_months - a.loan_amount), 2) AS projected_interest_income,
    ROUND(AVG(a.interest_rate), 2)                              AS avg_rate_pct
FROM applications a
JOIN loan_performance l ON a.application_id = l.application_id
GROUP BY a.credit_tier
ORDER BY AVG(a.credit_score) DESC;


-- ============================================================
-- SECTION 7: GEOGRAPHIC DISTRIBUTION
-- ============================================================

SELECT
    state,
    COUNT(*)                                               AS total_apps,
    SUM(CASE WHEN decision = 'Approved' THEN 1 ELSE 0 END) AS approved,
    ROUND(AVG(credit_score), 0)                            AS avg_score,
    ROUND(SUM(CASE WHEN decision='Approved' THEN loan_amount ELSE 0 END), 2) AS total_funded
FROM applications
GROUP BY state
ORDER BY total_funded DESC;


-- ============================================================
-- SECTION 8: WINDOW FUNCTIONS — PORTFOLIO RANKING
-- ============================================================

-- Rank each approved loan by loan amount within its credit tier
SELECT
    a.application_id,
    a.credit_tier,
    a.loan_amount,
    a.credit_score,
    RANK() OVER (PARTITION BY a.credit_tier ORDER BY a.loan_amount DESC) AS rank_in_tier,
    ROUND(AVG(a.loan_amount) OVER (PARTITION BY a.credit_tier), 2)       AS tier_avg_loan
FROM applications a
WHERE a.decision = 'Approved'
ORDER BY a.credit_tier, rank_in_tier;


-- Running total of funded loan amounts over time
SELECT
    funded_date,
    loan_id,
    ROUND(a.loan_amount, 2) AS loan_amount,
    ROUND(SUM(a.loan_amount) OVER (ORDER BY l.funded_date, l.loan_id), 2) AS running_portfolio_total
FROM loan_performance l
JOIN applications a ON l.application_id = a.application_id
ORDER BY l.funded_date;


-- ============================================================
-- SECTION 9: SUBQUERY — ABOVE-AVERAGE RISK LOANS
-- ============================================================

-- Funded loans with LTV above the portfolio average
SELECT
    l.loan_id,
    a.credit_tier,
    a.credit_score,
    ROUND(a.ltv_ratio, 3)               AS ltv,
    ROUND(a.loan_amount, 2)             AS loan_amount,
    l.status
FROM loan_performance l
JOIN applications a ON l.application_id = a.application_id
WHERE a.ltv_ratio > (
    SELECT AVG(ltv_ratio)
    FROM applications
    WHERE decision = 'Approved'
)
ORDER BY a.ltv_ratio DESC;


-- ============================================================
-- SECTION 10: CREDIT SCORE DISTRIBUTION BUCKET ANALYSIS
-- ============================================================

SELECT
    CASE
        WHEN credit_score >= 750 THEN '750-850 (Super Prime)'
        WHEN credit_score >= 680 THEN '680-749 (Prime)'
        WHEN credit_score >= 620 THEN '620-679 (Near Prime)'
        WHEN credit_score >= 550 THEN '550-619 (Subprime)'
        ELSE '400-549 (Deep Subprime)'
    END AS score_bucket,
    COUNT(*)                                                              AS total,
    SUM(CASE WHEN decision = 'Approved' THEN 1 ELSE 0 END)               AS approved,
    ROUND(AVG(CASE WHEN decision='Approved' THEN 1.0 ELSE 0 END)*100,1)  AS approval_pct,
    ROUND(AVG(interest_rate), 2)                                          AS avg_rate
FROM applications
GROUP BY score_bucket
ORDER BY MIN(credit_score) DESC;
