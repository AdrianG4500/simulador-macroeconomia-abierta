import streamlit as st
import logging
import json

@st.cache_data(ttl=3600, show_spinner=False)
def call_chavez_narrator(context_json: str) -> str:
    """
    Llama a la API de OpenAI para generar la narrativa del período actual.
    Utiliza caché basada en el contenido de context_json para no repetir llamadas idénticas.
    """
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        return "⚠️ Narrador no disponible. Verifica OPENAI_API_KEY en .streamlit/secrets.toml o usa la narrativa determinista del simulador."

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Parseamos el contexto dinámico
        context_data = json.loads(context_json)
        
        # El user_prompt dinámico
        user_prompt = f"""
        Contexto macroeconómico del semestre {context_data.get('t')}:
        - Régimen: {context_data.get('regime')}
        - Política aplicada: {context_data.get('policy')}
        - Shock exógeno: {context_data.get('shock')}
        
        Resultados:
        - PIB (Y): {context_data.get('Y')}
        - Reservas (R): {context_data.get('R')}
        - Tipo de Cambio (E): {context_data.get('E')}
        - Inflación (π): {context_data.get('pi')}
        - Desempleo (U): {context_data.get('U')}
        - Puntuación (Score): {context_data.get('score')}
        - Tendencia vs período anterior: {context_data.get('trend')}
        
        Analiza estos datos y redacta una narrativa pedagógica de 3-4 párrafos.
        """

        # Llamada a OpenAI (manejamos tanto el intento de stored prompt como fallback a chat estándar)
        try:
            # Intento de usar el endpoint de responses para prompts guardados si la librería lo soporta
            response = client.responses.create(
                model="gpt-4o-mini", # Asumimos gpt-4o-mini o la versión instalada compatible
                prompt={
                    "id": "pmpt_6a0c3290a1188195b979cbef004b26aa0f01e7309ee141ca",
                    "version": "1"
                }
            )
            return response.choices[0].message.content.strip()
        except Exception:
            # Fallback a Chat Completions estándar si el método anterior no existe o falla por formato
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres el Narrador Chávez, un experto macroeconomista que explica de forma pedagógica, clara y realista los resultados del último semestre. Evalúas la sostenibilidad, las variables macro y los regímenes cambiarios con rigor académico pero en tono narrativo accesible."},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"Error en Narrador AI: {e}")
        return "⚠️ Error al conectar con el Narrador AI. Por favor, usa la narrativa determinista de la pestaña de período."
