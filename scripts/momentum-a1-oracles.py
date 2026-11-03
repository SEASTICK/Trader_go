#!/usr/bin/env python3
"""Räknar om de handräknade kontrollfallen i momentumprotokollets A1-utkast och skriver/kontrollerar orakelfilen.

Endast syntetiska tal, ingen marknadshistorik. Detta är en oberoende räknekontroll av kontraktets formler,
inte strategimotorn. Ledgern är kontantekvivalent C och enheter q: E = C + q*M.
"""
import argparse
import json
import math
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'docs/momentum-a1-orakel.json'
C16 = 0.0016  # (10 + 2/2 + 5) / 10 000


def size(E, q_old, P, M, w, c=C16):
    """K04: q_new med q_new*M = w*E_after. Grenen väljs från den kostnadsfria lösningen; inkonsekvent gren avvisas."""
    if not (E > 0 and P > 0 and M > 0):
        raise ValueError('Icke-positivt kapital eller pris')
    if w == 0:
        return 0.0
    q0 = w * (E - q_old * (M - P)) / (M - w * (M - P))
    if q0 == q_old:
        return q_old
    k = M - P - c * P if q0 > q_old else M - P + c * P
    den = M - w * k
    q = w * (E - q_old * k) / den
    if den <= 0 or (q0 > q_old) != (q > q_old) or q * w < 0:
        raise ValueError('Ingen konsekvent lösning')
    return q


def trade(C, q_old, q_new, P, c=C16):
    """Bokför affären en gång: C minskar med delta_q*P och kostnaden c*P*|delta_q|."""
    d = q_new - q_old
    return C - d * P - c * P * abs(d), c * P * abs(d)


def fund(C, q, M_ref, rate, stress=False):
    pay = q * M_ref * rate
    if stress and pay > 0:
        pay *= 2
    return C - pay, pay


def liq_mark(C, q, mmr):
    """Korsmarginal: likvidation när C + q*m <= mmr*|q|*m. Long: m <= -C/(q(1-mmr)); short: m >= C/(|q|(1+mmr))."""
    return -C / (q * (1 - mmr)) if q > 0 else C / (-q * (1 + mmr))


def fill(E, C, q_old, P, M, w, c=C16):
    q = size(E, q_old, P, M, w, c)
    C2, cost = trade(C, q_old, q, P, c)
    E2 = C2 + q * M
    return {'q': q, 'cost': cost, 'C': C2, 'E_after': E2, 'weight_after': q * M / E2 if q else 0.0}


def cases():
    out = {}
    # O1 Codex avgiftsorakel och O2 målvikt 1 efter avgift.
    o1 = fill(100_000, 100_000, 0, 100, 100, 0.5)
    o2 = fill(100_000, 100_000, 0, 100, 100, 1.0)
    out['O1_avgift_w05'] = o1
    out['O2_avgift_w1'] = {**o2, 'naiv_q1000_vikt': 1000 * 100 / (100_000 - C16 * 100 * 1000)}
    # O3 basis: kontraktspris 100, markpris 99,5.
    out['O3_basis'] = {**fill(100_000, 100_000, 0, 100, 99.5, 0.5), 'basisresultat': fill(100_000, 100_000, 0, 100, 99.5, 0.5)['q'] * (99.5 - 100)}
    # O4 partialköp vid 110 till 0,60 och partialsälj vid 105 till 0,40, från O1.
    C, q = o1['C'], o1['q']
    E = C + q * 110
    b = fill(E, C, q, 110, 110, 0.60)
    E2 = b['C'] + b['q'] * 105
    s = fill(E2, b['C'], b['q'], 105, 105, 0.40)
    out['O4_partial'] = {'E_fore_kop': E, 'vikt_fore_kop': q * 110 / E, 'kop': b,
                         'E_fore_salj': E2, 'vikt_fore_salj': b['q'] * 105 / E2, 'salj': s}
    # O5 funding och handel på samma gräns, scenario A (funding före) och B (efter).
    rate = 0.0001
    a_in = fill(100_000, 100_000, 0, 100, 100, 0.5)  # q_old = 0 betalar inget i A
    b_C, b_pay = fund(a_in['C'], a_in['q'], 100, rate)
    q5, C5 = o1['q'], o1['C']
    aC, apay = fund(C5, q5, 100, rate)
    aC2, acost = trade(aC, q5, 0, 100)
    bC2, bcost = trade(C5, q5, 0, 100)
    out['O5_funding_samma_grans'] = {
        'inträde_A': {'funding': 0.0, 'E': a_in['E_after']},
        'inträde_B': {'funding': b_pay, 'E': b_C + a_in['q'] * 100},
        'utgång_A': {'funding': apay, 'E': aC2}, 'utgång_B': {'funding': 0.0, 'E': bC2}}
    # O6 dagsreset med väntande riskexit.
    C6, q6 = 50_000, 1000
    E_close = C6 + q6 * 47.9
    day = E_close / 100_000 - 1
    w_cur = q6 * 47.9 / E_close
    A_C, A_pay = fund(C6, q6, 47.5, rate)
    A_end, A_cost = trade(A_C, q6, 0, 47.55)
    B_end, B_cost = trade(C6, q6, 0, 47.55)
    out['O6_dagsreset'] = {'E_close_D': E_close, 'dagsavkastning_D': day, 'dagsstopp': day <= -0.02,
                           'vikt_vid_beslut': w_cur, 'normal_avsikt_strykt': True, 'day_start_D1': E_close,
                           'A': {'funding': A_pay, 'kostnad': A_cost, 'E_efter': A_end, 'dag_D1_hittills': A_end / E_close - 1},
                           'B': {'funding': 0.0, 'kostnad': B_cost, 'E_efter': B_end}}
    # O7 intrastapel-bound för huvudmodellen (q konstant inom stapeln).
    C7, q7, peak = 50_000, 500, 105_000
    o, h, l, cl = 100, 112, 95, 101
    E_o, E_h, E_l, E_c = (C7 + q7 * m for m in (o, h, l, cl))
    bpeak = max(peak, E_o, E_h)
    out['O7_intrastapel_main'] = {'E_open': E_o, 'E_high': E_h, 'E_low': E_l, 'E_close': E_c,
                                  'bound_peak': bpeak, 'bound_dd': E_l / bpeak - 1, 'close_dd': E_c / peak - 1}
    # O8 legacy long med ATR-stop: stop inom stapeln och gap förbi stop.
    C8, q8, S = 10_000, 900, 95
    exit_C, exit_cost = trade(C8, q8, 0, min(100, S))
    pts = {'E_mark_open': C8 + q8 * 99.9, 'E_mark_high': C8 + q8 * 101, 'E_mark_low_om_öppen': C8 + q8 * 92.5,
           'E_efter_stop': exit_C, 'stopkostnad': exit_cost}
    pts['bound_trough'] = min(pts['E_mark_low_om_öppen'], pts['E_efter_stop'])
    gap_C, gap_cost = trade(C8, q8, 0, 94)
    out['O8_legacy_stop'] = {'inom_stapel': pts,
                             'gap': {'E_mark_open': C8 + q8 * 93.9, 'E_efter_fyllning': gap_C, 'kostnad': gap_cost,
                                     'bound_trough': min(C8 + q8 * 93.9, gap_C)}}
    # O9 main mot new_mix: cap 0,9 och signaler (1,0,0).
    m = fill(100_000, 100_000, 0, 100, 100, 0.3)
    sub = fill(100_000 / 3, 100_000 / 3, 0, 100, 100, 0.9)
    up_main = m['C'] + m['q'] * 110
    up_sub = sub['C'] + sub['q'] * 110
    dn_main = m['C'] + m['q'] * 97.7
    dn_sub = sub['C'] + sub['q'] * 97.7
    out['O9_main_mot_new_mix'] = {
        'main': m, 'mom7_delkonto': sub,
        'upp_110': {'main_vikt': m['q'] * 110 / up_main, 'main_band': abs(0.3 - m['q'] * 110 / up_main) >= 0.02,
                    'mom7_vikt': sub['q'] * 110 / up_sub, 'mom7_band': abs(0.9 - sub['q'] * 110 / up_sub) >= 0.02},
        'ned_97_7': {'main_dag': dn_main / m['E_after'] - 1, 'mom7_dag': dn_sub / sub['E_after'] - 1,
                     'main_dagsstopp': dn_main / m['E_after'] - 1 <= -0.02, 'mom7_dagsstopp': dn_sub / sub['E_after'] - 1 <= -0.02}}
    # O10 första och sista dag.
    term_C, term_cost = trade(60_000, 400, 0, 95.1)
    out['O10_horisont'] = {'startkapital': 100_000.0, 'dagar': 365 + 365 + 366, 'terminal_E': term_C,
                           'terminal_kostnad': term_cost, 'E_fore_terminal': 60_000 + 400 * 95}
    # O11 likvidationsgräns i den avgränsade korsmarginalmodellen.
    sh = fill(100_000, 100_000, 0, 100, 100, -1.0)
    out['O11_likvidation'] = {'legacy_short_w-1': {**sh, 'mark_mmr_0_05': liq_mark(sh['C'], sh['q'], 0.05),
                                                    'mark_mmr_0_005': liq_mark(sh['C'], sh['q'], 0.005)},
                              'main_long_w1': {'C': o2['C'], 'mark_mmr_0_05': liq_mark(o2['C'], o2['q'], 0.05),
                                               'efter_betald_funding_500': liq_mark(o2['C'] - 500, o2['q'], 0.05)}}
    # O12 målvikt från planens exempel och lika pris ger 0.
    out['O12_mal'] = {'w': (2 / 3) * min(1, 0.10 / 0.60), 'lika_pris_signal': int(100 / 100 - 1 > 0)}
    # O5b kapitalfaser i scenario B: identitet och cap mot E_trade, drift efter funding mot E_post.
    E_post = b_C + a_in['q'] * 100
    out['O5b_kapitalfaser_B'] = {'q': a_in['q'], 'E_trade': a_in['E_after'], 'vikt_after_trade': a_in['weight_after'],
                                 'funding': b_pay, 'E_post': E_post, 'vikt_after_funding_B': a_in['q'] * 100 / E_post,
                                 'cap': 0.5, 'cap_kontroll_after_trade': a_in['weight_after'] <= 0.5 + 1e-12}
    # O13 Codex motexempel: ekonomiskt sämre avkastning kan ge högre Sharpe.
    sharpe = lambda r: statistics.mean(r) / statistics.stdev(r) * math.sqrt(365)
    orig, worse = [0.010, 0.011, 0.009, 0.100], [0.010, 0.011, 0.009, 0.010]
    out['O13_sharpe_ej_monoton'] = {'original': sharpe(orig), 'ekonomiskt_samre': sharpe(worse),
                                    'samre_ger_hogre_sharpe': sharpe(worse) > sharpe(orig)}
    # O14 reduce-only: riskavsikt till frusen vikt 0,195 från C=800, q=2 (vikt 0,20 vid close 100).
    out['O14_reduce_only'] = {f'open_{px}': risk_fill(800, 2, px, px, 0.195) for px in (90, 110)}
    # O15 normalavsikt sälj till 0,15 blir köp efter gap ned till 70; riskavsikt samtidigt stryker normal.
    n = fill(800 + 2 * 70, 800, 2, 70, 70, 0.15)
    out['O15_normal_efter_gap'] = {'vikt_vid_beslut': 2 * 100 / 1000, 'vikt_vid_open': 2 * 70 / 940, 'fyllning': n,
                                   'riktning': 'köp' if n['q'] > 2 else 'sälj',
                                   'med_samtidig_riskavsikt': 'normal strykt, riskavsikt fylls reduce-only'}
    # O16 exakta fundingtider kring fyllningen 2022-01-02 00:00 (q 0 -> 500, M=P=100, ränta 0,0001).
    T = datetime(2022, 1, 2, tzinfo=timezone.utc)
    q_old, q_new = 0.0, 500.0
    events = {'samtidig_exakt_T': T, 'plus_30s': T + timedelta(seconds=30), 'minus_30s': T - timedelta(seconds=30)}
    rows = {}
    for name, t in events.items():
        kind = funding_kind(t, T)
        pay = {'A': q_old * 100 * rate if kind == 'samtidig' else (q_new if t > T else q_old) * 100 * rate}
        pay['B'] = q_new * 100 * rate if kind == 'samtidig' else pay['A']
        rows[name] = {'tid': t.isoformat(), 'typ': kind, 'dag': (t.date()).isoformat(),
                      'efter_fyllning': t > T, 'betalt_A': pay['A'], 'betalt_B': pay['B']}
    start, term = datetime(2022, 1, 1, tzinfo=timezone.utc), datetime(2024, 12, 31, 20, tzinfo=timezone.utc)
    rows['forsta_exakt_2022_01_01'] = {'typ': funding_kind(start, start), 'q_A': 'q_old = 0', 'q_B': 'första q_new'}
    rows['fore_start_2021_12_31_23_59_30'] = {'bokfors': False, 'skal': 'före startpunkten, q = 0'}
    rows['exakt_terminal_2024_12_31_20'] = {'typ': funding_kind(term, term), 'q_A': 'q_old', 'q_B': '0 efter terminal'}
    rows['efter_terminal_20_00_30'] = {'typ': funding_kind(term + timedelta(seconds=30), term), 'q': 0}
    out['O16_fundingtider'] = rows
    return out


def funding_kind(t, T):
    """D18: bara exakt samma tid som fyllningen är samtidig; allt annat är en kronologisk mellanhändelse."""
    return 'samtidig' if t == T else 'mellan'


def risk_fill(C, q_old, P, M, w, c=C16):
    """D17: riskavsikt är reduce-only. Lösarens q* används bara om den inte ökar |q|."""
    E = C + q_old * M
    q_star = size(E, q_old, P, M, w, c)
    hold = abs(q_star) > abs(q_old) or q_star * q_old < 0
    q = q_old if hold else q_star
    C2, cost = trade(C, q_old, q, P, c)
    return {'vikt_vid_open': q_old * M / E, 'q_star': q_star, 'risk_reduce_only_hold': hold, 'q': q,
            'cost': cost, 'E_trade': C2 + q * M, 'vikt_after_trade': q * M / (C2 + q * M)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true', help='Fail if the oracle file is stale')
    args = p.parse_args()
    text = json.dumps(cases(), ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != text:
            raise SystemExit('Orakel inaktuellt; kör python3 scripts/momentum-a1-oracles.py')
    else:
        TARGET.write_text(text)
    print('PASS: momentum A1-orakel omräknade från kontraktets formler')


if __name__ == '__main__':
    main()
