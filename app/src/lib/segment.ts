// Decides Gap / Switch / Skip / Unknown from the benefits extracted out of a company's job ads.
// The model only extracts; this code decides. Absence of food only counts when the evidence is broad.

export type AdBenefits = {
  sourceUrl: string;
  perks: string[];          // every benefit named in the ad, as written
  isRecruiter: boolean;     // ad posted by an agency for an unnamed client
  foodQuote: string | null; // exact sentence mentioning food, if any
};

export type Segment = "gap" | "switch" | "skip" | "unknown";

export type SegmentResult = {
  segment: Segment;
  reasons: string[];
  perks: string[];
  evidence: { url: string; quote: string }[];
  adsAnalysed: number;
};

export const MIN_ADS_FOR_ABSENCE = 3;
export const MIN_PERKS_PER_AD = 3;

const MEAL_CARD = /pluxee|sodexo|edenred|lunchit|spendit|essensgutschein|essenszuschuss|essenszulage|restaurantscheck|mahlzeitenzuschuss|meal voucher|meal allowance|lunch allowance/i;
const HAS_FOOD = /kantine|betriebsrestaurant|canteen|cafeteria|free lunch|kostenlose[sn]? mittagessen|mittagessen|lunch|catering|bella ?& ?bona/i;
const COMPETITOR_FOR_CHURN = /pluxee|sodexo|edenred|lunchit|spendit|wolt/i;

function matchesAny(texts: string[], re: RegExp): string | undefined {
  return texts.find((t) => re.test(t));
}

export function segmentCompany(ads: AdBenefits[]): SegmentResult {
  const direct = ads.filter((a) => !a.isRecruiter);
  const perks = [...new Set(direct.flatMap((a) => a.perks.map((p) => p.trim())).filter(Boolean))];
  const evidence = direct
    .filter((a) => a.foodQuote)
    .map((a) => ({ url: a.sourceUrl, quote: a.foodQuote as string }));
  const base = { perks, evidence, adsAnalysed: direct.length };

  if (direct.length === 0) {
    return { ...base, segment: "unknown", reasons: ["No ads posted by the company itself"] };
  }

  const foodTexts = [...perks, ...evidence.map((e) => e.quote)];
  const mealCard = matchesAny(foodTexts, MEAL_CARD);
  if (mealCard) {
    return { ...base, segment: "switch", reasons: [`Already pays a meal benefit: "${mealCard}"`] };
  }

  const food = matchesAny(foodTexts, HAS_FOOD);
  if (food) {
    return { ...base, segment: "skip", reasons: [`Already provides food: "${food}"`] };
  }

  const richAds = direct.filter((a) => a.perks.length >= MIN_PERKS_PER_AD);
  if (richAds.length < MIN_ADS_FOR_ABSENCE) {
    return {
      ...base,
      segment: "unknown",
      reasons: [
        `Only ${richAds.length} ad(s) list ${MIN_PERKS_PER_AD}+ perks; need ${MIN_ADS_FOR_ABSENCE} before trusting that food is missing`,
      ],
    };
  }

  return {
    ...base,
    segment: "gap",
    reasons: [`${richAds.length} ads list ${MIN_PERKS_PER_AD}+ perks and none mentions food`],
  };
}

// For existing customers: their ads naming a competitor is an early churn warning.
export function competitorMention(ads: AdBenefits[]): string | null {
  const texts = ads.flatMap((a) => [...a.perks, a.foodQuote ?? ""]);
  return matchesAny(texts, COMPETITOR_FOR_CHURN) ?? null;
}
