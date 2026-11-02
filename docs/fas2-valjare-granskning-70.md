# Strategiväljare H-0013 – granskning av PR #70

Granskad PR-head: `8e6617d7ab4e6e91bcfe50c534df113eb8d73225`, kodcommit `a483162`, gren `fas2-valjare`, bas `977b352`.
PR: https://github.com/SEASTICK/Trader_go/pull/70. Ingen merge, driftsättning, publicering eller körning på riktig data har gjorts i granskningen.

## Fynd före merge

**P2 – spelbokskontraktet accepterar saknat eller motsägande versionsunderlag.** I `engine/traderlab/adaptive.py:67–73` kontrollerar `Playbook.from_dict()` bara versionerna som råkar finnas i `candidates`. Fältet kan saknas eller vara tomt. En spelbok som väljer EMA i alla fyra lägen accepteras även med kandidatlistan `{"bb_rsi_reversion": "1.0.0"}`. `to_dict()` fyller därefter tyst i EMA:s version från den aktuella koden. Den inlästa spelbokens versionsunderlag har alltså ersatts i stället för verifierats.

Oberoende syntetiska kontraktsprov på exakt PR-head bekräftade att samtliga dessa tre felaktiga representationer accepteras och normaliseras till en vanlig EMA-spelbok med samma id. Korrekt explicit versionsmismatch avvisas redan; problemet gäller frånvarande och motsägande manifest.

Dessutom kan den publika dataklasskonstruktorn kringgå `of()` helt: `Playbook((("upp/hög vol", "not_a_strategy"),))` accepteras trots ofullständiga lägen och okänd kandidat. Kravet på exakt fyra giltiga val gäller därför inte alla instanser av typen som `signals()` accepterar.

Rätta F2-301 innan kontraktet används som gräns mellan lagring, träning och worker:

- Kräv ett komplett kandidatmanifest som exakt motsvarar de kandidater som används i `choices`, inklusive `platt: null` när platt används.
- Avvisa saknat/tomt manifest, saknade eller extra kandidatposter och fel versioner i stället för att fylla i dem.
- Säkerställ att varje `Playbook` är giltig oavsett konstruktorväg: exakt de fyra unika regimerna, endast tillåtna kandidater och ett stabilt normaliserat innehåll.
- Regressionstesta dessa ogiltiga representationer samt giltig round-trip, stabila id och alla 81 spelböcker.

Detta är ett fel i datakontraktets validering, inte ett konstaterat framtidsläckage i nuvarande historiska signalkod.

## Verifierat

- Isolerad kopia av exakt PR-head: **306 Python-testfall passerar**, inklusive **53 adaptiva** och **66 regimtestfall**. GitHub Actions Engine check är också grön för samma PR-head.
- De fasta kandidaterna och standardparametrarna återanvänds utan ändring av `SPECS` eller kandidatstrategier.
- Long/short-filtret och platt vid `okänt` följer protokollet.
- Byte av läge eller aktiv kandidat stänger via målposition noll, utan att ta över kandidatens gamla affär. En ny spelbok med samma aktiva kandidat orsakar inte onödig stängning.
- Tidsregeln använder det läge som gäller nästa stapel vid beslut på den nuvarande stapelns stängning. Vid dygnsgränsen är föregående dygn då precis stängt; det kräver ingen framtida prisdata. Metadata i `AdaptiveSignals` avser konsekvent nästa stapel.
- Nästa öppning och ATR-stop från kandidaten provas i den befintliga backtestmotorn. Motorns spärr efter stop används; väljaren representerar avsedd målposition och ska inte tolkas som en avstämd faktisk position.
- Prefixkontrollerna för framtida data passerar. Tillförda dagslägen och spelboksscheman måste fortfarande komma från ett korrekt tidsavgränsat träningsflöde; det ingår i kommande walk-forward-leverans.
- PR #69 är mergad som `29e44ec`; kod och regimtester är oförändrade jämfört med granskad `866d393`.

## Checklista och nästa steg

F2-302–F2-305 är verifierade på denna PR-head. F2-301 förblir `in_progress` tills kontraktsvalideringen är rättad och omgranskad. Checklistan visar därmed **14/40**, med tydlig åtskillnad mellan granskad PR-kod, mergad kod och drift.

Behåll den konservativa regeln om ny signal efter byte. Ingen träning, optimering, kö, worker, appintegration eller riktig datakörning behövs för att rätta kontraktet. Fullständig väljare kan godkännas för merge efter omgranskning av rättningen; därefter kommer den förregistrerade tränings-/urvalsregeln och walk-forward.

## Omgranskning av db54bbe – godkänd för merge

Granskad PR-head: `db54bbe8c2414aec64e334d02d4e893e074d84ec`, kodrättning `9128008`. Det tidigare kontraktsfyndet är åtgärdat:

- `from_dict()` kräver exakt toppnivåschema och exakt kandidatmanifest för spelbokens använda kandidater och låsta versioner.
- Saknade, tomma och motsägande kandidatmanifest avvisas i stället för att normaliseras tyst.
- `__post_init__` validerar även direkt konstruktion: fyra unika giltiga regimer och tillåtna kandidater, med normaliserad ordning.
- Oberoende återkörning av granskningens fyra felprov avvisar nu samtliga med `ValueError`.
- Alla 81 giltiga spelböcker verifierade med round-trip och stabila id även vid omvänd konstruktorordning.

En isolerad körning på exakt PR-head gav **327 passerade Python-testfall**, inklusive **74 adaptiva testfall**. GitHub Actions Engine check är grön för samma PR-head. En strukturell AST-jämförelse mot granskade 8e6617d visar att `signals`, `candidate_signals`, `_schedule` och `_direction` är oförändrade.

**Beslut:** strategiväljaren och kontraktet är godkända för merge på denna kodversion. F2-301–F2-305 är nu verifierade och den gemensamma checklistan visar **15/40**. PR #70 är fortfarande öppen vid granskningen; inget har mergats, driftsatts, publicerats eller körts mot riktig data här. Detta är kodgodkännande, inte ett godkännande av strategiernas avkastning, papper eller livehandel.

Nästa leverans efter merge är F2-401–F2-405: förregistrerad kandidatselektion på träningsdata och sex walk-forward-fönster, först verifierat med syntetiska data och utan att öppna slutprovet. Befintliga kostnads-, risk- och dataprov gäller fortsatt i de separata kontrollpunkterna.
