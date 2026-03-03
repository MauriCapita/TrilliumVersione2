"""
Trillium RAG - Pagina Analytics
Dashboard di utilizzo: feedback, domande frequenti, documenti più citati.
"""

import streamlit as st
from feedback import get_feedback_stats, get_recent_negative_feedback, _load_feedback

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def render():
    """Renderizza la pagina Analytics."""
    st.markdown("## Analytics e Qualità")

    # Statistiche feedback
    stats = get_feedback_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Risposte Valutate", stats["total"])
    with col2:
        st.metric("Positive", stats["positive"])
    with col3:
        st.metric("Negative", stats["negative"])
    with col4:
        rate = f"{stats['satisfaction_rate']:.0f}%" if stats["total"] > 0 else "N/A"
        st.metric("Soddisfazione", rate)

    st.markdown("---")

    # Grafici
    if stats["total"] > 0 and PLOTLY_AVAILABLE:
        col_pie, col_trend = st.columns(2)

        with col_pie:
            st.markdown("### Distribuzione Feedback")
            fig = go.Figure(data=[go.Pie(
                labels=["Positive", "Negative"],
                values=[stats["positive"], stats["negative"]],
                hole=0.4,
                marker=dict(colors=["#10803e", "#d04040"]),
            )])
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_trend:
            st.markdown("### Trend Utilizzo")
            data = _load_feedback()
            if data:
                # Raggruppa per giorno
                from collections import Counter
                days = Counter()
                for d in data:
                    day = d.get("timestamp", "")[:10]
                    if day:
                        days[day] += 1
                if days:
                    sorted_days = sorted(days.items())
                    fig = px.bar(
                        x=[d[0] for d in sorted_days],
                        y=[d[1] for d in sorted_days],
                        labels={"x": "Data", "y": "Domande"},
                        color_discrete_sequence=["#344054"],
                    )
                    fig.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig, use_container_width=True)

    # Feedback negativi recenti
    st.markdown("---")
    st.markdown("### Feedback Negativi Recenti")
    negatives = get_recent_negative_feedback(limit=5)
    if negatives:
        for fb in reversed(negatives):
            with st.expander(f"{fb.get('timestamp', '')} — {fb.get('question', '')[:60]}..."):
                st.markdown(f"**Domanda:** {fb.get('question', '')}")
                st.markdown(f"**Anteprima risposta:** {fb.get('answer_preview', '')[:200]}...")
                if fb.get("comment"):
                    st.markdown(f"**Commento:** {fb['comment']}")
    else:
        st.info("Nessun feedback negativo registrato.")

    # Domande frequenti (word cloud semplificato)
    st.markdown("---")
    st.markdown("### Argomenti Più Frequenti")
    data = _load_feedback()
    if data:
        import re
        from collections import Counter
        words = Counter()
        stopwords = {"come", "cosa", "dove", "quando", "quale", "quali", "che", "non",
                     "per", "con", "una", "uno", "del", "della", "nel", "nella", "sono",
                     "essere", "fare", "quanto", "dalla", "dall", "alla", "questo"}
        for d in data:
            q = d.get("question", "").lower()
            tokens = re.findall(r"\w{4,}", q)
            for t in tokens:
                if t not in stopwords:
                    words[t] += 1
        
        top_words = words.most_common(15)
        if top_words:
            cols = st.columns(5)
            for i, (word, count) in enumerate(top_words):
                with cols[i % 5]:
                    st.markdown(f"**{word}** ({count})")
    else:
        st.info("Nessun dato di utilizzo disponibile. I dati verranno raccolti dalle interazioni in chat.")
