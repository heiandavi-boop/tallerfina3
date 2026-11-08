# Cierre final PRUNIN AI Core

Estado de evidencia para la entrega académica. No asigna calificación oficial ni afirma validación empresarial/producción. El SHA exacto de publicación y el run `quality` deben corresponder al `main` publicado; el identificador de workflow se comunica en la entrega final y no se reutiliza ningún run histórico.

## Verificaciones ejecutadas

| Gate | Resultado observado |
|---|---|
| Dependencias Python | `pip install -r requirements.txt` completó; `pip check`: `No broken requirements found.` |
| Frontend | `npm ci` desde lockfile final; `npm audit`: 0 vulnerabilidades; Vitest: 18 passed; `npm run build`: success. |
| Backend | `PYTHONPATH=src python -m pytest -q`: 137 passed, 1 skipped, 0 failed. El skip es `kubectl` opcional no instalado. |
| Sintaxis Python | `python -m compileall -q src scripts tests`: success. |
| KPI original | `python scripts/validate_original_promise.py --check`: `PROMISE VALIDATION: OK`; detección de cohorte completa al 60 %: 0.758985. |
| Preflight demo | `RESULTADO: LISTO PARA DEMO`, artifact `0.9.0-academic`. |
| Preflight GenAI | `RESULTADO: OLLAMA READY`; Qwen3 8B disponible durante esta corrida local. |
| Manifiesto Kubernetes | YAML parseable y pruebas estáticas Deployment/Service/HPA/PDB, probes, recursos, no-root, rootfs read-only con `/tmp` acotado, cierre graceful y selectores. No hay `kubectl` ni cluster operado. |

## Métricas que se preservan

Promesa original: “Detectar tempranamente al menos el 75 % de los proyectos críticos o en alto riesgo.” Risk Alert, que agrupa At Risk OR Critical, detecta **359/473 = 75.90 %** al 60 % de avance con **96 % de cobertura TEST**. Risk Alert Recall final: **82.45 %**; Precision: **92.20 %**; F1: **87.05 %**. El **Critical Recall exacto sigue en 56.82 %**. No son métricas intercambiables.

Health Macro F1: **0.627576**. Delay MAE: **27.710468 días** frente a baseline **27.850313**; mejora marginal. Cost MAE: **0.147158 puntos porcentuales** y R² **0.991816**, con caveat estructural CPI/EVM del generador sintético.

La evaluación Qwen oficial congelada no se modificó ni se reejecutó: 30 casos, 29/30 aceptadas, 1 claim numérico no soportado, mediana 3092.645 ms y p95 6634.72 ms.

## Benchmarks nuevos, separados

El benchmark de candidatos GenAI es `partial`: misma cohorte TEST de 30 casos, hardware, prompt/evidencia, temperatura 0.1, timeout 30 s y validador. Solo `qwen3:8b` estaba disponible; `gemma3:4b` y `ministral:8b` se marcaron `not_available`, sin descarga. En la nueva corrida Qwen obtuvo 29/30 generación/schema/grounding proxy/actionability, cero cifras no soportadas, un JSON inválido, cero timeouts, mediana 6336.35 ms y p95 13340.74 ms. Estos valores no reemplazan la evaluación Qwen oficial.

La prueba local de concurrencia (30 casos/nivel) midió éxito 96.67/93.33/73.33/36.67 %, timeout 0/0/26.67/63.33 %, p50 6256.955/12305.81/28567.37/30002.805 ms, p95 15337.88/23252.48/30003.31/30005.73 ms y throughput 0.1335/0.1402/0.1475/0.2499 req/s en concurrencia 1/2/4/8. El throughput crece junto con fallos y timeouts. **No es una prueba productiva ni evidencia de escalabilidad.**

## Integridad científica

**Cambios científicos: NINGUNO.** No se modificaron dataset académico, targets/labels, split, seed, thresholds del modelo, `.joblib`, predicciones TEST, métricas/reportes históricos ni evaluación Qwen congelada. El benchmark comparativo y la concurrencia son corridas nuevas independientes. `input_profile.json` es un perfil estadístico derivado exclusivamente de los project IDs TRAIN (2,800 proyectos / 50,772 snapshots); no altera predicciones y su OOD solo advierte. Dataset y split conservan sus SHA256 registrados.

Fingerprints observados antes de cerrar:

| Archivo | SHA256 |
|---|---|
| `data/processed/mendeley_core.csv` | `32b7586db9dda0b3994573a3985c114dafe65dee93c948254b69f00d194c0ac3` |
| `artifacts/0.9.0-academic/split_manifest.json` | `ed8f9db66e254123e411e7d016e91c01563a58c11e3a7f337bd9592ab92db26c` |
| `artifacts/0.9.0-academic/training_config_resolved.yaml` | `e8049c4e9ef4015e3bbb52323620e4e8584fb557b580381442680397eb505b49` |
| `artifacts/0.9.0-academic/health.joblib` | `81dba769ecbcec2f64a312432ab5eb9720af3d37e5018f15249e821e1ca52c18` |
| `artifacts/0.9.0-academic/delay_days.joblib` | `84924fc4ddfbcd3842dfc24686286bc9affc23a7f4024698607b678af78916b3` |
| `artifacts/0.9.0-academic/cost_overrun_ratio.joblib` | `0881ac24d6780378fce8ca9fcfd0f03d5f89c7ef475a33c882ec01efff9c7ba6` |
| `reports/0.9.0-academic/metrics.json` | `5464f55fe9e8f507259c71141681bd5a3aad6d3764a79744a57a42f0f984f89a` |

El detector de drift/OOD es académico/offline. Kubernetes quedó como diseño validado estáticamente: “deployment automation/design validated statically; production cluster not operated.” No se activó retraining automático.

## Estado de 27 criterios

La tabla completa machine-readable, con evidencia, claims seguros/no seguros y gaps, está en [reports/rubric_final/rubric_final.json](../reports/rubric_final/rubric_final.json); resumen: [reports/rubric_final/rubric_final.md](../reports/rubric_final/rubric_final.md). La evaluación clasifica 20 criterios como `DEMONSTRATED_WITH_LIMITATION` y 7 como `PREPARED_HUMAN` (RA2 F1–F7). Ningún criterio oral se declara demostrado.

## Pendientes humanos antes de entregar

- Completar autor, institución y portada.
- Revisar renders, referencias y slides en el formato de entrega.
- Ensayar y registrar una versión de 7/10/12 minutos.
- Practicar voz, pausas, volumen, postura, contacto visual y defensa espontánea.
- Probar red/proyector, fallback sin Ollama y copia offline.
- No presentar eficiencia operacional como productividad humana ni el benchmark local como prueba productiva.

## Veredicto

Los gates locales del repositorio pasan y el proyecto está **preparado para entrega académica**, sujeto a que GitHub Actions `quality` termine `success` en el commit final publicado de `main` y a completar los pendientes humanos. No está listo para producción ni validado con empresas. El veredicto “Listo para entrega académica” solo se usa tras comprobar ese CI exacto; el resultado y SHA se verifican en el historial del repositorio, no se copian de runs anteriores.