# src/components/charts.py
from __future__ import annotations

from typing import Iterable, List, Optional

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def line(
    df,
    x: str,
    ys: Iterable[str],
    *,
    title: Optional[str] = None,
    markers: bool = True,
    yaxis_title: Optional[str] = None,
) -> go.Figure:
    """Wykres liniowy z wieloma seriami (Plotly)."""
    fig = go.Figure()
    ys_list: List[str] = list(ys)
    for col in ys_list:
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=df[col],
                name=col,
                mode="lines+markers" if markers else "lines",
            )
        )
    fig.update_layout(
        title=title or "",
        xaxis_title=x,
        yaxis_title=yaxis_title or "",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def bar(
    df,
    x: str,
    y: str,
    *,
    title: Optional[str] = None,
    barmode: str = "group",
    yaxis_title: Optional[str] = None,
) -> go.Figure:
    """Wykres słupkowy (Plotly Express)."""
    fig = px.bar(df, x=x, y=y, title=title or "")
    fig.update_layout(
        barmode=barmode,
        yaxis_title=yaxis_title or "",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def area(
    df,
    x: str,
    ys: Iterable[str],
    *,
    title: Optional[str] = None,
    stackgroup: str = "one",
    yaxis_title: Optional[str] = None,
) -> go.Figure:
    """Wykres area (stacked)."""
    fig = go.Figure()
    for col in ys:
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=df[col],
                stackgroup=stackgroup,
                name=col,
                mode="lines",
            )
        )
    fig.update_layout(
        title=title or "",
        xaxis_title=x,
        yaxis_title=yaxis_title or "",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# ---- JEDYNE miejsce renderowania (bez use_container_width) ----
def show_plot(fig: go.Figure) -> None:
    """Render wykresu z nowym API szerokości."""
    st.plotly_chart(fig, width="stretch")
