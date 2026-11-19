# Manifiesto de entrega académica

## Archivos públicos de la entrega
- `README.md`: visión del problema, instrucciones y resultados.
- `docs/INFORME_FINAL.md`: planteamiento, metodología, resultados, interpretación, conclusiones y referencias.
- `docs/PRESENTACION_FINAL.md`: contenido académico de las 12 diapositivas, sin notas privadas de ensayo.
- `docs/DEMO_PROTOCOL.md`: pasos reproducibles de la demostración.
- `docs/architecture.md`, `docs/training.md`, `docs/datasets.md`, `docs/model_card.md`: diseño, entrenamiento, procedencia y limitaciones.
- `docs/genai_evaluation.md`, `docs/ai_providers.md`, `docs/ethics_security.md`: evaluación del componente generativo, selección de proveedor y riesgos.
- `src/`, `frontend/`, `scripts/`, `tests/`, `configs/`: implementación y pruebas.
- `reports/0.9.0-academic/`, `reports/promise_validation/` y reportes específicos de evaluación: evidencia experimental existente.
- `reports/genai/provider_comparison_2026/`: comparación controlada y operativa de 30 casos; Qwen3 8B medido (30/30 aceptadas), OpenAI no ejecutado por clave ausente en el proceso.
- `reports/efficiency/inprocess_2026/` y `reports/human_validation/productivity_summary.json`: eficiencia técnica y estado NO MEDIDA de la productividad humana.
- `reports/mlops/`: registro de modelos y ciclo de reentrenamiento demostrativo.
- `reports/technical_closure/`: benchmark HTTP individual/CSV y concurrencia, ejecución offline de drift y auditoría técnica. En HTTP hubo 100/100 respuestas válidas por nivel 1/4/8/16; no se operó un clúster ni se probó caída de una réplica.
- `reports/technical_closure/technical_audit.md`, `technical_audit.json`, `test_summary.md`, `evidence_index.md`, `scientific_integrity.json` y `remaining_external_dependencies.md`: cierre reproducible, estado de validación, hashes académicos y límites no medidos.
- `reports/monitoring/profiles/0.9.0-academic-train-profile.json`: perfil agregado de features TRAIN para los avisos OOD; no publica filas ni labels individuales.
- `docs/ORAL_EVIDENCE.md`: correspondencia entre recursos públicos y criterios orales por comprobar.

## Contenido privado/no publicado
Guiones literales, bancos personales de preguntas, notas de ensayo y registros de práctica. Se conservan en el paquete de estudio separado, no en `main`. Tampoco se publican credenciales, datasets pesados, artefactos de modelos con extensión `.joblib`, cachés, ni expedientes empresariales.

## Estado de aceptación
El último commit de entrega debe pasar `quality`, incluido el build/smoke Docker con artefactos de demostración, y enlazarse en el registro final y conservar intactos los resultados científicos congelados. En la auditoría local Docker CLI estaba instalada pero sin daemon; el CI de `main` sí construyó y ejecutó el smoke test. El archivo oficial de la universidad se recibió y sus 27 criterios están contrastados en [RUBRICA_OFICIAL_PAIII_2026.md](RUBRICA_OFICIAL_PAIII_2026.md). La matriz de estados sigue siendo una **evaluación interna de evidencias**; el mentor e invitado no han asignado nivel ni nota al proyecto. Los criterios orales requieren observación humana. OpenAI no se midió: `OPENAI_API_KEY` no estaba disponible para el proceso y el gasto de benchmark fue 0 USD.

## Ética de autoría
La documentación describe el sistema y su evidencia verificable. No se incluyen transcripciones de trabajo ni instrucciones privadas de redacción. Debe cumplirse cualquier exigencia institucional de declaración de herramientas empleadas; retirar archivos de trabajo no sustituye una declaración de autoría cuando sea obligatoria.
