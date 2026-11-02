"""Bygg en atomisk första installation för Supabase SQL Editor.

Endast för ett projekt där forskningstabellerna inte redan finns. Avbryt hellre
än att ändra okända tabeller eller policies. Ingen hemlighet behövs i SQL-filen.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
migrations = root / "supabase" / "migrations"
tables = ["candles", "funding_rates", "strategies", "hypotheses", "runs",
          "run_results", "run_trades", "research_members"]
checks = "\n".join(
    f"  if to_regclass('public.{name}') is not null then\n"
    f"    raise exception 'Tabellen public.{name} finns redan. Ingen ändring utförd.';\n"
    "  end if;" for name in tables
)
output = root / "supabase" / "research-first-install.sql"
output.write_text(
    "-- Genererad av scripts/build-research-bootstrap.py.\n"
    "-- Kör hela filen i Supabase SQL Editor för rätt projekt.\n"
    "-- Första installation; ska inte köras igen efter lyckad installation.\n"
    "begin;\nset local search_path = public;\n"
    "do $$\nbegin\n" + checks + "\nend $$;\n\n" +
    "\n\n".join((migrations / name).read_text() for name in
                   ["0001_research.sql", "0002_research_members.sql"]) +
    "\ncommit;\n", encoding="utf-8"
)
print(output)
