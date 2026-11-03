# 🏛️ ESPECIFICACIÓN TÉCNICA V1.3: MEJORAS DE REALISMO MACROECONÓMICO Y EXPERIENCIA EDUCATIVA
> **Proyecto:** The Economic War Room — Edición Educativa (V1.3 SIMPLE)  
> **Fecha:** Noviembre 2026  
> **Estado:** Documento de Especificación Aprobado para Implementación  

---

## 1. Motivación y Diagnóstico Post-Prueba Manual

Tras las pruebas de jugabilidad manual de la Versión 1.2, se confirmó la **total solidez algebraica** (error contable $< 10^{-12}$, cero solvers iterativos, superación garantizada de los 4 escenarios en 10 turnos). Sin embargo, se identificaron seis áreas clave de mejora didáctica y realismo económico:

1. **Claridad de Controles y Botones de Ayuda (Help):**
   - El término `Tasa de Política Monetaria (TPM r_ref %)` se renombra a `🏦 Tasa de Interés del Banco Central (TPM %)`.
   - Todos los componentes (las 8 palancas, las 8 tarjetas KPI, las 4 pestañas gráficas y los paneles de asesoría) deben contar con botones de ayuda contextual (`help="..."`) explícitos, claros y didácticos que expliquen la definición del instrumento, el canal de transmisión y los efectos colaterales al subirlo o bajarlo.
2. **Asignación Rigurosa de Cuadrantes en Salter-Swan y Modelo IS-LM-BP:**
   - **Salter-Swan:** Las curvas IB (Balance Interno, pendiente negativa) y EB (Balance Externo, pendiente positiva) deben derivarse con exactitud analítica y particionar el espacio $(A, q)$ en los 4 cuadrantes estándar de manual macroeconómico:
     - **Zona I:** Inflación + Superávit ($A + NX > Y_{\text{pot}}$ y $NX > 0$).
     - **Zona II:** Desempleo + Superávit ($A + NX < Y_{\text{pot}}$ y $NX > 0$).
     - **Zona III:** Desempleo + Déficit ($A + NX < Y_{\text{pot}}$ y $NX < 0$).
     - **Zona IV:** Inflación + Déficit ($A + NX > Y_{\text{pot}}$ y $NX < 0$).
     - Fondo sombreado semitransparente con los colores de cada zona y marcador destacado del país con su trayectoria histórica.
   - **IS-LM-BP:** Curva MP/LM horizontal o de regla de Taylor (enfoque moderno de tasa de interés) y visualización en línea segmentada del equilibrio del turno anterior vs proyección actual para mostrar pedagógicamente el desplazamiento provocado por los sliders.
3. **Visibilidad y Tipografía en Columna de Informe y Asesoría:**
   - Aumento general de tamaño de fuente, legibilidad y contraste en toda la Columna 3.
   - Tarjetas de los Asesores de Gabinete con diseño llamativo, bordes de color institucional (Banco Central en azul marino, Hacienda en dorado/ámbar, Trabajo y Comercio en verde esmeralda) y badges de alerta temprana destacados para forzar la atención del estudiante.
4. **Choques Exógenos como Ventanas Emergentes (Pop-ups):**
   - Los eventos exógenos (programados y aleatorios) **NO deben ubicarse como botones en el panel de control izquierdo** ni ser provocados manualmente por el estudiante.
   - Se activan dinámicamente en el ciclo de avance de turno y congelan la pantalla mediante un modal emergente nativo (`@st.dialog("🚨 EVENTO MACROECONÓMICO: COMUNICADO OFICIAL")`).
   - El modal despliega el titular periodístico, la tabla con los deltas de impacto cuantitativo en variables externas ($r^*, P^*, Y_{\text{pot}}$), la advertencia del gabinete y un único botón de confirmación: **`"Continuar gobernando 🏛️"`**.
   - Shocks calibrados leves y narrativos con ventana de cooldown (mínimo 2 turnos entre shocks graves).
5. **Realismo en Deuda Soberana, Reservas y Calificación Soberana:**
   - **Piso Estructural de Deuda / Fondo Soberano:** La deuda bruta no puede caer a $0.0$. Se fija un piso de liquidez para el mercado de capitales ($B_{\text{min}} = 10\%$ del PIB Nominal). El superávit fiscal excedente se acumula en un **Fondo Soberano de Estabilización (FSE)** o en reservas internacionales.
   - **Calificación Crediticia Multidimensional:** El rating crediticio adopta la metodología de las agencias internacionales (S&P, Moody's), ponderando Sostenibilidad Fiscal (50%), Estabilidad de Inflación (30%) y Salud Laboral/Crecimiento (20%). Si la inflación o el desempleo son críticos, el país pierde el grado de inversión independientemente de su nivel de deuda.
6. **Evolución Temporal con Finanzas Públicas y Balanza de Pagos:**
   - Incorporar en Tab 4 un gráfico de barras de **Balance Fiscal (% del PIB)** (superávit en verde, déficit en rojo) y una serie de tiempo de **Balanza de Pagos** desglosando Cuenta Corriente ($NX$) y Flujos de Capital ($KA$).

---

## 2. Catálogo Detallado de Especificaciones Matemáticas y de Interfaz

### 2.1. Panel de Control y Botones de Ayuda Contextual (`ui_simple/controls_panel.py`)

- **Nomenclatura:** `🏦 Tasa de Interés del Banco Central (TPM %)` en lugar del críptico `r_ref %`.
- **Textos de Ayuda (`help`) Obligatorios por Instrumento:**
  1. **Gasto Público Corriente ($G_c$):**  
     *"Gasto en sueldos públicos y bienes de consumo del Estado. Expande la demanda agregada y el PIB inmediatamente, pero eleva el déficit fiscal y presiona la inflación."*
  2. **Inversión Pública en Infraestructura ($I_g$):**  
     *"Gasto de capital en carreteras, puertos y energía. Aumenta la demanda presente y expande el PIB potencial futuro ($Y_{\text{pot}}$), generando crowding-in en la inversión privada."*
  3. **Impuesto a la Renta y Consumo ($t_c$):**  
     *"Grava el ingreso disponible de los hogares. Subirlo incrementa la recaudación y baja el déficit, pero frena el consumo privado y el PIB."*
  4. **Impuesto Corporativo a Empresas ($t_k$):**  
     *"Grava los beneficios empresariales. Subirlo aumenta la recaudación fiscal, pero desincentiva directamente la inversión privada de capital ($I_{\text{priv}}$)."*
  5. **Tasa de Interés del Banco Central (TPM):**  
     *"Tasa de referencia de política monetaria. Subirla eleva el costo del crédito, frena la inflación y atrae capitales externos ($KA$), pero enfría la inversión y el empleo."*
  6. **Arancel a las Importaciones ($\tau$):**  
     *"Impuesto sobre bienes importados. Protege la industria nacional y reduce las importaciones ($M$), pero encarece los precios locales y genera presiones inflacionarias."*
  7. **Subsidio a las Exportaciones ($s_x$):**  
     *"Incentivo directo a los productores exportadores. Incrementa las exportaciones brutas ($X$) y mejora la cuenta corriente, pero representa un gasto fiscal directo."*
  8. **Tipo de Cambio Nominal / Tasa de Deslizamiento ($E$ / $\text{crawl}$):**  
     *"Precio de la divisa extranjera en moneda local. Devaluar abarata los productos nacionales en el exterior y mejora $NX$, pero encarece transables y genera inflación vía pass-through."*

---

### 2.2. Ventana Emergente Modal para Choques Exógenos (`main_layout.py` y `events.py`)

- **Activación:** Se gatilla al inicio del turno si:
  a) Existe un evento histórico programado para el turno (ej. subida de tasas de la Fed en Corea T3, desaceleración global en Chile T3, shock Tequila en México T1, etc.).
  b) O se activa un evento aleatorio calibrado leve en escenarios libres.
- **Estructura Visual del Modal:**
  ```python
  @st.dialog("🚨 COMUNICADO MACROECONÓMICO OFICIAL")
  def show_event_modal(event_data):
      st.subheader(f"📰 {event_data['title']}")
      st.write(event_data['description'])
      # Tabla de impactos cuantitativos
      st.table(event_data['impact_metrics'])
      st.info(f"💡 Asesoría del Gabinete: {event_data['advice_summary']}")
      if st.button("Continuar gobernando 🏛️", use_container_width=True):
          st.session_state.event_modal_dismissed = True
          st.rerun()
  ```
- **Calibración de Shocks Aleatorios Leves:**
  - *Boom de commodities:* $+5\%$ temporal en $P^*$.
  - *Alza de tasas de la Fed:* $+150$ bps en $r^*$ (no $+400$ bps).
  - *Sequía / Clima:* $-2\%$ en PIB potencial temporal.
  - *Histéresis / Cooldown:* Mínimo 2 turnos de pausa antes de que pueda ocurrir otro evento aleatorio.

---

### 2.3. Diagrama Salter-Swan Riguroso y Cuadrantes Canónicos (`charts_panel.py`)

El espacio se define con:
- **Eje X:** Absorción Doméstica $A = C + I_{\text{priv}} + G$.
- **Eje Y:** Tipo de Cambio Real $q = \frac{E \cdot P^*}{P_{\text{local}}}$.

#### A. Ecuación de la Curva IB (Internal Balance — Pleno Empleo $Y = Y_{\text{pot}}$):
$$Y_{\text{pot}} = A + NX(q, Y_{\text{pot}})$$
$$NX(q, Y_{\text{pot}}) = X(q) - M_{\text{imp}}(q, Y_{\text{pot}})$$
Despejando $q$ en función de $A$, la pendiente es **estrictamente negativa**:
$$\left.\frac{dq}{dA}\right|_{IB} = -\frac{1}{\epsilon_x + \epsilon_m} < 0$$

#### B. Ecuación de la Curva EB (External Balance — Cuenta Corriente Equilibrada $NX = 0$):
$$NX(q, A) = 0 \implies X(q) = M_{\text{imp}}(q, A)$$
Despejando $q$ en función de $A$, la pendiente es **estrictamente positiva**:
$$\left.\frac{dq}{dA}\right|_{EB} = \frac{m_1}{\epsilon_x + \epsilon_m} > 0$$

#### C. Asignación Canónica de los 4 Cuadrantes:

```
  Tipo de Cambio Real (q) ↑
          │        (EB: NX = 0)
          │          /  
          │  ZONA II/   ZONA I
          │        /   
          │       /   (IB: Pleno Empleo)
          │      / \
          │     /   \
          │    /     \
          │   /       \
          │  / ZONA III\  ZONA IV
          │ /           \
          └─────────────────────────────→ Absorción Doméstica (A)
```

| Zona | Nombre Canónico | Condición Matemática | Diagnóstico Macroeconómico | Prescripción de Política |
| :---: | :--- | :---: | :--- | :--- |
| **I** | **Inflación + Superávit** | $q > q_{IB} \quad\text{y}\quad q > q_{EB}$ | Sobrecalentamiento con exceso de demanda externa | Reducir absorción ($A \downarrow$) o apreciar moneda ($q \downarrow$) |
| **II** | **Desempleo + Superávit** | $q < q_{IB} \quad\text{y}\quad q > q_{EB}$ | Capacidad ociosa con superávit en cuenta corriente | Estimular gasto interno ($A \uparrow$) |
| **III** | **Desempleo + Déficit** | $q < q_{IB} \quad\text{y}\quad q < q_{EB}$ | Recesión y desbalance externo crítico (crisis clásica) | Devaluar moneda ($q \uparrow$) |
| **IV** | **Inflación + Déficit** | $q > q_{IB} \quad\text{y}\quad q < q_{EB}$ | Sobreconsumo interno con fuga de divisas | Ajuste fiscal contractivo ($A \downarrow$) |

---

### 2.4. Dinámica de Deuda Realista y Rating Crediticio Multidimensional (`dynamics.py`)

#### A. Piso Estructural de Deuda Soberana y Fondo Soberano (FSE):
1. **Piso de Emisión Soberana:**
   $$B_{\text{min}} = 0.10 \cdot \text{PIB Nominal}_t$$
2. **Evolución de Deuda Bruta:**
   $$B_t = \max(B_{\text{min}}, \; B_{t-1} + \text{Déficit}_t)$$
3. **Mecanismo de Fondo Soberano / Reservas:**
   Si la economía genera superávit fiscal ($\text{Déficit}_t < 0$) y la deuda ya está en su piso ($B_{t-1} \le B_{\text{min}}$):
   $$\text{Ahorro Soberano Excedente} = |\text{Déficit}_t| \implies \Delta R_t = |\text{Déficit}_t|$$
   La deuda bruta no desaparece; el patrimonio soberano neto se incrementa en reservas internacionales líquidas.

#### B. Matriz de Calificación Soberana Multidimensional:
El puntaje crediticio integral $S_{\text{rating}} \in [0, 10]$ se calcula como:
$$S_{\text{rating}} = 0.50 \cdot S_{\text{deuda}} + 0.30 \cdot S_{\text{inflación}} + 0.20 \cdot S_{\text{laboral}}$$

1. **Subpuntaje Fiscal ($S_{\text{deuda}}$):**
   - $\text{RatioDeuda} \le 25\% \to 10$
   - $\text{RatioDeuda} \le 50\% \to 8$
   - $\text{RatioDeuda} \le 75\% \to 6$
   - $\text{RatioDeuda} \le 100\% \to 4$
   - $\text{RatioDeuda} \le 135\% \to 2$
   - $\text{RatioDeuda} > 135\% \to 0$
2. **Subpuntaje Monetario ($S_{\text{inflación}}$):**
   - $|\pi - 3\%| \le 1.5\% \to 10$
   - $|\pi - 3\%| \le 4.0\% \to 7$
   - $|\pi - 3\%| \le 8.0\% \to 5$
   - $|\pi - 3\%| \le 15.0\% \to 2$
   - $|\pi - 3\%| > 15.0\% \to 0$ (Incompatible con Grado de Inversión)
3. **Subpuntaje Real y Laboral ($S_{\text{laboral}}$):**
   - $U \le U_n + 1.0\% \to 10$
   - $U \le U_n + 3.0\% \to 7$
   - $U \le U_n + 6.0\% \to 4$
   - $U > U_n + 6.0\% \to 1$

**Escala de Calificación:**
- $S \ge 9.0 \implies \mathbf{AAA}$
- $8.0 \le S < 9.0 \implies \mathbf{AA}$
- $6.5 \le S < 8.0 \implies \mathbf{A}$
- $5.0 \le S < 6.5 \implies \mathbf{BBB}$ *(Límite de Grado de Inversión)*
- $3.5 \le S < 5.0 \implies \mathbf{BB}$
- $2.0 \le S < 3.5 \implies \mathbf{B}$
- $S < 2.0 \implies \mathbf{CCC/D}$

---

### 2.5. Rediseño Visual de Asesores de Gabinete (`explanation_panel.py` y `styles.py`)

- **Tipografía y Legibilidad:**
  - Aumento de tamaño de fuente (`font-size: 0.95rem` en párrafos, `1.15rem` en encabezados).
  - Alto contraste (negro carbón `#0f172a` sobre tarjetas blanco puro con sutiles sombras CSS).
- **Tarjetas Ministeriales con Identidad Visual:**
  - 🏛️ **Banco Central:** Borde izquierdo azul institucional (`#1e40af`, 4px), enfocado en la tasa real $r - \pi^e$, anclaje y tipo de cambio.
  - 💼 **Ministerio de Hacienda:** Borde izquierdo dorado/ámbar (`#d97706`, 4px), enfocado en balance primario, intereses y ratio de deuda.
  - 📈 **Ministerio de Trabajo y Comercio:** Borde izquierdo verde esmeralda (`#059669`, 4px), enfocado en desempleo $U$, saldos de cuenta corriente $NX$ y estímulos a infraestructura.
- **Banner de Alerta Prioritaria:** Si algún indicador entra en zona de tensión, la tarjeta correspondiente despliega en la parte superior un banner parpadeante: `"⚠️ ADVERTENCIA CRÍTICA PARA EL MINISTRO"`.
