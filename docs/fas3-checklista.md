# Fas 3 – Utvecklingsplan

**0 av 40 uppgifter verifierade · 8 arbetsområden.**

Planering · Kontrollerad 2026-11-03 · Granskad kodversion `72107ed`.

Ny genomförandeplan efter godkänd Fas 2 (40/40). Alla Fas 3-punkter är ännu overifierade. Teknisk utveckling och SIM-prov kan förberedas; ingen strategi är godkänd för framåttest. Inga körningar eller driftsättningar startas av denna plan.

## Uppdateringsregler

- `docs/fas3-status.json` är gemensam källa för status. Ändra status där; denna Markdown genereras.
- Efter varje relevant kodändring: kontrollera berörda uppgifter, kör relevanta tester och uppdatera status/underlag i samma leverans.
- Bocka bara av verifierat och granskat arbete. Att en fil finns eller att en commit är pushad räcker inte.
- Spara kod-/testunderlag i `evidence`. Sätt `in_progress` när arbetet pågår och `todo` om en tidigare verifiering inte längre gäller.
- Skilj på lokal kod, mergad kod, driftsättning, publicering och installerat app-test. De har egna kontrollpunkter.
- Framåttest kräver READY_FOR_PAPER, fryst strategi och startbeslut. H-0013 förblir REJECT; inga frysta resultat ändras.
- Kör `python3 scripts/render-fas3-checklist.py` efter uppdatering och `python3 scripts/render-fas3-checklist.py --check` före commit.
- Chatvyn är en ögonblicksbild. En filändring i en annan session startar inte en verifiering här. Begär en ny kontroll eller uppdatera vyn i nästa leverans.

## 1. Avgränsning och startvillkor

0/5 verifierade.

- [ ] **F3-101** Kartlägg befintlig pappersmotor, serverdrift och återanvändbara komponenter
- [ ] **F3-102** Definiera BTCUSDT, tidsram, instrument och virtuellt startkapital för första pilot
- [ ] **F3-103** Skilj tekniska SIM-prov från godkänt framåttest och håll H-0013 REJECT
- [ ] **F3-104** Dokumentera ansvar, start/stopp och gränsen mellan app och server
- [ ] **F3-105** Registrera Fas 3-planens acceptanskriterier och koppling till forskningsgrindarna

## 2. Godkänd och fryst strategi

0/5 verifierade.

- [ ] **F3-201** Identifiera en kandidat som klarat historiska krav; ny forskning kräver egen förregistrerad hypotes
- [ ] **F3-202** Verifiera dokumenterat slutprov och READY_FOR_PAPER innan riktigt framåttest får starta
- [ ] **F3-203** Frys strategi eller väljare, kodrevision, parametrar och kostnadsmodell
- [ ] **F3-204** Förregistrera minst tre månaders test, erforderligt antal affärer och slutregel
- [ ] **F3-205** Lås jämförelseunderlag, osäkerhetsmått och kriterier för avvikelse eller underkännande

## 3. Marknadsdata i realtid

0/5 verifierade.

- [ ] **F3-301** Återanvänd publik insamling och verifiera serverns datakvalitet för piloten
- [ ] **F3-302** Beräkna signaler endast från kompletta stängda staplar med UTC-tider
- [ ] **F3-303** Återhämta luckor och anslutningsavbrott utan dubbletter eller ändrad ordning
- [ ] **F3-304** Hantera inaktuell data, ofullständiga dagar och indikatorernas uppvärmning
- [ ] **F3-305** Logga mottagningstider och dataversion så att varje beslut kan återskapas

## 4. Beslut och pappersutförande

0/5 verifierade.

- [ ] **F3-401** Återanvänd den frysta strategins beslut och eventuella godkända regimval
- [ ] **F3-402** Simulera fyllning vid nästa tillgängliga öppning utan framtidsdata
- [ ] **F3-403** Hantera virtuella positioner, kapital och realiserat respektive orealiserat resultat
- [ ] **F3-404** Simulera avgifter, spread, slippage, stop och take-profit med publicerad modell
- [ ] **F3-405** Hantera funding och relevanta terminsrisker utan börskonto eller riktiga order

## 5. Risk och återhämtning

0/5 verifierade.

- [ ] **F3-501** Lås gränser för storlek, exponering, förlust och antal samtidiga positioner
- [ ] **F3-502** Blockera nya inträden vid inaktuell data eller osäkert kontotillstånd
- [ ] **F3-503** Definiera nödstopp, paus och hantering av befintliga virtuella positioner
- [ ] **F3-504** Säkerställ exakt en aktiv pilotprocess och idempotenta signaler och fyllningar
- [ ] **F3-505** Återställ positioner och beslutshistorik efter omstart utan dubbla affärer

## 6. Lagring och serverdrift

0/5 verifierade.

- [ ] **F3-601** Versionera kontrakt för papperskörningar, signaler, affärer och händelser
- [ ] **F3-602** Spara oföränderlig journal och spårbarhet till strategi, data och kod
- [ ] **F3-603** Verifiera Supabase-behörigheter och skilj papper från historisk forskningskö
- [ ] **F3-604** Förbered driftsättning, backup och isolerad återställning av pappersdata
- [ ] **F3-605** Verifiera hälsostatus och loggar; håll externa driftlarm som uppskjutet separat val

## 7. Pappersportfölj i TraderGO

0/5 verifierade.

- [ ] **F3-701** Visa tydligt PAPPER, virtuellt kapital och att inga riktiga pengar används
- [ ] **F3-702** Visa vald strategi, marknadsläge, senaste stapel och skäl till beslut eller platt läge
- [ ] **F3-703** Visa positioner, affärer, kostnader, kapitalutveckling och drawdown
- [ ] **F3-704** Visa startvillkor, paus, stopp, serverstatus och anslutningsfel utan dold aktivering
- [ ] **F3-705** Skilj tekniska SIM-körningar från fryst framåttest och verifiera gamla sidor offline

## 8. Tester, pilot och godkännande

0/5 verifierade.

- [ ] **F3-801** Jämför deterministisk återspelning med backtest på samma data och antaganden
- [ ] **F3-802** Prova avbrott, omstart, dubbletter, dataluckor och riskstopp med tekniska testdata
- [ ] **F3-803** Granska och driftsätt pilot efter dokumenterat strategigodkännande och startbeslut
- [ ] **F3-804** Följ hela förregistrerade perioden och jämför affärstakt, exponering, kostnader och utfall
- [ ] **F3-805** Granska slutrapport, registrera beslut och godkänn Fas 3 separat utan automatisk liveövergång
