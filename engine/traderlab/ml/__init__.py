"""Maskininlärning med ärlig validering.

Regler:
- Features använder bara data till och med stapelns stängning.
- Etiketten för stapel t är avkastningen från öppningen t+1 till öppningen t+1+h, samma som en affär
  beslutad vid stängningen av t. Den är känd först vid stängningen av stapel t+h.
- Träning sker bara på exempel vars etikett var känd vid tidpunkten (walk-forward), och
  korsvalidering gallrar överlappande exempel och lägger till embargo (López de Prado).
"""
