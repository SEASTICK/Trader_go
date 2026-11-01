import { CandleChart } from "../components/CandleChart";
import { Page } from "../components/ui";
import type { SeriesRef } from "../lib/candles";

const BTC_4H: SeriesRef = { provider: "binance", market: "spot", symbol: "BTCUSDT", interval: "4h" };

/** Marknaden just nu: samma prisdiagram som i rutornas detaljvy, direkt från menyn. */
export default function Market() {
  return (
    <Page title="Marknad" sub="Bitcoin på Binance spot med verkliga priser. Appen samlar in dem själv, utan konto och utan nycklar.">
      <CandleChart series={BTC_4H} noSourceReason="Ingen datakälla för den här marknaden än." />
      <p className="footnote">Riktiga priser betyder inte riktig handel. Allt i Trader_go är papper eller historik.</p>
    </Page>
  );
}
