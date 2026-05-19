import streamlit as st
import pandas as pd
import io

def render_data_tab(mgr):
    history = mgr.state["history"]
    if not history:
        st.warning("No hay datos para mostrar.")
        return

    df_raw = pd.DataFrame(history)
    if 'policy' in df_raw.columns:
        df_raw['policy'] = df_raw['policy'].astype(str)
    if 'shock' in df_raw.columns:
        df_raw['shock'] = df_raw['shock'].astype(str)

    st.write("### Tabla de Datos Completa")

    col1, col2 = st.columns(2)
    with col1:
        max_t = int(df_raw['t'].max())
        if max_t > 1:
            t_range = st.slider("Filtrar por período (t)", 1, max_t, (1, max_t))
        else:
            t_range = (1, 1)
            st.info("Solo hay 1 período disponible para filtrar.")
    with col2:
        search_text = st.text_input("Buscar en política o shock")

    mask = (df_raw['t'] >= t_range[0]) & (df_raw['t'] <= t_range[1])
    if search_text:
        mask &= (df_raw['policy'].str.contains(search_text, case=False) | df_raw['shock'].str.contains(search_text, case=False))

    df_filtered = df_raw[mask].copy()

    cols = ["t", "Y", "r", "E", "M", "R", "B", "pi", "U", "gY", "def", "score", "policy", "shock"]
    # Ensure all columns exist, fallback if not
    cols = [c for c in cols if c in df_filtered.columns]

    df_display = df_filtered[cols].copy()
    for pct_col in ["pi", "U", "gY", "def"]:
        if pct_col in df_display:
            df_display[pct_col] = df_display[pct_col] * 100

    st.dataframe(df_display, use_container_width=True, hide_index=True,
                 column_config={
                     "Y": st.column_config.NumberColumn("PIB", format="%.1f MM $"),
                     "R": st.column_config.NumberColumn("Reservas", format="%.1f MM $"),
                     "B": st.column_config.NumberColumn("Deuda", format="%.1f MM $"),
                     "r": st.column_config.NumberColumn("Tasa", format="%.2f%%"),
                     "pi": st.column_config.NumberColumn("Inflación", format="%.2f%%"),
                     "U": st.column_config.NumberColumn("Desempleo", format="%.2f%%"),
                     "gY": st.column_config.NumberColumn("Crecimiento", format="%.2f%%"),
                     "def": st.column_config.NumberColumn("Déficit", format="%.2f%%"),
                     "score": st.column_config.NumberColumn("Score", format="%d")
                 })

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button("📥 Descargar CSV", df_filtered[cols].to_csv(index=False).encode('utf-8'), "datos.csv", "text/csv")
    with col_dl2:
        buffer = io.BytesIO()
        df_filtered[cols].to_parquet(buffer, engine='pyarrow')
        st.download_button("📥 Descargar Parquet", buffer.getvalue(), "datos.parquet", "application/octet-stream")

    st.write("### Resumen Estadístico")
    st.table(df_raw[["Y", "r", "score", "R"]].agg(['min', 'max', 'mean']).round(2))
