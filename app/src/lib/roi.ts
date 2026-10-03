// Money figures shown to sales. Each one carries its source so nobody presents a claim as a measurement.

// 2026: Sachbezugswert Mittagessen €4.57 + €3.10 employer top-up = €7.67 tax-free per meal.
// Source: Haufe (Sachbezugswerte für Mahlzeiten 2026) and bellabona.com/en/office-lunch.
export const TAX_FREE_PER_WORKDAY_EUR = 7.67;
export const WORKDAYS_PER_YEAR = 220; // planning assumption, not a statutory figure

// Bella&Bona's own marketing claim: ~€33,000/year saved for 50 employees vs. an equivalent raise.
export const BB_CLAIM_SAVING_PER_EMPLOYEE_EUR = 33000 / 50;

export function maxTaxFreeLunchBudgetEur(employees: number): number {
  return Math.round(employees * TAX_FREE_PER_WORKDAY_EUR * WORKDAYS_PER_YEAR);
}

export function claimedSavingVsRaiseEur(employees: number): number {
  return Math.round(employees * BB_CLAIM_SAVING_PER_EMPLOYEE_EUR);
}
