from mcp_server.server import classify_lab


def test_normal():
    result = classify_lab(10, 5, 15)
    assert result["severity"] == "Normal"
    assert result["route_order"] == 3


def test_warning_low():
    result = classify_lab(4, 5, 15)
    assert result["severity"] == "Warning"
    assert result["route_order"] == 2


def test_critical_high():
    result = classify_lab(30, 5, 15)
    assert result["severity"] == "Critical"
    assert result["route_order"] == 1
