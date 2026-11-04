# Radar de Mercados

Tablero con análisis técnico y fundamental de una lista de acciones y materias primas. Se actualiza cada día hábil a las 7:40 a. m. (hora de Lima).

- **Página:** `index.html`, publicada con GitHub Pages. Lee los datos de Supabase.
- **Base de datos:** Supabase, con acceso solo para el dueño (inicio de sesión). Tablas: activos, historial, cartera, solicitudes, estudios.
- **Datos cifrados:** el repositorio es público, así que `data/activos.enc` va cifrado (AES-256, `motor/cifrar.sh`); Supabase lo descifra al cargarlo con `public.cargar_activos()`.
- **Motor:** `motor/analizar.py` descarga precios y estados financieros de Yahoo Finance (con retraso) y calcula promedios móviles, RSI, MACD, soportes, resistencias, crecimiento, márgenes y valoración.

```bash
python3 motor/analizar.py GC=F OUST TMDX VSH > resultado.json   # análisis
python3 motor/backtest.py > data/backtest.json                    # prueba del puntaje (10 años)
python3 motor/alertas.py activos.json cartera.json enviadas.json  # alertas en horario de bolsa
```

Incluye: promedios móviles, RSI, MACD, bandas de Bollinger, Fibonacci, volumen, fuerza frente al S&P 500, precio en soles, historial diario del puntaje y precio objetivo.

## Puntaje

Cada activo recibe un puntaje técnico y uno fundamental de −100 a +100; el total es su promedio (solo técnico en materias primas):

| Puntaje | Tendencia |
|---|---|
| 35 o más | Tendencia alcista |
| 10 a 34 | Ligeramente alcista |
| −9 a 9 | Lateral |
| −34 a −10 | Ligeramente bajista |
| −35 o menos | Tendencia bajista |

## Precio objetivo a 12 meses

- **Analistas / bancos:** consenso publicado, buscado en la web en cada actualización (con fuente y fecha).
- **Proyección del Radar:** modelo propio. Acciones: 70 % valoración (ventas esperadas × precio/ventas histórico de 2 años, y ganancia esperada × PER futuro histórico) y 30 % tendencia de 3 meses (a la mitad, máximo ±30 %). Materias primas: 50 % tendencia y 50 % regreso al promedio de 200 días.
- **Resistencia técnica:** próximo máximo reciente por encima del precio.

## Método Value Investing

Valor intrínseco por acción, como promedio de dos métodos, comparado con el precio (margen de seguridad):

- **Flujo de caja descontado (DCF):** flujo de caja libre base (el menor entre los últimos 12 meses y el último año), crecimiento igual al de las ventas (máximo 15 %) por 5 años, que baja a 2,5 % al año 10; tasa de descuento de 10 % (12 % si la empresa reporta en una moneda distinta al dólar); se resta la deuda neta.
- **Número de Graham:** √(22,5 × utilidad por acción de 12 meses × valor en libros por acción).

No aplica a materias primas ni a empresas con pérdidas o flujo de caja negativo. Los estados en otra moneda (por ejemplo, soles) se convierten a la moneda de cotización.

## ¿Funciona el puntaje?

`motor/backtest.py` probó el puntaje técnico en 20 activos durante 10 años. No anticipó subidas: después de una "tendencia bajista" el rendimiento a 3 meses fue mayor que el promedio, y después de una "tendencia alcista", menor. Sirve para describir la tendencia, no como señal de compra o venta.

Es información para análisis propio, no una recomendación de inversión.
