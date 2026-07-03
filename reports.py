"""
reports.py
----------
Turns the raw `payments` table into Daily / Weekly / Monthly / Yearly
collection reports, with Plotly charts and Excel/CSV/PDF export.
"""

import io
import pandas as pd
import plotly.express as px
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def payments_to_dataframe(payments: list[dict]) -> pd.DataFrame:
    """Convert the list of payment dict rows into a typed DataFrame ready
    for grouping/aggregation."""
    if not payments:
        return pd.DataFrame(
            columns=["id", "tenant_id", "tenant_name", "room_number", "amount", "payment_date"]
        )
    df = pd.DataFrame(payments)
    df["payment_date"] = pd.to_datetime(df["payment_date"])
    return df


def group_collections(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """Group payment amounts by the requested period.

    period: one of 'Daily', 'Weekly', 'Monthly', 'Yearly'
    Returns a two-column DataFrame: [period_label, total_amount].
    """
    if df.empty:
        return pd.DataFrame(columns=["period", "total_amount"])

    # Note: 'ME'/'YE' (month-end / year-end) are the modern pandas aliases;
    # the older 'M'/'Y' aliases were removed in pandas 2.2+.
    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "ME", "Yearly": "YE"}
    freq = freq_map.get(period, "D")

    grouped = (
        df.set_index("payment_date")
        .resample(freq)["amount"]
        .sum()
        .reset_index()
    )
    grouped = grouped[grouped["amount"] > 0]  # drop empty periods for a cleaner chart

    fmt_map = {
        "Daily": "%d %b %Y",
        "Weekly": "Week of %d %b %Y",
        "Monthly": "%b %Y",
        "Yearly": "%Y",
    }
    grouped["period"] = grouped["payment_date"].dt.strftime(fmt_map.get(period, "%d %b %Y"))
    return grouped[["period", "amount"]].rename(columns={"amount": "total_amount"})


def collection_chart(grouped_df: pd.DataFrame, period: str):
    """Return a Plotly bar chart figure for a grouped collections DataFrame."""
    if grouped_df.empty:
        fig = px.bar(title=f"{period} Collection (no data yet)")
        return fig
    fig = px.bar(
        grouped_df,
        x="period",
        y="total_amount",
        title=f"{period} Rent Collection",
        labels={"period": period, "total_amount": "Amount Collected (₹)"},
        text_auto=".2s",
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_tickangle=-30,
        showlegend=False,
    )
    fig.update_traces(marker_color="#6C5CE7")
    return fig


# --------------------------------------------------------------------------
# EXPORTS
# --------------------------------------------------------------------------

def export_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def export_to_excel_bytes(df: pd.DataFrame, sheet_name="Report") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


def export_to_pdf_bytes(df: pd.DataFrame, title: str = "Rent Collection Report") -> bytes:
    """Render a DataFrame as a simple styled PDF table using reportlab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    if df.empty:
        elements.append(Paragraph("No data available for this report.", styles["Normal"]))
    else:
        data = [list(df.columns)] + df.astype(str).values.tolist()
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6C5CE7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F1FE")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)

    doc.build(elements)
    return buffer.getvalue()
