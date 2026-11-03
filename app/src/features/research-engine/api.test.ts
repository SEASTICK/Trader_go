import { afterEach, describe, expect, it, vi } from "vitest";
import { ResearchApi } from "./api";

afterEach(() => vi.unstubAllGlobals());
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const session = { access_token: "user-session", refresh_token: "refresh", expires_in: 3600 };

describe("Research API", () => {
  it("kräver medlemskap och använder användartoken för dataläsning", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(session))
      .mockResolvedValueOnce(response([{ user_id: "member" }])).mockResolvedValueOnce(response([]));
    vi.stubGlobal("fetch", fetcher);
    const api = new ResearchApi(); await api.signIn("member@example.test", "password");
    await api.runs();
    expect(fetcher.mock.calls[2][1].headers.Authorization).toBe("Bearer user-session");
    api.signOut(); await expect(api.runs()).rejects.toThrow("Logga in");
  });
  it("nekar ett konto utan medlemsrad", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response([])));
    const api = new ResearchApi();
    await expect(api.signIn("outsider@example.test", "password")).rejects.toThrow("medlemsåtkomst");
    await expect(api.runs()).rejects.toThrow("Logga in");
  });
  it("visar nätverksfel utan att lämna ut inloggningsuppgifter", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("request failed")));
    await expect(new ResearchApi().signIn("member@example.test", "password")).rejects.toThrow("Ingen serveranslutning");
  });
  it.each([
    { error: "invalid_grant", error_description: "Invalid login credentials" },
    { message: "backend-detail-that-must-not-be-shown" },
    null,
  ])("skiljer nekad inloggning från köfel utan att visa råa auth-svar", async (body) => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(body, 400));
    vi.stubGlobal("fetch", fetcher);
    const api = new ResearchApi();
    await expect(api.signIn("member@example.test", "synthetic-invalid-password")).rejects.toThrow(
      "Det gick inte att logga in. Kontrollera e-postadress och lösenord.");
    await expect(api.runs()).rejects.toThrow("Logga in för att använda Research Lab");
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it("behåller databasens svenska köavvisning efter inloggning", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(session))
      .mockResolvedValueOnce(response([{ user_id: "member" }]))
      .mockResolvedValueOnce(response({ message: "Kön är full" }, 400));
    vi.stubGlobal("fetch", fetcher);
    const api = new ResearchApi(); await api.signIn("member@example.test", "synthetic-password");
    await expect(api.enqueueH0013("synthetic-request-key")).rejects.toThrow("Begäran nekades: Kön är full");
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
  it("upprepar inte ett köanrop automatiskt när svaret tappas", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response([{ user_id: "member" }]))
      .mockRejectedValueOnce(new TypeError("offline"));
    vi.stubGlobal("fetch", fetcher); const api = new ResearchApi(); await api.signIn("a@b.test", "password");
    await expect(api.enqueue({ request_key: "same-key" })).rejects.toThrow();
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
});
