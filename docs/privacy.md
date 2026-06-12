# Ficha Técnica de Privacidad — LatAm Synth

**Versión:** 0.2.0 · **Fecha:** 2026-06-12 · **Clasificación:** Pública

---

## 1. Naturaleza del output

LatAm Synth produce **datos 100% sintéticos**. Ningún registro del archivo de salida corresponde a, ni puede ser revertido a, un individuo real. El output es un conjunto de datos estadísticamente plausible generado por un modelo probabilístico; no es un subconjunto, anonimización ni seudonimización de datos reales.

---

## 2. Ausencia de PII y riesgo de re-identificación

El output no contiene:

| Campo | Presente en output | Nota |
|---|---|---|
| Nombre, apellido | No | Sustituido por ID UUID aleatorio |
| Email, teléfono | No | No se genera |
| Dirección, ubicación GPS | No | Solo país, de distribución agregada |
| Fecha de nacimiento | No | No se genera |
| Número de documento | No | No se genera |
| Información financiera real | No | Montos son sintéticos del modelo |
| IP, device ID | No | No se genera |

El campo `user_id` es un UUID v4 generado en tiempo de ejecución. No existe una tabla de correspondencia con personas reales porque esa tabla no existe: los usuarios sintéticos no tienen contrapartes reales.

El riesgo de re-identificación es **nulo** por construcción: el modelo no dispone de información individual en ninguna etapa del pipeline.

---

## 3. Metodología de calibración: qué se usó y qué no

### Dataset fuente
La calibración se realizó sobre un dataset privado de **506,311 registros** de transacciones de una aplicación de ahorro LatAm (2015-2024). Este dataset:

- **Nunca se distribuye** con el producto ni en ningún artefacto del repositorio.
- **No se almacena** en el entorno de producción del generador.
- Se usó exclusivamente como fuente estadística en un proceso offline y descartado tras la extracción de parámetros.

### Qué se extrajo
Del dataset fuente se extrajeron únicamente **estadísticas agregadas**:

- Percentiles de distribución de montos de transacción (p1, p5, p10, p25, p50, p75, p90, p95, p99)
- Parámetros de mezcla de distribuciones lognormales (medias y varianzas de componentes)
- Proporciones categóricas (mix geográfico, distribución de categorías de metas, share de depósitos vs retiros)
- Correlaciones entre scores de usuario a nivel de cohorte
- Estacionalidad mensual y semanal agregada

Todos estos parámetros están almacenados en `calibration_params.json` y son públicamente inspeccionables. **Ningún registro individual** del dataset fuente está codificado, implícito ni recuperable a partir de estos parámetros.

### Garantía matemática
Las distribuciones paramétricas (lognormales, Poisson, mezclas gaussianas) y los procesos de punto son modelos de la *forma* de los datos, no memorias de los datos. Por el teorema de representación de De Finetti y las propiedades de información de las distribuciones paramétricas, la capacidad de recuperar registros individuales a partir de los parámetros es matemáticamente equivalente a recuperarlos desde los momentos de una distribución — imposible en ausencia del dataset original.

---

## 4. Proceso de generación

```
calibration_params.json          (parámetros agregados, públicos)
         │
         ▼
  SyntheticGenerator(seed)
         │
         ├─ Usuarios: cópula gaussiana sobre distribuciones marginales
         ├─ Metas: muestreo de categorías, montos y horizontes calibrados
         └─ Transacciones: proceso de punto con intensidad decreciente,
            montos de mezcla de lognormales + snap a valores redondos
         │
         ▼
  Output: users.csv, goals.csv, transactions.csv
  (o JSON equivalente)
```

El proceso es **determinista dado un seed**: el mismo seed produce el mismo output byte a byte. Esta propiedad es intencional y necesaria para casos de uso de testing y reproducibilidad de benchmarks.

---

## 5. Marco regulatorio aplicable

| Regulación | Aplica al output | Fundamento |
|---|---|---|
| GDPR (UE) | **No aplica** | El output no contiene datos de personas físicas identificadas o identificables (Art. 4.1 GDPR) |
| LGPD (Brasil) | **No aplica** | Sin dados pessoais (Art. 5.I LGPD) |
| CCPA (California) | **No aplica** | Sin "personal information" de consumidores de California |
| LFPDPPP (México) | **No aplica** | Sin datos personales (Art. 3.V LFPDPPP) |
| LOPD (España/Colombia) | **No aplica** | Sin datos de personas físicas identificadas |

Para jurisdicciones con marcos no listados: dado que el output no contiene información de personas físicas ni puede ser revertido a ellas, la clasificación esperada es la de datos no personales en cualquier marco que adopte la definición de la OCDE o ISO/IEC 27701.

---

## 6. Recomendaciones para el área de Compliance del comprador

1. **No se requiere DPA (Data Processing Agreement):** LatAm Synth no procesa datos personales del comprador ni de terceros. No existe flujo de datos personales entre las partes.

2. **No se requiere consentimiento de usuarios finales:** Los datos de salida no corresponden a personas reales; no hay sujetos de datos cuyos derechos ARCO/ARCOPLUS gestionar.

3. **Uso recomendado:** desarrollo y prueba de modelos de machine learning, benchmarking de sistemas financieros, generación de datos de demostración para entornos de pre-producción, investigación académica.

4. **Uso no recomendado:** el producto no debe usarse como sustituto de datos reales en decisiones financieras individuales (scoring crediticio, underwriting) sin validación adicional.

5. **Auditoría:** el código fuente completo y los parámetros de calibración son inspeccionables. Cualquier auditor técnico puede verificar que el pipeline no contiene rutas de acceso a datos reales.

---

## 7. Contacto

Para preguntas técnicas de privacidad o compliance: ver repositorio del producto en GitHub. El código es el contrato.
