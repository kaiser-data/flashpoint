import { describe, expect, it } from "vitest";
import { companyDomainFromEmail } from "./domain";
import { competitorMention, segmentCompany, type AdBenefits } from "./segment";
import { maxTaxFreeLunchBudgetEur } from "./roi";

const ad = (perks: string[], foodQuote: string | null = null, isRecruiter = false): AdBenefits => ({
  sourceUrl: `https://example.org/${Math.random()}`,
  perks,
  foodQuote,
  isRecruiter,
});
const rich = ["JobRad", "Deutschlandticket", "Urban Sports Club"];

describe("companyDomainFromEmail", () => {
  it("returns the registrable domain", () => {
    expect(companyDomainFromEmail("Anna@Mail.Doctolib.de")).toBe("doctolib.de");
    expect(companyDomainFromEmail("x@team.example.co.uk")).toBe("example.co.uk");
  });
  it("drops freemail and garbage", () => {
    expect(companyDomainFromEmail("someone@gmail.com")).toBeNull();
    expect(companyDomainFromEmail("someone@web.de")).toBeNull();
    expect(companyDomainFromEmail("not-an-email")).toBeNull();
  });
});

describe("segmentCompany", () => {
  it("is gap only with three rich ads and no food", () => {
    expect(segmentCompany([ad(rich), ad(rich), ad(rich)]).segment).toBe("gap");
  });
  it("abstains when evidence is thin", () => {
    expect(segmentCompany([ad(rich), ad(rich)]).segment).toBe("unknown");
    expect(segmentCompany([ad(["JobRad"]), ad(["JobRad"]), ad(["JobRad"])]).segment).toBe("unknown");
  });
  it("detects meal cards as switch", () => {
    const r = segmentCompany([ad([...rich, "Pluxee Essensgutscheine"])]);
    expect(r.segment).toBe("switch");
  });
  it("skips companies that already feed people", () => {
    const r = segmentCompany([ad(rich, "Subventionierte Kantine im Haus"), ad(rich), ad(rich)]);
    expect(r.segment).toBe("skip");
    expect(r.evidence).toHaveLength(1);
  });
  it("ignores recruiter ads", () => {
    expect(segmentCompany([ad(rich, null, true), ad(rich, null, true), ad(rich, null, true)]).segment).toBe("unknown");
  });
});

describe("churn and roi", () => {
  it("flags competitor mentions", () => {
    expect(competitorMention([ad(["Wolt Catering für Teamevents"])])).toContain("Wolt");
    expect(competitorMention([ad(rich)])).toBeNull();
  });
  it("computes the tax-free ceiling", () => {
    expect(maxTaxFreeLunchBudgetEur(50)).toBe(84370);
  });
});
