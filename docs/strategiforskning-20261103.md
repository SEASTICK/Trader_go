# Nästa strategiforskning – netto och risk, 2026-11-03

Edwin vill hitta eller skapa en strategi med positiv nettoavkastning. Han har valt cirka 20 % maximal tillfällig nedgång som riskmål. Detta är ett mål och ett godkännandekriterium, ingen garanti för framtida avkastning eller maximal förlust.

## Vad den sparade forskningen visar

Positivt historiskt netto finns redan, men inget försök är godkänt för papper. H-0012 gav +115,436 % netto, +49,88 % med kostnadsstress, Sharpe 0,919 och maximal nedgång −30,884 %. t=1,596 understeg det låsta kravet 2,638. Resultatet kom från walk-forward med parameteroptimering och 280 Optuna-försök, inte en enda fast parameteruppsättning. Det kan inte användas som bevis för att en ny fast strategi fungerar. H-0012 förblir REJECT och dess slutprov öppnas inte.

H-0013 kombinerade inte squeeze-strategin: dess kandidater var EMA/ADX och Bollinger/RSI. Att säga att alla strategierna är olönsamma vore därför fel.

## Oberoende diagnos av H-0013:s urval

Skriptet `research/audits/h0013-selection-20261103/review.py` läser bara den arkiverade JSON-filen. Det verifierar dess SHA-256 och räknar om vilka kandidater som klarade de låsta träningskraven. Ingen marknadshistorik, signalmotor eller nytt backtest används. Utdata finns i `diagnostics.json` i samma katalog.

Sex fönster × två kandidater × fyra lägen ger 48 bedömningar. Dessa är överlappande träningsbedömningar, inte 48 oberoende försök:

| Träningsutfall | Antal |
|---|---:|
| För få affärer och t inte positivt | 28 |
| Bara för få affärer | 18 |
| Bara t inte positivt | 1 |
| Båda träningskraven uppfyllda | 1 |

46/48 bedömningar hade färre än 20 inledda affärer. Det enda kvalificerade valet var BB/RSI i upp/låg volatilitet inför 2024 H1: 22 träningsaffärer och t=0,165. Det gav sedan fem testaffärer och förlust. Efter sista träningen hade EMA i upp/låg vol t=2,141 men bara sju affärer. BB i samma läge hade 31 affärer men t=−1,171. Slutboken blev korrekt platt överallt.

Detta förklarar urvalets platta lägen, men är inte en omräkning av hur många signaler varje handelsfilter blockerade. En sådan attribution skulle kräva ny instrumentering. Vi sänker inte affärskravet i efterhand för att få H-0013 att handla mer.

## Nästa registrerade försök

H-0016 undersöker en enklare fast squeeze-strategi, long/platt och med ett separat risklager. Se `research/h0016-protokoll.md`. Den använder standardparametrar, inte H-0012:s efteroptimerade slutparametrar. Ingen regimväljare, ML eller ny parametersökning ingår.

Idén är vald efter att resultaten redan setts och räknas som ett nytt försök. Utvecklingshistoriken är inte ren. Riskgränserna är designval, inte uppmätt förbättring. Positivt historiskt netto ensamt ger inte godkännande.

## Arbetsordning

1. Commita registreringen och protokollet innan någon H-0016-körning.
2. Granska riskkontraktet och bygg isolerad implementation med syntetiska tester. Befintligt risk_overlay använder bruttoavkastning och kan inte återanvändas oförändrat för H-0016:s nettobaserade riskgränser.
3. Verifiera exakta arkiv/data och reproducerbart körningspaket. Ingen riktig H-0016-data finns i den lokala arbetskopians data/raw.
4. Kör det enda registrerade försöket med låsta regler och spara även fel/avbrott. H-0013:s köingång tillåter inte H-0016; den får inte återanvändas under fel id. Ingen ny körning har startats i denna leverans.
5. Granska resultat och riskutfall. REJECT bevaras vid underkänt resultat; ändring av regler kräver nytt id. Ett eventuellt slutprov kräver separat beslut efter MORE_RESEARCH.

Fas 3:s tekniska planering kan fortsätta parallellt, men framåttestet väntar på en kandidat med READY_FOR_PAPER. Inga riktiga pengar eller börsnycklar används.
