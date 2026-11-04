# H-0017 C5-01: ordningsbeslut

Datum: 2026-11-04. Underlag: [C5-01-granskningen av b131ff4](momentum-C5-granskning-b131ff4.md), [C5-uppdragets punkt 5](claude-uppdrag-momentum-C5.md) och [det frysta protokollet](../research/h0017-protokoll.md).

**Fråga.** Vilka exakta mellanfundinghändelser ska ingå i Account.funding_net när marginalprövningen träffar inom stapeln men träffens tid är okänd, och vilka belopp ska hanteras av liquidation_adjustment?

**Beslut: KRÄVER EDWIN. Inget alternativ väljs.** Punkt 5 ger Codex uppgiften att granska den materiella frågan före kodning, men gör inte en saknad ledgerkonvention till en redan förregistrerad regel. Den berörda rättningen ska invänta Edwins uttryckliga beslut om konventionen och hur den dokumenteras i förhållande till det frysta protokollet.

**Motivering.** §8.3 och D18 kräver kronologisk bokföring vid exakt tid på q vid händelsen. §8.3:s C efter betald och före mottagen funding definierar marginalens konservativa prövningsunderlag, inte en historisk händelseordning. §9 och D21 låser totalförlust och absorberande noll efter träff, men bestämmer inte vilka händelser som föregick den okända träfftiden. Invarianten om att en mellanhändelse aldrig möter en redan likviderad position löser inte denna informationslucka. Invarianterna står i §13.3 i den lästa revisionen, inte §12.

Alternativ 1 är en transparent föreslagen redovisningskonvention: det bevarar osäkerheten och skiljer underlag från ledger. Det följer däremot inte entydigt av protokollet att även händelser som kan ha föregått träffen ska uteslutas ur fundingledgern. Att föra samtliga till en ny kategori och liquidation_adjustment påverkar dessutom betald/mottagen-redovisningen i §13.4 och eventspåret i §15. Det är därför ett materiellt tillägg, inte enbart en teknisk rättning. Identiskt slutkapital, dagsserie och C6 ersätter inte detta beslut. Alternativ 2 antar en obestyrkt ordning; alternativ 3 kvarstår som underkänt enligt C5-01. Ingen protokolländring görs eller godkänns här.

**Regressioner efter beslutad konvention.** Oberoende hand-/Decimalfacit ska täcka kredit före betalning och omvänt, flera betalningar/krediter, nollränta, båda mmr, A/B, med/utan samtidig funding och träff/ingen träff. Proven ska visa:

- Separat underlags-C, E_low och MM; mottagen funding räddar inte prövningen och betalningar räknas inte dubbelt.
- Varje event-id exakt en gång i spåret med exakt fundingtid och entydig bokföringskategori; likvidationstiden anges som okänd inom stapeln, utan påstådd relation till fundingtiderna.
- Historisk funding före träffstapeln och öppningens A/B-bokföring bevaras; utan träff bokförs mellanhändelser kronologiskt enligt befintligt kontrakt.
- Funding_net, betalda/mottagna summor, eventuella separat redovisade absorberade belopp och liquidation_adjustment stäms av var för sig mot det beslutade facit. Identiteten C = deposit + realized − costs − funding_net + liquidation_adjustment − q·avg = 0 håller vid likvidation.
- E=C=q=0 och likvidationsflaggan består över close, midnatt och terminal utan ny funding, affär eller återupplivning. Dagsserie och C6 bevarar protokollets utfall.

Detta är ett kontraktsbeslut om fortsatt hantering, inte verifiering eller godkännande av en implementation. Inga regressioner har körts för denna dokumentleverans; C5-01 är inte stängt.
