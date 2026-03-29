"""
Credit Analysis Engine
Mauricio Morales — Portfolio Project

Simulates an auto lender's credit decision process:
- Tier classification
- DTI calculation
- LTV assessment
- Rate calculation
- Approve / Counter / Decline decision
- Credit memo generation
"""

from datetime import date

# ── LENDER POLICY CONSTANTS ──────────────────────────────────────────────────

CREDIT_TIERS = [
    {"name": "Super Prime",   "min": 720, "max": 850, "base_premium": 0.0,  "max_dti": 0.50, "max_ltv": 1.20},
    {"name": "Prime",         "min": 680, "max": 719, "base_premium": 0.02, "max_dti": 0.48, "max_ltv": 1.20},
    {"name": "Near Prime",    "min": 620, "max": 679, "base_premium": 0.06, "max_dti": 0.43, "max_ltv": 1.15},
    {"name": "Subprime",      "min": 550, "max": 619, "base_premium": 0.12, "max_dti": 0.38, "max_ltv": 1.10},
    {"name": "Deep Subprime", "min": 300, "max": 549, "base_premium": 0.19, "max_dti": 0.33, "max_ltv": 1.05},
]

BASE_RATE          = 0.055   # Fed/Prime base (5.5%)
INCOME_RATIO_MAX   = 0.15    # Max car payment as % of gross monthly income
HARD_DECLINE_SCORE = 500     # Below this = automatic decline

# Term length risk premiums
TERM_PREMIUMS = {36: 0.0, 48: 0.0025, 60: 0.005, 72: 0.0075, 84: 0.01}

# LTV risk premiums
def ltv_premium(ltv):
    if ltv <= 1.00: return 0.0
    if ltv <= 1.10: return 0.005
    if ltv <= 1.20: return 0.0075
    return 0.015

# Vehicle age premiums (older = higher rate)
def vehicle_age_premium(vehicle_year):
    age = date.today().year - vehicle_year
    if age <= 2:  return 0.0
    if age <= 4:  return 0.005
    if age <= 6:  return 0.01
    if age <= 8:  return 0.015
    return 0.025


# ── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def get_tier(credit_score):
    for tier in CREDIT_TIERS:
        if tier["min"] <= credit_score <= tier["max"]:
            return tier
    return None

def monthly_payment(principal, annual_rate, term_months):
    if annual_rate == 0:
        return principal / term_months
    r = annual_rate / 12
    return principal * r / (1 - (1 + r) ** -term_months)

def max_loan_from_income(gross_monthly_income, annual_rate, term_months):
    max_pmt = gross_monthly_income * INCOME_RATIO_MAX
    if annual_rate == 0:
        return max_pmt * term_months
    r = annual_rate / 12
    return max_pmt * (1 - (1 + r) ** -term_months) / r


# ── CORE DECISION ENGINE ─────────────────────────────────────────────────────

def analyze_application(
    applicant_name,
    credit_score,
    annual_income,
    existing_monthly_debt,
    loan_amount_requested,
    vehicle_value,
    vehicle_year,
    term_months=60,
):
    """
    Run a full credit analysis and return a decision dict + memo.
    """

    result = {
        "applicant": applicant_name,
        "date": str(date.today()),
        "inputs": {
            "credit_score": credit_score,
            "annual_income": annual_income,
            "gross_monthly_income": round(annual_income / 12, 2),
            "existing_monthly_debt": existing_monthly_debt,
            "loan_requested": loan_amount_requested,
            "vehicle_value": vehicle_value,
            "vehicle_year": vehicle_year,
            "term_months": term_months,
        },
        "flags": [],
        "decision": None,
        "approved_amount": None,
        "rate": None,
        "monthly_payment": None,
        "counter": None,
    }

    gross_monthly = annual_income / 12

    # ── Step 1: Hard decline check
    if credit_score < HARD_DECLINE_SCORE:
        result["decision"] = "DECLINE"
        result["decline_reason"] = f"Credit score {credit_score} below minimum threshold of {HARD_DECLINE_SCORE}"
        result["flags"].append("HARD DECLINE — Score below minimum")
        return result

    # ── Step 2: Get credit tier
    tier = get_tier(credit_score)
    if not tier:
        result["decision"] = "DECLINE"
        result["decline_reason"] = "Unable to classify credit score"
        return result

    result["credit_tier"] = tier["name"]

    # ── Step 3: Calculate rate
    raw_rate = (
        BASE_RATE
        + tier["base_premium"]
        + TERM_PREMIUMS.get(term_months, 0.01)
        + ltv_premium(loan_amount_requested / vehicle_value)
        + vehicle_age_premium(vehicle_year)
    )
    result["rate"] = round(raw_rate, 4)

    # ── Step 4: LTV check
    ltv = loan_amount_requested / vehicle_value
    result["ltv"] = round(ltv, 3)

    if ltv > tier["max_ltv"]:
        result["flags"].append(
            f"LTV {ltv:.1%} exceeds {tier['name']} max of {tier['max_ltv']:.0%}"
        )

    # ── Step 5: DTI check
    proposed_payment = monthly_payment(loan_amount_requested, raw_rate, term_months)
    back_end_dti = (existing_monthly_debt + proposed_payment) / gross_monthly
    result["back_end_dti"] = round(back_end_dti, 3)
    result["proposed_payment"] = round(proposed_payment, 2)

    if back_end_dti > tier["max_dti"]:
        result["flags"].append(
            f"DTI {back_end_dti:.1%} exceeds {tier['name']} max of {tier['max_dti']:.0%}"
        )

    # ── Step 6: Income-based max loan
    max_loan_income = max_loan_from_income(gross_monthly, raw_rate, term_months)
    result["max_loan_by_income"] = round(max_loan_income, 2)

    if loan_amount_requested > max_loan_income:
        result["flags"].append(
            f"Requested loan ${loan_amount_requested:,.0f} exceeds income-based max ${max_loan_income:,.0f}"
        )

    # ── Step 7: Final decision
    hard_fails = [f for f in result["flags"] if "exceeds" in f or "HARD" in f]

    if not result["flags"]:
        result["decision"] = "APPROVE"
        result["approved_amount"] = loan_amount_requested
        result["monthly_payment"] = round(proposed_payment, 2)

    elif len(hard_fails) == 0 or (len(hard_fails) == 1 and "LTV" in hard_fails[0]):
        # Soft conditions — counter with adjusted terms
        result["decision"] = "CONDITIONAL APPROVE"

        # Calculate max approvable loan
        max_by_dti_payment = (tier["max_dti"] * gross_monthly - existing_monthly_debt)
        r = raw_rate / 12
        if max_by_dti_payment > 0 and r > 0:
            max_by_dti = max_by_dti_payment * (1 - (1 + r)**-term_months) / r
        else:
            max_by_dti = loan_amount_requested

        max_by_ltv = vehicle_value * tier["max_ltv"]
        counter_amount = round(min(max_by_dti, max_by_ltv, max_loan_income), 2)

        if counter_amount < loan_amount_requested * 0.80:
            result["decision"] = "DECLINE"
            result["decline_reason"] = "Counter amount too far below requested — not viable"
        else:
            counter_payment = monthly_payment(counter_amount, raw_rate, term_months)
            result["counter"] = {
                "approved_amount": counter_amount,
                "monthly_payment": round(counter_payment, 2),
                "difference": round(loan_amount_requested - counter_amount, 2),
            }
            result["approved_amount"] = counter_amount
            result["monthly_payment"] = round(counter_payment, 2)

    else:
        result["decision"] = "DECLINE"
        result["decline_reason"] = "; ".join(hard_fails)

    return result


# ── CREDIT MEMO GENERATOR ────────────────────────────────────────────────────

def print_credit_memo(r):
    line = "=" * 65
    print(f"\n{line}")
    print(f"  AUTO LOAN CREDIT ANALYSIS MEMO")
    print(f"  Date: {r['date']}")
    print(f"{line}")

    inp = r["inputs"]
    print(f"\n  APPLICANT:        {r['applicant']}")
    print(f"  Credit Score:     {inp['credit_score']}  ({r.get('credit_tier','N/A')})")
    print(f"  Annual Income:    ${inp['annual_income']:,.0f}  (${inp['gross_monthly_income']:,.0f}/mo)")
    print(f"  Existing Debt:    ${inp['existing_monthly_debt']:,.0f}/mo")

    print(f"\n  VEHICLE & LOAN REQUEST")
    print(f"  Vehicle Year:     {inp['vehicle_year']}")
    print(f"  Vehicle Value:    ${inp['vehicle_value']:,.0f}")
    print(f"  Loan Requested:   ${inp['loan_requested']:,.0f}")
    print(f"  Term:             {inp['term_months']} months")

    print(f"\n  ANALYSIS")
    print(f"  LTV Ratio:        {r.get('ltv', 'N/A'):.1%}" if r.get('ltv') else "  LTV Ratio:        N/A")
    print(f"  Back-End DTI:     {r.get('back_end_dti', 'N/A'):.1%}" if r.get('back_end_dti') else "  Back-End DTI:     N/A")
    print(f"  Proposed Rate:    {r.get('rate', 0)*100:.2f}% APR" if r.get('rate') else "  Proposed Rate:    N/A")
    print(f"  Proposed Payment: ${r.get('proposed_payment', 0):,.2f}/mo" if r.get('proposed_payment') else "")
    max_loan_str = f"${r['max_loan_by_income']:,.0f}" if r.get('max_loan_by_income') else 'N/A'
    print(f"  Max Loan (Income): {max_loan_str}")

    if r["flags"]:
        print(f"\n  ⚠️  CONDITIONS / FLAGS")
        for flag in r["flags"]:
            print(f"     • {flag}")

    dec = r["decision"]
    symbol = "✅" if "APPROVE" in dec and "CONDITIONAL" not in dec else "⚡" if "CONDITIONAL" in dec else "❌"
    print(f"\n  {symbol} DECISION: {dec}")

    if r.get("counter"):
        c = r["counter"]
        print(f"\n  COUNTER OFFER")
        print(f"  Approved Amount:  ${c['approved_amount']:,.0f}  (${c['difference']:,.0f} less than requested)")
        print(f"  Monthly Payment:  ${c['monthly_payment']:,.2f}/mo")

    elif r.get("approved_amount") and "APPROVE" in dec:
        print(f"  Approved Amount:  ${r['approved_amount']:,.0f}")
        print(f"  Monthly Payment:  ${r['monthly_payment']:,.2f}/mo")

    if r.get("decline_reason"):
        print(f"  Decline Reason:   {r['decline_reason']}")

    print(f"\n{line}\n")


# ── RUN SAMPLE SCENARIOS ─────────────────────────────────────────────────────

if __name__ == "__main__":

    scenarios = [
        # Clean approval
        {
            "applicant_name": "Maria Gonzalez",
            "credit_score": 745,
            "annual_income": 72000,
            "existing_monthly_debt": 450,
            "loan_amount_requested": 28000,
            "vehicle_value": 30000,
            "vehicle_year": 2023,
            "term_months": 60,
        },
        # Conditional — DTI too high, counter offered
        {
            "applicant_name": "James Walker",
            "credit_score": 645,
            "annual_income": 48000,
            "existing_monthly_debt": 800,
            "loan_amount_requested": 32000,
            "vehicle_value": 30000,
            "vehicle_year": 2021,
            "term_months": 72,
        },
        # Decline — score too low
        {
            "applicant_name": "Tyler Brooks",
            "credit_score": 480,
            "annual_income": 38000,
            "existing_monthly_debt": 600,
            "loan_amount_requested": 22000,
            "vehicle_value": 20000,
            "vehicle_year": 2019,
            "term_months": 60,
        },
        # Near prime with high LTV — counter
        {
            "applicant_name": "Angela Reyes",
            "credit_score": 635,
            "annual_income": 55000,
            "existing_monthly_debt": 350,
            "loan_amount_requested": 26000,
            "vehicle_value": 21000,
            "vehicle_year": 2020,
            "term_months": 60,
        },
    ]

    for s in scenarios:
        result = analyze_application(**s)
        print_credit_memo(result)


# ── MANUAL REVIEW ENGINE ─────────────────────────────────────────────────────

def manual_review(
    applicant_name,
    credit_score,
    annual_income,
    existing_monthly_debt,
    loan_amount_requested,
    vehicle_value,
    vehicle_year,
    term_months=60,
    # Manual review context factors
    months_at_job=None,
    previous_repo=False,
    savings_balance=None,
    income_type="W2",          # W2 / Self-Employed / Contract
    explanation_letter=False,  # Did applicant provide explanation for derogatory marks?
    co_applicant_score=None,
):
    """
    Manual review tier — for borderline applications the algorithm flags
    but can't definitively approve or decline.
    Returns a recommendation with analyst notes.
    """
    base = analyze_application(
        applicant_name, credit_score, annual_income, existing_monthly_debt,
        loan_amount_requested, vehicle_value, vehicle_year, term_months
    )

    if base["decision"] == "APPROVE":
        return base  # Clean file — no manual needed

    gross_monthly = annual_income / 12
    tier = base.get("credit_tier", "Unknown")
    ltv = loan_amount_requested / vehicle_value
    proposed_pmt = base.get("proposed_payment", 0)
    dti = base.get("back_end_dti", 0)

    strengths = []
    concerns = []
    recommendation = None

    # ── Evaluate strengths
    if credit_score >= 600:
        strengths.append(f"Score {credit_score} is within workable range for manual")
    if months_at_job and months_at_job >= 24:
        strengths.append(f"Stable employment: {months_at_job} months at current job")
    elif months_at_job and months_at_job >= 12:
        strengths.append(f"Employment: {months_at_job} months — adequate but borderline")
    if savings_balance and savings_balance >= loan_amount_requested * 0.20:
        strengths.append(f"Savings of ${savings_balance:,.0f} shows financial reserves")
    if explanation_letter:
        strengths.append("Applicant provided explanation letter for derogatory marks")
    if co_applicant_score and co_applicant_score >= 680:
        strengths.append(f"Co-applicant score {co_applicant_score} significantly strengthens file")
    if income_type == "W2":
        strengths.append("W2 income — verifiable and stable")
    if ltv <= 1.10:
        strengths.append(f"LTV {ltv:.1%} is manageable")

    # ── Evaluate concerns
    if credit_score < 570:
        concerns.append(f"Score {credit_score} is low — limited lender options")
    if previous_repo:
        concerns.append("Previous repossession on file — major negative factor")
    if dti and dti > 0.50:
        concerns.append(f"DTI {dti:.1%} is significantly elevated")
    elif dti and dti > 0.43:
        concerns.append(f"DTI {dti:.1%} is borderline — tight but potentially workable")
    if income_type == "Self-Employed":
        concerns.append("Self-employed income — requires 2 years tax returns for verification")
    if months_at_job and months_at_job < 6:
        concerns.append(f"New employment: only {months_at_job} months — high instability risk")
    if ltv > 1.20:
        concerns.append(f"LTV {ltv:.1%} is high — significant collateral risk")

    # ── Build recommendation
    score_card = len(strengths) - len(concerns) * 1.5  # concerns weigh more

    if previous_repo:
        recommendation = "DECLINE — Prior repo is disqualifying for most lenders"
    elif credit_score < 540:
        recommendation = "DECLINE — Score too low for manual override"
    elif score_card >= 2 and not previous_repo:
        recommendation = "APPROVE WITH CONDITIONS — Strengths outweigh concerns"
    elif score_card >= 0:
        recommendation = "COUNTER OFFER — Reduce loan amount to lower payment and LTV"
    else:
        recommendation = "DECLINE — Too many unresolved risk factors"

    line = "=" * 65
    print(f"\n{line}")
    print(f"  MANUAL REVIEW MEMO — ANALYST DECISION REQUIRED")
    print(f"  Date: {base['date']}")
    print(f"{line}")
    print(f"\n  APPLICANT:     {applicant_name}")
    print(f"  Credit Score:  {credit_score}  ({tier})")
    print(f"  Income:        ${annual_income:,.0f}/yr  (${gross_monthly:,.0f}/mo) [{income_type}]")
    print(f"  Loan Request:  ${loan_amount_requested:,.0f}  |  Vehicle: ${vehicle_value:,.0f}  |  LTV: {ltv:.1%}")
    print(f"  Term:          {term_months}mo  |  Rate:  {base.get('rate', 0)*100:.2f}% APR  |  Payment: ${proposed_pmt:,.2f}/mo")
    print(f"  Back-End DTI:  {dti:.1%}" if dti else "")

    print(f"\n  ✅ STRENGTHS ({len(strengths)})")
    for s in strengths:
        print(f"     + {s}")

    print(f"\n  ⚠️  CONCERNS ({len(concerns)})")
    for c in concerns:
        print(f"     - {c}")

    print(f"\n  📋 ANALYST CHECKLIST")
    checklist = [
        ("Pay stubs / VOE verified",        True),
        ("Bank statements reviewed",         savings_balance is not None),
        ("Previous repo confirmed",          previous_repo),
        ("Explanation letter received",      explanation_letter),
        ("Co-applicant evaluated",           co_applicant_score is not None),
        ("Employment history verified",      months_at_job is not None),
    ]
    for item, done in checklist:
        mark = "☑" if done else "☐"
        print(f"     {mark} {item}")

    print(f"\n  🏦 ANALYST RECOMMENDATION: {recommendation}")
    print(f"\n{line}\n")


    # ── Manual Review Scenarios
    print("\n\n" + "="*65)
    print("  MANUAL REVIEW SCENARIOS")
    print("="*65)

    # Borderline subprime — strengths outweigh concerns
    manual_review(
        applicant_name="David Chen",
        credit_score=588, annual_income=62000, existing_monthly_debt=620,
        loan_amount_requested=24000, vehicle_value=22000, vehicle_year=2020,
        term_months=60, months_at_job=18, previous_repo=False,
        savings_balance=4500, income_type="W2", explanation_letter=True,
    )

    # Prior repossession — automatic decline regardless of other factors
    manual_review(
        applicant_name="Marcus Thompson",
        credit_score=575, annual_income=44000, existing_monthly_debt=480,
        loan_amount_requested=18000, vehicle_value=17000, vehicle_year=2019,
        term_months=60, months_at_job=8, previous_repo=True,
        savings_balance=800, income_type="W2", explanation_letter=False,
    )

    # Self-employed with strong co-applicant and savings
    manual_review(
        applicant_name="Sofia Mendez",
        credit_score=612, annual_income=88000, existing_monthly_debt=750,
        loan_amount_requested=35000, vehicle_value=33000, vehicle_year=2022,
        term_months=72, months_at_job=36, previous_repo=False,
        savings_balance=22000, income_type="Self-Employed",
        explanation_letter=True, co_applicant_score=705,
    )
