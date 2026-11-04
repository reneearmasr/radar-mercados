#!/usr/bin/env python3
"""Prueba del puntaje técnico con datos pasados.

Para cada activo y cada día de los últimos 10 años calcula el puntaje técnico con los datos
disponibles ese día y mira qué pasó con el precio 1 y 3 meses después. Agrupa los resultados
por tendencia y los compara con el rendimiento promedio de cualquier día (la base).

Uso: python3 motor/backtest.py > data/backtest.json
El puntaje fundamental no se prueba: no hay estados financieros diarios para el pasado.
"""
import json, os, sys, time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analizar as A  # noqa: E402

UNIVERSO = ["GC=F", "OUST", "TMDX", "VSH", "SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMZN", "TSLA",
            "JPM", "XOM", "KO", "JNJ", "CAT", "GLD", "SI=F", "CL=F"]
HORIZONTES = {"1m": 21, "3m": 63}
GRUPOS = ["Tendencia alcista", "Tendencia ligeramente alcista", "Tendencia lateral",
          "Tendencia ligeramente bajista", "Tendencia bajista"]


def grupo(p):
    return A.sesgo(p, None)[1]


def precios10(sym):
    d = A.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{A.urllib.parse.quote(sym)}?range=10y&interval=1d")
    res = d["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    return [(c, h or c) for c, h in zip(q["close"], q["high"]) if c is not None]


def main():
    filas = {g: {k: [] for k in HORIZONTES} for g in GRUPOS}
    base = {k: [] for k in HORIZONTES}
    por_activo, usados = {}, []
    for sym in UNIVERSO:
        try:
            datos = precios10(sym)
        except Exception as e:  # noqa
            print(f"{sym}: {e}", file=sys.stderr)
            continue
        c = [x[0] for x in datos]; h = [x[1] for x in datos]
        if len(c) < 400:
            continue
        usados.append(sym)
        S = A.senales(c, h)
        pa = {g: [] for g in GRUPOS}
        for i in range(252, len(c) - 63, 5):  # un día de cada cinco para no contar casi lo mismo
            g = grupo(A.evaluar(c, S, i, textos=False)[0])
            for k, n in HORIZONTES.items():
                r = (c[i + n] / c[i] - 1) * 100
                filas[g][k].append(r); base[k].append(r)
            pa[g].append((c[i + 63] / c[i] - 1) * 100)
        por_activo[sym] = {g: {"n": len(v), "prom_3m": round(sum(v) / len(v), 2) if v else None} for g, v in pa.items()}
        time.sleep(0.4)

    def resumen(xs):
        if not xs:
            return {"n": 0}
        xs = sorted(xs)
        return {"n": len(xs), "promedio": round(sum(xs) / len(xs), 2), "mediana": round(xs[len(xs) // 2], 2),
                "pct_positivos": round(sum(1 for x in xs if x > 0) / len(xs) * 100, 1)}

    out = {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "activos": usados, "anios": 10,
        "base": {k: resumen(v) for k, v in base.items()},
        "grupos": {g: {k: resumen(v) for k, v in filas[g].items()} for g in GRUPOS},
        "por_activo": por_activo,
    }
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
