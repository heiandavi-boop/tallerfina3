# Checklist previo a entrega

No marcar una casilla por intención. Registrar commit y evidencia actual en `docs/FINAL_READINESS.md` tras ejecutar las comprobaciones.

- [ ] CI verde sobre HEAD exacto
- [x] frontend probado
- [x] API probada
- [x] modelo 0.9.0-academic
- [x] promesa 75 % validada
- [x] Qwen status comprobado
- [x] CSV probado
- [x] JSON exportado
- [x] demo preparada
- [ ] slides revisados
- [x] referencias revisadas
- [ ] identidad académica completa
- [ ] tiempos ensayados
- [ ] copia offline lista

## Comprobaciones automáticas

```bash
python -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend -- --run
python scripts/validate_original_promise.py --check
python -m compileall -q src scripts tests
PYTHONPATH=src python -m pytest -q
./scripts/preflight_demo.sh
./scripts/preflight_genai.sh
```

El preflight GenAI requiere Ollama activo y el modelo configurado. No forma parte de CI. Los benchmarks de candidatos/concurrencia también son manuales y no deben interpretarse como producción.

## Evidencia humana

- [ ] Completar nombre/institución en portada
- [ ] Ensayar versión elegida y registrar tiempos reales
- [ ] Practicar voz, postura, contacto visual y preguntas difíciles
- [ ] Probar proyección, red, fallback sin Ollama y copia offline
- [ ] No declarar RA2 demostrado sin observación de la sustentación