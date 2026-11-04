# Radar de Mercados

Tablero con análisis técnico y fundamental de una lista de acciones y materias primas. Se actualiza cada día hábil a las 7:40 a. m. (hora de Lima).

- **Página:** `index.html`, publicada con GitHub Pages. Lee los datos de Supabase.
- **Base de datos:** Supabase. El esquema y la seguridad están en `supabase/esquema.sql`.
- **Motor:** `motor/analizar.py` descarga precios y estados financieros de Yahoo Finance (con retraso) y calcula promedios móviles, RSI, MACD, soportes, resistencias, crecimiento, márgenes y valoración.

```bash
python3 motor/analizar.py GC=F OUST TMDX VSH > resultado.json
```

## Puntaje

Cada activo recibe un puntaje técnico y uno fundamental de −100 a +100; el total es su promedio (solo técnico en materias primas):

| Puntaje | Sesgo |
|---|---|
| 35 o más | Sesgo comprador |
| 10 a 34 | Ligeramente positivo |
| −9 a 9 | Neutral / esperar |
| −34 a −10 | Ligeramente negativo |
| −35 o menos | Sesgo vendedor |

Es información para análisis propio, no una recomendación de inversión.
