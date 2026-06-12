# Business case — Generador de datos sintéticos de comportamiento financiero LatAm

**Producto de trabajo:** "LatAm Savings Behavior Synthetic Generator" (nombre comercial por definir)
**Fecha:** Junio 2026
**Estado:** Pre-construcción · Decisión go/no-go
**Inversión requerida:** ~0 USD en capital · 2-4 semanas de tiempo de construcción asistida por agentes

---

## 1. Resumen ejecutivo

Se propone construir un generador de datos sintéticos de comportamiento de ahorro financiero, calibrado con las distribuciones estadísticas de un dataset real de 506,311 registros (305,808 transacciones, 108,570 metas de ahorro, 91,933 usuarios) capturados entre 2015 y 2024 en una app de ahorro que operó principalmente en México, Colombia y otros siete países de LatAm.

El producto no vende los datos —que son públicos en Kaggle y por tanto sin valor de mercado directo— sino la capacidad de generar volúmenes ilimitados de datos sintéticos estadísticamente fieles al comportamiento financiero real latinoamericano. El comprador objetivo es el equipo de ingeniería o data science de una fintech, banco digital, consultora o proveedor de software que necesita datos realistas para testing, demos, entrenamiento de modelos o sandboxes regulatorios, sin exposición a datos personales.

La distribución es 100% por marketplaces (Apify, AWS Marketplace, RapidAPI, Gumroad para el canal educativo), sin equipo comercial. El modelo de ingresos es pago por uso más licencias one-time. El escenario base proyecta entre 500 y 2,000 USD mensuales al mes 6-9, con techo realista en el rango de 3,000-5,000 USD mensuales. Esto es un negocio de productos digitales, no una startup venture-scale, y el caso se construye explícitamente sobre esa expectativa.

---

## 2. Contexto y problema de mercado

Las empresas de software financiero enfrentan una tensión estructural: necesitan datos transaccionales realistas para desarrollar y probar sus productos, pero el uso de datos reales de clientes está cada vez más restringido. Una encuesta de cumplimiento empresarial de 2026 citada por K2view encontró que solo el 9% de las empresas considera sus bases SQL totalmente conformes fuera de producción, y el 76% ha experimentado incidentes con datos sensibles en ambientes de desarrollo.

La respuesta del mercado son los datos sintéticos. Gartner proyecta que hasta 2030 los datos sintéticos estructurados crecerán al menos 3 veces más rápido que los datos reales para entrenamiento de modelos, y el segmento de entrenamiento de modelos representa el 46.3% del mercado de datos sintéticos en 2026 (Coherent Market Insights). En servicios financieros específicamente, las organizaciones que usan datos sintéticos para sortear restricciones regulatorias reportan reducciones de 40-60% en tiempos de desarrollo de modelos (Cogent).

El gap específico que este producto ataca: los generadores sintéticos existentes (por ejemplo, los actores publicados en Apify para datos financieros sintéticos) producen datos genéricos con patrones inventados o norteamericanos. No existe un generador calibrado con comportamiento financiero real de América Latina. Para una fintech mexicana que quiere probar su motor de recomendaciones de ahorro, o una consultora que arma una demo para un banco colombiano, datos sintéticos con distribuciones de Ohio no sirven: los montos, la estacionalidad, las categorías de metas y las tasas de abandono son distintas.

---

## 3. El activo: qué tenemos exactamente

El valor diferencial no son los datos crudos sino los parámetros estadísticos extraídos de ellos, que se convierten en el motor de calibración del generador. Inventario verificado del activo:

**Distribuciones de montos reales.** Los depósitos siguen una distribución log-normal de cola pesada con mediana de $100 (moneda local), p75 de $815, p90 de $6,000 y p99 de $200,000. La proporción depósito:retiro es 6.2:1. Estas distribuciones son imposibles de inventar verosímilmente sin referencia real.

**Estacionalidad mensual observada.** El comportamiento de depósitos muestra picos en enero (9.7% del volumen anual, efecto propósitos de año nuevo), agosto-octubre (9.2-9.4%) y caída en diciembre (7.1%, el gasto navideño desplaza al ahorro). Este patrón es contraintuitivo (se esperaría ahorro pre-navideño) y solo se conoce teniéndolo medido.

**Taxonomía real de metas de ahorro.** Sobre 108,495 metas con nombre: viajes 7.0%, vehículos 6.7%, tecnología 6.6% (celular e iPhone dominan), vivienda 3.0%, eventos 3.0%, educación 1.2%, más una larga cola de ahorro libre. Con montos objetivo y horizontes temporales reales por categoría (mediana de horizonte: 120 días; p25: 44 días; p75: 268 días).

**Tasas de éxito y abandono reales.** 73.8% de metas vencidas, 19.2% en progreso, 7.0% logradas. Las metas compartidas (2.1% del total) logran 8.9% vs 7.0% individuales, con montos objetivo 67% mayores. La correlación entre disciplina de ahorro y logro de metas es 0.89. Estos son los números que un modelo de churn o un motor de gamificación necesita reproducir en testing.

**Distribución geográfica.** México 39.9%, Colombia 12.4%, Argentina 7.8%, Perú 4.7%, Chile 4.4%, España 5.0%, con coordenadas y ciudades.

**Limitaciones del activo (declaradas).** Los datos tienen ruido real: outliers absurdos en montos (hasta 1e25, claramente errores de captura), 90,214 de 91,933 usuarios sin género registrado, países imposibles (Afghanistan 7.5%, probable basura de formularios), y el volumen decae fuertemente después de 2018. Para el producto esto es manejable —el generador usa distribuciones limpias— e incluso es un argumento de venta para el canal educativo: datasets sucios realistas son exactamente lo que los bootcamps necesitan para enseñar limpieza de datos.

---

## 4. Definición del producto

**Producto núcleo: API/CLI de generación sintética.** Un motor estadístico (sin LLM: distribuciones paramétricas ajustadas, muestreo correlacionado, procesos de punto para series temporales) que genera, bajo demanda, datasets sintéticos de usuarios, metas y transacciones con los patrones calibrados. Parámetros configurables: número de usuarios, rango de fechas, mezcla de países, tasa de éxito de metas, semilla reproducible, formato de salida (CSV, JSON, Parquet, SQL inserts).

**Garantía de privacidad estructural.** Ningún registro sintético deriva de un registro real individual; solo de distribuciones agregadas. No hay PII, no hay riesgo de reidentificación, no aplica GDPR/LGPD/habeas data al output. Esto se documenta como ficha técnica de privacidad, que es parte del producto.

**Producto secundario: paquete educativo.** El dataset original curado más guía docente, 4 notebooks resueltos (limpieza, EDA, modelo de churn, segmentación), rúbricas de evaluación y narrativa de negocio. Para bootcamps, profesores universitarios y estudiantes armando portafolio. Precio one-time, venta en Gumroad/Lemon Squeezy.

**Qué NO es el producto.** No es scoring (regulado), no es venta de datos personales (los datos reales nunca se entregan como producto principal), no es un producto de IA generativa (sin volatilidad de modelos fundacionales), no requiere mantener infraestructura propia compleja (los marketplaces hospedan).

---

## 5. Mercado y canales de distribución (validados)

| Canal | Tipo de producto | Modelo de cobro | Comisión | Descubrimiento |
|---|---|---|---|---|
| Apify Store | Actor de generación (API) | Pago por uso / renta mensual | ~20% plataforma | Orgánico, búsqueda interna + SEO; ya existen actores comparables de datos financieros sintéticos, validando demanda |
| AWS Marketplace / Data Exchange | Producto de datos / SaaS | Suscripción | Variable | Orgánico dentro del ecosistema AWS; comprador enterprise |
| RapidAPI | API REST | Freemium + tiers | ~20% | Orgánico, desarrolladores |
| Gumroad | Paquete educativo | One-time $30-80 | 13.2% sobre venta | 41% de ventas en Gumroad provienen de búsqueda orgánica del marketplace |
| Lemon Squeezy | Paquete educativo (alternativa) | One-time | ~5.5% | Menor descubrimiento, mejor margen |

La estrategia de entrada es Apify primero (menor fricción de publicación, demanda comparable demostrada, hospedaje incluido), Gumroad en paralelo para el educativo (esfuerzo marginal), y AWS Marketplace como segunda ola si hay tracción, porque su proceso de onboarding de vendedor es más pesado pero abre comprador enterprise.

**Comprador objetivo por orden de probabilidad:** (1) desarrolladores y QA de fintechs LatAm que necesitan fixtures de testing realistas; (2) consultoras y agencias que arman demos para clientes bancarios; (3) equipos de data science que entrenan modelos de churn/recomendación y necesitan datos de arranque; (4) bootcamps e instructores de data science en español; (5) investigadores académicos en inclusión financiera.

---

## 6. Modelo de ingresos y escenarios

Precios de referencia tomados de productos comparables en los marketplaces citados:

| Producto | Precio |
|---|---|
| Generador — tier gratuito | 1,000 registros/mes (anzuelo de descubrimiento) |
| Generador — pago por uso | ~$2-5 USD por 100K registros generados |
| Generador — renta mensual (Apify) | $15-30 USD/mes uso razonable |
| Licencia dataset sintético pre-generado (1M registros) | $49-99 USD one-time |
| Paquete educativo | $39-59 USD one-time |

**Escenarios a 12 meses (ingresos mensuales al estabilizar, netos de comisiones):**

| | Pesimista | Base | Optimista |
|---|---|---|---|
| Suscriptores generador | 3-5 | 15-25 | 50-80 |
| Ventas educativo/mes | 2-4 | 8-15 | 25-40 |
| Ingreso mensual neto | $80-200 | $500-1,200 | $2,500-5,000 |

Supuestos del escenario base: tasa de conversión del marketplace consistente con productos nicho bien documentados, sin inversión en ads, con 2-3 piezas de contenido SEO (artículos técnicos sobre datos sintéticos fintech LatAm) como único esfuerzo de marketing, generables también con agentes.

El punto de equilibrio es trivial porque el costo marginal es ~0: cualquier venta es margen. El riesgo no es perder dinero sino perder tiempo; por eso la construcción agéntica (sección 8) está diseñada para que la apuesta total sea de 2-4 semanas de esfuerzo a tiempo parcial.

---

## 7. Análisis competitivo y defensa

**Competidores directos:** generadores sintéticos genéricos (actores de Apify, Faker/Mimesis como librerías gratuitas, Mostly AI/Gretel/K2view en enterprise). Ninguno ofrece calibración LatAm verificable.

**Defensa frente a "te copia una big tech o un LLM":** el foso no es el código del generador (replicable) sino la calibración con datos de referencia reales que ya no se pueden volver a capturar (la app murió; nadie más tiene 9 años de comportamiento de ahorro LatAm con metas etiquetadas). Un LLM puede inventar transacciones plausibles pero no puede afirmar fidelidad estadística a comportamiento real medido, que es exactamente lo que el comprador de testing/ML necesita poder citar.

**Defensa frente a "los datos son públicos en Kaggle":** correcto, y por eso los datos crudos no son el producto. El producto es el motor + la conveniencia + la documentación + la garantía de privacidad + los formatos listos para consumir. El comprador de un marketplace paga por no tener que hacer 3 semanas de ingeniería estadística; la existencia del dataset público es de hecho material de marketing (transparencia de la fuente de calibración).

**Riesgos reales y mitigación:**

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Demanda insuficiente en marketplace | Media | Tier gratuito como prueba de demanda en semanas 1-4 antes de invertir más; criterio de kill abajo |
| Datos de referencia envejecen (2015-2024) | Baja-media | Para testing/educación la antigüedad es irrelevante; para ML se documenta como limitación |
| Marketplace cambia comisiones/reglas | Media | Multi-canal desde el día 1; el motor es portable |
| Calidad del dato fuente (ruido) | Ya materializado | Pipeline de limpieza documentado; el ruido se excluye de la calibración con reglas explícitas |

---

## 8. Plan de ejecución agéntica

El principio operativo: el humano decide dirección y aprueba; los agentes ejecutan construcción, documentación y mantenimiento.

**Fase 1 — Motor de calibración (esta conversación, días 1-2).** Claude extrae del CSV todas las distribuciones paramétricas (montos por tipo y país, estacionalidad, horizontes de meta, taxonomía de categorías, tasas de transición de estado de metas, correlaciones entre scores) y las serializa en un archivo de parámetros versionado. Entregable: `calibration_params.json` + reporte de validación estadística (test de bondad de ajuste sintético vs real).

**Fase 2 — Generador (Claude Code, días 3-7).** Construcción del paquete Python: motor de muestreo, CLI, API FastAPI, tests, documentación de uso, ficha de privacidad. Empaquetado como actor de Apify y como repo desplegable. Intervención humana: revisar y aprobar, crear las cuentas de marketplace.

**Fase 3 — Listings y materiales (Claude.ai, días 8-12).** Páginas de producto para Apify y Gumroad, README comercial, 3 artículos técnicos SEO, dataset educativo curado con notebooks. Intervención humana: publicar (los marketplaces requieren identidad del vendedor).

**Fase 4 — Operación (continua, ~2 horas/semana humanas).** Claude Code monitorea issues/reviews, responde solicitudes de features comunes (nuevos formatos de salida, nuevos parámetros), genera contenido SEO mensual. El producto es estadístico y estático en esencia: el mantenimiento real es bajo.

---

## 9. Criterios de decisión (go/kill)

**Go inmediato si:** se aceptan los escenarios de ingresos como objetivo (negocio de producto digital, no venture), y hay disponibilidad de ~10-15 horas humanas totales en 4 semanas.

**Checkpoint a 60 días post-publicación:** si el tier gratuito no acumula al menos 30-50 usuarios únicos o el listing no genera ninguna conversión de pago, el costo hundido es mínimo y se mata o pivota (el motor de calibración queda como activo reutilizable para el canal educativo, que tiene dinámica independiente).

**Señal de doblar la apuesta:** cualquier solicitud entrante de personalización enterprise (una fintech pidiendo calibración con sus propios datos) convierte esto en un negocio de servicios de mayor ticket, con el marketplace como canal de leads — ese es el upside no lineal del caso.

---

## Anexo A — Fuentes de validación de mercado

Proyección de crecimiento 3x de datos sintéticos estructurados (Gartner, vía K2view, 2026) · Segmento de entrenamiento de modelos 46.3% del mercado sintético 2026 (Coherent Market Insights) · Reducción 40-60% en tiempos de desarrollo con datos sintéticos en servicios financieros (Cogent) · Casos de uso de compartición banco-fintech con datos sintéticos (bobsguide, ChatFin) · Existencia de generadores financieros sintéticos comerciales en Apify (validación de demanda y formato) · Estructura de comisiones: Gumroad 13.2%, Lemon Squeezy ~5.5% por venta de $100 (InsightRaider) · 41% de ventas orgánicas en marketplace Gumroad (InsightRaider) · Marketplaces de datos activos: Datarade 3,000+ datasets, AWS Data Exchange 3,500+ (Monda, CyberYozh)

## Anexo B — Parámetros de calibración verificados (muestra)

Dataset fuente: 506,311 registros (305,808 tx · 108,570 metas · 91,933 usuarios), 2015-04-24 a 2024-05-07 · Mediana depósito $100, p90 $6,000, ratio depósito:retiro 6.2:1 · Estacionalidad: pico enero 9.7%, valle diciembre 7.1% · Metas: 73.8% vencidas / 19.2% en progreso / 7.0% logradas · Compartidas 2.1% del total, logro 8.9% vs 7.0%, monto mediano $10K vs $6K · Horizonte de meta: mediana 120 días (p25 44, p75 268) · Categorías: viaje 7.0%, vehículo 6.7%, tech 6.6%, vivienda 3.0% · Geografía: MX 39.9%, CO 12.4%, AR 7.8% · Correlación disciplina-logro: 0.89
