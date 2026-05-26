# Simulador Macroeconómico Abierto V2.0 — Guía de Producción

¡Bienvenido a la versión V2.0 del Simulador Macroeconómico Abierto! Esta aplicación recrea un modelo Mundell-Fleming dinámico e interactivo diseñado para experimentar con la formulación de políticas fiscales, monetarias y cambiarias en economías abiertas.

## 📊 Arquitectura del Sistema (V2.0)

El simulador se divide estrictamente según un flujo de datos unidireccional para garantizar desacoplamiento y consistencia:

```
[Configuraciones] ➔ [Motor Matemático/Dinámico] ➔ [Administrador de Estado] ➔ [Pantallas e Interfaz UI]
```

1. **Configuración (`config/`)**:
   - `parameters_v2.py`: Declaración de esquemas `TypedDict` y valores por defecto (impuestos proporcionales `t`, elasticidades, movilidad capitales `f`, pass-through).
   - `scenarios_v2.py`: Presets pre-calibrados para el onboarding del juego.
   - `validation_rules_v2.py`: Restricciones de validación de entradas de sliders y checks de cordura.
   - `scoring_v2.py`: Pesos y algoritmos de penalización/desempeño por turno.
2. **Motor (`engine/`)**:
   - `core_v2.py`: Solver puro analítico e iterativo IS-LM-BP (con `fsolve` para TC flexible).
   - `dynamics_v2.py`: Ecuaciones de inflación adaptativa con pass-through, desempleo con brecha de Okun y dinámica fiscal de deuda pública.
   - `game_state.py`: Definición tipada de la snapshot y el historial.
   - `events_engine.py`: Motor endógeno/exógeno con semillas hashes estables y deterministas.
   - `advisor_system.py`: Proyecciones preventivas "dry-run" del gabinete ministerial.
   - `state_manager_v2.py`: El cerebro orquestador que gestiona el loop de juego de 10 turnos.
3. **Interfaz (`ui/`)**:
   - Visualizaciones Bloomberg-Style optimizadas en dashboards de 3 columnas (`dashboard_main.py`).
   - KPI Panels con Plotly sparklines embebidas.
   - Spider Charts normalizados [0, 1] y exportación a PDF de reportes finales en el Endgame (`endgame_screen.py`).

---

## 🐯 Presets de Escenarios de Onboarding

Cada escenario ha sido rigurosamente calibrado bajo piloto automático para ofrecer una experiencia balanceada y desafiante:

1. **🐯 El Tigre Asiático (Fácil)**:
   - *Contexto*: Economía con crecimiento acelerado y reservas sólidas.
   - *Comportamiento*: Sin intervención, finaliza en el Turno 10 en recalentamiento controlado con una inflación acumulada $\pi > 8\%$.
2. **📉 Desequilibrio Comercial (Medio)**:
   - *Contexto*: Elevada brecha autónoma comercial ($NX_0 = -10$) y reservas decrecientes.
   - *Comportamiento*: Sin intervención, detona el circuit breaker cambiario por falta de reservas internacionales ($R \le 0$) entre el Turno 6 y 8.
3. **🔥 Crisis Latinoamericana (Difícil)**:
   - *Contexto*: Economía estanflacionaria clásica con elevadas expectativas de inflación y reservas al límite.
   - *Comportamiento*: Sin intervención, incurre en un default de deuda pública (soberano) forzando el Game Over antes del Turno 7.
4. **💀 Espiral de la Muerte (Muy difícil)**:
   - *Contexto*: Hiperinflación rampante combinada con recesión profunda y deuda desbocada al borde del colapso.
   - *Comportamiento*: Sin intervención, precipita un Game Over inevitable antes del Turno 4.

---

## 🚀 Instalación y Despliegue

### ⚙️ Requisitos de Entorno
- **Python**: Versión `3.12` recomendada (definida en `.python-version`).
- **Streamlit**: Configurado con servidor seguro y tema oscuro oficial en `.streamlit/config.toml`.

### 📦 Instalación en Producción
Instale las dependencias optimizadas de producción (sin paquetes de testing o desarrollo redundantes):
```bash
pip install -r requirements.txt
```

### 🛠️ Instalación en Desarrollo
Instale todas las dependencias incluyendo suites de testing (`pytest`), linters (`black`, `mypy`) y modeladores de Monte Carlo (`scikit-learn`):
```bash
pip install -r requirements-dev.txt
```

### 💻 Levantar Localmente
Para iniciar la app interactiva de Streamlit localmente:
```bash
streamlit run main.py
```

---

## 🧪 Suite de Pruebas Automatizadas

El proyecto incluye 37 pruebas unitarias e integración en `validation/` que cubren el 100% de la consistencia matemática y económica del modelo.

Para ejecutar toda la suite de pruebas:
```bash
python -m pytest validation/ -v
```

### Casos de Prueba de Integración (`validation/test_integration.py`):
1. `test_tiger_asia_no_game_over`: 10 turnos estables con $\pi > 8\%$ en piloto automático.
2. `test_death_spiral_game_over_before_t5`: Colapso inminente antes del Turno 5.
3. `test_event_social_unrest_fires`: Detonación reactiva de disturbios si $U > 12\%$.
4. `test_ml_condition_policy_impact`: Empeoramiento de NX ante devaluación con Marshall-Lerner insatisfecho ($< 1.0$).
5. `test_crowding_out_visible`: Desplazamiento visible de la inversión privada ante expansión del gasto público.
6. `test_advisor_warning_one_turn_ahead`: Alertas preventivas emitidas exactamente un período antes del colapso.
7. `test_spider_chart_area_calculation`: Área del radar de gestión mayor que la base si el score de desempeño es positivo.
8. `test_difficulty_hard_params_hidden`: Niebla de guerra activa ocultando sliders estructurales en modo difícil.
