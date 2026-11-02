"""Forskningsworkern som körs på servern (DigitalOcean). Bara publik marknadsdata, papper och historik.

Workern har aldrig några börsnycklar och kan inte lägga order. Den skriver till Supabase med service-nyckeln,
som bara finns i serverns miljöfil (/etc/tradergo/worker.env), aldrig i Git.
"""
