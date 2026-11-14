"""Avstämning av NYSE-ledgern (research/h0024/nyse-closures-ledger.csv) mot officiella dokument. Ingen SPY-data, inga priser.

Vad som stäms av, och mot vad (dokumenten hämtas från publika adresser och låses med SHA-256 i `EVIDENCE`):
  * NYSE:s årliga handelskalendrar (PDF) för 2022, 2023 och 2024: dagar fyllda med legendens färg "Exchange Holiday - Market Closed" läses ur PDF:en (ordpositioner via
    `pdftotext -bbox` och pixlar via `pdftoppm`). Både det som är stängt och det som inte är det jämförs med ledgern för hela året.
  * NYSE:s regelbok (`NYSE_Rules.pdf`): daterade Information Memos 2006 och 2007 ("will be closed on <veckodag>, <datum>") och notisen om att börsen var stängd 2007-01-02
    (Gerald Ford). Rule 7.2 (helgdagslistan och flyttregeln) kontrolleras som text, men styrker bara regeln, inte enskilda datum.
  * SEC Release No. 34-70097 (sidan 6): NYSE:s stängning 2012-10-29 och 2012-10-30 (Sandy).
Allt annat lämnas overifierat. `--apply` fyller `verified_*` bara för rader som ett dokument faktiskt styrker. Kräver `pdftotext` och `pdftoppm` (poppler) och Pillow.

Körning: `python -m traderlab.nyse_verify --evidence-dir <katalog> [--download] [--apply]`
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from . import nyse_sessions

EVIDENCE = {
    "NYSE-CAL-2022": {"file": "ICE_NYSE_2022_Yearly_Trading_Calendar.pdf", "url": "https://www.nyse.com/publicdocs/ICE_NYSE_2022_Yearly_Trading_Calendar.pdf",
                      "sha256": "2c2e63b780c4a373d8d546904ae46c8ba7e8070ad9357d23d2c92749985bb6c9", "what": "NYSE 2022 Trading Calendar (Exchange Holiday - Market Closed)"},
    "NYSE-CAL-2023": {"file": "ICE_NYSE_2023_Yearly_Trading_Calendar.pdf", "url": "https://www.nyse.com/publicdocs/ICE_NYSE_2023_Yearly_Trading_Calendar.pdf",
                      "sha256": "3d28b46a7197424c822087fb7117cdf3f303bd9a73f29660525b605f542bcfe2", "what": "NYSE 2023 Trading Calendar (Exchange Holiday - Market Closed)"},
    "NYSE-CAL-2024": {"file": "ICE_NYSE_2024_Yearly_Trading_Calendar.pdf", "url": "https://www.nyse.com/publicdocs/ICE_NYSE_2024_Yearly_Trading_Calendar.pdf",
                      "sha256": "02282e733512d1f112230372efccfd18f81599c682af94bb6f21fd9bccbfd145", "what": "NYSE 2024 Trading Calendar (Exchange Holiday - Market Closed)"},
    "NYSE-RULES": {"file": "NYSE_Rules.pdf", "url": "https://www.nyse.com/publicdocs/nyse/regulation/nyse/NYSE_Rules.pdf",
                   "sha256": "b57592941c629f7147f8328de96540e8f91278b64b7e442dc54edb5781939a22", "what": "NYSE Rules guide (Rule 7.2; Information Memos 06-xx och 07-05; notis 2007-01-02)"},
    "SEC-34-70097": {"file": "34-70097.pdf", "url": "https://www.sec.gov/rules/sro/nysearca/2013/34-70097.pdf",
                     "sha256": "62d4faadddc1beee4d3e7fa6802f5284a8a983f3f8b73deb7340b840b76eb2e1", "what": "SEC Release No. 34-70097, avsnittet Events During Superstorm Sandy (s. 6)"},
}
CALENDAR_YEARS = {2022: "NYSE-CAL-2022", 2023: "NYSE-CAL-2023", 2024: "NYSE-CAL-2024"}
DPI = 130
MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MEMO_RE = re.compile(r"closed\s+on\s+(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,\s+(" + "|".join(MONTH_NAMES) + r")\s+(\d{1,2}),\s+(20\d\d)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for key, e in EVIDENCE.items():
        target = evidence_dir / e["file"]
        if not target.exists():
            req = urllib.request.Request(e["url"], headers={"User-Agent": "trader_go-research"})
            with urllib.request.urlopen(req, timeout=300) as r:
                target.write_bytes(r.read())


def check_hashes(evidence_dir: Path) -> dict[str, str]:
    """SHA-256 per dokument. Dokument med känt hash måste stämma; hashen för okända (None) skrivs ut så att den kan låsas efter granskning."""
    out = {}
    for key, e in EVIDENCE.items():
        p = evidence_dir / e["file"]
        if not p.exists():
            raise FileNotFoundError(f"{p} saknas (kör med --download)")
        got = sha256(p)
        if e["sha256"] is not None and got != e["sha256"]:
            raise ValueError(f"{key}: sha256 {got} != {e['sha256']}: dokumentet har ändrats")
        out[key] = got
    return out


def _bbox_words(pdf: Path) -> list[tuple[float, float, float, float, str]]:
    xml = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    return [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', xml)]


def calendar_closures(pdf: Path, year: int, workdir: Path) -> set[date]:
    """Dagar i en NYSE-årskalender som är fyllda med legendens färg för "Exchange Holiday - Market Closed". Legendens färg läses ur PDF:en själv (rutan till vänster om texten)."""
    from PIL import Image
    words = _bbox_words(pdf)
    prefix = workdir / f"cal{year}"
    subprocess.run(["pdftoppm", "-r", str(DPI), "-png", "-singlefile", str(pdf), str(prefix)], check=True)
    img = Image.open(str(prefix) + ".png").convert("RGB")
    k = DPI / 72.0

    def region(x0, y0, x1, y1):
        return img.crop((int(x0 * k), int(y0 * k), max(int(x1 * k), int(x0 * k) + 1), max(int(y1 * k), int(y0 * k) + 1)))

    # legendens färg: ordet "Exchange" i raden "Exchange Holiday - Market Closed"; rutan ligger till vänster om texten
    ex = [w for w in words if w[4] == "Exchange" and any(v[4] == "Holiday" and abs(v[1] - w[1]) < 2 for v in words)]
    if not ex:
        raise ValueError("hittar inte legenden 'Exchange Holiday'")
    x0, y0, x1, y1 = ex[0][:4]
    sw = region(x0 - 40, y0, x0 - 6, y1)
    colors = sorted(sw.getcolors(maxcolors=100000), reverse=True)
    legend = next(c for n, c in colors if not (c[0] > 235 and c[1] > 235 and c[2] > 235))        # vanligaste icke-vita färgen
    heads = [(w, MONTHS.index(w[4])) for w in words if w[4] in MONTHS]
    if len(heads) != 12:
        raise ValueError(f"förväntade 12 månadsrubriker, hittade {len(heads)}")
    legend_y = min(w[1] for w in words if w[4] == "HOLIDAYS")
    closed: set[date] = set()
    for (xa, ya, xb, yb, t) in words:
        if not re.fullmatch(r"\d{1,2}", t) or ya > legend_y:
            continue
        cx = (xa + xb) / 2
        above = [(h, m) for h, m in heads if h[1] < ya and abs((h[0] + h[2]) / 2 - cx) < 80]
        if not above:
            continue
        (h, m) = max(above, key=lambda hm: hm[0][1])
        part = region(xa - 2, ya, xb + 2, yb)
        crop = list(part.get_flattened_data() if hasattr(part, "get_flattened_data") else part.getdata())
        near = sum(1 for p in crop if all(abs(p[i] - legend[i]) < 28 for i in range(3)))
        if near / max(len(crop), 1) >= 0.35:
            closed.add(date(year, m + 1, int(t)))
    return closed


def memo_closures(rules_text: str, years: set[int]) -> dict[date, str]:
    """Datum som NYSE:s Information Memos i regelboken anger som stängda ("closed on <veckodag>, <månad> <dag>, <år>")."""
    out = {}
    for m in MEMO_RE.finditer(rules_text):
        d = date(int(m.group(3)), MONTH_NAMES.index(m.group(1)) + 1, int(m.group(2)))
        if d.year in years:
            out[d] = m.group(0)
    return out


def verify(evidence_dir: Path, workdir: Path) -> dict:
    """Stäm ledgern av mot dokumenten. Returnerar {datum: (källa, hänvisning)} för rader som styrks, samt avvikelser."""
    hashes = check_hashes(evidence_dir)
    led = nyse_sessions.read_ledger()
    led["d"] = pd.to_datetime(led["date"]).dt.date
    ledger_dates = set(led["d"])
    supported: dict[date, tuple[str, str]] = {}
    problems: list[str] = []
    workdir.mkdir(parents=True, exist_ok=True)
    for year, key in CALENDAR_YEARS.items():
        got = calendar_closures(evidence_dir / EVIDENCE[key]["file"], year, workdir)
        want = {d for d in ledger_dates if d.year == year}
        if got != want:
            problems.append(f"{year}: kalendern och ledgern avviker: bara i kalendern {sorted(got - want)}, bara i ledgern {sorted(want - got)}")
        for d in got & want:
            supported[d] = (key, f"{EVIDENCE[key]['what']}: {d.isoformat()} fylld som Exchange Holiday - Market Closed")
    rules = subprocess.run(["pdftotext", "-layout", str(evidence_dir / EVIDENCE["NYSE-RULES"]["file"]), "-"], check=True, capture_output=True, text=True).stdout
    memos = memo_closures(rules, {2006, 2007})
    for d, phrase in memos.items():
        if d in ledger_dates and d not in supported:
            supported[d] = ("NYSE-RULES", f"NYSE Rules guide, Information Memo {'06-02 (2006-01-12)' if d.year == 2006 else '07-05 (2007-01-19)'}, margin extensions holiday schedule: \"{phrase}\"")
        elif d not in ledger_dates:
            problems.append(f"memo anger {d} som stängd men ledgern saknar raden")
    ford = re.search(r"will be closed on Tuesday, January 2, 2007, in observance of\s+the national day of mourning for former President Gerald Ford", rules)
    if ford and date(2007, 1, 2) in ledger_dates:
        supported[date(2007, 1, 2)] = ("NYSE-RULES", "NYSE Rules guide, Information Memo 06-88 (2006-12-29): \"The New York Stock Exchange will be closed on Tuesday, January 2, 2007, in observance of the national day of mourning for former President Gerald Ford\"")
    elif date(2007, 1, 2) in ledger_dates:
        problems.append("hittar inte Ford-notisen")
    rule72 = re.search(r"Rule 7\.2\., New York Stock Exchange, Holidays\s+Click to open document in a browser\s+The Exchange will not be open for business on New Year's Day, Martin Luther King Jr\. Day, Presidents' Day,\s+Good Friday, Memorial Day, Independence Day, Labor Day, Thanksgiving Day and Christmas Day\.", rules)
    sec = subprocess.run(["pdftotext", "-layout", str(evidence_dir / EVIDENCE["SEC-34-70097"]["file"]), "-"], check=True, capture_output=True, text=True).stdout
    sandy = re.search(r"On October 29 and 30, 2012.{0,900}?closed\s+for\s+those\s+two\s+days", sec, re.S)
    if sandy:
        for d in (date(2012, 10, 29), date(2012, 10, 30)):
            if d in ledger_dates:
                supported[d] = ("SEC-34-70097", "SEC Release No. 34-70097, s. 6: \"On October 29 and 30, 2012 ... all U.S. equities and options markets would be closed for those two days\"")
    else:
        problems.append("hittar inte Sandy-stycket")
    return {"hashes": hashes, "supported": supported, "problems": problems, "rule_7_2_text_found": bool(rule72), "ledger_rows": len(ledger_dates), "supported_rows": len([d for d in supported if d in ledger_dates])}


def apply(supported: dict[date, tuple[str, str]], verified_by: str, verified_date: str | None = None) -> int:
    """Fyller `verified_*` i ledgern för rader som styrks (rörs inte om raden redan har en verifierad källa). Returnerar antal fyllda rader."""
    led = nyse_sessions.read_ledger()
    day = verified_date or datetime.now(timezone.utc).date().isoformat()
    n = 0
    for i, row in led.iterrows():
        d = pd.Timestamp(row["date"]).date()
        if d in supported and not str(row["verified_source"]).strip():
            key, ref = supported[d]
            led.loc[i, "verified_source"] = f"{key}: {ref}"
            led.loc[i, "verified_by"] = verified_by
            led.loc[i, "verified_date"] = day
            n += 1
    nyse_sessions.LEDGER_FILE.write_text(led.to_csv(index=False, lineterminator="\n"), encoding="utf-8", newline="\n")
    return n


if __name__ == "__main__":
    import argparse
    import tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verified-by", default="Claude (maskinavstämning mot dokumentet; ej mänsklig granskning)")
    a = ap.parse_args()
    if a.download:
        download(a.evidence_dir)
    with tempfile.TemporaryDirectory() as tmp:
        r = verify(a.evidence_dir, Path(tmp))
    print("SHA-256:", *(f"\n  {k}: {v}" for k, v in r["hashes"].items()))
    print(f"rader som styrks: {r['supported_rows']} av {r['ledger_rows']}; Rule 7.2-texten hittad: {r['rule_7_2_text_found']}")
    for p in r["problems"]:
        print("AVVIKELSE:", p)
    if a.apply:
        if r["problems"]:
            sys.exit("avbryter: avvikelser måste redas ut före --apply")
        print("fyllda rader:", apply(r["supported"], a.verified_by))
