"""
EduManage Pro - School Settings Model
Stores institute profile, EIIN, contact details, currency, logo path, and academic configurations.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class SchoolSetting(Base, TimestampMixin):
    __tablename__ = "school_settings"

    school_name = Column(String(200), default="Ideal Model High School & College", nullable=False)
    school_name_bn = Column(String(200), default="আইডিয়াল মডেল হাই স্কুল অ্যান্ড কলেজ", nullable=True)
    motto = Column(String(255), default="Excellence in Education & Character", nullable=True)
    eiin_number = Column(String(50), default="134211", nullable=True)
    registration_no = Column(String(50), default="REG-DH-2024-889", nullable=True)

    address = Column(Text, default="Plot 12, Road 4, Sector 7, Uttara", nullable=True)
    city = Column(String(100), default="Dhaka", nullable=True)
    district = Column(String(100), default="Dhaka", nullable=True)
    country = Column(String(100), default="Bangladesh", nullable=True)

    phone = Column(String(50), default="+880 1712-345678", nullable=True)
    email = Column(String(120), default="contact@idealmodel.edu.bd", nullable=True)
    website = Column(String(150), default="https://idealmodel.edu.bd", nullable=True)
    principal_name = Column(String(120), default="Prof. Dr. Mohammad Rafiqul Islam", nullable=True)
    logo_path = Column(String(255), nullable=True)

    currency_code = Column(String(10), default="BDT", nullable=False)
    currency_symbol = Column(String(10), default="৳", nullable=False)
    language = Column(String(10), default="en", nullable=False)  # "en" or "bn"
    date_format = Column(String(30), default="%d %b %Y", nullable=False)

    is_setup_completed = Column(Boolean, default=False, nullable=False)

    # Enterprise & Schema Metadata
    edition = Column(String(30), default="Standalone", nullable=False)  # Standalone | Enterprise
    schema_version = Column(Integer, default=2, nullable=False)
    current_academic_year_id = Column(
        Integer,
        ForeignKey("academic_years.id", ondelete="SET NULL"),
        nullable=True,
    )

    current_academic_year = relationship("AcademicYear", foreign_keys=[current_academic_year_id])

    def __repr__(self):
        return f"<SchoolSetting(name='{self.school_name}', edition='{self.edition}')>"

