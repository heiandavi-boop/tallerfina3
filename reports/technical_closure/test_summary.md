# Resumen de validación técnica

## Resultados

| Comando / validación | Resultado |
|---|---|
| Pruebas focalizadas: seguridad, MLOps, drift y benchmark HTTP | 19 passed |
| `PYTHONPATH=src ./.venv/bin/python -m pytest -q` | 216 passed, 1 skipped |
| `./.venv/bin/python -m pip check` | No broken requirements found |
| `./.venv/bin/python -m compileall -q src scripts tests` | Correcto |
| `npm test --prefix frontend -- --reporter=dot` | 22 passed |
| `npm run build --prefix frontend` | Build completado |
| `./.venv/bin/python scripts/validate_original_promise.py --check` | `PROMISE VALIDATION: OK`; recall cohorte completa al 60 % = 0.758985 |
| `bash scripts/run_demo.sh` | Correcto; generó 3.200 filas y 400 proyectos sintéticos |
| `git diff --check` | Sin errores de whitespace |

La suite backend emitió warnings de joblib y de fixtures sintéticos de métricas; no hubo fallas en la ejecución final.

## Corrección durante la validación

El primer intento completo dejó un fallo en `test_explicit_ollama_selection_does_not_mutate_process_env`: el test esperaba invocar el transporte Ollama con `PRUNIN_ENABLE_OLLAMA=0`, en conflicto con el control de servidor añadido. Se cambió el setup de ese test a habilitado para que compruebe su objetivo (no mutar el entorno); la prueba de seguridad separada verifica que la bandera `0` bloquea la llamada. La suite completa se ejecutó de nuevo: 216 passed, 1 skipped.

## No ejecutado / bloqueado

- Docker: `docker info` indicó que `/var/run/docker.sock` no existe y el sandbox denegó la lectura de `~/.docker/config.json`. No se repitió el acceso ni se intentó eludir la política.
- Kubernetes: no hay contexto configurado ni clúster disponible.
- Productividad humana: no hay participantes; el resultado permanece NO MEDIDA.

La prueba de Docker en GitHub Actions y la prueba estática de manifiestos son evidencias distintas y no se reportan como operación local de Docker o Kubernetes.
