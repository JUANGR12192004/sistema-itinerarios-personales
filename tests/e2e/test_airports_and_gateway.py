"""Catálogo de aeropuertos y comportamiento propio del API Gateway, de punta a punta (Fase 11)."""

import httpx


def test_el_catalogo_llega_traducido_al_modelo_interno(gateway: httpx.Client) -> None:
    airports = gateway.get("/api/airports").json()

    for airport in airports:
        assert airport["iata_code"] != "N/A"  # "N/A" del proveedor → None (Adapter, 1B)
        if airport["coordinates"] is not None:  # coordenadas corregidas: rango de Colombia
            assert -5 <= airport["coordinates"]["latitude"] <= 14
            assert -82 <= airport["coordinates"]["longitude"] <= -66


def test_map_data_tiene_un_valor_por_aeropuerto_ubicado(gateway: httpx.Client) -> None:
    airports = gateway.get("/api/airports").json()
    map_data = gateway.get("/api/airports/map-data").json()

    located = [airport for airport in airports if airport["coordinates"] is not None]
    assert map_data["count"] == len(located)
    lists = [value for value in map_data.values() if isinstance(value, list)]
    assert lists and all(len(values) == map_data["count"] for values in lists)


def test_consultas_repetidas_se_sirven_desde_la_cache(gateway: httpx.Client, airport_ids: tuple[int, int]) -> None:
    url = f"/api/airports/{airport_ids[0]}"
    gateway.get(url)

    assert gateway.get(url).headers["X-Cache"] == "HIT"


def test_un_aeropuerto_inexistente_responde_404_del_servicio_sin_cambios(gateway: httpx.Client) -> None:
    response = gateway.get("/api/airports/9999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AIRPORT_NOT_FOUND"


def test_el_gateway_sirve_el_frontend_y_rechaza_rutas_desconocidas(gateway: httpx.Client) -> None:
    home = gateway.get("/")
    unknown = gateway.get("/api/no-existe")

    assert home.status_code == 200 and "text/html" in home.headers["content-type"]
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "ROUTE_NOT_FOUND"


def test_el_gateway_propaga_o_genera_el_correlation_id(gateway: httpx.Client) -> None:
    sent = gateway.get("/api/itineraries", headers={"X-Correlation-ID": "e2e-correlacion-1"})
    generated = gateway.get("/api/itineraries", headers={"X-Correlation-ID": "no es valido!"})

    assert sent.headers["X-Correlation-ID"] == "e2e-correlacion-1"
    assert generated.headers["X-Correlation-ID"] != "no es valido!"
    assert len(generated.headers["X-Correlation-ID"]) == 36  # forma de UUID
