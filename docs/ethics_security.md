# Ética, privacidad y seguridad

## Principio

PRUNIN es un sistema de apoyo a decisiones. No sustituye al director del proyecto ni presenta sensibilidad del modelo como causalidad.

| Riesgo | Manifestación posible | Mitigación implementada | Riesgo residual |
|---|---|---|---|
| Alucinación generativa | El LLM inventa una causa o cifra | Prompt grounded, evidence_feature allow-list, validación de esquema, bloqueo de nuevas cifras y fallback determinístico | Una frase puede seguir siendo semánticamente poco útil; requiere validación humana |
| Automatización excesiva | Usuario acepta una recomendación como decisión | Disclaimer explícito, separación entre predicción y recomendación, humano en el circuito | Sesgo de automatización del usuario |
| Privacidad | Datos sensibles enviados a terceros | Ollama local por defecto; el prompt recibe evidencia estructurada y no texto libre del proyecto | El despliegue productivo debe definir clasificación de datos y controles de acceso |
| Sesgo / representatividad | Dataset sintético no refleja proyectos reales | Dataset marcado como sintético, limitaciones visibles, no se declara validez productiva | El comportamiento puede cambiar con proyectos reales |
| Leakage | Outcome final entra al modelo | whitelist de features, split por project_id y exclusión de actual cost/duration/targets | SPI/CPI tardíos pueden estar cerca del outcome |
| Causalidad falsa | Feature importance se interpreta como causa | drivers rotulados como sensibilidad local, no causalidad | Un usuario puede sobreinterpretar la explicación |
| Disponibilidad | Ollama no responde | fallback determinístico; ML funciona independientemente | Calidad de explicación puede bajar |
| Entrada malformada | Valores fuera de rango o CSV excesivo | Pydantic, límites de rango, máximo 100 filas y 5 MB en la demo | Producción requiere autenticación, rate limiting y WAF |
| Exposición web | CORS abierto en demo | `PRUNIN_CORS_ORIGINS` permite restringir orígenes en despliegue | La demo local mantiene `*` si no se configura |
| Drift | Distribución real cambia | métricas/versionado y monitoring runtime; política de reentrenamiento documentada | Aún no existe una serie histórica real para umbrales de drift |

## Uso responsable de Team Health

`team_health_index` utiliza señales operativas. No estima moral, felicidad, salud mental ni características psicológicas. No debe emplearse para decisiones de recursos humanos sobre individuos.

## Datos reales

Antes de usar proyectos reales deben definirse:

- propósito y base legal del tratamiento;
- minimización de datos;
- clasificación de información empresarial;
- retención y borrado;
- autenticación y autorización;
- registro de acceso;
- anonimización o pseudonimización cuando aplique;
- proceso de revisión humana para recomendaciones de alto impacto.
