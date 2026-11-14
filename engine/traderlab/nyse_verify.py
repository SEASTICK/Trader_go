"""Avstämning av NYSE-ledgern (research/h0024/nyse-closures-ledger.csv) mot officiella dokument. Ingen SPY-data, inga priser.

Vad som stäms av, och mot vad (dokumenten hämtas från publika adresser och låses med SHA-256 i `EVIDENCE`):
  * NYSE:s årliga handelskalendrar (PDF) för 2020 och 2022–2024: dagar fyllda med legendens färg "Exchange Holiday - Market Closed" läses ur PDF:en (ordpositioner via
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
    "NYSE-CAL-2020": {"file": "NYSE_2020_Trading_Calendar.pdf", "url": "https://www.nyse.com/publicdocs/NYSE_2020_Trading_Calendar.pdf",
                      "sha256": "17109dceb6fb078cd51905d29091e083ec074beefb79a8ac05885bcc270dac2d", "what": "NYSE 2020 Trading Calendar (Exchange Holiday - Market Closed)"},
    "NYSE-CAL-2022": {"file": "ICE_NYSE_2022_Yearly_Trading_Calendar.pdf", "url": "https://www.nyse.com/publicdocs/ICE_NYSE_2022_Yearly_Trading_Calendar.pdf",
                      "sha256": "2c2e63b780c4a373d8d546904ae46c8ba7e8070ad9357d23d2c92749985bb6c9", "what": "NYSE 2022 Trading Calendar (Exchange Holiday - Market Closed)"},
    "NYSE-CAL-2023": {"file": "ICE_NYSE_2023_Yearly_Trading_Calendar.pdf", "url": "https://www.nyse.com/publicdocs/ICE_NYSE_2023_Yearly_Trading_Calendar.pdf",
                      "sha256": "3d28b46a7197424c822087fb7117cdf3f303bd9a73f29660525b605f542bcfe2", "what": "NYSE 2023 Trading Calendar (Exchange Holiday - Market Closed)"},
    "NYSE-CAL-2024": {"file": "ICE_NYSE_2024_Yearly_Trading_Calendar.pdf", "url": "https://www.nyse.com/publicdocs/ICE_NYSE_2024_Yearly_Trading_Calendar.pdf",
                      "sha256": "02282e733512d1f112230372efccfd18f81599c682af94bb6f21fd9bccbfd145", "what": "NYSE 2024 Trading Calendar (Exchange Holiday - Market Closed)"},
    "ICE-HOL-2018-2020": {"file": "ICE_NYSE_holidays_2018-2020.pdf", "url": "https://s2.q4cdn.com/154085107/files/doc_news/archive/27aaa58b-ebcb-4f53-b505-aee992f54968.pdf",
                          "sha256": "b13c0181091b10164319992cb537e948e2d4ee8ceff71f61fdfe7989ccd89812",
                          "what": "NYSE Group press release 2017-11-27, \"2018, 2019 and 2020 holiday and early closings calendar\" (holiday table)"},
    "ICE-HOL-2019-2021": {"file": "ICE_NYSE_holidays_2019-2021.pdf", "url": "https://s2.q4cdn.com/154085107/files/doc_news/archive/15638cee-2935-4422-bcb4-a3733587eb8b.pdf",
                          "sha256": "bfc91ff0fef5ecbdce022898e1ae622579c06257918a0bb9995750dc5bafb58a",
                          "what": "NYSE Group press release 2018-12-04, \"2019, 2020 and 2021 holiday and early closings calendar\" (holiday table)"},
    "NYSE-RULES": {"file": "NYSE_Rules.pdf", "url": "https://www.nyse.com/publicdocs/nyse/regulation/nyse/NYSE_Rules.pdf",
                   "sha256": "b57592941c629f7147f8328de96540e8f91278b64b7e442dc54edb5781939a22", "what": "NYSE Rules guide (Rule 7.2; Information Memos 06-xx och 07-05; notis 2007-01-02)"},
    "FINRA-IN-2008": {"file": "FINRA_Information_Notice_2008_holidays.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p037658.pdf",
                     "sha256": "b2e5291350d86625a8bfd00f283dd8ef2f1508806d6d3e2750746ba9a913b5dd", "what": "FINRA Information Notice 12/20/07 (publicerad 2007-12-21), \"2008 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2009": {"file": "FINRA_Information_Notice_2009_holidays.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p117623.pdf",
                     "sha256": "29a7d42a4d4d17a11dd89bb12eb62643499e4a6a0a792ae63a87eecec27153cc", "what": "FINRA Information Notice 12/23/08, \"2009 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2010": {"file": "FINRA_Information_Notice_2010_holidays.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p120549.pdf",
                     "sha256": "957a6bcda8cc203cbb833e21c81bb9291aa481e92c6f9d8f038a1425b2848f7c", "what": "FINRA Information Notice 12/14/09, \"2010 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2011": {"file": "FINRA_Information_Notice_2011_holidays.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p122519.pdf",
                     "sha256": "ab3d323809581fce007d8c1ea96cc8b2ea44ba90c1a7085df23254e46fca693a", "what": "FINRA Information Notice 12/2/10, \"2011 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2012": {"file": "FINRA_Information_Notice_2012_holidays.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p125272.pdf",
                     "sha256": "05c8345cac1c879b40107e37d9dd88a79bb5e695c72cda4b52d5b90c05382601", "what": "FINRA Information Notice 12/15/11, \"2012 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2013": {"file": "FINRA_Information_Notice_2013_holidays.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p197438.pdf",
                     "sha256": "2491a7ea12354e85d4e74634a2212c2904cf6108f26e41e4d7d4720aef7d1cc2", "what": "FINRA Information Notice 12/10/12, \"2013 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2014": {"file": "FINRA_Information_Notice_2014_holidays.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p413654.pdf",
                     "sha256": "231b15b5d42962b4d17815a56456251b839ecdf1bb276ef92a86471ed09e1d65", "what": "FINRA Information Notice 12/23/13, \"2014 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2015": {"file": "FINRA_Information_Notice_2015_holidays.pdf", "url": "https://www.finra.org/sites/default/files/notice_other_file_ref/Notice_Information_122314-Holidays%202014.pdf",
                     "sha256": "837ce80480061d734883255466b0f10fa39f4cd22c4dc835db103d24595c0671", "what": "FINRA Information Notice 12/23/14, \"2015 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2016": {"file": "FINRA_Information_Notice_2016_holidays.pdf", "url": "https://www.finra.org/sites/default/files/notice_doc_file_ref/Information-Notice_122215.pdf",
                     "sha256": "a5df095c05cc3557b2735db4bbecce26158813a1c2087cc16ac9a356f701f69f", "what": "FINRA Information Notice 12/22/15, \"2016 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-IN-2017": {"file": "FINRA_Information_Notice_2017_holidays.pdf", "url": "https://www.finra.org/sites/default/files/notice_doc_file_ref/Information-Notice-121416.pdf",
                     "sha256": "9cea38b735baf56e4d67d787d09f97eee869d62ce258fd2b359ddb2c1a81647e", "what": "FINRA Information Notice 12/14/16, \"2017 Holiday Trade Date, Settlement Date and Margin Extensions Schedule\""},
    "FINRA-NTM-05-81": {"file": "NASD_NTM_05-81_2006_schedule.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p015761.pdf",
                     "sha256": "80bc00e6c6b42d3d850b8aa188f098c820f5c7d61fa33dfdb363e989fae9be23", "what": "NASD Notice to Members 05-81 (december 2005), \"2006 Trade Date–Settlement Date Schedule\""},
    "FINRA-NTM-06-73": {"file": "NASD_NTM_06-73_2007_schedule.pdf", "url": "https://www.finra.org/sites/default/files/NoticeDocument/p018163.pdf",
                     "sha256": "9019f35a1fe432a246a75d09f04c26b667696cbb06841a35f1c215e23d8a4f31", "what": "NASD Notice to Members 06-73 (december 2006), \"2007 Trade Date–Settlement Date Schedule\""},
    "NASD-UPC-092-2005": {"file": "NASD_UPC_092-2005_new_years_2006.pdf", "url": "https://www.finra.org/sites/default/files/UPCNotice/p015658_0.pdf",
                     "sha256": "c97ee3e800966ae32bd0516cdec55796e7db017e709013449444eeabef21d997", "what": "NASD Uniform Practice Advisory UPC #092-2005 (2005-12-07), \"Christmas Day and New Year's Day: Trade Date – Settlement Date Schedule\""},
    "FINRA-RN-18-39": {"file": "FINRA_Regulatory_Notice_18-39.pdf", "url": "https://www.finra.org/sites/default/files/Regulatory-Notice-18-39.pdf",
                       "sha256": "5763c6a9e7afe47aeb1b473e301713eb1877d098eb4e617c0ad557a3ba5d6d15", "what": "FINRA Regulatory Notice 18-39 (2018-12-03), \"Unexpected Close of Securities Markets\""},
    "SEC-34-70097": {"file": "34-70097.pdf", "url": "https://www.sec.gov/rules/sro/nysearca/2013/34-70097.pdf",
                     "sha256": "62d4faadddc1beee4d3e7fa6802f5284a8a983f3f8b73deb7340b840b76eb2e1", "what": "SEC Release No. 34-70097, avsnittet Events During Superstorm Sandy (s. 6)"},
}
CALENDAR_YEARS = {2020: "NYSE-CAL-2020", 2022: "NYSE-CAL-2022", 2023: "NYSE-CAL-2023", 2024: "NYSE-CAL-2024"}
# FINRA Information Notices (tillsynsmyndighetens årliga schema, ett per år) för 2008-2017: varje helgdag har en egen mening "The securities exchanges will be closed on <veckodag>, <datum>, in observance of ..."
# och en tabell med raden "Markets Closed" för samma dag. Dokumentet anger själv datumet; inget härleds ur helgdagsregler.
FINRA_NOTICES = {y: f"FINRA-IN-{y}" for y in range(2008, 2018)}
# NASD:s dokument (FINRA:s föregångare) för 2006-2008: {dokument: (hela år som dokumentet täcker, ytterligare enstaka datum som det anger, datum i de åren som det inte anger utan ett annat dokument)}.
# Samma typ av mening och tabell som i FINRA-schemana.
NASD_NOTICES = {"NASD-UPC-092-2005": ((), {date(2006, 1, 2)}, set()),
                "FINRA-NTM-05-81": ((2006,), {date(2007, 1, 1)}, {date(2006, 1, 2)}),
                "FINRA-NTM-06-73": ((2007,), {date(2008, 1, 1)}, {date(2007, 1, 1)})}
# Rader som Codex (eller en människa) har läst mot ett dokument som Claude inte kunnat öppna härifrån (nyse.com svarar 403 på automatiska anrop). Redovisas som sådana: verified_by anger vem som läste.
HUMAN_VERIFIED = {date(2018, 12, 5): {
    "source": ("NYSE Arca Options RB-18-06 / NYSE American RB-18-176 (2018-12-03), s. 1: \"Exchanges will be closed on Wednesday, December 5, 2018 in observance of a National Day of Mourning for President George H. W. Bush.\" "
               "https://www.nyse.com/publicdocs/nyse/markets/arca-options/rule-interpretations/2018/NYSE%20Arca%20Options%2018-06.pdf"),
    "by": "Codex (läste PDF:en via länken; citat och sida återgivna av SEASTICK i PR #133, kommentar 6875755443; Claude har inte kunnat öppna dokumentet, så detta är ingen maskinavstämning)", "date": "2026-11-14"}}
PRESS_RELEASES = {"ICE-HOL-2018-2020": (2018, 2019, 2020), "ICE-HOL-2019-2021": (2019, 2020, 2021)}      # årskolumnerna i respektive tabell
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


WEEKDAY = r"(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day"
DATE_RE = re.compile(WEEKDAY + r",\s+(" + "|".join(MONTH_NAMES) + r")\s+(\d{1,2})(?:,\s+(20\d\d))?")
HOLIDAY_ROWS = ["New Year", "Martin Luther King", "W a s h i n g t o n", "Good Friday", "Memorial Day", "Independence Day", "Labor Day", "Thanksgiving Day", "Christmas Day"]


def press_release_closures(text: str, years: tuple[int, ...]) -> tuple[dict[int, dict[str, date]], set[date]]:
    """Läser helgdagstabellen i ett NYSE Group-pressmeddelande: {år: {radnamn: datum}} för heldagsstängningar, och separat de datum som fotnoterna anger som tidiga stängningar
    (1:00 p.m.) och därför INTE är stängda dagar. Tabellraderna läses före första fotnoten; en rad som radbryts (\"(July 4 holiday observed)\") ger inga extra datum."""
    head, _, tail = text.partition("\n* ")
    table = head[head.index("HOLIDAY"):]
    out: dict[int, dict[str, date]] = {y: {} for y in years}
    for line in table.splitlines():
        name = next((n for n in HOLIDAY_ROWS if line.strip().startswith(n)), None)
        if not name:
            continue
        found = DATE_RE.findall(line)
        if len(found) != len(years):
            raise ValueError(f"raden '{name}' har {len(found)} datum, förväntade {len(years)}: {line.strip()[:120]}")
        for y, (month, day, _y) in zip(years, found):
            out[y][name] = date(y, MONTH_NAMES.index(month) + 1, int(day))
    flat = " ".join(("* " + tail).split())
    flat = flat.split("NYSE Group Markets holidays")[0]
    early: set[date] = set()
    for m in re.finditer(r"close early at 1:00 p\.m\.[^*]*?(?=\*|$)", flat):
        for month, day, year in re.findall(WEEKDAY + r",\s+(" + "|".join(MONTH_NAMES) + r")\s+(\d{1,2}),\s+(20\d\d)", m.group(0)):
            early.add(date(int(year), MONTH_NAMES.index(month) + 1, int(day)))
    return out, early


FULL_DATE_RE = re.compile(WEEKDAY + r",\s*(" + "|".join(MONTH_NAMES) + r")\s+(\d{1,2}),\s*(20\d\d)")
CLOSED_SENTENCE_RE = re.compile(r"(?:will be|were|is) closed on [^.]*?(?:in observance of[^.]*\.|\.)")
ROW_RE = re.compile(r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(\d{1,2})(?:,\s*20\d\d)?\s+(?:Markets?\s+Closed|N/A)\b")


def notice_closures(text: str) -> dict[date, tuple[int, str, bool]]:
    """Läser ett FINRA/NASD-schema (pdftotext -layout, sidor skilda med formfeed): {datum: (sida, mening, tabellrad)} för varje mening "... closed on <veckodag>, <månad> <dag>, <år>".
    `tabellrad` är sant om schemats tabell direkt efter meningen har en rad för samma dag där avvecklingsdagen är "Markets Closed" eller "N/A". Datumet måste stå med veckodag och år i
    meningen; tidiga stängningar och bankhelgdagar (Columbus Day, Veterans Day) ger inga datum."""
    flat = " ".join(text.replace("\f", " <<SIDA>> ").split())                                   # sidbrytning som ord (formfeed räknas som blanktecken och försvinner annars i split)
    spans = list(CLOSED_SENTENCE_RE.finditer(flat))
    out: dict[date, tuple[int, str, bool]] = {}
    for i, sent in enumerate(spans):
        page = flat.count("<<SIDA>>", 0, sent.start()) + 1
        segment = flat[sent.end(): spans[i + 1].start() if i + 1 < len(spans) else len(flat)]
        rows = {int(m.group(1)) for m in ROW_RE.finditer(segment)}
        for month, day, year in FULL_DATE_RE.findall(sent.group(0)):
            d = date(int(year), MONTH_NAMES.index(month) + 1, int(day))
            out.setdefault(d, (page, sent.group(0), d.day in rows))
    return out


def notice_problems(key: str, closures: dict[date, tuple[int, str, bool]], expected: set[date]) -> list[str]:
    """Jämför ett dokuments stängda dagar (från 2006 och framåt) med det som ledgern ska innehålla för dokumentet. Fångar saknade datum, extra datum och en dag som meningen anger men
    som saknar rad i dokumentets egen tabell."""
    problems = []
    mine = {d for d in closures if d.year >= 2006}
    if mine != expected:
        problems.append(f"{key}: dokumentet och ledgern avviker: bara i dokumentet {sorted(mine - expected)}, bara i ledgern {sorted(expected - mine)}")
    for d in sorted(mine):
        if not closures[d][2]:
            problems.append(f"{key}: meningen anger {d} som stängd men tabellen saknar raden för dagen")
    return problems


def memo_nasd_conflicts(memos: set[date], nasd: set[date]) -> list[str]:
    """NYSE:s Information Memos (regelboken) och NASD:s scheman är två oberoende källor för 2006-2007 och ska ge samma stängda dagar. Undantag: Ford-dagen 2007-01-02 kom efter NASD:s schema,
    och 2006-01-02 samt 2007-01-01 står bara i NASD:s dokument."""
    problems = [f"NYSE-memot anger {d} som stängd men NASD-schemat gör det inte" for d in sorted(memos) if d != date(2007, 1, 2) and d not in nasd]
    problems += [f"NASD-schemat anger {d} som stängd men NYSE-memot gör det inte" for d in sorted(nasd) if d.year in (2006, 2007) and d not in memos and d not in (date(2006, 1, 2), date(2007, 1, 1))]
    return problems


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
    sessions = {t.date() for t in nyse_sessions.load()}
    parsed: dict[str, dict[int, dict[str, date]]] = {}
    for key, years in PRESS_RELEASES.items():
        txt = subprocess.run(["pdftotext", "-layout", str(evidence_dir / EVIDENCE[key]["file"]), "-"], check=True, capture_output=True, text=True).stdout
        closures, early = press_release_closures(txt, years)
        parsed[key] = closures
        for e in sorted(early):
            if e not in sessions or e in ledger_dates:
                problems.append(f"{key}: {e} är en tidig stängning (1:00 p.m.) men ledgern/kalendern behandlar den som stängd")
        for y in years:
            listed = set(closures[y].values())
            ordinary = {d for d, n in zip(led["d"], led["name"]) if d.year == y and not n.startswith("Extra")}
            if listed != ordinary:
                problems.append(f"{key} {y}: tabellen och ledgerns ordinarie rader avviker: bara i tabellen {sorted(listed - ordinary)}, bara i ledgern {sorted(ordinary - listed)}")
            if y in CALENDAR_YEARS and listed != {d for d in ordinary if d.year == y}:
                problems.append(f"{key} {y}: pressmeddelandet och årskalendern avviker")
    for y in (2018, 2019, 2021):                                                              # år som bara pressmeddelandena täcker
        for key in [k for k, ys in PRESS_RELEASES.items() if y in ys]:
            for name, d in parsed[key][y].items():
                if d in ledger_dates and d not in supported:
                    other = [k for k, ys in PRESS_RELEASES.items() if y in ys and k != key]
                    extra = f" Samma datum anges också av {EVIDENCE[other[0]]['what']}." if other and parsed[other[0]][y].get(name) == d else ""
                    supported[d] = (key, f"{EVIDENCE[key]['what']}, tabellrad {name} {y}: {d.strftime('%A, %B')} {d.day}; heldagsstängning (tidiga stängningar 1:00 p.m. ingår inte).{extra}")
    for y in (2019, 2020):                                                                     # åren som anges av båda pressmeddelandena ska stämma sinsemellan
        a, b = parsed["ICE-HOL-2018-2020"][y], parsed["ICE-HOL-2019-2021"][y]
        if a != b:
            problems.append(f"pressmeddelandena avviker sinsemellan för {y}: {a} mot {b}")
    ordinary = {d for d, n in zip(led["d"], led["name"]) if not n.startswith("Extra")}

    def read_notice(key: str):
        txt = subprocess.run(["pdftotext", "-layout", str(evidence_dir / EVIDENCE[key]["file"]), "-"], check=True, capture_output=True, text=True).stdout
        return notice_closures(txt), len([pg for pg in txt.split("\f") if pg.strip()])

    notice_sets: dict[str, set[date]] = {}
    for key, expected in [(FINRA_NOTICES[y], {d for d in ordinary if d.year == y}) for y in FINRA_NOTICES] + \
            [(k, ({d for d in ordinary if d.year in years} - not_here) | extra) for k, (years, extra, not_here) in NASD_NOTICES.items()]:
        closures, pages = read_notice(key)
        problems += notice_problems(key, closures, expected)
        notice_sets[key] = {d for d in closures if d.year >= 2006}
        for d, (page, sent, row) in closures.items():
            if d in expected and d in ledger_dates and d not in supported and row:
                supported[d] = (key, f"{EVIDENCE[key]['what']}, s. {page} av {pages}: \"{sent[:170]}\" (dagen har också en tabellrad Markets Closed/N/A)")
    rules = subprocess.run(["pdftotext", "-layout", str(evidence_dir / EVIDENCE["NYSE-RULES"]["file"]), "-"], check=True, capture_output=True, text=True).stdout
    memos = memo_closures(rules, {2006, 2007})
    nasd = set().union(*(notice_sets[k] for k in NASD_NOTICES))
    problems += memo_nasd_conflicts(set(memos), nasd)
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
    rn = subprocess.run(["pdftotext", "-layout", str(evidence_dir / EVIDENCE["FINRA-RN-18-39"]["file"]), "-"], check=True, capture_output=True, text=True).stdout
    bush = re.search(r"unexpectedly close for business, for example, on the national day of mourning declared in memory of President George H\.W\. Bush on December 5, 2018", " ".join(rn.split()))
    if bush and date(2018, 12, 5) in ledger_dates and date(2018, 12, 5) not in supported:
        supported[date(2018, 12, 5)] = ("FINRA-RN-18-39", "FINRA Regulatory Notice 18-39 (2018-12-03), s. 1, tillsynsmyndighetens besked till medlemmarna: \"the securities markets may unexpectedly close for business, for example, on the national day of mourning declared in memory of President George H.W. Bush on December 5, 2018\"; "
                                        "s. 4 behandlar \"the day of closure\" som dag då \"U.S. equity exchanges would be closed\". Ett allmänt besked som anger dagen som exempel, inte börsernas egen kungörelse (den finns i HUMAN_VERIFIED).")
    elif date(2018, 12, 5) in ledger_dates and date(2018, 12, 5) not in supported:
        problems.append("hittar inte 2018-12-05-stycket i FINRA Regulatory Notice 18-39")
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
            if d in HUMAN_VERIFIED:                                                             # en människa har dessutom läst börsens egen kungörelse: båda källorna står på raden
                h = HUMAN_VERIFIED[d]
                led.loc[i, "verified_source"] += f" || Dessutom läst av en människa: {h['source']}"
                led.loc[i, "verified_by"] += f" || {h['by']}"
            n += 1
    for i, row in led.iterrows():                                   # en rad som bara en människa läst får även maskinavstämningens källa, om en sådan finns
        d = pd.Timestamp(row["date"]).date()
        src = str(row["verified_source"])
        if d in supported and src.strip() and d in HUMAN_VERIFIED and supported[d][0] not in src:
            key, ref = supported[d]
            led.loc[i, "verified_source"] = f"{src} || Dessutom maskinavstämt: {key}: {ref}"
            led.loc[i, "verified_by"] = f"{row['verified_by']} || {verified_by}"
            n += 1
    for i, row in led.iterrows():                                   # rader som en människa verifierat mot ett dokument Claude inte kunnat läsa
        d = pd.Timestamp(row["date"]).date()
        if d in HUMAN_VERIFIED and not str(row["verified_source"]).strip():
            h = HUMAN_VERIFIED[d]
            led.loc[i, "verified_source"], led.loc[i, "verified_by"], led.loc[i, "verified_date"] = h["source"], h["by"], h["date"]
            n += 1
    nyse_sessions.LEDGER_FILE.write_text(led.to_csv(index=False, lineterminator="\n"), encoding="utf-8", newline="\n")
    return n


GAPS_FILE = nyse_sessions.LEDGER_FILE.with_name("nyse-unverified-dates.md")


def gaps_markdown(led: pd.DataFrame | None = None) -> str:
    """Alla ledger-rader som saknar verifierad källa, datum för datum, grupperade per år. Genereras ur ledgern (`--write-gaps`) så att listan aldrig kan avvika från den."""
    led = nyse_sessions.read_ledger() if led is None else led
    src = led["verified_source"].astype(str).str.strip()
    open_ = led[(src == "") | (src.str.lower() == "saknas")]
    reason = ("Anledning för alla rader: inget dagsdokument från NYSE eller en tillsynsmyndighet har kunnat läsas för just datumet. Rule 7.2 och Rule 51 styrker bara regeln."
              if len(open_) else "Alla rader har en verifierad källa (dokument och hänvisning står på respektive rad i ledgern). Rule 7.2 och Rule 51 styrker bara regeln och räknas inte som källa för ett datum.")
    lines = ["# Overifierade NYSE-stängningar för H-0024 (genereras ur nyse-closures-ledger.csv)", "",
             f"{len(open_)} av {len(led)} rader saknar verifierad källa. Genereras med `python -m traderlab.nyse_verify --evidence-dir <katalog> --write-gaps`; ändra inte för hand.", "",
             reason, ""]
    for year, g in open_.groupby(pd.to_datetime(open_["date"]).dt.year):
        lines.append(f"## {year} ({len(g)})")
        lines += [f"- {r['date']} {r['name']}" for _, r in g.iterrows()]
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--write-gaps", action="store_true")
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
    if a.write_gaps:
        GAPS_FILE.write_text(gaps_markdown(), encoding="utf-8", newline="\n")
