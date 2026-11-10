"""
EduManage Pro - Financial Statement & Accounting Audit PDF Generator
Generates official A4 Income & Expenditure Statement and Cash Summary using ReportLab.
"""

import os
from typing import Dict, Any, List
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class FinancialStatementPDFGenerator:
    @staticmethod
    def generate_statement(
        summary: Dict[str, Any],
        income_breakdown: List[Dict[str, Any]],
        expense_breakdown: List[Dict[str, Any]],
        school_info: Dict[str, str],
        period_str: str,
        output_path: str
    ) -> bool:
        """
        Builds formal A4 Income & Expense Financial Statement document.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=36
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "SchoolTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                alignment=1,
                textColor=colors.HexColor("#1e3a8a")
            )
            subtitle_style = ParagraphStyle(
                "SchoolSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                alignment=1,
                textColor=colors.HexColor("#475569")
            )
            doc_badge_style = ParagraphStyle(
                "DocBadge",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                alignment=1,
                textColor=colors.HexColor("#0f172a")
            )
            sec_header_style = ParagraphStyle(
                "SectionHeader",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                textColor=colors.HexColor("#1e293b")
            )
            cell_bold = ParagraphStyle("CellBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11)
            cell_norm = ParagraphStyle("CellNorm", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)
            cell_right = ParagraphStyle("CellRight", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, alignment=2)
            cell_right_bold = ParagraphStyle("CellRightBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, alignment=2)

            story = []

            # 1. School Header
            school_name = school_info.get("name", "EduManage Pro Model High School")
            school_address = school_info.get("address", "Sector 7, Uttara, Dhaka-1230, Bangladesh")
            eiin = school_info.get("eiin", "134211")
            phone = school_info.get("phone", "+880 1712-345678")

            story.append(Paragraph(school_name.upper(), title_style))
            story.append(Paragraph(f"{school_address} &bull; EIIN: {eiin} &bull; Tel: {phone}", subtitle_style))
            story.append(Spacer(1, 8))
            story.append(Paragraph("ANNUAL STATEMENT OF INCOME & EXPENDITURE", doc_badge_style))
            story.append(Paragraph(f"Reporting Scope: {period_str} | Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}", subtitle_style))
            story.append(Spacer(1, 14))

            # 2. Executive KPI Summary Box
            total_income = summary.get("total_income", 0.0)
            total_expense = summary.get("total_expense", 0.0)
            net_surplus = summary.get("net_surplus", 0.0)
            cash_in_hand = summary.get("cash_in_hand", 0.0)
            is_surplus = net_surplus >= 0

            summary_data = [
                [
                    Paragraph("<b>TOTAL REVENUE / INFLOW</b>", cell_bold),
                    Paragraph("<b>TOTAL OPERATIONAL EXPENDITURE</b>", cell_bold),
                    Paragraph(f"<b>NET {'SURPLUS (PROFIT)' if is_surplus else 'DEFICIT (LOSS)'}</b>", cell_bold),
                    Paragraph("<b>CASH-IN-HAND BALANCE</b>", cell_bold)
                ],
                [
                    Paragraph(f"<font color='#047857' size='12'><b>৳ {total_income:,.2f}</b></font>", cell_bold),
                    Paragraph(f"<font color='#b91c1c' size='12'><b>৳ {total_expense:,.2f}</b></font>", cell_bold),
                    Paragraph(f"<font color='{'#047857' if is_surplus else '#b91c1c'}' size='12'><b>৳ {net_surplus:,.2f}</b></font>", cell_bold),
                    Paragraph(f"<font color='#1e3a8a' size='12'><b>৳ {cash_in_hand:,.2f}</b></font>", cell_bold)
                ]
            ]
            summary_table = Table(summary_data, colWidths=[130, 130, 130, 130])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 14))

            # 3. Revenue Breakdown Table
            story.append(Paragraph("1. Operating Income / Revenue Heads", sec_header_style))
            story.append(Spacer(1, 4))

            inc_rows = [[
                Paragraph("<b>Code</b>", cell_bold),
                Paragraph("<b>Revenue Particulars / Head</b>", cell_bold),
                Paragraph("<b>Transactions</b>", cell_bold),
                Paragraph("<b>Amount (BDT)</b>", cell_right_bold),
                Paragraph("<b>Share %</b>", cell_right_bold)
            ]]

            for row in income_breakdown:
                share = (row["amount"] / total_income * 100) if total_income > 0 else 0.0
                inc_rows.append([
                    Paragraph(row["code"], cell_norm),
                    Paragraph(row["category"], cell_norm),
                    Paragraph(str(row["count"]), cell_norm),
                    Paragraph(f"৳ {row['amount']:,.2f}", cell_right),
                    Paragraph(f"{share:.1f}%", cell_right)
                ])

            inc_rows.append([
                Paragraph("", cell_bold),
                Paragraph("<b>Subtotal Income</b>", cell_bold),
                Paragraph("", cell_bold),
                Paragraph(f"<b>৳ {total_income:,.2f}</b>", cell_right_bold),
                Paragraph("<b>100.0%</b>", cell_right_bold)
            ])

            t_income = Table(inc_rows, colWidths=[65, 230, 65, 100, 60])
            t_income.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
            ]))
            story.append(t_income)
            story.append(Spacer(1, 14))

            # 4. Expenditure Breakdown Table
            story.append(Paragraph("2. Operational Expenditure Heads", sec_header_style))
            story.append(Spacer(1, 4))

            exp_rows = [[
                Paragraph("<b>Code</b>", cell_bold),
                Paragraph("<b>Expenditure Particulars / Head</b>", cell_bold),
                Paragraph("<b>Vouchers</b>", cell_bold),
                Paragraph("<b>Amount (BDT)</b>", cell_right_bold),
                Paragraph("<b>Share %</b>", cell_right_bold)
            ]]

            for row in expense_breakdown:
                share = (row["amount"] / total_expense * 100) if total_expense > 0 else 0.0
                exp_rows.append([
                    Paragraph(row["code"], cell_norm),
                    Paragraph(row["category"], cell_norm),
                    Paragraph(str(row["count"]), cell_norm),
                    Paragraph(f"৳ {row['amount']:,.2f}", cell_right),
                    Paragraph(f"{share:.1f}%", cell_right)
                ])

            exp_rows.append([
                Paragraph("", cell_bold),
                Paragraph("<b>Subtotal Expenditure</b>", cell_bold),
                Paragraph("", cell_bold),
                Paragraph(f"<b>৳ {total_expense:,.2f}</b>", cell_right_bold),
                Paragraph("<b>100.0%</b>", cell_right_bold)
            ])

            t_expense = Table(exp_rows, colWidths=[65, 230, 65, 100, 60])
            t_expense.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
            ]))
            story.append(t_expense)
            story.append(Spacer(1, 18))

            # 5. Auditor Certification & Signatures
            signatures = [
                [
                    Paragraph("<b>Prepared By:</b><br/><br/><br/>_______________________<br/>Accountant / Bursar", cell_norm),
                    Paragraph("<b>Verified & Audited:</b><br/><br/><br/>_______________________<br/>Internal Auditor / GC", cell_norm),
                    Paragraph("<b>Approved By:</b><br/><br/><br/>_______________________<br/>Principal / Head of Institution", cell_norm)
                ]
            ]
            t_sig = Table(signatures, colWidths=[170, 170, 180])
            t_sig.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(KeepTogether([t_sig]))

            doc.build(story)
            return True
        except Exception as e:
            print(f"[FinancialStatementPDF] Error generating PDF: {e}")
            return False
