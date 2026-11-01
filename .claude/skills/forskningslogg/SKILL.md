---
name: forskningslogg
description: Använd för att föra in en hypotes, ett resultat eller en lärdom i vår Obsidian-anteckningsbok, eller för att sammanfatta vad som har testats.
---

# Forskningslogg i Obsidian

`research/registry.md` är facit. Obsidian är där vi tänker: anteckningarna får länkas och
utvecklas, men de ändrar aldrig ett beslut. Följ `obsidian-markdown` för formatet och
`obsidian-bases` om en översikt ska byggas.

## Var

Lägg anteckningar i `research/TraderGO/01 Research/` i repot, så att ni båda får dem via Git.
Öppna `research/` som valv i Obsidian. Skillen `obsidian-tradergo` sätter gränserna: skriv bara
inom `research/TraderGO/`, och fråga innan något skrivs utanför.

## En anteckning per hypotes

Filnamn: `H-0001 kort namn.md`

```markdown
---
id: H-0001
status: REJECT
datum: 2026-11-01
t:
t_krav:
ren_data: false
tags: [hypotes]
---

## Idé
## Vad som hände
## Varför beslutet blev som det blev
## Vad vi lärde oss
## Relaterat
[[H-0002 kort namn]]
```

## Regler

- Siffrorna kopieras från registret och avrundas inte så att de ser bättre ut.
- Avvisade idéer får lika bra anteckningar som lyckade. De är det som hindrar oss från att
  göra om samma misstag.
- En ledtråd märks som ledtråd, inte som strategi.
- Inga API-nycklar, lösenord eller kontouppgifter i anteckningar.
