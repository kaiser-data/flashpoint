import "server-only";

// Fails loudly with the variable name, so a missing key is obvious in the demo log.
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable ${name} (run through: keys run -- npm run dev)`);
  return value;
}

export const CLUSTER_THRESHOLD = Number(process.env.CLUSTER_THRESHOLD ?? 5);
