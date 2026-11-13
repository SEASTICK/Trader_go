import { useState } from "react";
import { Page, Segmented } from "../components/ui";
import { isDesktop, Paper } from "../desktop";
import Investors from "./Investors";

const TABS = ["Följer investerare", "Egna affärer"] as const;
type Tab = (typeof TABS)[number];

/** Allt som är papper på ett ställe. Egna affärer finns bara i skrivbordsprogrammet (Tauri-bryggan saknas på webben). */
export default function Papper() {
  const [tab, setTab] = useState<Tab>("Följer investerare");
  const tabs = isDesktop ? <Segmented value={tab} options={[...TABS]} onChange={setTab} /> : undefined;
  if (isDesktop && tab === "Egna affärer") {
    return (
      <Page title="Egna affärer" sub="Bara papper. Ingen riktig order läggs." actions={tabs}>
        <div className="card pad desk"><Paper /></div>
      </Page>
    );
  }
  return <Investors actions={tabs} />;
}
