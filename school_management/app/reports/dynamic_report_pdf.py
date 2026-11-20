"""
EduManage Pro - Dynamic Multi-Domain Report PDF Generator
Renders any Report Builder result (all 11 institutional domains, selected columns,
applied filters, grouping summaries, sorting, date range, academic year, and totals)
as a formatted A4 Landscape ReportLab PDF document.
"""

from html import escape
import os
from typing import Any, Dict, List

from reportlab.lib.colors import HexColor, colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class DynamicReportPDFGenerator:
    """Universal PDF generator for custom & preset reports built by ReportingEngine."""

    @classmethod
    def generate_pdf(
        cls,
        report_result: Dict[str, Any],
        school: Any,
        output_pdf_path: str,
        include_grouped_summary: bool = True,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=landscape(A4),
            leftMargin=26,
            rightMargin=26,
            topMargin=26,
            bottomMargin=26,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DynTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=1,
            textColor=HexColor("#1E3A8A"),
        )
        sub_style = ParagraphStyle(
            "DynSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=HexColor("#475569"),
        )
        section_style = ParagraphStyle(
            "DynSection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=HexColor("#1E3A8A"),
        )
        header_cell = ParagraphStyle(
            "DynHdrCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white,
        )
        body_cell = ParagraphStyle(
            "DynBodyCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=HexColor("#0F172A"),
        )
        body_num = ParagraphStyle(
            "DynBodyNum",
            parent=body_cell,
            alignment=2,
        )
        total_cell = ParagraphStyle(
            "DynTotalCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=HexColor("#1E3A8A"),
        )
        total_num = ParagraphStyle(
            "DynTotalNum",
            parent=total_cell,
            alignment=2,
        )

        elements: List[Any] = []

        school_name = getattr(school, "school_name", "EduManage Pro Model Academy")
        eiin = getattr(school, "eiin_number", "N/A")
        address = getattr(school, "address", "")
        phone = getattr(school, "phone", "")

        elements.append(Paragraph(escape(str(school_name).upper()), title_style))
        elements.append(
            Paragraph(
                escape(f"{address} | Phone: {phone} | EIIN: {eiin}"),
                sub_style,
            )
        )
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=1.2, color=HexColor("#1E3A8A"), spaceAfter=6))

        rep_title = f"{report_result.get('title', 'Report')} ({report_result.get('domain_label', '')})"
        elements.append(Paragraph(escape(rep_title), section_style))

        meta_bits = [
            f"Generated: {report_result.get('generated_at', '')}",
            f"Academic Year: {report_result.get('academic_year_label', 'All Academic Years')}",
            f"Records: {report_result.get('row_count', 0)}",
        ]
        if report_result.get("date_from") or report_result.get("date_to"):
            meta_bits.append(
                f"Date Range: {report_result.get('date_from') or 'Start'} to {report_result.get('date_to') or 'End'}"
            )
        if report_result.get("sort_by"):
            order_lbl = "DESC" if report_result.get("sort_desc") else "ASC"
            meta_bits.append(f"Sorted: {report_result['sort_by']} ({order_lbl})")
        if report_result.get("group_by_label"):
            meta_bits.append(f"Grouped By: {report_result['group_by_label']}")
        if report_result.get("filters"):
            f_txt = ", ".join(
                f"{f.get('field')} {f.get('op')} '{f.get('value')}'"
                for f in report_result["filters"]
            )
            meta_bits.append(f"Filters: [{f_txt}]")

        elements.append(Paragraph(escape(" | ".join(meta_bits)), ParagraphStyle(
            "DynMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=HexColor("#475569"),
        )))
        elements.append(Spacer(1, 8))

        usable_width = landscape(A4)[0] - 52  # ~790pt

        # Optional Grouped Summary Table
        grouped_rows = report_result.get("grouped_rows") or []
        group_cols = report_result.get("group_columns") or []
        if include_grouped_summary and grouped_rows and group_cols:
            elements.append(Paragraph(escape(f"Grouped Rollup Summary (By {report_result.get('group_by_label')})"), section_style))
            elements.append(Spacer(1, 3))
            g_col_w = usable_width / max(1, len(group_cols))
            g_data = [[Paragraph(escape(gc["label"]), header_cell) for gc in group_cols]]
            for gr in grouped_rows:
                row_cells = []
                for gc in group_cols:
                    val = gr.get(gc["key"])
                    if gc["type"] == "num" and isinstance(val, float):
                        txt = f"{val:,.2f}"
                        st = body_num
                    elif gc["type"] == "num" and isinstance(val, int):
                        txt = str(val)
                        st = body_num
                    else:
                        txt = "" if val is None else str(val)
                        st = body_cell
                    row_cells.append(Paragraph(escape(txt), st))
                g_data.append(row_cells)

            g_tbl = Table(g_data, colWidths=[g_col_w] * len(group_cols), repeatRows=1)
            g_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0F766E")),
                ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), HexColor("#F0FDFA")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(g_tbl)
            elements.append(Spacer(1, 10))

        # Detailed Data Table
        cols = report_result.get("columns") or []
        rows = report_result.get("rows") or []
        if not cols:
            elements.append(Paragraph("No columns selected for report output.", body_cell))
        elif not rows:
            elements.append(Paragraph("No matching database records found for the selected criteria.", body_cell))
        else:
            elements.append(Paragraph("Detailed Records", section_style))
            elements.append(Spacer(1, 3))

            # Proportional column widths
            weights = []
            for c in cols:
                if c["type"] == "num":
                    weights.append(0.85)
                elif c["type"] == "date":
                    weights.append(0.9)
                else:
                    weights.append(1.25)
            total_w = sum(weights) or 1.0
            col_widths = [usable_width * (w / total_w) for w in weights]

            t_data: List[List[Any]] = [
                [Paragraph(escape(c["label"]), header_cell) for c in cols]
            ]

            for r in rows:
                row_cells = []
                for c in cols:
                    val = r.get(c["key"])
                    if c["type"] == "num" and isinstance(val, float):
                        txt = f"{val:,.2f}"
                        st = body_num
                    elif c["type"] == "num" and isinstance(val, int):
                        txt = str(val)
                        st = body_num
                    else:
                        txt = "" if val is None else str(val)
                        st = body_cell
                    row_cells.append(Paragraph(escape(txt), st))
                t_data.append(row_cells)

            totals = report_result.get("totals") or {}
            has_totals = bool(totals)
            if has_totals:
                tot_cells = []
                for idx, c in enumerate(cols):
                    if c["key"] in totals:
                        tot_cells.append(Paragraph(escape(f"{totals[c['key']]:,.2f}"), total_num))
                    elif idx == 0:
                        tot_cells.append(Paragraph("<b>TOTAL</b>", total_cell))
                    else:
                        tot_cells.append(Paragraph("", total_cell))
                t_data.append(tot_cells)

            tbl = Table(t_data, colWidths=col_widths, repeatRows=1)
            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E3A8A")),
                ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2 if has_totals else -1), [HexColor("#FFFFFF"), HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
            if has_totals:
                style_cmds.append(("BACKGROUND", (0, -1), (-1, -1), HexColor("#DBEAFE")))
            tbl.setStyle(TableStyle(style_cmds))
            elements.append(tbl)

        doc.build(elements)
        return output_pdf_path
