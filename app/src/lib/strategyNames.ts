// Lättbegripliga namn på de registrerade strategierna. Id och den fullständiga hypotesen visas alltid bredvid,
// så namnet ersätter aldrig registret. En hypotes utan namn här visas med sin korta rubrik ur registret.
export type StrategyName = { name: string; idea: string };

export const STRATEGY_NAMES: Record<string, StrategyName> = {
  "H-0001": { name: "Bitcoin-trend med två snitt", idea: "Äg Bitcoin när det korta snittpriset ligger över det långa, annars stå utanför." },
  "H-0002": { name: "Maskininlärd riktning", idea: "En modell som lär sig av gamla priser gissar om Bitcoin går upp eller ner det kommande dygnet." },
  "H-0003": { name: "Bitcoin med volatilitetsbroms", idea: "Äg Bitcoin, men minska positionen när priset svänger mycket." },
  "H-0004": { name: "Motvalls vid hög finansieringsränta", idea: "Gå emot trängseln när den ena sidan av terminsmarknaden betalar ovanligt mycket." },
  "H-0005": { name: "Ethereum-trend", idea: "Äg Ethereum när priset ligger över sitt 50-dagarssnitt, annars stå utanför." },
  "H-0006": { name: "Bitcoin över 200-dagarssnittet", idea: "Äg Bitcoin bara när priset ligger över sitt långa snitt. Lugnare variant." },
  "H-0007": { name: "Ethereum mot Bitcoin, återgång", idea: "Köp Ethereum mot Bitcoin när kvoten är ovanligt låg, sälj när den är ovanligt hög." },
  "H-0008": { name: "Säkrad finansieringsränta", idea: "Äg Bitcoin och sälj terminen lika mycket för att tjäna finansieringsräntan utan prisrisk." },
  "H-0009": { name: "Trend med styrkefilter", idea: "Följ trenden i Bitcoin-terminen, men bara när trenden är tydligt stark." },
  "H-0010": { name: "Utbrott till nya toppar", idea: "Köp när priset bryter över sin senaste topp, sälj när det bryter under botten." },
  "H-0011": { name: "Köp dippen, sälj toppen", idea: "Köp när priset fallit ovanligt långt och sälj när det stigit ovanligt långt." },
  "H-0012": { name: "Utbrott efter lugn period", idea: "Vänta på en ovanligt lugn period och följ sedan utbrottet åt det håll priset tar." },
  "H-0013": { name: "Spelbok efter marknadsläge", idea: "Välj strategi efter om marknaden är i trend och om den svänger mycket eller lite." },
  "H-0014": { name: "Starkaste mynten mot svagaste", idea: "Varje vecka: köp de fem mynt som gått bäst och sälj blankt de fem som gått sämst." },
  "H-0015": { name: "Räntejakt bland tio mynt", idea: "Varje vecka: tjäna på finansieringsräntan genom att ta motsatt sida i de mynt där den är högst och lägst." },
  "H-0016": { name: "Följ kända investerare", idea: "Äg samma aktier som tio kända investerare enligt deras kvartalsredovisningar." },
  "H-0017": { name: "Kopiera Pelosis aktieaffärer", idea: "Köp och sälj samma aktier som Nancy Pelosi, dagen efter att affären blivit offentlig." },
  "H-0018": { name: "Starkaste mynten, hela marknaden", idea: "Som ”starkaste mot svagaste”, men över alla likvida mynt och med tiondelar." },
  "H-0019": { name: "Räntejakt, hela marknaden", idea: "Som räntejakten, men över alla likvida mynt och med tiondelar." },
  "H-0020": { name: "Kassa och termin på BTC och ETH", idea: "Köp myntet och sälj terminen när terminen är tillräckligt dyr, och håll skillnaden till förfall." },
  "H-0021": { name: "Varje mynts egen trend", idea: "Varje vecka: äg de mynt som själva stigit senaste månaden och sälj blankt de som fallit." },
  "H-0022": { name: "Kassa och termin på altcoins", idea: "Samma kassa-och-termin-idé på sju mindre mynt med kvartalskontrakt." },
  "H-0023": { name: "Kassa och termin på altcoins, version B", idea: "Kassa och termin på sju mindre mynt, med en fast regel för när positionen byts." },
  "H-0024": { name: "Månadsskiftet i S&P 500", idea: "Äg S&P 500 kring varje månadsskifte och stå utanför resten av månaden." },
  "H-0025": { name: "Utbrott efter lugn period, med riskstopp", idea: "Utbrott efter en lugn period i Bitcoin, med fast risk per affär och stopp om förlusterna blir för stora." },
  "H-0026": { name: "Riskstyrd Bitcoin-trend", idea: "Äg Bitcoin när priset stigit senaste veckan, två veckorna och månaden, med lägre vikt när det svänger mycket och stopp vid stora förluster." },
};

export const strategyName = (id: string, fallback: string): StrategyName =>
  STRATEGY_NAMES[id] ?? { name: fallback, idea: "" };
