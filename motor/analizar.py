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


def rsi_serie(xs, n=14):
    out = [None] * len(xs)
    if len(xs) <= n:
        return out
    g = p = 0.0
    for i in range(1, n + 1):
        d = xs[i] - xs[i - 1]
        g += max(d, 0); p += max(-d, 0)
    g /= n; p /= n
    out[n] = 100.0 if p == 0 else 100 - 100 / (1 + g / p)
    for i in range(n + 1, len(xs)):
        d = xs[i] - xs[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n
        p = (p * (n - 1) + max(-d, 0)) / n
        out[i] = 100.0 if p == 0 else 100 - 100 / (1 + g / p)
    return out


def sma_serie(xs, n):
    out, s = [None] * len(xs), 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= n:
            s -= xs[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def senales(c, h):
    """Series completas de indicadores para poder evaluar el puntaje en cualquier día."""
    e12, e26 = ema_serie(c, 12), ema_serie(c, 26)
    macd = [a - b for a, b in zip(e12, e26)]
    return {"s50": sma_serie(c, 50), "s200": sma_serie(c, 200), "macd": macd, "senal": ema_serie(macd, 9),
            "rsi": rsi_serie(c), "h": h}


def evaluar(c, S, i, textos=True):
    """Puntaje técnico del día i usando solo datos hasta ese día. Devuelve (puntos, motivos)."""
    p, s50, s200 = c[i], S["s50"][i], S["s200"][i]
    puntos, motivos = 0, []
    def suma(n, txt):
        nonlocal puntos
        puntos += n
        if textos:
            motivos.append({"peso": n, "texto": txt()})
    if s200:
        suma(20 if p > s200 else -20, lambda: f"Precio {'sobre' if p > s200 else 'bajo'} el promedio de 200 días (tendencia de largo plazo {'alcista' if p > s200 else 'bajista'})")
    if s50:
        suma(15 if p > s50 else -15, lambda: f"Precio {'sobre' if p > s50 else 'bajo'} el promedio de 50 días")
    if s50 and s200:
        suma(15 if s50 > s200 else -15, lambda: "Promedio de 50 días " + ("sobre el de 200 (cruce dorado)" if s50 > s200 else "bajo el de 200 (cruce de la muerte)"))
    if S["macd"][i] > S["senal"][i]:
        suma(15, lambda: "MACD sobre su línea de señal (impulso al alza)")
    else:
        suma(-15, lambda: "MACD bajo su línea de señal (impulso a la baja)")
    r = S["rsi"][i]
    if r is not None:
        if r >= 70: suma(-15, lambda: f"RSI {r:.0f}: sobrecompra, riesgo de corrección")
        elif r <= 30: suma(15, lambda: f"RSI {r:.0f}: sobreventa, posible rebote")
        elif r >= 50: suma(5, lambda: f"RSI {r:.0f}: fuerza moderada")
        else: suma(-5, lambda: f"RSI {r:.0f}: debilidad moderada")
    if i >= 63:
        m3 = pct(p, c[i - 63])
        suma(10 if m3 > 0 else -10, lambda: f"Variación de 3 meses: {m3:+.1f}%")
    hi52 = max(S["h"][max(0, i - 251):i + 1])
    dist = pct(p, hi52)
    if dist is not None and dist < -40:
        suma(-5, lambda: f"A {abs(dist):.0f}% de su máximo de 52 semanas")
    return max(-100, min(100, puntos)), motivos


def tecnico(filas, bench=None):
    c = [f[1] for f in filas]
    h = [f[2] or f[1] for f in filas]
    l = [f[3] or f[1] for f in filas]
    v = [f[4] or 0 for f in filas]
    fechas_all = [datetime.fromtimestamp(f[0], timezone.utc).strftime("%Y-%m-%d") for f in filas]
    p = c[-1]
    S = senales(c, h)
    s20 = sma(c, 20)
    r = S["rsi"][-1]
    hi52, lo52 = max(h[-252:]), min(l[-252:])
    sop = sorted({round(min(l[-20:]), 2), round(min(l[-60:]), 2)}, reverse=True)
    res = sorted({round(max(h[-20:]), 2), round(max(h[-60:]), 2)})
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(len(c) - 14, len(c))]
    atr = sum(tr) / 14
    vol20 = sum(v[-20:]) / 20 if any(v[-20:]) else None
    vol60 = sum(v[-60:]) / 60 if any(v[-60:]) else None
    puntos, motivos = evaluar(c, S, len(c) - 1)
    m1 = pct(p, c[-22]) if len(c) > 22 else None
    m3 = pct(p, c[-64]) if len(c) > 64 else None

    # Bandas de Bollinger (20 días, 2 desviaciones)
    bb_sup, bb_inf = [], []
    for i in range(len(c)):
        if i < 19:
            bb_sup.append(None); bb_inf.append(None); continue
        w = c[i - 19:i + 1]; m = sum(w) / 20
        sd = (sum((x - m) ** 2 for x in w) / 20) ** 0.5
        bb_sup.append(m + 2 * sd); bb_inf.append(m - 2 * sd)
    # Fibonacci sobre el rango de 52 semanas
    fib = {k: round(hi52 - (hi52 - lo52) * k, 4) for k in (0.236, 0.382, 0.5, 0.618, 0.786)}
    # Historial del puntaje técnico (último año)
    n0 = max(0, len(c) - 252)
    hist = [evaluar(c, S, i, textos=False)[0] for i in range(n0, len(c))]
    # Fuerza relativa frente al S&P 500
    rel = None
    if bench:
        import bisect
        bf = [x[0] for x in bench]
        def bval(f):
            k = bisect.bisect_right(bf, f) - 1
            return bench[k][1] if k >= 0 else None
        def rend(dias):
            if len(c) <= dias:
                return None
            b0, b1 = bval(fechas_all[-1 - dias]), bval(fechas_all[-1])
            if b0 and b1:
                return round(pct(c[-1], c[-1 - dias]) - pct(b1, b0), 1)
            return None
        rel = {"1m": rend(21), "3m": rend(63), "1a": rend(252)}

    R = lambda xs: [None if x is None else round(x, 4) for x in xs[-252:]]
    return {
        "precio": round(p, 4), "cierre_previo": round(c[-2], 4),
        "var_dia": round(pct(p, c[-2]), 2), "var_1m": None if m1 is None else round(m1, 1),
        "var_3m": None if m3 is None else round(m3, 1),
        "var_1a": round(pct(p, c[-253]), 1) if len(c) > 253 else None,
        "sma20": s20 and round(s20, 4), "sma50": S["s50"][-1] and round(S["s50"][-1], 4),
        "sma200": S["s200"][-1] and round(S["s200"][-1], 4),
        "rsi": r and round(r, 1), "macd": round(S["macd"][-1], 4), "macd_senal": round(S["senal"][-1], 4),
        "max52": round(hi52, 4), "min52": round(lo52, 4), "atr": round(atr, 4),
        "atr_pct": round(atr / p * 100, 2), "soportes": sop, "resistencias": res,
        "volumen_rel": round(vol20 / vol60, 2) if vol20 and vol60 else None,
        "bollinger": {"sup": round(bb_sup[-1], 4), "inf": round(bb_inf[-1], 4)},
        "fibonacci": fib, "vs_sp500": rel,
        "puntaje": puntos, "motivos": motivos,
        "fechas": fechas_all[-252:], "cierres": R(c),
        "sma50s": R(S["s50"]), "sma200s": R(S["s200"]),
        "bb_sup": R(bb_sup), "bb_inf": R(bb_inf), "volumenes": [int(x) for x in v[-252:]],
        "puntajes_hist": hist,
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
    corte = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 730 * 86400))
    f["_hist_ps"] = [v for d, v in datos.get("trailingPsRatio", []) if d >= corte]
    f["_hist_fpe"] = [v for d, v in datos.get("trailingForwardPeRatio", []) if d >= corte]
    return f


def mediana(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def acotar(v, p, lo, hi):
    return None if v is None else max(p * lo, min(p * hi, v))


def proyeccion(t, f):
    """Precio proyectado a 12 meses: por valoración (múltiplos históricos) y por tendencia del último año."""
    p = t["precio"]
    c = t["cierres"]
    # Tendencia: pendiente de los últimos 3 meses (regresión del logaritmo), anualizada,
    # reducida a la mitad (las tendencias se agotan) y limitada a ±30 %
    c6 = c[-63:]
    n = len(c6)
    xs = list(range(n)); ys = [math.log(v) for v in c6]
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    anual = math.exp(b * 252) - 1
    tend = p * (1 + max(-0.3, min(0.3, anual / 2)))
    out = {"tendencia": round(tend, 2), "tendencia_anual_pct": round(anual * 100, 1)}

    val, partes = [], []
    if f and f.get("capitalizacion") and f.get("ingresos_ttm"):
        acciones = f["capitalizacion"] / p
        g = (f.get("crec_ingresos_ttm") if f.get("crec_ingresos_ttm") is not None else f.get("crec_ingresos_yoy") or 0) / 100
        g = max(-0.2, min(0.4, g))
        ventas = f["ingresos_ttm"] * (1 + g)
        hist = f["_hist_ps"][:-1]
        ps_act = f.get("precio_ventas") or f["capitalizacion"] / f["ingresos_ttm"]
        ps_obj = mediana(hist) if len(hist) >= 2 else ps_act
        ps_obj = max(ps_act * 0.75, min(ps_act * 1.33, ps_obj))
        v = acotar(ps_obj * ventas / acciones, p, 0.3, 3)
        val.append(v)
        partes.append(f"ventas a 12 meses (+{g*100:.0f}%) × precio/ventas histórico {ps_obj:.1f}")
        fpe = f.get("per_futuro")
        hfpe = [x for x in f["_hist_fpe"][:-1] if 0 < x < 100]
        if fpe and 0 < fpe < 100 and len(hfpe) >= 2:
            pe_obj = max(fpe * 0.75, min(fpe * 1.33, mediana(hfpe)))
            v2 = acotar(pe_obj * p / fpe, p, 0.3, 3)
            val.append(v2)
            partes.append(f"ganancia esperada × PER futuro histórico {pe_obj:.0f}")
    if val:
        out["valoracion"] = round(sum(val) / len(val), 2)
        out["valoracion_metodo"] = "; ".join(partes)
        central = 0.7 * out["valoracion"] + 0.3 * tend
    else:
        # Sin estados financieros (materias primas): mitad tendencia, mitad regreso al promedio de 200 días
        media = t.get("sma200") or p
        out["reversion"] = round(media, 2)
        central = 0.5 * tend + 0.5 * media
    out["central"] = round(central, 2)
    out["potencial_pct"] = round((central / p - 1) * 100, 1)
    out["resistencia"] = next((r for r in t["resistencias"] if r > p), None)
    return out


def sesgo(pt, pf):
    total = pt if pf is None else round(pt * 0.5 + pf * 0.5)
    if total >= 35: e = "Sesgo comprador"
    elif total >= 10: e = "Sesgo ligeramente positivo"
    elif total > -10: e = "Neutral / esperar"
    elif total > -35: e = "Sesgo ligeramente negativo"
    else: e = "Sesgo vendedor"
    return total, e


_CACHE = {}


def referencia(sym):
    """Serie de referencia (S&P 500 o tipo de cambio), descargada una sola vez."""
    if sym not in _CACHE:
        try:
            _, f = precios(sym)
            _CACHE[sym] = [(datetime.fromtimestamp(x[0], timezone.utc).strftime("%Y-%m-%d"), x[1]) for x in f]
        except Exception:  # noqa
            _CACHE[sym] = None
    return _CACHE[sym]


def analizar(sym):
    meta, filas = precios(sym)
    t = tecnico(filas, referencia("^GSPC"))
    f = None if sym in MATERIAS else fundamentales(sym)
    total, etiqueta = sesgo(t["puntaje"], f and f["puntaje"])
    p = t["precio"]
    proy = proyeccion(t, f)
    if f:
        f.pop("_hist_ps", None); f.pop("_hist_fpe", None)
    return {
        "simbolo": sym, "nombre": NOMBRES.get(sym) or meta.get("longName") or meta.get("shortName") or sym,
        "tipo": "materia prima" if sym in MATERIAS else "acción",
        "moneda": meta.get("currency", "USD"), "bolsa": meta.get("fullExchangeName"),
        "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fecha_precio": t["fechas"][-1],
        "tecnico": t, "fundamental": f, "puntaje_total": total, "sesgo": etiqueta, "proyeccion": proy,
        "tipo_cambio_pen": (referencia("PEN=X") or [[None, None]])[-1][1] if meta.get("currency", "USD") == "USD" else None,
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
