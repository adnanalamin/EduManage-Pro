"""
EduManage Pro - School Bus Pass Generator (ReportLab PDF)
Phase 11: CR80 PVC Printable Transport ID Pass with Route, Stop, Seat & Barcode
"""

import os
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from app.models.transport import TransportPassenger
from app.models.school import SchoolSetting


class BusPassGenerator:
    """Generates standard CR80 (85.6mm x 54mm) student & faculty bus transit passes."""
    CARD_WIDTH = 3.375 * inch   # ~85.6 mm
    CARD_HEIGHT = 2.125 * inch  # ~54 mm

    @classmethod
    def generate_single_pass(
        cls,
        passenger: TransportPassenger,
        school: SchoolSetting = None,
        output_pdf_path: str = "bus_transit_pass.pdf"
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))

        # 1. Background Outline & White Fill
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=1)

        # 2. Header Bar (Dark Amber / Gold Transport Theme)
        c.setFillColor(colors.HexColor("#B45309"))  # Amber 700
        c.rect(0, cls.CARD_HEIGHT - 38, cls.CARD_WIDTH, 38, fill=1, stroke=0)

        # School Name & Card Type
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        school_title = school.school_name if school else "Ideal Model High School & College"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 16, school_title[:38])

        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(colors.HexColor("#FEF3C7"))  # Amber 100
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 28, "OFFICIAL SCHOOL BUS TRANSIT PASS")

        # 3. Photo / Avatar Box
        photo_x = 12
        photo_y = 30
        photo_w = 52
        photo_h = 64
        c.setStrokeColor(colors.HexColor("#FCD34D"))
        c.setFillColor(colors.HexColor("#FFFBEB"))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)

        passenger_name = "Passenger"
        class_roll = ""
        emg_phone = ""
        if passenger.student:
            passenger_name = passenger.student.full_name
            class_roll = f"Class {passenger.student.school_class.name if passenger.student.school_class else ''} (Roll {passenger.student.roll_number})"
            emg_phone = passenger.student.emergency_contact or passenger.student.phone or ""
        elif passenger.teacher:
            passenger_name = passenger.teacher.full_name
            class_roll = passenger.teacher.designation or "Faculty"
            emg_phone = passenger.teacher.phone or ""

        initials = "".join([part[0] for part in passenger_name.split()[:2]]).upper() or "BUS"
        c.setFillColor(colors.HexColor("#B45309"))
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + (photo_h / 2.0) - 4, initials)

        c.setFont("Helvetica", 5.5)
        c.setFillColor(colors.HexColor("#92400E"))
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + 4, passenger.passenger_type.upper())

        # 4. Details Column
        info_x = photo_x + photo_w + 10
        info_y = cls.CARD_HEIGHT - 50
        line_spacing = 9.5

        # Name
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, passenger_name[:24])

        # Class / Designation
        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.HexColor("#475569"))
        if class_roll:
            info_y -= line_spacing
            c.drawString(info_x, info_y, class_roll[:28])

        # Route Code & Bus No
        info_y -= line_spacing
        route_text = passenger.route.route_code if passenger.route else "RT-01"
        v_num = passenger.vehicle.vehicle_number if passenger.vehicle else "Fleet Bus"
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(colors.HexColor("#B45309"))
        c.drawString(info_x, info_y, f"{route_text}  •  {v_num[:14]}")

        # Stop & Seat
        info_y -= line_spacing
        stop_title = passenger.stop.stop_name if passenger.stop else "Campus Gate"
        seat_text = passenger.seat_number or "Assigned"
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(info_x, info_y, f"Stop: {stop_title[:20]}")

        info_y -= line_spacing
        c.drawString(info_x, info_y, f"Seat: {seat_text}  |  Emg: {emg_phone[:14]}")

        # 5. Simulated Barcode at Bottom
        barcode_x = 12
        barcode_y = 8
        barcode_w = cls.CARD_WIDTH - 24
        barcode_h = 14

        c.setFillColor(colors.HexColor("#0F172A"))
        curr_x = barcode_x + 10
        code_str = f"BUS-{passenger.id:04d}-{route_text}"
        for i, char in enumerate(code_str * 2):
            val = ord(char) + i
            bar_w = 1.0 if (val % 2 == 0) else 1.8
            if curr_x + bar_w > barcode_x + barcode_w - 10:
                break
            c.rect(curr_x, barcode_y + 4, bar_w, barcode_h - 4, fill=1, stroke=0)
            curr_x += bar_w + (1.2 if (val % 3 == 0) else 0.8)

        # Barcode text caption
        c.setFont("Helvetica", 5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawCentredString(cls.CARD_WIDTH / 2.0, barcode_y - 1, f"*{code_str}*")

        c.showPage()
        c.save()
        return output_pdf_path
