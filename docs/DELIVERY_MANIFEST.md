# Manifiesto de entrega académica: repositorio público y material local

## Material que debe permanecer en GitHub

- `README.md`: descripción, instrucciones de ejecución y resultados.
- `docs/INFORME_FINAL.md`: documento técnico académico y conclusiones verificables.
- `docs/DEMO_PROTOCOL.md`: comprobación técnica reproducible de la aplicación, **no** guion oral ni contenido de diapositivas.
- `docs/RUBRICA_OFICIAL_PAIII_2026.md`: matriz de trazabilidad de evidencias y límites observados, sin atribución de nota oficial.
- `docs/architecture.md`, `docs/training.md`, `docs/datasets.md`, `docs/model_card.md`: arquitectura, datos, preprocesamiento, entrenamiento y reproducibilidad.
- `docs/genai_evaluation.md`, `docs/genai_model_selection.md`, `docs/ai_providers.md`, `docs/ethics_security.md`: integración, comparación experimental y restricciones éticas.
- `src/`, `frontend/`, `scripts/`, `tests/`, `configs/`, `.github/workflows/`: implementación, pruebas y CI.
- `reports/0.9.0-academic/`, `reports/promise_validation/`, `reports/genai/`: resultados científicos y comparativos con trazabilidad.
- `reports/efficiency/`, `reports/technical_closure/`, `reports/mlops/`: benchmarks operativos, CI, evidencias MLOps y sus limitaciones.
- `reports/human_validation/productivity_summary.json`: estado **NO MEDIDA**; no hay participantes ni se afirma productividad humana.

## Exclusivamente local: material de la presentación

Los siguientes documentos se retiraron del árbol activo del repositorio y se conservan mediante una **copia fuera de Git**:

- `PRESENTACION_FINAL.md` — estructura y contenido de diapositivas.
- `ORAL_EVIDENCE.md` — preparación y criterios de exposición oral.
- `DEFENSA_PAIII_NIVEL4.md` — preguntas del jurado, respuestas y guía de defensa.

Tampoco publicar notas personales, guiones literales, sesiones de ensayo, formatos de práctica, diapositivas PPTX/PDF, grabaciones, materiales de exposición ni bancos privados de preguntas. La ruta `material_privado/` y los nombres históricos de estas notas están ignorados en `.gitignore`.

**Para recuperar los tres archivos originales:** desde una copia local de Git, ejecutar `git show 862d8747f76afa87eef525a8e470fbabbd49f389:docs/PRESENTACION_FINAL.md` (y cambiar el nombre para los otros dos archivos); guardar las salidas en una carpeta personal fuera del repositorio. Retirar archivos de `main` no reescribe el historial remoto.

## Aclaraciones de entrega

Este repositorio sigue siendo suficiente para revisión del **código y evidencia técnica**, pero los archivos de exposición oral se entregan por separado si la institución los exige. La fuente institucional original de la rúbrica también permanece fuera de Git.

No se versionan contraseñas, credenciales, expedientes privados ni datasets/modelos pesados salvo los artefactos explícitamente autorizados.

**Estado de aceptación:** la CI debe aprobar el commit final; no se deduce ninguna calificación docente por pasar pruebas automatizadas. La ausencia de productividad humana medida, uso empresarial y evaluación oral observada se declara en los documentos públicos.

**Integridad de autoría:** cumplir las reglas institucionales de citación y declaración de herramientas, cuando correspondan. Separar notas privadas no equivale a borrar los commits históricos ni a ocultar contribuciones exigidas por las normas académicas.
