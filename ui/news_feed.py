"""
ui/news_feed.py
===============
Componente de la barra lateral (sidebar) que muestra el feed de noticias del gobierno.

Renderiza las noticias del periódico en orden cronológico inverso.
Muestra las 5 noticias más recientes en tarjetas visuales de colores por severidad,
y archiva las anteriores en un expander.
"""

from __future__ import annotations

import streamlit as st
from engine.game_state import GameState, NewsItem


def render_news_feed(state: GameState) -> None:
    """
    Renderiza el feed de noticias en la barra lateral de Streamlit.
    """
    st.sidebar.markdown("""
    <style>
      .news-feed-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: #f1f5f9;
          margin-bottom: 12px;
          text-transform: uppercase;
          border-bottom: 2px solid #e2e8f0;
          padding-bottom: 6px;
          letter-spacing: 0.5px;
      }
      .news-card {
          border-radius: 8px;
          padding: 12px 14px;
          margin-bottom: 10px;
          border: 1px solid #1e293b;
          transition: transform 0.2s ease;
      }
      .news-card:hover {
          transform: translateY(-2px);
      }
      .news-critical {
          background: #3b111a;
          border-left: 5px solid #ef4444 !important;
      }
      .news-warning {
          background: #3b2c11;
          border-left: 5px solid #f59e0b !important;
      }
      .news-info {
          background: #111e3b;
          border-left: 5px solid #3b82f6 !important;
      }
      .news-header {
          font-weight: 800;
          font-size: 0.85rem;
          margin-bottom: 4px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
      }
      .news-header-critical { color: #fca5a5; }
      .news-header-warning { color: #fde047; }
      .news-header-info { color: #93c5fd; }
      
      .news-msg {
          font-size: 0.8rem;
          color: #cbd5e1;
          line-height: 1.4;
      }
      .news-meta {
          font-size: 0.7rem;
          color: #94a3b8;
          margin-top: 6px;
          text-align: right;
          font-weight: 600;
      }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<div class='news-feed-title'>📰 Diario Oficial de la Nación</div>", unsafe_allow_html=True)

    news_feed = state.get("news_feed", [])

    if not news_feed:
        st.sidebar.info("📰 Aún no hay noticias reportadas este período.")
        return

    # Invertir orden (lo más nuevo arriba)
    reversed_news = list(reversed(news_feed))

    # Tomar los 5 más recientes
    recent_news = reversed_news[:5]
    older_news = reversed_news[5:]

    # Renderizar los 5 más recientes en tarjetas visuales de periódico
    for item in recent_news:
        sev = item.get("severity", "info")
        t = item.get("t", 0)
        
        # Determinar clases CSS según severidad
        card_class = "news-info"
        hdr_class = "news-header-info"
        badge = "ℹ️ NOTICIA GENERAL"
        
        if sev == "critical":
            card_class = "news-critical"
            hdr_class = "news-header-critical"
            badge = "🚨 URGENTE / CRITICAL"
        elif sev == "warning":
            card_class = "news-warning"
            hdr_class = "news-header-warning"
            badge = "⚠️ ADVERTENCIA"

        # Separar titular de narrativa si viene en formato "TITULO: narrativa"
        msg = item["message"]
        headline = badge
        narrative = msg
        
        if ": " in msg:
            parts = msg.split(": ", 1)
            headline = parts[0]
            narrative = parts[1]

        st.sidebar.markdown(f"""
        <div class='news-card {card_class}'>
          <div class='news-header {hdr_class}'>{headline}</div>
          <div class='news-msg'>{narrative}</div>
          <div class='news-meta'>Mes de Gobierno {t}</div>
        </div>
        """, unsafe_allow_html=True)

    # Si hay noticias anteriores, colapsarlas en un expander para no saturar la sidebar
    if older_news:
        with st.sidebar.expander("📁 Historial de Noticias Anteriores", expanded=False):
            for item in older_news:
                sev = item.get("severity", "info")
                t = item.get("t", 0)
                msg = item["message"]
                
                emoji = "ℹ️"
                if sev == "critical":
                    emoji = "🚨"
                elif sev == "warning":
                    emoji = "⚠️"
                    
                st.markdown(f"**{emoji} Mes {t}:** {msg}")
