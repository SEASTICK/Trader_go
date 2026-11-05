from traderlab.data import ftd


def test_class_symbols_get_hyphen_only_when_listed_that_way():
    listed = {"BRK-B", "BF-B", "META", "GOOGL"}
    assert ftd.class_symbol("BRKB", listed) == "BRK-B"
    assert ftd.class_symbol("BFB", listed) == "BF-B"
    assert ftd.class_symbol("META", listed) == "META"
    assert ftd.class_symbol("CELG", listed) == "CELG"     # avnoterad: oförändrad
