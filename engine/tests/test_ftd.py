from traderlab.data import ftd


def test_class_symbols_get_hyphen_only_when_listed_that_way():
    listed = {"BRK-B", "BF-B", "META", "GOOGL"}
    assert ftd.class_symbol("BRKB", listed) == "BRK-B"
    assert ftd.class_symbol("BFB", listed) == "BF-B"
    assert ftd.class_symbol("META", listed) == "META"
    assert ftd.class_symbol("CELG", listed) == "CELG"     # avnoterad: oförändrad


def test_xxxx_suffix_is_removed():
    from traderlab.data import ftd as f
    assert f.clean_symbol("GOOGLXXXX") == "GOOGL"
    assert f.clean_symbol("LRCXXXXX") == "LRCX"
    assert f.clean_symbol("XOM") == "XOM" and f.clean_symbol("XXXX") == "XXXX"
