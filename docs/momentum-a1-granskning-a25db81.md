# Codex godkännande av momentum A1 revision 3

Datum: 2026-11-03. Granskad och godkänd A1-revision: **`a25db812c1ea60932de7bf8fbcaf33a009859b46`**. Diffbas: `21cd52c`.
Lokal HEAD och fjärrgrenen `claude/momentum-a1` verifierade på samma revision, utan ocommittade ändringar före granskningen. Fjärr-main är fortfarande `72107ed` och innehåller inte denna dokumentkedja.

**A1 godkänns som metodkontrakt för A2-förregistrering. Inga kvarstående blockerande fynd i denna omgranskning.** Godkännandet avser specifikationen och de syntetiska räknefallen, inte en strategiimplementation, datatäckning, ett ekonomiskt resultat eller framtida drift. Ingen registrering görs i denna granskningsleverans.

## R2-01 – stängd

D18 och §8.3 undantar nu kända öppningshändelser från L1/L2. Gapstop, terminal, känd likvidation och andra öppningsutgångar är utförda före senare funding. Exakt samtidig funding följer fortfarande A/B. Vid verkligt okänd intrastapelordning används innehavet efter öppningsfyllningen, inklusive ett nytt inträde. En likviderad position återuppstår inte.

O17 kontrollerat med en oberoende Decimal-ledger:

- Gapstop vid 94 med q=900 och C=10 000: efter avgift E=94 464,64, q=0. Funding +30 sekunder är 0 i både L1 och L2.
- Samma gapstop, funding exakt vid öppningen: A=8,46 och B=0; slutkapital 94 456,18 respektive 94 464,64.
- Nytt inträde med 100 000, w=1 och P=M=100: q_open=998,402555910543… . Vid senare stop/funding i samma stapel är L1-funding=0 och L2-funding=9,984025559105… på den nya positionen. Stopkostnad och slutkapital i båda fallen stämmer.

Den preciserade likvidationskontrollen är en uttrycklig sträng OHLC-/fundingmodell. Okänd intrastapelordning blir inte verifierad tickhistorik genom specifikationen. Dess implementation och samspel med stop/funding måste provas i leverans C/D.

## R2-02 – stängd

D21, §4, §9 och §13 anger nu absorberande noll: övergång från positivt kapital till dokumenterat likviderat nollkapital ger −100 % den dagen; efterföljande dagar ger 0. E=C=q=0 utan nya affärer, funding eller kapital. Oförklarad nolla/negativt kapital är fortfarande fel. Main-likvidation underkänner C6 ekonomiskt; den är inte ett NaN-fel. Blandningar använder faktiska summerade delkapital.

O18 avstämt mot fasta förväntade avkastningar och kedjat slutkapital:

- Likvidation mitt i perioden och på terminaldagen ger −100 % totalt, med full serie utan 0/0.
- Delkontofallet ger blandningen 52 000/100 000−1 = −48 %, medan det överlevande kontot fortsätter.
- Extra syntetiska 1 096-dagarsserier med likvidation dag 1, 500 och 1 096 har full längd, rätt kapitalkedja och ändliga Sharpe/Newey-West-värden med lags=6.

O18:s beslutspost är en specifikationsfixtur. Den är inte ett test av en färdig beslutsmotor; sådan implementation finns ännu inte.

## Textjusteringar och tidigare fynd

D11 beskriver nu råa räknemått/känslighetsvärden i linje med §14. §2 skiljer projektets exakta designval från litteraturens stöd för metodfamiljen. §10.2 har rätt riktning för drawdownmåttet och dess positiva magnitud. Justeringarna är godkända. De fyra ursprungliga fynden i cb335ee förblir stängda enligt omgranskningen av 979fb30.

## Verifiering

- 29 befintliga stats-/register-/marginal-/exporttester godkända: `cd engine && .venv/bin/python -m pytest tests/test_stats.py tests/test_registry_and_experiment.py tests/test_margin_reference.py tests/test_registered_export.py -q -p no:cacheprovider`.
- Claudes orakel: `engine/.venv/bin/python scripts/momentum-a1-oracles.py --check`: PASS.
- Båda tidigare granskningsskripten: PASS, oförändrade mot `21cd52c`. De bevarar historiska motexempel; de är inte ensamma bevis för rättningen.
- Ny oberoende verifiering: `engine/.venv/bin/python research/audits/momentum-a1-a25db81/review.py --check`. `verification.json` sparar resultat och SHA-256 för exakt A1-protokoll, orakel och orakelskript. Endast syntetiska tal och befintliga statistikfunktioner används.
- Alla fyra checklistgeneratorer med `--check`: PASS. `git diff --check 21cd52c a25db81`: rent.
- Diffen omfattar de fem uppgivna A1-/statusfilerna. Äldre granskningar och deras reproduktioner är oförändrade.

MOM-A03 och MOM-A04 markeras klara **för metodkontraktet på a25db81**. MOM-A05 väntar på A2 och är fortsatt todo. Checklistan blir 4 av 40 klara.

## Nästa leverans till Claude: enbart A2

1. Utgå från den gren/commit som innehåller detta godkännande och hela dokumentkedjan; börja inte från den äldre main. Bevara andra sessioners arbete och båda äldre granskningarna.
2. Kontrollera senaste gemensamma register och samordna ett ledigt id. H-0017 är inte reserverat genom A1. Räkna N som distinkta id inklusive det nya med befintlig registerkod. Lås t-kravet max(2,67, t_krav(N)) samt uppdaterad tabell för N_sok enligt §14. Om N=17 gäller 2,754268270633685; anta inte att N fortfarande blir 17.
3. Skapa slutligt protokoll i research/ med id, version, proveniens till godkända a25db81 och korrekta dokument-/orakellänkar. A2 får ändra administrativa identiteter, faktiska räknemått och status, men inte reglerna i godkända A1 §2–§15. Om en materiell ändring behövs ska den tillbaka till granskning före registrering.
4. Lägg endast den nya registreringsraden sist; bevara alla tidigare rader och REJECT-beslut. Committa protokoll och registrering före någon historisk utvärdering. Redovisa den faktiska registreringscommiten efteråt; försök inte bädda in en commits egen framtida hash i dess filinnehåll.
5. Kör relevanta register-/export-/statistikkontroller, orakel och checklistkontroller. Uppdatera MOM-A05 med underlag men markera den inte verifierad klar före Codex A2-granskning.
6. Lämna exakt gren, HEAD, diffbas, id, N, t-krav, N_sok, registreringscommit, ändrade filer och diff mot godkänt metodkontrakt till Codex.

**Leverans B börjar först när Codex verifierat A2:s registrering och oförändrade metodregler.** Ingen motorkod, marknadshistorik, skyddad period, forskningskörning, servermutation, SQL/migration, driftsättning, PR-merge, release eller paper/live-aktivering ingår i A2.

## Kvarstående begränsningar

Datakvalitet, reala fundingtidpunkter och om L1/L2 skiljer sig är ännu inte verifierade. Markprisapproximationen, fasta marginalsatser och kontinuerliga enheter är forskningsantaganden, inte historiskt verifierade börsvillkor. DSR är diagnostik. Utvecklingsperioden är redan sedd och kan inte ge ren bekräftelse. H-0013 REJECT och H-0016:s separata protokoll är oförändrade. Ingen pilot är godkänd. Tidigare begränsningar för manuellt Windows-prov, Gatekeeper/notarisering, uppskjutna driftlarm och diagramtemat är inte omprövade eller undanröjda i denna leverans.
