import streamlit as st
import numpy as np
import plotly.graph_objects as go

def generate_period_narrative(t, policy, shock, eq, regime):
    narrative = f"**En el semestre t={t}**:\n\n"

    if policy and policy != "Ninguna" and policy != "{}":
        narrative += f"- **Política aplicada:** Se implementó {policy}. Esto desplaza principalmente la curva IS (si es fiscal) o LM (si es monetaria).\n"
    else:
        narrative += "- **Política aplicada:** Ninguna.\n"

    if shock and shock != "Ninguno":
        narrative += f"- **Shock exógeno:** Ocurrió un(a) '{shock}'. Esto altera los parámetros estructurales del modelo.\n"
    else:
        narrative += "- **Shock exógeno:** Ninguno.\n"

    narrative += f"\n**Mecanismo de transmisión:**\nEl nuevo equilibrio se establece en Y={eq['Y']:.2f} y r={eq['r']:.2f}. "

    if "M_endo" in eq:
        narrative += f"Bajo tipo de cambio fijo, el Banco Central ajustó la oferta monetaria a M={eq.get('M_endo', eq.get('M', 0)):.2f} para mantener la paridad cambiaria."
    elif "E_endo" in eq:
        narrative += f"Bajo tipo de cambio flexible, la moneda se ajustó a E={eq['E_endo']:.2f} para equilibrar el mercado de divisas."

    if regime == "🏛️ TC Fijo" or regime == "🌊 TC Flexible":
        narrative += "\n\n📌 **Nota sobre la tasa de interés**: Bajo movilidad perfecta de capitales, r = r* en equilibrio. Por eso la tasa no cambia aunque modifiques G, T, M o E. Para ver r ≠ r*, selecciona el régimen '🔐 Movilidad Imperfecta'."

    return narrative

def render_period_islm_tab(mgr, regime: str, period_selector: int):
    history = mgr.state["history"]
    if not history:
        st.warning("No hay datos para mostrar.")
        return

    period_data = next((h for h in history if h["t"] == period_selector), None)
    if not period_data:
        st.warning(f"No hay datos para t={period_selector}")
        return

    params = period_data["params"]
    eq = period_data["eq"]

    Y_eq = eq["Y"]
    r_eq = eq["r"]

    Y_range = np.linspace(max(0, Y_eq * 0.5), Y_eq * 1.5, 100)

    A = params["c0"] - params["c1"]*params["T"] + params["I0"] + params["G"] + params["NX0"]
    mult = 1.0 / (1.0 - params["c1"] + params["m1"])

    E_val = eq.get("E_endo", params.get("E", 1.0))
    M_val = eq.get("M_endo", params.get("M", 50.0))

    b = params["b"]
    if b > 0:
        r_IS = (A + params["x1"]*E_val - Y_range/mult) / b
    else:
        r_IS = np.full_like(Y_range, np.nan) 

    h = params["h"]
    if h > 0:
        r_LM = (params["k"]*Y_range - M_val) / h
    else:
        r_LM = np.full_like(Y_range, np.nan)

    if regime == "🔐 Movilidad Imperfecta":
        sigma = 0.4
        r_BP = params["r_star"] + (1.0/sigma) * (params["NX0"] + params["x1"]*E_val - params["m1"]*Y_range)
    else:
        r_BP = np.full_like(Y_range, params["r_star"])

    fig = go.Figure()

    if b > 0:
        fig.add_trace(go.Scatter(x=Y_range, y=r_IS, mode='lines', name='IS', line=dict(color='#3b82f6', width=2.5)))
    else:
        fig.add_vline(x=Y_eq, line=dict(color='#3b82f6', dash='dash', width=2.5), name='IS')

    if h > 0:
        fig.add_trace(go.Scatter(x=Y_range, y=r_LM, mode='lines', name='LM', line=dict(color='#f59e0b', width=2.5)))
    else:
        fig.add_vline(x=Y_eq, line=dict(color='#f59e0b', dash='dash', width=2.5), name='LM')

    fig.add_trace(go.Scatter(x=Y_range, y=r_BP, mode='lines', name='BP', line=dict(color='#10b981', width=2.5)))

    fig.add_trace(go.Scatter(
        x=[Y_eq], y=[r_eq],
        mode='markers+text',
        name=f'Equilibrio t={period_selector}',
        marker=dict(size=12, color='#f59e0b', line=dict(width=2, color='#ffffff')),
        text=[f"E({Y_eq:.1f}, {r_eq:.1f})"],
        textposition="top center"
    ))

    fig.update_layout(
        title=f"Modelo IS-LM-BP (Período t={period_selector})",
        xaxis_title="Ingreso (Y)",
        yaxis_title="Tasa de interés (r)",
        template="plotly_dark",
        plot_bgcolor="#0B1120",
        paper_bgcolor="#0B1120",
        font=dict(color="#e2e8f0"),
        xaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155"),
        yaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155"),
        yaxis_range=[max(0, r_eq - 10), r_eq + 10]
    )

    st.plotly_chart(fig, use_container_width=True)

    st.write("### Línea de tiempo de scores")
    import pandas as pd
    from ui.score_dashboard import render_score_history
    df_hist = pd.DataFrame(history)
    render_score_history(df_hist)

    st.write("### Análisis Narrativo")
    narrative = generate_period_narrative(period_selector, period_data["policy"], period_data["shock"], eq, regime)
    st.info(narrative)

    with st.expander("🔍 Ver ecuaciones del período"):
        st.latex(r"IS: Y = rac{1}{1 - c_1 + m_1} [A + x_1 E - b r]")
        st.latex(r"LM: rac{M}{P} = k Y - h r")
        if regime == "🔐 Movilidad Imperfecta":
            st.latex(r"BP: r = r^* + rac{1}{\sigma} NX")
        else:
            st.latex(r"BP: r = r^*")
        st.json(params)
