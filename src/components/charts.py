import plotly.express as px

def line(df, x, ys, title=None):
    fig = px.line(df, x=x, y=ys, markers=True, title=title)
    return fig

def bar(df, x, y, title=None):
    fig = px.bar(df, x=x, y=y, title=title)
    return fig
