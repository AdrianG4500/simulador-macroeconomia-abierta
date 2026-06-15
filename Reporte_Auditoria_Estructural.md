# Reporte de Auditoría Estructural: Trayectorias Nominales y Reales (V3.2)

Este informe contiene el análisis de trayectoria pasiva para los cuatro escenarios del Simulador Macroeconómico, evaluando la transición intertemporal entre el Turno 0, Turno 1 y Turno 2 sin cambios de política fiscal ni monetaria por parte del usuario.

### 🐯 Milagro Coreano (tiger_asia)
| Variable | Símbolo | Turno 0 | Turno 1 | Turno 2 | Δ% (T1 vs T0) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Consumo Autónomo Base | `c0` | 12.0000 | 12.0000 | 12.0000 | +0.00% |
| Inversión Autónoma | `I0` | 16.0000 | 16.0000 | 16.0000 | +0.00% |
| Absorción Autónoma Reportada | `A_auto` | 52.0000 | 52.0000 | 52.0000 | +0.00% |
| Ponderación de Hábitos | `lambda_h` | 0.2010 | 0.2010 | 0.2010 | +0.00% |
| Gasto Corriente | `G_c` | 12.0000 | 12.0000 | 12.0000 | +0.00% |
| Inversión Pública | `I_g` | 8.0000 | 8.0000 | 8.0000 | +0.00% |
| Tasa Impositiva Consumo e Ingreso | `t_c` | 0.1800 | 0.1800 | 0.1800 | +0.00% |
| Tasa de Política Monetaria | `r_ref` | 7.5000 | 7.5000 | 7.5000 | +0.00% |
| Tipo de Cambio Nominal | `E` | 10.0000 | 10.0000 | 10.0000 | +0.00% |
| Multiplicador Keynesiano Efectivo | `k_m` | 1.6474 | 1.6474 | 1.6474 | +0.00% |
| Consumo Dinámico por Hábitos Efectivo | `c0_eff` | 25.6518 | 25.6530 | 26.2738 | +0.00% |
| Efecto Crowding Neto Calculado | `delta_I0` | 0.1957 | 0.1912 | 0.1934 | -2.32% |
| PIB Real Resultante del Solver | `Y` | 101.8269 | 107.6186 | 107.8677 | +5.69% |
| PIB Potencial de la Frontera | `Y_pot` | 100.0000 | 103.2000 | 106.4640 | +3.20% |
| Output Gap Calculado (%) | `gap` | 1.83% | 4.28% | 1.32% | +133.88% |
| Tasa de Desempleo Cíclica (%) | `U` | 3.50% | 3.50% | 3.50% | +0.00% |
| Tasa de Inflación Registrada (%) | `pi` | 3.00% | 8.20% | 10.36% | +173.33% |
| Inflación Núcleo Doméstica (%) | `pi_core` | N/A | 8.20% | 4.14% | N/A |
| Expectativa Inflacionaria Rezagada (%) | `pi_e` | 3.00% | 3.00% | 6.64% | +0.00% |
| Tasa de Interés Real de Fisher (%) | `r_real` | 3.08% | -2.05% | -0.20% | -166.48% |
| Saldo Neto de Exportaciones | `NX` | -6.9949 | -7.8057 | -7.8751 | +11.59% |
| Stock de Deuda Pública Soberana | `B` | 20.0000 | 21.7300 | 24.3800 | +8.65% |
| Balance Fiscal / Déficit Resultante | `deficit` | 2.7712 | 1.7286 | 2.6480 | -37.62% |
| Reservas Internacionales Netas | `R` | 120.0000 | 120.0000 | 120.0000 | +0.00% |
| Prima de Riesgo País (%) | `rho` | 1.50% | 1.50% | 1.50% | +0.00% |
| Calificación Crediticia Moody's | `rating` | AA | AA | AA | N/A |


### 🏛️ Estabilidad Chilena (Economia_Saludable)
| Variable | Símbolo | Turno 0 | Turno 1 | Turno 2 | Δ% (T1 vs T0) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Consumo Autónomo Base | `c0` | 14.0000 | 14.0000 | 14.0000 | +0.00% |
| Inversión Autónoma | `I0` | 12.0000 | 12.0000 | 12.0000 | +0.00% |
| Absorción Autónoma Reportada | `A_auto` | 46.0000 | 46.0000 | 46.0000 | +0.00% |
| Ponderación de Hábitos | `lambda_h` | 0.4030 | 0.4030 | 0.4030 | +0.00% |
| Gasto Corriente | `G_c` | 15.0000 | 15.0000 | 15.0000 | +0.00% |
| Inversión Pública | `I_g` | 5.0000 | 5.0000 | 5.0000 | +0.00% |
| Tasa Impositiva Consumo e Ingreso | `t_c` | 0.2000 | 0.2000 | 0.2000 | +0.00% |
| Tasa de Política Monetaria | `r_ref` | 5.0000 | 5.0000 | 5.0000 | +0.00% |
| Tipo de Cambio Nominal | `E` | 10.0000 | 10.0000 | 10.0000 | +0.00% |
| Multiplicador Keynesiano Efectivo | `k_m` | 1.4925 | 1.4925 | 1.4925 | +0.00% |
| Consumo Dinámico por Hábitos Efectivo | `c0_eff` | 45.8772 | 46.1828 | 45.9825 | +0.67% |
| Efecto Crowding Neto Calculado | `delta_I0` | 0.0661 | 0.0647 | 0.0647 | -2.10% |
| PIB Real Resultante del Solver | `Y` | 99.9602 | 98.2878 | 93.8098 | -1.67% |
| PIB Potencial de la Frontera | `Y_pot` | 100.0000 | 102.7500 | 105.5550 | +2.75% |
| Output Gap Calculado (%) | `gap` | -0.04% | -4.34% | -11.13% | +10750.00% |
| Tasa de Desempleo Cíclica (%) | `U` | 5.02% | 7.17% | 10.56% | +42.83% |
| Tasa de Inflación Registrada (%) | `pi` | 3.00% | 0.83% | -4.56% | -72.33% |
| Inflación Núcleo Doméstica (%) | `pi_core` | N/A | 0.33% | -1.50% | N/A |
| Expectativa Inflacionaria Rezagada (%) | `pi_e` | 3.00% | 3.00% | 1.00% | +0.00% |
| Tasa de Interés Real de Fisher (%) | `r_real` | 5.99% | 12.11% | 17.37% | +102.09% |
| Saldo Neto de Exportaciones | `NX` | -12.4723 | -12.2214 | -11.5508 | -2.01% |
| Stock de Deuda Pública Soberana | `B` | 15.0000 | 16.9200 | 19.9300 | +12.80% |
| Balance Fiscal / Déficit Resultante | `deficit` | 0.9830 | 1.9174 | 3.0144 | +95.06% |
| Reservas Internacionales Netas | `R` | 60.0000 | 60.0000 | 60.0000 | +0.00% |
| Prima de Riesgo País (%) | `rho` | 1.50% | 1.50% | 1.50% | +0.00% |
| Calificación Crediticia Moody's | `rating` | AA | AA | AA | N/A |


### 📉 Crisis de Deuda Mexicana (latam_crisis)
| Variable | Símbolo | Turno 0 | Turno 1 | Turno 2 | Δ% (T1 vs T0) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Consumo Autónomo Base | `c0` | 8.0000 | 8.0000 | 8.0000 | +0.00% |
| Inversión Autónoma | `I0` | 6.5000 | 6.5000 | 6.5000 | +0.00% |
| Absorción Autónoma Reportada | `A_auto` | 31.5000 | 31.5000 | 31.5000 | +0.00% |
| Ponderación de Hábitos | `lambda_h` | 0.4655 | 0.4655 | 0.4655 | +0.00% |
| Gasto Corriente | `G_c` | 18.0000 | 18.0000 | 18.0000 | +0.00% |
| Inversión Pública | `I_g` | 2.0000 | 2.0000 | 2.0000 | +0.00% |
| Tasa Impositiva Consumo e Ingreso | `t_c` | 0.1200 | 0.1200 | 0.1200 | +0.00% |
| Tasa de Política Monetaria | `r_ref` | 16.0000 | 16.0000 | 16.0000 | +0.00% |
| Tipo de Cambio Nominal | `E` | 10.0000 | 10.0000 | 10.0000 | +0.00% |
| Multiplicador Keynesiano Efectivo | `k_m` | 1.7123 | 1.7123 | 1.7123 | +0.00% |
| Consumo Dinámico por Hábitos Efectivo | `c0_eff` | 56.4931 | 59.1995 | 61.2107 | +4.79% |
| Efecto Crowding Neto Calculado | `delta_I0` | -0.1107 | -0.1120 | -0.1525 | +1.23% |
| PIB Real Resultante del Solver | `Y` | 99.8297 | 102.4499 | 69.5881 | +2.62% |
| PIB Potencial de la Frontera | `Y_pot` | 104.0000 | 106.3800 | 108.8076 | +2.29% |
| Output Gap Calculado (%) | `gap` | -4.01% | -3.69% | -36.04% | -7.98% |
| Tasa de Desempleo Cíclica (%) | `U` | 8.00% | 7.85% | 24.02% | -1.88% |
| Tasa de Inflación Registrada (%) | `pi` | 8.00% | 6.15% | -12.82% | -23.12% |
| Inflación Núcleo Doméstica (%) | `pi_core` | N/A | 6.15% | -1.50% | N/A |
| Expectativa Inflacionaria Rezagada (%) | `pi_e` | 8.00% | 8.00% | 5.21% | +0.00% |
| Tasa de Interés Real de Fisher (%) | `r_real` | 18.87% | 30.19% | 72.82% | +59.99% |
| Saldo Neto de Exportaciones | `NX` | -23.0529 | -23.5769 | -17.0039 | +2.27% |
| Stock de Deuda Pública Soberana | `B` | 55.0000 | 74.0500 | 106.9200 | +34.64% |
| Balance Fiscal / Déficit Resultante | `deficit` | 14.3454 | 19.0466 | 32.8725 | +32.77% |
| Reservas Internacionales Netas | `R` | 15.0000 | 15.0000 | 45.0000 | +0.00% |
| Prima de Riesgo País (%) | `rho` | 4.50% | 13.62% | 21.66% | +202.67% |
| Calificación Crediticia Moody's | `rating` | BBB | CCC | CCC | N/A |


### 🔥 Stagflation Boliviana (death_spiral)
| Variable | Símbolo | Turno 0 | Turno 1 | Turno 2 | Δ% (T1 vs T0) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Consumo Autónomo Base | `c0` | 6.0000 | 6.0000 | 6.0000 | +0.00% |
| Inversión Autónoma | `I0` | 4.0000 | 4.0000 | 4.0000 | +0.00% |
| Absorción Autónoma Reportada | `A_auto` | 28.0000 | 28.0000 | 28.0000 | +0.00% |
| Ponderación de Hábitos | `lambda_h` | 0.7435 | 0.7435 | 0.7435 | +0.00% |
| Gasto Corriente | `G_c` | 22.0000 | 22.0000 | 22.0000 | +0.00% |
| Inversión Pública | `I_g` | 1.0000 | 1.0000 | 1.0000 | +0.00% |
| Tasa Impositiva Consumo e Ingreso | `t_c` | 0.0800 | 0.0800 | 0.0800 | +0.00% |
| Tasa de Política Monetaria | `r_ref` | 24.0000 | 24.0000 | 24.0000 | +0.00% |
| Tipo de Cambio Nominal | `E` | 10.0000 | 10.8000 | 11.6640 | +8.00% |
| Multiplicador Keynesiano Efectivo | `k_m` | 1.7857 | 1.7857 | 1.7857 | +0.00% |
| Consumo Dinámico por Hábitos Efectivo | `c0_eff` | 103.7031 | 129.8312 | 164.6997 | +25.20% |
| Efecto Crowding Neto Calculado | `delta_I0` | -0.2723 | -0.2932 | -0.4175 | +7.69% |
| PIB Real Resultante del Solver | `Y` | 99.7806 | 129.8817 | 269.4514 | +30.17% |
| PIB Potencial de la Frontera | `Y_pot` | 95.5000 | 88.6785 | 91.4889 | -7.14% |
| Output Gap Calculado (%) | `gap` | 4.48% | 46.46% | 194.52% | +937.05% |
| Tasa de Desempleo Cíclica (%) | `U` | 5.08% | 3.50% | 3.50% | -31.10% |
| Tasa de Inflación Registrada (%) | `pi` | 14.00% | 440.83% | 810.34% | +3048.79% |
| Inflación Núcleo Doméstica (%) | `pi_core` | N/A | 437.23% | 806.74% | N/A |
| Expectativa Inflacionaria Rezagada (%) | `pi_e` | 14.00% | 14.00% | 309.48% | +0.00% |
| Tasa de Interés Real de Fisher (%) | `r_real` | 159.66% | -217.54% | -399.51% | -236.25% |
| Saldo Neto de Exportaciones | `NX` | -30.0329 | -37.5582 | -72.2150 | +25.06% |
| Stock de Deuda Pública Soberana | `B` | 65.0000 | 95.4800 | 136.7900 | +46.89% |
| Balance Fiscal / Déficit Resultante | `deficit` | 25.0926 | 30.4845 | 41.3092 | +21.49% |
| Reservas Internacionales Netas | `R` | 8.0000 | 8.0000 | 8.0000 | +0.00% |
| Prima de Riesgo País (%) | `rho` | 6.50% | 18.50% | 32.75% | +184.62% |
| Calificación Crediticia Moody's | `rating` | BB | CCC | Default | N/A |

