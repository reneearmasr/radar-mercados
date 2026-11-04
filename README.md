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

## Precio objetivo a 12 meses

- **Analistas / bancos:** consenso publicado, buscado en la web en cada actualización (con fuente y fecha).
- **Proyección del Radar:** modelo propio. Acciones: 70 % valoración (ventas esperadas × precio/ventas histórico de 2 años, y ganancia esperada × PER futuro histórico) y 30 % tendencia de 3 meses (a la mitad, máximo ±30 %). Materias primas: 50 % tendencia y 50 % regreso al promedio de 200 días.
- **Resistencia técnica:** próximo máximo reciente por encima del precio.

Es información para análisis propio, no una recomendación de inversión.
