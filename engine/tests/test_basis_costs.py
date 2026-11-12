import io
import math
import zipfile

import pytest

from traderlab.basis_costs import (COINM_FEES, fut_taker_on, hold_cycle, implied_contract_size, margin_ratio, pre_expiry_cycle,
                                   round_trip_cost)


def test_daterade_avgifter_byter_vid_rätt_datum():
    assert fut_taker_on("2020-09-01") == 0.0004          # före 2021-04-27
    assert fut_taker_on("2021-04-27") == 0.0005
    assert fut_taker_on("2023-09-25") == 0.0005 and fut_taker_on("2023-09-26") == 0.0005
    assert [c[0] for c in COINM_FEES] == sorted(c[0] for c in COINM_FEES)


def test_kostnadsbudget_fyra_ben_och_stresspåslag():
    base = round_trip_cost()
    # spot köp 10+5, termin sälj 5+5, termin utträde 5+5, spot sälj 10+5 = 50 bp
    assert base["total_bp"] == pytest.approx(50.0)
    assert round_trip_cost(exit="settlement")["total_bp"] == pytest.approx(45.0)      # avräkning: bara takeravgift
    stressed = round_trip_cost(stress=2.5)
    assert stressed["total"] == pytest.approx(base["total"] * 2.5) and stressed["total_bp"] == pytest.approx(125.0)
    assert set(base["legs"]) == {"spot_buy", "future_sell", "future_exit", "spot_sell"}
    with pytest.raises(ValueError):
        round_trip_cost(exit="x")


def test_utan_avgifter_är_avkastningen_exakt_basis_när_kontrakten_går_jämnt_upp():
    c = hold_cycle(capital_usd=1000.0, spot0=100.0, fut0=102.0, settle=150.0, spot_end=150.0, contract_usd=10.0,
                   spot_fee=0.0, fut_taker=0.0, slippage=0.0)
    assert c.ret == pytest.approx(102.0 / 100.0 - 1, abs=1e-3)       # heltalsavrundning kostar högst ett kontrakt
    assert c.effective_leverage <= 1.0 + 1e-12
    assert c.contracts * 10.0 <= c.coins_bought * 102.0              # aldrig mer exponering än marginalen (ingen gratis hävstång)


def test_hävstången_är_högst_1_även_med_avgifter():
    c = hold_cycle(capital_usd=1e6, spot0=100.0, fut0=102.0, settle=110.0, spot_end=110.0, contract_usd=10.0)
    assert c.effective_leverage <= 1.0 + 1e-12


def test_avkastningen_beror_inte_på_riktningen_hos_priset_när_avrundningen_är_försumbar():
    kw = dict(capital_usd=1e7, spot0=100.0, fut0=102.0, contract_usd=10.0)
    up = hold_cycle(settle=300.0, spot_end=300.0, **kw)
    down = hold_cycle(settle=40.0, spot_end=40.0, **kw)
    assert up.ret == pytest.approx(down.ret, abs=0.001)               # delta-hedgad: samma utfall oavsett pris


def test_avrundningsresten_är_en_oredovisad_prisexponering_vid_litet_kapital():
    kw = dict(capital_usd=1000.0, spot0=100.0, fut0=102.0, contract_usd=10.0)
    up = hold_cycle(settle=300.0, spot_end=300.0, **kw)
    down = hold_cycle(settle=40.0, spot_end=40.0, **kw)
    assert abs(up.ret - down.ret) > 0.01                              # ett kontrakt är ~1 % av 1 000 USD: kvarvarande mynt följer priset
    # övre gräns: resten är högst ett kontrakt (10 USD vid ingång) i mynt, som rör sig med prisspannet
    residual_coins = 10.0 / 102.0
    assert abs(up.ret - down.ret) <= residual_coins * (300.0 - 40.0) / 1000.0 + 0.001


def test_hela_kapitalet_räknas_och_kostnaderna_minskar_slutvärdet():
    free = hold_cycle(capital_usd=1000.0, spot0=100.0, fut0=100.0, settle=120.0, spot_end=120.0, contract_usd=10.0, spot_fee=0, fut_taker=0, slippage=0)
    costly = hold_cycle(capital_usd=1000.0, spot0=100.0, fut0=100.0, settle=120.0, spot_end=120.0, contract_usd=10.0)
    assert free.usd_end > costly.usd_end
    assert costly.ret < 0 and costly.ret > -0.02                      # ~ −1 % kostnad utan basis, inte "gratis"


def test_marginalkvoten_är_oberoende_av_priset_vid_full_täckning():
    c = hold_cycle(capital_usd=1000.0, spot0=100.0, fut0=100.0, settle=100.0, spot_end=100.0, contract_usd=10.0,
                   spot_fee=0, fut_taker=0, slippage=0)
    for mark in (20.0, 50.0, 100.0, 400.0, 2000.0):
        r = margin_ratio(margin_coins=c.margin_coins, contracts=c.contracts, contract_usd=10.0, entry=100.0, mark=mark, mmr=0.25)
        assert r == pytest.approx(0.25, rel=1e-3)                    # 1x täckt: kvoten = MMR, aldrig nära 1
    over = margin_ratio(margin_coins=c.margin_coins, contracts=c.contracts * 3, contract_usd=10.0, entry=100.0, mark=200.0, mmr=0.025)
    assert over > 0.25                                                # tredubbel exponering ger en annan bild


def _zip_with(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("x.csv", "\n".join(",".join(str(v) for v in r) for r in rows))
    return buf.getvalue()


def test_kontraktsstorlek_härleds_ur_kontrakt_och_mynt(tmp_path):
    # 1 000 kontrakt à 10 USD vid ~2 USD = 5 000 mynt; en stapel utan volym ignoreras
    rows = [[1600000000000, 2, 2.2, 1.8, 2.0, 1000, 1600086399999, 5000.0, 10, 0, 0, 0],
            [1600086400000, 2, 2, 2, 2, 0, 1600172799999, 0, 0, 0, 0, 0]]
    p = tmp_path / "a.zip"
    p.write_bytes(_zip_with(rows))
    out = implied_contract_size([p])
    assert out["bars"] == 1 and out["median"] == pytest.approx(5000 * 2.0 / 1000)


def test_tomt_underlag_ger_noll_staplar(tmp_path):
    p = tmp_path / "e.zip"
    p.write_bytes(_zip_with([]))
    assert implied_contract_size([p]) == {"bars": 0}
    assert not math.isnan(round_trip_cost()["total"])


# ------------------------------------------------------------------ förslaget: utträde före förfall (inte avräkning)
BIG = 1e9    # så stort kapital att heltalsavrundningen är försumbar


def test_pre_expiry_utan_avgifter_ger_exakt_basisförändringen_med_separata_priser():
    for fut_exit, spot_exit in ((102.0, 100.0), (150.0, 149.0), (60.0, 61.0), (100.0, 100.0)):
        c = pre_expiry_cycle(capital_usd=BIG, spot0=100.0, fut0=103.0, fut_exit=fut_exit, spot_exit=spot_exit, contract_usd=10.0,
                             spot_fee=0.0, fut_taker=0.0, slippage=0.0)
        assert c.ret == pytest.approx((103.0 / 100.0) * (spot_exit / fut_exit) - 1, abs=1e-6)


def test_pre_expiry_noll_basis_kostar_exakt_budgeten_50_bp_med_alla_fyra_ben():
    c = pre_expiry_cycle(capital_usd=BIG, spot0=100.0, fut0=100.0, fut_exit=80.0, spot_exit=80.0, contract_usd=10.0)
    assert -c.ret == pytest.approx(round_trip_cost()["total"], abs=2e-5)           # 0,0050
    assert -c.ret * 1e4 == pytest.approx(50.0, abs=0.2)
    up = pre_expiry_cycle(capital_usd=BIG, spot0=100.0, fut0=100.0, fut_exit=300.0, spot_exit=300.0, contract_usd=10.0)
    assert -up.ret == pytest.approx(-c.ret, abs=2e-5)                               # kostnaden beror inte på prisriktningen


def test_pre_expiry_stresstest_2_5_gånger_ger_125_bp():
    c = pre_expiry_cycle(capital_usd=BIG, spot0=100.0, fut0=100.0, fut_exit=100.0, spot_exit=100.0, contract_usd=10.0,
                         spot_fee=0.001 * 2.5, fut_taker=0.0005 * 2.5, slippage=0.0005 * 2.5)
    # Kostnaderna är andelar av ett värde som krymper efter varje ben, så den bokförda kostnaden (124,2 bp) hamnar strax under den
    # additiva budgeten (125 bp): budgeten är en övre gräns, och skillnaden ska vara under 1 bp.
    assert -c.ret * 1e4 <= round_trip_cost(stress=2.5)["total_bp"] + 1e-9
    assert -c.ret * 1e4 == pytest.approx(125.0, abs=1.0)


def test_pre_expiry_är_inte_avräkning_ben_och_priser_skiljer_sig_från_hold_cycle():
    kw = dict(capital_usd=BIG, spot0=100.0, fut0=103.0, contract_usd=10.0)
    pre = pre_expiry_cycle(fut_exit=101.0, spot_exit=100.0, **kw)
    # hold_cycle har bara ett slutpris (avräkning), ingen glidning på terminsutträdet och ett ben mindre i kostnaden
    hold = hold_cycle(settle=100.0, spot_end=100.0, **kw)
    assert pre.ret < hold.ret + 0.003                       # utträdet före förfall bär basisrest (101 mot 100) och extra glidning
    assert round_trip_cost(exit="pre_expiry")["total_bp"] - round_trip_cost(exit="settlement")["total_bp"] == pytest.approx(5.0)
    assert pre.ret != pytest.approx(hold.ret, abs=1e-5)
    import inspect
    assert "fut_exit" in inspect.signature(pre_expiry_cycle).parameters and "settle" not in inspect.signature(pre_expiry_cycle).parameters


def test_pre_expiry_hävstång_högst_1_och_avrundningen_redovisas():
    c = pre_expiry_cycle(capital_usd=1000.0, spot0=100.0, fut0=102.0, fut_exit=90.0, spot_exit=88.0, contract_usd=10.0)
    assert c.effective_leverage <= 1.0 + 1e-12
    assert c.contracts * 10.0 <= c.coins_bought * 102.0
    big = pre_expiry_cycle(capital_usd=BIG, spot0=100.0, fut0=102.0, fut_exit=90.0, spot_exit=88.0, contract_usd=10.0)
    assert abs(c.ret - big.ret) > 0.0005                     # litet kapital: avrundningsresten ger en märkbar avvikelse
