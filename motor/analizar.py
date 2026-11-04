#!/usr/bin/env python3
"""Motor de analisis tecnico + fundamental (datos de Yahoo Finance, con retraso).

Uso: python3 analizar.py GC=F OUST TMDX VSH > resultado.json
Devuelve una lista JSON, un objeto por activo. No es asesoria financiera.
"""
import json, sys, time, math, urllib.request, urllib.parse
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0"}
NOMBRES = {"GC=F": "Oro (futuro)", "SI=F": "Plata (futuro)", "CL=F": "Petróleo WTI",
           "HG=F": "Cobre (futuro)", "GLD": "Oro (ETF GLD)"}
MATERIAS = {"GC=F", "SI=F", "CL=F", "HG=F", "BZ=F", "NG=F", "PL=F", "PA=F"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def precios(sym):
    d = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=2y&interval=1d")
    res = d["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    filas = [(t, c, h, l, v) for t, c, h, l, v in zip(res["timestamp"], q["close"], q["high"], q["low"], q["volume"])
             if c is not None]
    return res["meta"], filas


def sma(xs, n):
    return sum(xs[-n:]) / n if len(xs) >= n else None


def ema_serie(xs, n):
    k, out, e = 2 / (n + 1), [], None
    for x in xs:
        e = x if e is None else x * k + e * (1 - k)
        out.append(e)
    return out


def rsi(xs, n=14):
    if len(xs) <= n:
        return None
    g = p = 0.0
    for i in range(1, n + 1):
        d = xs[i] - xs[i - 1]
        g += max(d, 0); p += max(-d, 0)
    g /= n; p /= n
    for i in range(n + 1, len(xs)):
        d = xs[i] - xs[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n
        p = (p * (n - 1) + max(-d, 0)) / n
    return 100.0 if p == 0 else 100 - 100 / (1 + g / p)


def pct(a, b):
    return None if (a is None or not b) else (a / b - 1) * 100


def tecnico(filas):
    c = [f[1] for f in filas]
    h = [f[2] or f[1] for f in filas]
    l = [f[3] or f[1] for f in filas]
    v = [f[4] or 0 for f in filas]
    p = c[-1]
    s20, s50, s200 = sma(c, 20), sma(c, 50), sma(c, 200)
    e12, e26 = ema_serie(c, 12), ema_serie(c, 26)
    macd = [a - b for a, b in zip(e12, e26)]
    senal = ema_serie(macd, 9)
    r = rsi(c)
    hi52, lo52 = max(h[-252:]), min(l[-252:])
    # soportes/resistencias: minimos y maximos de los ultimos 20 y 60 dias
    sop = sorted({round(min(l[-20:]), 2), round(min(l[-60:]), 2)}, reverse=True)
    res = sorted({round(max(h[-20:]), 2), round(max(h[-60:]), 2)})
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(len(c) - 14, len(c))]
    atr = sum(tr) / 14
    vol20 = sum(v[-20:]) / 20 if any(v[-20:]) else None
    vol60 = sum(v[-60:]) / 60 if any(v[-60:]) else None

    puntos, motivos = 0, []
    def suma(n, txt):
        nonlocal puntos
        puntos += n
        motivos.append({"peso": n, "texto": txt})

    if s200:
        suma(20 if p > s200 else -20, f"Precio {'sobre' if p > s200 else 'bajo'} el promedio de 200 días (tendencia de largo plazo {'alcista' if p > s200 else 'bajista'})")
    if s50:
        suma(15 if p > s50 else -15, f"Precio {'sobre' if p > s50 else 'bajo'} el promedio de 50 días")
    if s50 and s200:
        suma(15 if s50 > s200 else -15, "Promedio de 50 días " + ("sobre el de 200 (cruce dorado)" if s50 > s200 else "bajo el de 200 (cruce de la muerte)"))
    if macd[-1] > senal[-1]:
        suma(15, "MACD sobre su línea de señal (impulso al alza)")
    else:
        suma(-15, "MACD bajo su línea de señal (impulso a la baja)")
    if r is not None:
        if r >= 70: suma(-15, f"RSI {r:.0f}: sobrecompra, riesgo de corrección")
        elif r <= 30: suma(15, f"RSI {r:.0f}: sobreventa, posible rebote")
        elif r >= 50: suma(5, f"RSI {r:.0f}: fuerza moderada")
        else: suma(-5, f"RSI {r:.0f}: debilidad moderada")
    m1 = pct(p, c[-22]) if len(c) > 22 else None
    m3 = pct(p, c[-64]) if len(c) > 64 else None
    if m3 is not None:
        suma(10 if m3 > 0 else -10, f"Variación de 3 meses: {m3:+.1f}%")
    dist_hi = pct(p, hi52)
    if dist_hi is not None and dist_hi < -40:
        suma(-5, f"A {abs(dist_hi):.0f}% de su máximo de 52 semanas")

    serie = [[datetime.fromtimestamp(f[0], timezone.utc).strftime("%Y-%m-%d"), round(f[1], 4)] for f in filas[-252:]]
    s50s = [None if i < 49 else sum(c[i - 49:i + 1]) / 50 for i in range(len(c))][-252:]
    s200s = [None if i < 199 else sum(c[i - 199:i + 1]) / 200 for i in range(len(c))][-252:]
    return {
        "precio": round(p, 4), "cierre_previo": round(c[-2], 4),
        "var_dia": round(pct(p, c[-2]), 2), "var_1m": None if m1 is None else round(m1, 1),
        "var_3m": None if m3 is None else round(m3, 1),
        "var_1a": round(pct(p, c[-253]), 1) if len(c) > 253 else None,
        "sma20": s20 and round(s20, 4), "sma50": s50 and round(s50, 4), "sma200": s200 and round(s200, 4),
        "rsi": r and round(r, 1), "macd": round(macd[-1], 4), "macd_senal": round(senal[-1], 4),
        "max52": round(hi52, 4), "min52": round(lo52, 4), "atr": round(atr, 4),
        "atr_pct": round(atr / p * 100, 2), "soportes": sop, "resistencias": res,
        "volumen_rel": round(vol20 / vol60, 2) if vol20 and vol60 else None,
        "puntaje": max(-100, min(100, puntos)), "motivos": motivos,
        "fechas": [s[0] for s in serie], "cierres": [s[1] for s in serie],
        "sma50s": [None if x is None else round(x, 4) for x in s50s],
        "sma200s": [None if x is None else round(x, 4) for x in s200s],
    }


TIPOS = ["quarterlyTotalRevenue", "quarterlyGrossProfit", "quarterlyNetIncome", "quarterlyDilutedEPS",
         "quarterlyOperatingIncome", "quarterlyCashCashEquivalentsAndShortTermInvestments", "quarterlyTotalDebt",
         "quarterlyFreeCashFlow", "trailingPeRatio", "trailingForwardPeRatio", "trailingPsRatio",
         "trailingMarketCap", "trailingPbRatio"]


def fundamentales(sym):
    url = ("https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
           f"{urllib.parse.quote(sym)}?type={','.join(TIPOS)}&period1=1640995200&period2={int(time.time()) + 86400}")
    d = get(url)
    datos = {}
    for r in d["timeseries"]["result"]:
        t = r["meta"]["type"][0]
        vals = [(x["asOfDate"], x["reportedValue"]["raw"]) for x in (r.get(t) or []) if x and x.get("reportedValue")]
        if vals:
            datos[t] = sorted(vals)
    if not datos.get("quarterlyTotalRevenue"):
        return None

    def ult(t):
        return datos[t][-1][1] if datos.get(t) else None

    rev = datos["quarterlyTotalRevenue"]
    trimestres = []
    for fecha, val in rev[-8:]:
        def en(t):
            return next((v for f, v in datos.get(t, []) if f == fecha), None)
        gp, ni = en("quarterlyGrossProfit"), en("quarterlyNetIncome")
        trimestres.append({"fecha": fecha, "ingresos": val, "margen_bruto": round(gp / val * 100, 1) if gp and val else None,
                           "utilidad_neta": ni, "eps": en("quarterlyDilutedEPS")})
    yoy = None
    if len(rev) >= 5:
        yoy = pct(rev[-1][1], rev[-5][1])
    ttm = sum(v for _, v in rev[-4:]) if len(rev) >= 4 else None
    ttm_ant = sum(v for _, v in rev[-8:-4]) if len(rev) >= 8 else None
    ni = datos.get("quarterlyNetIncome", [])
    ttm_ni = sum(v for _, v in ni[-4:]) if len(ni) >= 4 else None
    caja, deuda = ult("quarterlyCashCashEquivalentsAndShortTermInvestments"), ult("quarterlyTotalDebt")

    f = {"trimestres": trimestres, "crec_ingresos_yoy": yoy and round(yoy, 1),
         "crec_ingresos_ttm": round(pct(ttm, ttm_ant), 1) if ttm and ttm_ant else None,
         "ingresos_ttm": ttm, "utilidad_ttm": ttm_ni,
         "per": ult("trailingPeRatio"), "per_futuro": ult("trailingForwardPeRatio"),
         "precio_ventas": ult("trailingPsRatio"), "precio_libros": ult("trailingPbRatio"),
         "capitalizacion": ult("trailingMarketCap"), "caja": caja, "deuda": deuda,
         "fcf_ult": ult("quarterlyFreeCashFlow")}

    puntos, motivos = 0, []
    def suma(n, txt):
        nonlocal puntos
        puntos += n
        motivos.append({"peso": n, "texto": txt})
    if yoy is not None:
        if yoy > 20: suma(25, f"Ingresos crecen {yoy:.0f}% vs. el mismo trimestre del año anterior")
        elif yoy > 5: suma(10, f"Ingresos crecen {yoy:.0f}% interanual")
        elif yoy > -5: suma(0, f"Ingresos estables ({yoy:+.0f}% interanual)")
        else: suma(-20, f"Ingresos caen {abs(yoy):.0f}% interanual")
    mb = [t["margen_bruto"] for t in trimestres if t["margen_bruto"] is not None]
    if len(mb) >= 5:
        dm = mb[-1] - mb[-5]
        suma(10 if dm > 1 else (-10 if dm < -1 else 0), f"Margen bruto {mb[-1]:.0f}% ({dm:+.1f} pts vs. hace un año)")
    if ttm_ni is not None:
        if ttm_ni > 0: suma(15, "Rentable en los últimos 12 meses")
        else: suma(-15, "Con pérdidas en los últimos 12 meses")
        if len(ni) >= 5:
            suma(10 if ni[-1][1] > ni[-5][1] else -10,
                 "Utilidad del trimestre " + ("mejora" if ni[-1][1] > ni[-5][1] else "empeora") + " frente a hace un año")
    if caja is not None and deuda is not None:
        suma(10 if caja > deuda else -10, "Caja " + ("mayor" if caja > deuda else "menor") + " que la deuda")
    per = f["per"]
    if per and per > 0:
        if per > 60: suma(-15, f"Valoración exigente: PER {per:.0f}")
        elif per < 15: suma(10, f"Valoración baja: PER {per:.0f}")
        else: suma(0, f"PER {per:.0f}")
    elif f["precio_ventas"]:
        ps = f["precio_ventas"]
        suma(-15 if ps > 10 else (0 if ps > 3 else 10), f"Precio/ventas {ps:.1f}")
    f["puntaje"] = max(-100, min(100, puntos))
    f["motivos"] = motivos
    return f


def sesgo(pt, pf):
    total = pt if pf is None else round(pt * 0.5 + pf * 0.5)
    if total >= 35: e = "Sesgo comprador"
    elif total >= 10: e = "Sesgo ligeramente positivo"
    elif total > -10: e = "Neutral / esperar"
    elif total > -35: e = "Sesgo ligeramente negativo"
    else: e = "Sesgo vendedor"
    return total, e


def analizar(sym):
    meta, filas = precios(sym)
    t = tecnico(filas)
    f = None if sym in MATERIAS else fundamentales(sym)
    total, etiqueta = sesgo(t["puntaje"], f and f["puntaje"])
    p = t["precio"]
    return {
        "simbolo": sym, "nombre": NOMBRES.get(sym) or meta.get("longName") or meta.get("shortName") or sym,
        "tipo": "materia prima" if sym in MATERIAS else "acción",
        "moneda": meta.get("currency", "USD"), "bolsa": meta.get("fullExchangeName"),
        "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fecha_precio": t["fechas"][-1],
        "tecnico": t, "fundamental": f, "puntaje_total": total, "sesgo": etiqueta,
        "niveles": {"stop_referencial": round(p - 2 * t["atr"], 4), "objetivo_referencial": round(p + 3 * t["atr"], 4)},
    }


if __name__ == "__main__":
    out = []
    for s in sys.argv[1:]:
        try:
            out.append(analizar(s.upper()))
        except Exception as e:  # noqa
            out.append({"simbolo": s.upper(), "error": str(e)})
        time.sleep(0.5)
    json.dump(out, sys.stdout, ensure_ascii=False)
