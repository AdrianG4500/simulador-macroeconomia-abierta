VALIDATION_RULES = {
    "c0": {"min": 0.0, "max": 50.0, "step": 1.0, "unit": "Unid.", "label": "Consumo autónomo", "warning": "", "rationale": "Consumo de subsistencia + gasto crediticio base. Independiente del ingreso."},
    "c1": {"min": 0.30, "max": 0.95, "step": 0.01, "unit": "Adim.", "label": "Propensión marginal a consumir (c₁)", "warning": "c₁ > 0.90 implica ahorro muy bajo; inestabilidad del multiplicador.", "rationale": "Fracción de cada unidad adicional de ingreso disponible que se destina al consumo. Valores típicos para economías en desarrollo: 0.65–0.85."},
    "I0": {"min": -20.0, "max": 50.0, "step": 1.0, "unit": "Unid.", "label": "Inversión autónoma", "warning": "", "rationale": "Inversión independiente de r. Negativo = contracción por crisis de confianza."},
    "b": {"min": 0.5, "max": 10.0, "step": 0.1, "unit": "Adim.", "label": "Sensibilidad inversión a r", "warning": "", "rationale": "Reacción empresarial a costos financieros. ↑b → IS más plana → política monetaria más potente."},
    "NX0": {"min": -20.0, "max": 50.0, "step": 1.0, "unit": "Unid.", "label": "Exportaciones netas autónomas", "warning": "", "rationale": "Saldo comercial estructural. Negativo = déficit comercial crónico."},
    "x1": {"min": 0.05, "max": 2.00, "step": 0.05, "unit": "Adim.", "label": "Elasticidad exportaciones a E", "warning": "", "rationale": "Competitividad cambiaria. Bolivia: primarias inelásticas (~0.1-0.3)."},
    "m1": {"min": 0.05, "max": 0.45, "step": 0.01, "unit": "Adim.", "label": "PMgM", "warning": "", "rationale": "Dependencia de importaciones. ↑m₁ → ↓multiplicador (fuga externa)."},
    "k": {"min": 0.10, "max": 1.00, "step": 0.05, "unit": "Adim.", "label": "Sensibilidad demanda dinero a Y", "warning": "", "rationale": "Intensidad monetaria del PIB. Controla pendiente de LM."},
    "h": {"min": 0.50, "max": 5.00, "step": 0.1, "unit": "Adim.", "label": "Sensibilidad demanda dinero a r", "warning": "", "rationale": "Preferencia por liquidez vs. bonos. ↑h → LM más plana."},
    "Y_pot": {"min": 50.0, "max": 200.0, "step": 1.0, "unit": "Unid.", "label": "PIB potencial", "warning": "", "rationale": "Capacidad productiva estructural. Referencia para brecha del producto."},
    "U_n": {"min": 0.03, "max": 0.10, "step": 0.01, "unit": "%", "label": "Desempleo natural (NAIRU)", "warning": "", "rationale": "Fricción + estructural mínima. Referencia para ley de Okun."},
    "G": {"min": 5.0, "max": 60.0, "step": 0.1, "unit": "% PIB norm.", "label": "Gasto público (G)", "warning": "", "rationale": "Instrumento fiscal: ↑G desplaza IS→. Efectivo bajo TC fijo, neutral bajo TC flexible."},
    "T": {"min": 5.0, "max": 50.0, "step": 0.1, "unit": "% PIB norm.", "label": "Impuestos lump-sum (T)", "warning": "", "rationale": "Política tributaria: ↑T reduce ingreso disponible → ↓C → IS←. Efecto menor que G por c₁<1."},
    "E": {"min": 1.0, "max": 30.0, "step": 0.1, "unit": "Bs/USD", "label": "Tipo de cambio nominal (E)", "warning": "", "rationale": "Instrumento cambiario (TC fijo): ↑E = devaluación → ↑competitividad → ↑NX → IS→."},
    "M": {"min": 10.0, "max": 500.0, "step": 1.0, "unit": "Unid. modelo", "label": "Oferta monetaria (M)", "warning": "", "rationale": "Instrumento monetario (TC flexible): ↑M desplaza LM→ → ↓r → ↑Y. Endógena bajo TC fijo."},
    "r_star": {"min": 0.0, "max": 15.0, "step": 0.1, "unit": "% anual", "label": "Tasa int. externa (r*)", "warning": "", "rationale": "Tasa internacional + prima riesgo. Afecta equilibrio vía condición externa."}
}
