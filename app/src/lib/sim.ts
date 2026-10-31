// Deterministisk SIMULERAD data. Används bara för att visa hur resultat kommer att se ut.
// Det här är inga resultat och ingen prognos.

export function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function walk(seed: number, n: number, drift = 0, vol = 0.012): number[] {
  const r = rng(seed);
  const out = [100];
  for (let i = 1; i < n; i++) {
    const u = (r() + r() + r() + r() - 2) * 1.7; // ungefär normalfördelat
    out.push(out[i - 1] * (1 + drift + vol * u));
  }
  return out;
}

export function hashSeed(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
