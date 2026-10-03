import "server-only";
import OpenAI from "openai";
import { z } from "zod";
import { requireEnv } from "./env";
import type { AdBenefits } from "../segment";

// Featherless is OpenAI-compatible. The model only extracts what the ad says; segment.ts decides.
const ExtractionSchema = z.object({
  perks: z.array(z.string()).max(40),
  is_recruiter: z.boolean(),
  food_quote: z.string().nullable(),
});

const SYSTEM = `You extract employee benefits from a German or English job ad.
Return ONLY a JSON object: {"perks": string[], "is_recruiter": boolean, "food_quote": string | null}.
- perks: every benefit the ad names, copied as written (e.g. "JobRad", "Deutschlandticket", "Pluxee Essensgutscheine"). No inventions.
- is_recruiter: true if a staffing or recruitment agency posts for an unnamed client.
- food_quote: the exact sentence from the ad that mentions food, lunch, canteen, meal vouchers or catering; null if none.`;

let client: OpenAI | null = null;

export async function extractBenefits(sourceUrl: string, adText: string): Promise<AdBenefits | null> {
  client ??= new OpenAI({ apiKey: requireEnv("FEATHERLESS_API_KEY"), baseURL: "https://api.featherless.ai/v1" });
  try {
    const res = await client.chat.completions.create({
      model: requireEnv("FEATHERLESS_MODEL"),
      temperature: 0,
      max_tokens: 600,
      messages: [
        { role: "system", content: SYSTEM },
        { role: "user", content: adText.slice(0, 12000) },
      ],
    });
    const raw = res.choices[0]?.message?.content ?? "";
    const json = raw.slice(raw.indexOf("{"), raw.lastIndexOf("}") + 1);
    const parsed = ExtractionSchema.parse(JSON.parse(json));

    // Reject a food quote the model did not copy from the ad.
    const quote = parsed.food_quote && adText.includes(parsed.food_quote.slice(0, 40)) ? parsed.food_quote : null;
    return { sourceUrl, perks: parsed.perks, isRecruiter: parsed.is_recruiter, foodQuote: quote };
  } catch (err) {
    console.warn(`[extract] skipped ${sourceUrl}: ${(err as Error).message}`);
    return null; // a failed extraction never counts as "no food"
  }
}
