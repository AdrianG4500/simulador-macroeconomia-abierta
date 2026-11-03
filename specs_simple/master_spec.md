# 🏛️ ESPECIFICACIÓN MAESTRA INTEGRAL: THE ECONOMIC WAR ROOM (V1.2 SIMPLE)

## 1. Filosofía y Arquitectura del Sistema

- **Base de código oficial:** Se trabaja exclusivamente sobre la arquitectura limpia y analítica (`main_simple.py`, `engine_simple/`, `config_simple/`, `ui_simple/`, `tests_simple/`).
    
      
    
- **Cero Solvers Iterativos:** Queda prohibido el uso de `scipy.optimize.fsolve` o `least_squares`. Todas las variables se resuelven mediante **fórmulas algebraicas cerradas** en un solo paso, garantizando velocidad instantánea para 40 usuarios simultáneos y error cero en la identidad macroeconómica ($\vert{}Y - (C + I + G + NX)\vert{} < 10^{-12}$).
    
      
    
- **Estética Conservada:** Se mantiene el diseño profesional blanco de 3 columnas de tu captura (`image_200986.png`):
    
      
    - **Columna Izquierda (25%):** Selector de escenario histórico, las 8 palancas agrupadas, previsualización en vivo (_Live Dry-Run_) y botón de avance de turno.
        
          
        
    - **Columna Central (50%):** 8 tarjetas KPI superiores, seguidas de las pestañas gráficas (_Modelo IS-LM-BP_, _Diagrama Salter-Swan_, _Trilema Cambiario_ y _Evolución Temporal_).
        
          
        
    - **Columna DereñAa (25%):** Periódico _El Observador Macroeconómico_ y tarjetas socráticas de los _Asesores de Gabinete_.
        
          
        

## 2. Catálogo Definitivo de las 8 Palancas de Política Económica

El estudiante controla exactamente **8 instrumentos** divididos en 3 bloques ministeriales:

  

|**#**|**Bloque**|**Instrumento**|**Variable**|**Rango**|**Paso**|**Canal de Transmisión Principal**|
|---|---|---|---|---|---|---|
|**1**|**Fiscal**|Gasto Público Corriente|$G_c$|$[5.0, 35.0]$|$0.5$|Sube la Demanda Agregada ($Y$) hoy; aumenta el déficit fiscal; no amplía el PIB potencial.|
|**2**|**Fiscal**|Inversión Pública (Infraestructura)|$I_g$|$[0.0, 25.0]$|$0.5$|Sube la Demanda Agregada ($Y$) hoy; expande el PIB Potencial futuro ($Y_{\text{pot}}$) y atrae inversión privada (_crowding-in_).|
|**3**|**Fiscal**|Impuesto a la Renta / Consumo|$t_c$|$[5.0\%, 40.0\%]$|$0.5\%$|Reduce el ingreso disponible de las familias ($C$) y achica el multiplicador keynesiano ($k_m$); aumenta la recaudación.|
|**4**|**Fiscal**|Impuesto Corporativo (Empresas)|$t_k$|$[0.0\%, 35.0\%]$|$0.5\%$|Reduce la Formación Bruta de Capital Privado ($I_{\text{priv}}$); aumenta la recaudación fiscal sin tocar directamente el consumo familiar.|
|**5**|**Monetario**|Tasa de Política Monetaria (TPM)|$r_{\text{ref}}$|$[1.0\%, 30.0\%]$|$0.25\%$|Sube la tasa de interés real ($r$), enfría la inversión privada ($I_{\text{priv}}$), frena la salida de capitales y ancla expectativas de inflación ($\pi^e$).|
|**6**|**Comercial**|Arancel a las Importaciones|$\tau$|$[0.0\%, 30.0\%]$|$0.5\%$|Frena importaciones ($M_{\text{imp}}$), protege Reservas ($R$) y recauda aduana ($\tau \cdot M_{\text{imp}}$), pero encarece precios locales ($P_{\text{local}}$) sumando inflación de costos.|
|**7**|**Comercial**|Subsidio a las Exportaciones|$s_x$|$[0.0\%, 20.0\%]$|$0.5\%$|Impulsa exportaciones ($X$), mejora la balanza comercial ($NX$) y el PIB, pero cuesta dinero al fisco ($s_x \cdot X$) aumentando el déficit.|
|**8**|**Cambiario**|Tipo de Cambio / Tasa de Crawl|$E$ / $\text{crawl}$|$E \in [5.0, 25.0]$|$0.1$|En **Fijo**: el jugador fija $E$ (devaluar mejora $NX$ pero dispara inflación por _pass-through_). En **Crawling**: fija el deslizamiento $\%$. En **Flexible**: bloqueado ($E$ flota solo según el mercado).|

> **Nota sobre Régimen Cambiario:** Cada escenario inicia con su régimen histórico predefinido. El usuario dispone de un botón especial de **"Reforma Cambiaria de Emergencia"** (por ejemplo, para pasar de Tipo de Cambio Fijo a Flotación en México 1994 o unificar el cambio en Bolivia 1985).
> 
>   

## 3. Fórmulas Exactas del Motor Analítico Cerrado (`engine_simple`)

Todas las ecuaciones se ejecutan en orden secuencial determinista en cada turno $t \in \{1, \dots, 10\}$:

  

### 3.1. Precios y Tipo de Cambio Real (Normalizados en Base $E_0 = 10.0$)

Para evitar que un tipo de cambio nominal $E = 10.0$ multiplique por 10 el nivel de precios en el Turno 0:

  

$$P_T = \left(\frac{E_t}{10.0}\right) \cdot P^* \cdot (1 + 0.50 \cdot \tau)$$

$$P_{\text{local}} = \alpha_{PT} \cdot P_T + (1 - \alpha_{PT}) \cdot P_{NT, t} \quad (\text{con } \alpha_{PT} = 0.40)$$

$$q_t = \frac{(E_t / 10.0) \cdot P^*}{P_{\text{local}}}$$

_(En $T=0$, con $E_0=10, P^*=1, P_{NT}=1, \tau = 0$ , resulta exactamente $P_{\text{local},0} = 1.00$ y $q_0 = 1.00$).*

  

### 3.2. Multiplicador y Componentes de Demanda Agregada ($Y = C + I + G + NX$)

1. **Multiplicador Keynesiano Ampliado:**
    
      
    
    $$k_m = \frac{1}{1 - c_1(1 - t_c) + m_1(1 - \tau)}$$
    
2. **Tasa de Interés Doméstica Efectiva ($r_t$):**
    
      
    - En régimen **Flexible**: $r_t = r_{\text{ref}} + 0.5 \cdot \rho_t$
        
          
        
    - En régimen **Fijo / Crawling** (Trilema): $r_t = 0.60 \cdot r_{\text{ref}} + 0.40 \cdot (r^* + \text{crawl\_rate} \cdot 100 + \rho_t)$
        
          
        
3. **Formación Bruta de Capital Privado ($I_{\text{priv}}$):**
    
      
    
    $$I_{\text{priv}, t} = \max\left(2.0, \; I_0 - b \cdot (r_t - r_0) - \rho_k \cdot (t_k - t_{k,0}) + \psi_{ci} \cdot (I_g - I_{g,0}) - \psi_{co} \cdot \max(0, \text{RatioDeuda}_{t-1} - 0.60)\right)$$
    
4. **Gasto Público Total ($G_t$):**
    
      
    
    $$G_t = G_c + I_g$$
    
5. **Comercio Exterior Desagregado ($X_t, M_{\text{imp}, t}, NX_t$):**
    
      
    
    $$X_t = x_0 + \epsilon_x \cdot (q_t - 1.0) + \eta_x \cdot s_x$$
    
    $$M_{\text{imp}, t} = \max\left(2.0, \; m_0 + m_1 \cdot (1 - \tau) \cdot Y_t - \epsilon_m \cdot (q_t - 1.0)\right)$$
    
6. **Solución Analítica Cerrada del PIB Real ($Y_{\text{eq}}$):**
    
      
    
    $$Y_{\text{eq}} = k_m \cdot \left[c_0 + I_{\text{priv}, t} + G_c + I_g + X_t - m_0 + \epsilon_m \cdot (q_t - 1.0)\right]$$
    
    **Amortiguador de Inercia Macroeconómica (65/35):**
    
      
    
    $$Y_t = 0.65 \cdot Y_{\text{eq}} + 0.35 \cdot Y_{t-1}$$
    
    _(Para conservar la identidad exacta $Y_t \equiv C_t + I_{\text{priv},t} + G_t + NX_t$ al milímetro tras el suavizado, $C_t = c_0 + c_1(1 - t_c)Y_t$, $M_{\text{imp},t}$ se evalúa con $Y_t$, y el ajuste de inventario se absorbe en $I_{\text{priv},t} = Y_t - C_t - G_t - NX_t$)._
    
      
    

### 3.3. Oferta Agregada, Empleo (Okun) e Inflación Ponderada (Phillips)

1. **Evolución del PIB Potencial ($Y_{\text{pot}}$):**
    
      
    
    $$Y_{\text{pot}, t} = Y_{\text{pot}, t-1} \cdot (1 + g_{\text{pot}}) + 0.18 \cdot (I_g - I_{g,\text{dep}})$$
    
2. **Brecha del Producto ($\text{Gap}_t$) y Desempleo ($U_t$):**
    
      
    
    $$\text{Gap}_t = \frac{Y_t - Y_{\text{pot}, t}}{Y_{\text{pot}, t}}$$
    
    $$U_t = \max\left(0.02, \; U_n - \gamma_{\text{okun}} \cdot \text{Gap}_t\right)$$
    
3. **Inflación Multicausal ($\pi_t$):**
    
    Explicada conjuntamente por **4 fuerzas reales** (Expectativas + Demanda + Devaluación + Costo Arancelario):
    
      
    
    $$\pi_t = \pi^e_t + \alpha_{\text{inf}} \cdot \text{Gap}_t + \beta_{PT} \cdot \left(\frac{E_t - E_{t-1}}{E_{t-1}}\right) + 0.15 \cdot (\tau_t - \tau_{t-1}) + \text{Shock}_{\text{señoreaje}}$$
    
4. **Credibilidad Endógena ($\theta_t \in [0.40, 0.80]$) y Expectativas ($\pi^e_{t+1}$):**
    
      
    - Base garantizada: $\theta_{\text{base}} = 0.40$ (nunca menor a $40\%$).
        
          
        
    - Bono por rigor monetario (Principio de Taylor): $+0.20$ si $r_{\text{ref}} \ge \pi_t \cdot 100$.
        
          
        
    - Bono por disciplina fiscal: $+0.20$ si el Déficit Primario $\le 1.5\%$ del PIB.
        
          
        
        $$\pi^e_{t+1} = \theta_t \cdot \pi_{\text{meta}} + (1 - \theta_t) \cdot \pi_t \quad (\text{con } \pi_{\text{meta}} = 0.03)$$
        

### 3.4. Finanzas Públicas, Deuda sobre PIB Nominal y Balanza de Pagos

1. **Recaudación, Costo de Subsidios y Déficit:**
    
      
    
    $$\text{Recaudación}_t = (t_c + t_k) \cdot Y_t + \tau \cdot M_{\text{imp}, t}$$
    
    $$\text{CostoSubsidios}_t = s_x \cdot X_t$$
    
    $$\text{InteresesDeuda}_t = \left(\frac{r^* + \rho_t}{100}\right) \cdot B_{t-1}$$
    
    $$\text{Déficit}_t = G_c + I_g + \text{CostoSubsidios}_t + \text{InteresesDeuda}_t - \text{Recaudación}_t$$
    
    $$B_t = \max(0.0, \; B_{t-1} + \text{Déficit}_t)$$
    
2. **Ratio de Sostenibilidad Fiscal (Sobre PIB Nominal):**
    
      
    
    $$\text{PIB Nominal}_t = Y_t \cdot P_{\text{local}, t}$$
    
    $$\text{RatioDeuda}_t = \frac{B_t}{\text{PIB Nominal}_t}$$
    
3. **Flujos de Capital ($KA_t$) y Reservas Internacionales ($R_t$):**
    
      
    
    $$KA_t = f \cdot \left(\frac{r_t - r^* - \rho_t - \Delta E^e}{100}\right)$$
    
    - En régimen **Fijo / Crawling**: $R_t = R_{t-1} + NX_t + KA_t$.
        
          
        
    - En régimen **Flexible**: $R_t = R_{t-1} + 0.15 \cdot (NX_t + KA_t)$ (el ajuste grueso lo absorbe el tipo de cambio $E_t = E_{t-1} \cdot \left[1 - 0.015 \cdot (NX_t + KA_t)\right]$).
        
          
        

## 4. Blindaje Anti-Bucle: Límites de Game Over y Aprobación Ciudadana

Para garantizar que **jamás se produzca un Game Over injusto cuando el alumno aplica las políticas correctas** y que Antigravity no entre en bucles tratando de pasar tests imposibles, se establecen dos reglas de hierro:

  

### Regla 1: Período de Gracia Inicial + Condición de Persistencia (2 Turnos Consecutivos)

Ningún escenario puede terminar en _Game Over_ en los **Turnos 1 y 2** (ventana de estabilización de emergencia). A partir del Turno 3, el _Game Over_ solo se ejecuta si una condición letal se mantiene durante **2 turnos consecutivos** (en el primer turno que se cruza el umbral, el Gabinete lanza una **Alerta Roja Crítica** dándole al estudiante 1 turno de margen para corregirlo):

  

|**Condición de Colapso**|**Umbral de Alerta Roja (1er Turno)**|**Umbral de Game Over (2 Turnos Seguidos)**|
|---|---|---|
|**1. Insolvencia Soberana (Default)**|$\frac{B_t}{Y_t \cdot P_{\text{local}, t}} > 135\%$|$\frac{B_t}{Y_t \cdot P_{\text{local}, t}} > 150\%$ por 2 turnos|
|**2. Crisis de Balanza de Pagos**|$R_t < 8.0\text{ MUSD}$|$R_t \le 2.0\text{ MUSD}$ por 2 turnos|
|**3. Espiral Hiperinflacionaria**|$\pi_t > 35.0\%$|$\pi_t > 50.0\%$ por 2 turnos|
|**4. Estallido Social / Depresión**|$U_t > 22.0\%$ o caída $g_Y < -15\%$|$U_t > 25.0\%$ por 2 turnos|

### Regla 2: Puntaje de Aprobación Ciudadana ($0$ a $100$) Ponderado

$$\text{Score}_t = 100 - \left(1.2 \cdot \vert{}\text{Gap}_t \cdot 100\vert{} + 2.0 \cdot \max(0, (U_t - U_n)\cdot 100) + 1.5 \cdot \vert{}\pi_t - 0.03\vert{}\cdot 100 + 0.5 \cdot \max(0, \text{RatioDeuda}_t\cdot 100 - 60)\right)$$

Acotado suavemente entre $[0, 100]$ con inercia $0.70 \cdot \text{Score}_{\text{calc}} + 0.30 \cdot \text{Score}_{t-1}$.

  

## 5. Calibración Histórica Real de los 4 Escenarios (Datos Banco Mundial / FMI)

Todos los escenarios están calibrados algebraicamente para que en $T=0$ el PIB inicial $Y_0$ cuadre exactamente con los datos históricos reales:

  

### Escenario 1: 🇰🇷 Corea del Sur (1985) — _"El Milagro del Río Han"_ (Dificultad: FÁCIL)

- **Datos Históricos Reales (WDI 1985):** Crecimiento PIB $\approx 7.8\%$, Inflación $2.5\%$, Desempleo $4.0\%$, Deuda Pública $\approx 19\%$ del PIB, fuerte impulso industrial exportador.
    
      
    
- **Estado Inicial Calibrado ($T=0$):**
    
      
    - $Y_0 = 100.0$, $Y_{\text{pot},0} = 100.0$ ($\text{Gap} = 0.0\%$), $\pi_0 = 3.0\%$, $U_0 = 4.0\%$ ($U_n = 4.0\%$), $R_0 = 80.0\text{ MUSD}$, $B_0 = 20.0$ ($\text{Deuda/PIB} = 20.0\%$, Rating `AA`).
        
          
        
    - **Palancas en $T=0$:** Régimen `FIXED` ($E=10.0$), $G_c = 12.0$, $I_g = 8.0$, $t_c = 15.0\%$, $t_k = 10.0\%$, $r_{\text{ref}} = 6.0\%$, $\tau = 5.0\%$, $s_x = 2.0\%$.
        
          
        
- **Evento Histórico Programado (T3):** _Alza de tasas internacionales / Fricción comercial_ ($r^*$ sube $+1.5\%$).
    
      
    
- **Receta Histórica para Ganar:** Mantener alta la inversión en infraestructura ($I_g \in [9, 12]$), impulsar subsidios exportadores ($s_x \in [4\%, 6\%]$), mantener impuesto corporativo bajo ($t_k \le 10\%$) y moderar inflación con $r_{\text{ref}} \approx 7\%$.
    
      
    

### Escenario 2: 🇨🇱 Chile (2000–2005) — _"Regla Fiscal y Estabilidad"_ (Dificultad: NORMAL)

- **Datos Históricos Reales (WDI 2000-2005):** Inflación en meta ($3.0\%$), Desempleo estructural $5.5\%$, Deuda Pública muy baja ($15.0\%$ del PIB), apertura comercial por TLCs (baja de aranceles) y superávit estructural con el cobre.
    
      
    
- **Estado Inicial Calibrado ($T=0$):**
    
      
    - $Y_0 = 100.0$, $Y_{\text{pot},0} = 100.0$ ($\text{Gap} = 0.0\%$), $\pi_0 = 3.0\%$, $U_0 = 5.0\%$ ($U_n = 5.0\%$), $R_0 = 60.0\text{ MUSD}$, $B_0 = 15.0$ ($\text{Deuda/PIB} = 15.0\%$, Rating `AA+`).
        
          
        
    - **Palancas en $T=0$:** Régimen `FLEXIBLE` ($E=10.0$), $G_c = 14.0$, $I_g = 6.0$, $t_c = 16.0\%$, $t_k = 10.0\%$, $r_{\text{ref}} = 5.0\%$, $\tau = 6.0\%$, $s_x = 0.0\%$.
        
          
        
- **Eventos Históricos Programados:** En **T3** _Desaceleración Global_ ($X_0$ cae $-4.0$); en **T6** _Superciclo del Cobre_ ($X_0$ sube $+8.0$).
    
      
    
- **Receta Histórica para Ganar:** Aplicar política contracíclica pura: en T3-T4 estimular con $I_g \uparrow$ y bajar $r_{\text{ref}}$; en T6-T9 (durante el boom del cobre) ahorrar conteniendo $G_c$ y reduciendo aranceles $\tau$ al $2\%$ para abaratar importaciones y mantener la inflación clavada en $3\%$.
    
      
    

### Escenario 3: 🇲🇽 México (1994–1995) — _"El Efecto Tequila"_ (Dificultad: DIFÍCIL)

- **Datos Históricos Reales (WDI / Banxico 1994):** Fuerte déficit de cuenta corriente ($NX = -9.0$), Reservas Internacionales desplomándose ($R_0 = 22.0\text{ MUSD}$), tipo de cambio semi-fijo sobrevaluado, inflación reprimida en $7.0\%$ que salta tras la devaluación, Deuda Pública en $52.0\%$ del PIB.
    
      
    
- **Estado Inicial Calibrado ($T=0$):**
    
      
    - $Y_0 = 98.0$, $Y_{\text{pot},0} = 100.0$ ($\text{Gap} = -2.0\%$), $\pi_0 = 7.5\%$, $U_0 = 6.5\%$ ($U_n = 5.5\%$), $R_0 = 22.0\text{ MUSD}$, $B_0 = 52.0$ ($\text{Deuda/PIB} = 53.1\%$, Rating `BB`).
        
          
        
    - **Palancas en $T=0$:** Régimen `FIXED` ($E=10.0$), $G_c = 16.0$, $I_g = 4.0$, $t_c = 14.0\%$, $t_k = 10.0\%$, $r_{\text{ref}} = 8.0\%$, $\tau = 5.0\%$, $s_x = 0.0\%$.
        
          
        
- **Evento Histórico Programado (T1):** _Fuga de Capitales y Choque de Tasas en EE. UU._ ($r^*$ sube $+2.5\%$ y riesgo país $\rho$ salta). Si el jugador deja el TC Fijo en $10.0$ sin hacer nada, las reservas se agotan en T3.
    
      
    
- **Receta Histórica para Ganar:**
    
      
    1. **T1–T2 (Estabilización de Emergencia):** Activar la transición a régimen **Flexible** (o devaluar $E$ a $12.5$), subir la TPM ($r_{\text{ref}}$ a $14\% - 16\%$) para frenar la salida de dólares y recortar gasto corriente ($G_c$ a $13.0$).
        
          
        
    2. **T3–T10 (Recuperación Exportadora TLCAN):** Con el tipo de cambio competitivo ($q > 1$), apoyar con subsidio exportador ($s_x = 4\%$), subir $I_g$ gradualmente a $7.0$ e ir bajando $r_{\text{ref}}$ hacia $8\%$ conforme cede la inflación.
        
          
        

### Escenario 4: 🇧🇴 Bolivia (1982–1985) — _"Hiperinflación y D.S. 21060"_ (Dificultad: MUY DIFÍCIL)

- **Datos Históricos Reales (BCB / WDI 1982-1985):** Colapso productivo ($\text{Gap} = -8.0\%$), inflación descontrolada alimentada por déficit fiscal crónico (gasto estatal alto con recaudación tributaria mínima), reservas casi agotadas ($R_0 = 15.0\text{ MUSD}$) y deuda elevada ($B_0 = 70.0$).
    
      
    
- **Estado Inicial Calibrado ($T=0$):**
    
      
    - $Y_0 = 92.0$, $Y_{\text{pot},0} = 100.0$ ($\text{Gap} = -8.0\%$), $\pi_0 = 24.0\%$ (escala de hiperinflación en el modelo), $U_0 = 11.0\%$ ($U_n = 6.5\%$), $R_0 = 15.0\text{ MUSD}$, $B_0 = 70.0$ ($\text{Deuda/PIB} = 76.1\%$, Rating `CCC`).
        
          
        
    - **Palancas en $T=0$:** Régimen `CRAWLING_PEG` ($\text{crawl} = 8.0\%$), $G_c = 22.0$ (sobredimensionado), $I_g = 2.0$, $t_c = 8.0\%$ (evasión/rezago tributario), $t_k = 5.0\%$, $r_{\text{ref}} = 10.0\%$ (tasa real negativa frente a $\pi=24\%$), $\tau = 10.0\%$, $s_x = 0.0\%$.
        
          
        
- **Receta Histórica para Ganar (El Plan D.S. 21060 + Reforma Tributaria Ley 843):**
    
      
    1. **T1–T3 (Terapia de Shock — Caja Única y Anclaje):** Recortar el gasto corriente de $22.0$ a $14.0$, aplicar la Reforma Tributaria subiendo $t_c$ de $8\%$ a $16\%$ y $t_k$ a $10\%$ (elimina el déficit fiscal de raíz), subir $r_{\text{ref}}$ a $18\% - 20\%$ (tasa real positiva) y pasar a flotación controlada / bajar el $\text{crawl}$ a $2\%$ para cortar el _pass-through_ cambiario. Esto dispara la credibilidad $\theta$ a $0.80$ y desploma la inflación del $24\%$ al $7\%$ en 3 turnos.
        
          
        
    2. **T4–T10 (Reactivación Post-Estabilización - Fondo Social de Emergencia):** Con la inflación ya controlada ($< 5\%$), bajar gradualmente $r_{\text{ref}}$ hacia $7\%$, invertir fuertemente en infraestructura pública ($I_g$ de $2.0$ a $8.0$) y estimular exportaciones ($s_x = 5\%$) para recuperar el pleno empleo ($Y \to 105, U \to 6.5\%$).
        
          
        

## 6. Interfaz Gráfica, Visualizaciones y Preparación para Fase B

1. Conservación del Layout de 3 Columnas (`image_200986.png`):
    
      
    - Mismo encabezado azul oscuro institucional, tarjetas limpias sobre fondo blanco y tipografía clara.
        
          
        
2. **Las 4 Pestañas Gráficas Centrales (`ui_simple/charts_panel.py`):**
    
      
    - **Tab 1 — `📈 Modelo IS-LM-BP`:** Muestra el desplazamiento en vivo de las curvas IS (azul), LM (verde) y BP (roja punteada) comparando el equilibrio anterior con la proyección de los sliders actuales.
        
          
        
    - **Tab 2 — `⚖️ Diagrama Salter-Swan`:** Eje X = Absorción Doméstica ($A = C+I+G$), Eje Y = Tipo de Cambio Real ($q$). Dibuja las 4 zonas coloreadas claramente (I: Inflación+Superávit, II: Desempleo+Superávit, III: Desempleo+Déficit, IV: Inflación+Déficit) y la trayectoria histórica del punto del país turno a turno.
        
          
        
    - **Tab 3 — `🔺 Trilema de Mundell-Fleming` (Nuevo Valor Agregado frente a Econland):** Gráfico visual del triángulo donde se iluminan los 2 vértices activos del país según el régimen actual (ej. _Tipo de Cambio Fijo + Movilidad de Capitales = Pérdida de Autonomía Monetaria_) con su explicación pedagógica.
        
          
        
    - **Tab 4 — `🕒 Evolución Temporal`:** Series de tiempo de los 10 turnos para PIB Real vs. Potencial, Inflación vs. Meta, Desempleo y Ratio Deuda/PIB Nominal.
        
          
        
3. **Asesores de Gabinete Socráticos (`engine_simple/advisor.py`):**
    
      
    - Tres tarjetas fijas (_Banco Central_, _Ministerio de Hacienda_, _Ministerio de Trabajo y Comercio_) que leen el estado actual y formulan preguntas guía y alertas preventivas sin regalar la respuesta exacta.
        
          
        
4. **Gancho de Serialización JSON (Listo para Fase B - Canvas y Supabase):**
    
      
    - El `StateManager` incluirá los métodos `.to_dict()` y `.from_dict(payload)` más un botón discreto en el menú lateral (`💾 Guardar / Cargar Partida JSON`), dejando la estructura de datos exacta que en el Paso B enviaremos a Supabase y Canvas.
        
          

