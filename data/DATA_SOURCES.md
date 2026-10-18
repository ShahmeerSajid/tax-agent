# Data Sources

Every website we have actually extracted tax information from. Nothing planned or hypothetical is listed here.

**How the data got in:** values were read from these pages by hand and saved in `data/tax_rules_2026.json` and `data/tax_parameters_2026.json`. No scraper or ingestion agent runs yet.

**Maintenance rules**
- Add an entry the moment a new page is used for extraction. Update the entry when its URL, purpose or code usage changes.
- One entry per URL. If a page serves several purposes, extend its entry instead of adding a second one.

---

## 1. CRA: Canadian income tax rates (current year)

- **URL:** https://www.canada.ca/en/revenue-agency/services/tax/individuals/frequently-asked-questions-individuals/canadian-income-tax-rates-individuals-current-previous-years/current-year.html
- **Purpose:** Federal brackets and rates, and the brackets and rates of every province and territory except Quebec. This is the base of every tax calculation.
- **Stored in:** `data/tax_rules_2026.json` (federal, NL, PE, NS, NB, ON, MB, SK, AB, BC, YT, NT, NU), then the database tables `jurisdictions` and `brackets`.
- **Code usage:**
  - `backend/load_data.py`: `load()` copies the JSON into Neon.
  - `backend/rules_db.py`: `load_rules_from_db()` reads it back.
  - `backend/calculator.py`: `bracket_tax()`, `calculate_tax()`.
  - `backend/core_tax.py`: all functions (tax, breakdown, rates, what-ifs, province comparison).
  - `backend/capital_gains.py`, `backend/payroll.py` (`self_employment_tax`), `backend/scenarios.py`, `backend/tax_years.py`: call `calculate_tax()`.
  - `backend/tools.py`: most tools, for example `calculate_income_tax`.

## 2. Revenu Québec: Income tax rates

- **URL:** https://www.revenuquebec.ca/en/citizens/income-tax-return/completing-your-income-tax-return/income-tax-rates/
- **Purpose:** Quebec's own provincial brackets and rates, because Quebec runs a separate tax system.
- **Stored in:** `data/tax_rules_2026.json` (QC), then the database tables `jurisdictions` and `brackets`.
- **Code usage:** same as source 1 whenever the province is `QC`.

## 3. CRA: MP, DB, RRSP, DPSP, ALDA, TFSA limits, YMPE and the YAMPE

- **URL:** https://www.canada.ca/en/revenue-agency/services/tax/registered-plans-administrators/pspa/mp-rrsp-dpsp-tfsa-limits-ympe.html
- **Purpose:** RRSP dollar limits (2024 to 2027) and TFSA annual limits (2009 to 2026). It also confirms the 2026 CPP ceilings (YMPE and YAMPE).
- **Stored in:** `data/tax_parameters_2026.json` under `rrsp.dollar_limit_by_year` and `tfsa.annual_limit_by_year`.
- **Code usage:**
  - `backend/savings_accounts.py`: `rrsp_deduction_limit()`, `tfsa_contribution_room()`.
  - `backend/reference.py`: `verified_parameters()`, `verify_source()`.
  - `backend/tools.py`: `get_verified_tax_parameters`, `calculate_rrsp_deduction_limit`, `calculate_tfsa_contribution_room`.

## 4. CRA: How contributions affect your RRSP deduction limit

- **URL:** https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/rrsps-related-plans/contributing-a-rrsp-prpp/contributions-affect-your-rrsp-prpp-deduction-limit.html
- **Purpose:** The RRSP deduction limit formula: carry-forward room, plus the lesser of 18% of last year's earned income and the annual limit, adjusted for pension amounts.
- **Stored in:** `data/tax_parameters_2026.json` under `rrsp.earned_income_rate`.
- **Code usage:**
  - `backend/savings_accounts.py`: `rrsp_deduction_limit()`.
  - `backend/reference.py`: `verified_parameters()`, `verify_source()`.
  - `backend/tools.py`: `calculate_rrsp_deduction_limit`.

## 5. CRA: CPP contribution rates, maximums and exemptions

- **URL:** https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/payroll-deductions-contributions/canada-pension-plan-cpp/cpp-contribution-rates-maximums-exemptions.html
- **Purpose:** 2026 CPP basic exemption, maximum pensionable earnings, contribution rate and maximum contributions (employee and self-employed).
- **Stored in:** `data/tax_parameters_2026.json` under `cpp`.
- **Code usage:**
  - `backend/payroll.py`: `employee_payroll_deductions()`, `self_employment_tax()`.
  - `backend/reference.py`: `verified_parameters()`, `verify_source()`.
  - `backend/tools.py`: `calculate_employee_payroll_deductions`, `calculate_self_employment_tax_and_cpp`, `get_verified_tax_parameters`.

## 6. ESDC: Maximum benefit amounts and related figures, CPP 2026

- **URL:** https://www.canada.ca/en/employment-social-development/programs/pensions/pension/statistics/2026-quarterly-april-june.html
- **Purpose:** The CPP2 figures (second additional contribution) that the CRA CPP page does not list: YAMPE, the 4% and 8% rates, and their maximums.
- **Stored in:** `data/tax_parameters_2026.json` under `cpp` (`yampe`, `cpp2_*`).
- **Code usage:** same as source 5.

## 7. CRA: EI premium rates and maximums

- **URL:** https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/payroll-deductions-contributions/employment-insurance-ei/ei-premium-rates-maximums.html
- **Purpose:** 2026 EI maximum insurable earnings, employee premium rates (Quebec and outside Quebec), maximum premiums and the employer multiplier.
- **Stored in:** `data/tax_parameters_2026.json` under `ei`.
- **Code usage:**
  - `backend/payroll.py`: `employee_payroll_deductions()`.
  - `backend/reference.py`: `verified_parameters()`, `verify_source()`.
  - `backend/tools.py`: `calculate_employee_payroll_deductions`, `get_verified_tax_parameters`.

## 8. CRA: Update on the administration of the proposed capital gains changes

- **URL:** https://www.canada.ca/en/revenue-agency/news/newsroom/tax-tips/tax-tips-2025/update-cra-administration-proposed-capital-gains-taxation-changes.html
- **Purpose:** States that the one-half capital gains inclusion rate is the currently enacted rate that the CRA administers.
- **Stored in:** `data/tax_parameters_2026.json` under `capital_gains.inclusion_rate` and its note.
- **Code usage:**
  - `backend/capital_gains.py`: `capital_gains_tax()`.
  - `backend/reference.py`: `verified_parameters()`, `verify_source()`.
  - `backend/tools.py`: `calculate_capital_gains_tax`, `get_verified_tax_parameters`.

## 9. Prime Minister of Canada: Cancellation of the proposed capital gains tax increase

- **URL:** https://www.pm.gc.ca/en/news/news-releases/2025/03/21/prime-minister-mark-carney-cancels-proposed-capital-gains-tax-increase
- **Purpose:** Official announcement (2025-03-21) that the proposed increase in the inclusion rate is cancelled. It does not state the rate itself, so it supports source 8.
- **Stored in:** `data/tax_parameters_2026.json` under `capital_gains` (note and source list).
- **Code usage:** same as source 8.

## 10. CRA: What is a TFSA

- **URL:** https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/tax-free-savings-account/what.html
- **Purpose:** How a TFSA is taxed: income and capital gains are generally tax-free, withdrawals are tax-free, contributions are not deductible, and over-contributions or professional-style trading can be taxed.
- **Stored in:** `data/tax_parameters_2026.json` under `tfsa.tax_treatment`.
- **Code usage:**
  - `backend/reference.py`: `verified_parameters()`, `verify_source()`.
  - `backend/tools.py`: `get_verified_tax_parameters` (topic `tfsa`).
