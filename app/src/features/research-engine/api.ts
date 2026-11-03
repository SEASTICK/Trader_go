export const PROJECT_URL = "https://klspebwvipfzvqbdexxh.supabase.co";
// Offentlig nyckel. Behörigheten kommer från Auth + RLS, aldrig från denna nyckel.
const PUBLIC_KEY = "sb_publishable_GXXtPcCrdBxp06w9qg8HHw_Qo2VE_JM";
type Session = { access_token: string; refresh_token: string; expires_in: number };
export type Run = { id: string; kind: string; hypothesis_id?: string | null; attempts?: number; strategy: string; market: string; interval: string;
  status: "queued" | "running" | "done" | "failed" | "cancelled"; progress: number; error: string | null;
  created_at: string; period_start: string; period_end: string; params: Record<string, number> };
type Curve = { t: string[]; equity: number[]; drawdown: number[] };
export type Result = { mode: string; stats: Record<string, unknown>; curves: Curve; baseline: Curve;
  warnings: string[]; effective_params: Record<string, number | boolean>;
  metadata: { fingerprint: string; dataset_sha256: string; engine_sha256: string; configuration: unknown };
  hypothesis_id?: string; reproduction_match?: boolean; decision?: string;
  trades: { side: string; entry_time: string; exit_time: string | null; entry_price: number;
    exit_price: number | null; net_return: number; exit_reason: string | null }[] };

export class ResearchApi {
  private session: Session | null = null;
  private expiresAt = 0;
  private refreshing: Promise<void> | null = null;
  private generation = 0;

  async request(path: string, method = "GET", body?: unknown, authenticated = true): Promise<unknown> {
    const generation = this.generation;
    if (authenticated) {
      if (!this.session) throw new Error("Logga in för att använda Research Lab.");
      if (Date.now() >= this.expiresAt - 30_000) await this.refresh();
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15_000);
    try {
      const response = await fetch(PROJECT_URL + path, { method, signal: controller.signal,
        headers: { apikey: PUBLIC_KEY, "Content-Type": "application/json",
          ...(authenticated && this.session ? { Authorization: `Bearer ${this.session.access_token}` } : {}) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
      if (generation !== this.generation) throw new Error("Sessionen avslutades.");
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) throw new Error("Inloggningen eller behörigheten kunde inte verifieras.");
        if (response.status === 404) throw new Error("Research-tjänsten är inte färdiginstallerad.");
        if (response.status === 400) {
          if (path === "/auth/v1/token?grant_type=password") {
            throw new Error("Det gick inte att logga in. Kontrollera e-postadress och lösenord.");
          }
          // Databasens egna, svenska avvisningar (till exempel "Kön är full") visas; inga hemligheter finns i dem.
          const detail = await response.json().then((b: { message?: unknown }) => typeof b?.message === "string" ? b.message : "").catch(() => "");
          throw new Error(detail ? `Begäran nekades: ${detail}` : "Begäran nekades. Kontrollera parametrar, period och att kön inte är full.");
        }
        throw new Error(`Servern svarade med fel (${response.status}).`);
      }
      const text = await response.text();
      return text ? JSON.parse(text) : null;
    } catch (error) {
      if (error instanceof TypeError || (error instanceof Error && error.name === "AbortError")) {
        throw new Error("Ingen serveranslutning. Försök igen när nätverket fungerar.");
      }
      throw error;
    } finally { clearTimeout(timer); }
  }

  private accept(session: Session) {
    this.session = session;
    this.expiresAt = Date.now() + session.expires_in * 1000;
  }
  private async refresh() {
    if (!this.refreshing) {
      const token = this.session?.refresh_token;
      this.refreshing = (async () => {
        const session = await this.request("/auth/v1/token?grant_type=refresh_token", "POST", { refresh_token: token }, false) as Session;
        this.accept(session);
      })().finally(() => { this.refreshing = null; });
    }
    await this.refreshing;
  }
  async signIn(email: string, password: string) {
    this.signOut();
    const session = await this.request("/auth/v1/token?grant_type=password", "POST", { email, password }, false) as Session;
    this.accept(session);
    try {
      const members = await this.request("/rest/v1/research_members?select=user_id&limit=1") as unknown[];
      if (members.length !== 1) throw new Error("Kontot saknar medlemsåtkomst. Kontakta projektadministratören.");
    } catch (error) { this.signOut(); throw error; }
  }
  signOut() { this.generation++; this.session = null; this.expiresAt = 0; }
  async runs(): Promise<Run[]> {
    return await this.request("/rest/v1/runs?kind=in.(exploration,registered)&select=id,kind,hypothesis_id,attempts,strategy,market,interval,status,progress,error,created_at,period_start,period_end,params&order=created_at.desc&limit=100") as Run[];
  }
  async h0013Runs(): Promise<Run[]> {
    return await this.request("/rest/v1/runs?hypothesis_id=eq.H-0013&select=id,kind,hypothesis_id,attempts,strategy,market,interval,status,progress,error,created_at,period_start,period_end,params&order=created_at.desc&limit=20") as Run[];
  }
  /** Den fasta H-0013-körningen. Allt utom nyckeln är låst i databasen (0005). */
  async enqueueH0013(requestKey: string): Promise<string> {
    return await this.request("/rest/v1/rpc/research_enqueue_h0013", "POST", { p_request_key: requestKey }) as string;
  }
  async payload(id: string): Promise<unknown | null> {
    const rows = await this.request(`/rest/v1/run_results?select=payload&run_id=eq.${encodeURIComponent(id)}&limit=1`) as { payload: unknown }[];
    return rows[0]?.payload ?? null;
  }
  async enqueue(request: Record<string, unknown>): Promise<string> {
    return await this.request("/rest/v1/rpc/research_enqueue", "POST", { p_request: request }) as string;
  }
  async enqueueRegistered(hypothesis: string, requestKey: string): Promise<string> {
    return await this.request("/rest/v1/rpc/research_enqueue_registered", "POST", {p_hypothesis:hypothesis,p_request_key:requestKey}) as string;
  }
  async cancel(id: string) {
    return this.request("/rest/v1/rpc/research_cancel", "POST", { p_id: id });
  }
  async result(id: string): Promise<Result | null> {
    const rows = await this.request(`/rest/v1/run_results?select=payload&run_id=eq.${encodeURIComponent(id)}&limit=1`) as { payload: Result }[];
    return rows[0]?.payload ?? null;
  }
}
