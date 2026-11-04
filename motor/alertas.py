#!/usr/bin/env python3
"""Revisa precios en horario de bolsa y lista las alertas nuevas.

Uso: python3 -I motor/alertas.py <activos.json> <cartera.json> <ya_enviadas.json>
  activos.json:     lista de activos (el archivo de datos descifrado).
  cartera.json:     lista de compras [{simbolo, stop}, ...] (puede ser []).
  ya_enviadas.json: lista de claves de alertas ya enviadas (puede ser []).
Imprime un JSON: [{clave, simbolo, texto}, ...]. Cada clave incluye la fecha, así que
cada alerta suena como máximo una vez por día.
"""
import json, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

LIMA = timezone(timedelta(hours=-5))


def precio(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=1d&interval=5m"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        m = json.loads(r.read().decode())["chart"]["result"][0]["meta"]
    return m.get("regularMarketPrice"), m.get("chartPreviousClose") or m.get("previousClose")


def fmt(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    activos = json.load(open(sys.argv[1]))
    cartera = json.load(open(sys.argv[2]))
    enviadas = set(json.load(open(sys.argv[3])))
    hoy = datetime.now(LIMA).strftime("%Y-%m-%d")
    stops = {}
    for c in cartera:
        if c.get("stop"):
            stops.setdefault(c["simbolo"], []).append(float(c["stop"]))
    out = []

    def alerta(clave, sym, texto):
        k = f"{hoy}:{sym}:{clave}"
        if k not in enviadas:
            out.append({"clave": k, "simbolo": sym, "texto": texto})

    for a in activos:
        if "error" in a:
            continue
        s = a["simbolo"]
        try:
            p, prev = precio(s)
        except Exception as e:  # noqa
            alerta("sin-datos", s, f"{s}: no se pudo leer el precio ({e}).")
            continue
        if not p:
            continue
        t = a["tecnico"]
        var = (p / prev - 1) * 100 if prev else 0
        if abs(var) >= 5:
            alerta("mov5", s, f"{s} se mueve {var:+.1f}% hoy ({fmt(p)}).")
        for r in t.get("resistencias", []):
            if r > t["precio"] and p >= r:
                alerta(f"res-{r}", s, f"{s} supera la resistencia {fmt(r)} (ahora {fmt(p)}).")
        for sp in t.get("soportes", []):
            if sp < t["precio"] and p <= sp:
                alerta(f"sop-{sp}", s, f"{s} perfora el soporte {fmt(sp)} (ahora {fmt(p)}).")
        obj = (a.get("objetivo_analistas") or {}).get("promedio") or (a.get("proyeccion") or {}).get("central")
        if obj and t["precio"] < obj <= p:
            alerta("objetivo", s, f"{s} alcanza su precio objetivo {fmt(obj)} (ahora {fmt(p)}).")
        for st in stops.get(s, []):
            if p <= st:
                alerta(f"stop-{st}", s, f"{s} toca tu stop de {fmt(st)} (ahora {fmt(p)}).")
            elif p <= st * 1.03:
                alerta(f"cerca-stop-{st}", s, f"{s} está a menos de 3% de tu stop de {fmt(st)} (ahora {fmt(p)}).")
        time.sleep(0.4)
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
