import { Page } from "../components/ui";

export default function Status() {
  return (
    <Page title="Status" sub="Är commit-koden densamma hos er båda ser ni samma version.">
      <section className="card pad">
        <dl className="dl">
          <dt>Version (commit)</dt><dd><code>{__COMMIT__}</code></dd>
          <dt>Senaste ändring</dt><dd>{__COMMIT_MSG__ || "okänd"}</dd>
          <dt>Byggd</dt><dd>{new Date(__BUILT_AT__).toLocaleString("sv-SE")}</dd>
          <dt>Läge</dt><dd>Forskning. Inga riktiga pengar, inga börskonton, inga order.</dd>
        </dl>
      </section>
    </Page>
  );
}
