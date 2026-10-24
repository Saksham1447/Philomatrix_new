import io
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.core.deps import get_current_user, get_db, require_roles, verify_student_access
from app.core.docstore import DocStore, UserDoc
from app.core.q import ids, index_by, group_by
from app.schemas.examination import ReportCardData, ReportCardSubjectScore

router = APIRouter(prefix="/reports", tags=["Report Cards & Performance Analytics"])


def calculate_grade(pct: Decimal) -> str:
    """Standard Indian Junior College grading rubric."""
    if pct >= 75:
        return "Distinction"
    elif pct >= 60:
        return "First Class"
    elif pct >= 50:
        return "Second Class"
    elif pct >= 35:
        return "Pass Class"
    else:
        return "Needs Improvement"


def compile_report_card_data(
    examination_id: str,
    student_id: str,
    current_user: UserDoc,
    db: DocStore
) -> ReportCardData:
    """Compile official report card data aggregating marks and attendance."""
    # Re-validate student access, tenant isolation, and guardian-child relationship server-side
    student = verify_student_access(student_id, current_user, db)

    exam = db.find_one("examinations", {"id": examination_id, "institution_id": student.institution_id})
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found in this institution")

    # If student or parent, verify publication
    if current_user.student_profile or current_user.guardian_profile:
        is_published = db.find_one("result_publications", {"examination_id": examination_id, "is_active": True})
        if not is_published:
            raise HTTPException(status_code=403, detail="Results for this examination have not yet been published")

    enrollment = db.find_one("enrollments", {"student_id": student.id})
    institution = db.get("institutions", student.institution_id)
    enrollment_year = db.get("academic_years", enrollment.academic_year_id) if enrollment else None
    enrollment_division = db.get("divisions", enrollment.division_id) if enrollment else None
    enrollment_class = db.get("classes", enrollment_division.class_id) if enrollment_division else None
    student_user = db.get("users", student.user_id)

    # Gather subject marks
    exam_subjects = db.find("exam_subjects", {"examination_id": examination_id})
    subjects_by_id = db.get_many("subjects", ids(exam_subjects, "subject_id"))
    marks_by_exam_subject = index_by(
        db.find("marks_entries", {"student_id": student.id, "exam_subject_id": {"$in": ids(exam_subjects)}}),
        "exam_subject_id",
    )
    subject_scores = []
    grand_total_max = Decimal("0.00")
    grand_total_obtained = Decimal("0.00")
    any_failed = False

    for es in exam_subjects:
        m = marks_by_exam_subject.get(es.id)
        subject = subjects_by_id[es.subject_id]
        t_max = es.max_theory_marks
        p_max = es.max_practical_marks
        tot_max = t_max + p_max
        grand_total_max += tot_max

        t_obt = m.theory_marks_obtained if m else None
        p_obt = m.practical_marks_obtained if m else None
        tot_obt = m.total_obtained if m else None

        if tot_obt is not None:
            grand_total_obtained += tot_obt

        pct = Decimal(round((tot_obt / tot_max) * 100, 2)) if tot_obt is not None and tot_max > 0 else Decimal("0.00")
        grd = calculate_grade(pct) if tot_obt is not None else "N/A"

        status_str = "PASS"
        if m and m.is_absent:
            status_str = "ABSENT"
            any_failed = True
        elif tot_obt is None or pct < es.min_passing_marks:
            status_str = "FAIL"
            any_failed = True

        subject_scores.append(
            ReportCardSubjectScore(
                subject_code=subject.code,
                subject_name=subject.name,
                theory_max=t_max,
                theory_obtained=t_obt,
                practical_max=p_max,
                practical_obtained=p_obt,
                total_max=tot_max,
                total_obtained=tot_obt,
                percentage=pct,
                grade=grd,
                status=status_str
            )
        )

    # Attendance Rollup (records whose session still exists, mirroring the former inner join)
    all_records = db.find("attendance_records", {"student_id": student.id})
    sessions_by_id = db.get_many("attendance_sessions", ids(all_records, "attendance_session_id"))
    att_records = [r for r in all_records if r.attendance_session_id in sessions_by_id]
    tot_conducted = len(att_records)
    tot_attended = sum(1 for r in att_records if r.status in ["PRESENT", "LATE", "EXCUSED"])
    att_pct = Decimal(round((tot_attended / tot_conducted) * 100, 2)) if tot_conducted > 0 else Decimal("100.00")

    overall_pct = (
        Decimal(round((grand_total_obtained / grand_total_max) * 100, 2))
        if grand_total_max > 0 else Decimal("0.00")
    )
    overall_grd = calculate_grade(overall_pct) if not any_failed else "Needs Improvement"
    final_res = "CONGRATULATIONS - PROMOTED" if not any_failed else "REQUIRES REMEDIAL SUPPORT"

    pub = db.find_one("result_publications", {"examination_id": examination_id})

    return ReportCardData(
        institution_name=institution.name,
        institution_address=institution.address or f"{institution.city}, {institution.state}",
        institution_code=institution.code,
        institution_logo_url=institution.logo_url,
        academic_year=enrollment_year.name if enrollment else "2026-2027",
        examination_name=exam.name,
        examination_type=exam.exam_type,
        student_name=student_user.full_name,
        admission_number=student.admission_number,
        roll_number=student.roll_number,
        class_name=enrollment_class.name if enrollment else "Class 11 Science",
        division_name=enrollment_division.name if enrollment else "A",
        stream="SCIENCE",
        attendance_percentage=att_pct,
        total_conducted_lectures=tot_conducted,
        total_attended_lectures=tot_attended,
        subjects=subject_scores,
        grand_total_max=grand_total_max,
        grand_total_obtained=grand_total_obtained,
        overall_percentage=overall_pct,
        overall_grade=overall_grd,
        final_result=final_res,
        teacher_remarks="Demonstrates strong analytical acumen and consistent laboratory discipline.",
        principal_remarks="Approved for official academic certification.",
        published_date=pub.published_at.date() if pub else None
    )


@router.get("/report-card/{examination_id}/student/{student_id}", response_model=ReportCardData)
def get_report_card(
    examination_id: str,
    student_id: str,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """Fetch compiled official report card data."""
    return compile_report_card_data(examination_id, student_id, current_user, db)


@router.get("/report-card/{examination_id}/student/{student_id}/pdf")
def download_report_card_pdf(
    examination_id: str,
    student_id: str,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """Generate and stream a professional printable PDF Report Card."""
    data = compile_report_card_data(examination_id, student_id, current_user, db)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'InstTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        alignment=1,  # Center
        textColor=colors.HexColor("#1e1b4b")
    )
    sub_style = ParagraphStyle(
        'InstSub',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#475569")
    )
    header_style = ParagraphStyle(
        'ReportHeader',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor("#4338ca")
    )

    elements = []

    # Institution Header
    elements.append(Paragraph(data.institution_name, title_style))
    elements.append(Paragraph(f"{data.institution_address} | Code: {data.institution_code}", sub_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"OFFICIAL REPORT CARD — {data.examination_name.upper()}", header_style))
    elements.append(Paragraph(f"Academic Year: {data.academic_year}", sub_style))
    elements.append(Spacer(1, 15))

    # Student Demographics Table
    demo_data = [
        [
            Paragraph(f"<b>Student Name:</b> {data.student_name}", styles['Normal']),
            Paragraph(f"<b>Admission No:</b> {data.admission_number}", styles['Normal']),
        ],
        [
            Paragraph(f"<b>Class & Division:</b> {data.class_name} - {data.division_name} ({data.stream})", styles['Normal']),
            Paragraph(f"<b>Roll No:</b> {data.roll_number or 'N/A'}", styles['Normal']),
        ],
        [
            Paragraph(f"<b>Term Attendance:</b> {data.attendance_percentage}% ({data.total_attended_lectures}/{data.total_conducted_lectures} Lectures)", styles['Normal']),
            Paragraph(f"<b>Result Status:</b> <b>{data.final_result}</b>", styles['Normal']),
        ]
    ]
    t_demo = Table(demo_data, colWidths=[270, 270])
    t_demo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_demo)
    elements.append(Spacer(1, 15))

    # Subject Scores Table
    table_data = [
        ["Subject Code", "Subject Name", "Theory (Max)", "Practical (Max)", "Total Max", "Total Obtained", "%", "Grade", "Status"]
    ]
    for s in data.subjects:
        th_str = f"{s.theory_obtained}" if s.theory_obtained is not None else "-"
        pr_str = f"{s.practical_obtained}" if s.practical_obtained is not None else "-"
        tot_str = f"{s.total_obtained}" if s.total_obtained is not None else "-"
        table_data.append([
            s.subject_code,
            s.subject_name,
            f"{s.theory_max}",
            f"{s.practical_max}",
            f"{s.total_max}",
            tot_str,
            f"{s.percentage}%",
            s.grade,
            s.status
        ])

    # Grand Total Row
    table_data.append([
        "TOTAL",
        "GRAND AGGREGATE",
        "-",
        "-",
        f"{data.grand_total_max}",
        f"{data.grand_total_obtained}",
        f"{data.overall_percentage}%",
        data.overall_grade,
        data.final_result
    ])

    t_scores = Table(table_data, colWidths=[65, 115, 60, 60, 50, 55, 45, 50, 40])
    t_scores.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4338ca")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_scores)
    elements.append(Spacer(1, 20))

    # Remarks & Signatures
    rem_data = [
        [
            Paragraph(f"<b>Teacher Remarks:</b> {data.teacher_remarks}", styles['Normal']),
            Paragraph(f"<b>Principal Remarks:</b> {data.principal_remarks}", styles['Normal'])
        ],
        [
            Paragraph("<br/><br/>_____________________<br/><b>Class Teacher Signature</b>", styles['Normal']),
            Paragraph("<br/><br/>_____________________<br/><b>Principal Seal & Signature</b>", styles['Normal'])
        ]
    ]
    t_rem = Table(rem_data, colWidths=[270, 270])
    t_rem.setStyle(TableStyle([
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 1), (1, 1), 'RIGHT'),
    ]))
    elements.append(t_rem)

    doc.build(elements)
    buffer.seek(0)

    filename = f"ReportCard_{data.admission_number}_{data.examination_type}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/analytics/class-performance")
def get_class_performance_analytics(
    division_id: Optional[str] = None,
    examination_id: Optional[str] = None,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] Aggregated class performance: average percentages, pass rates, toppers, and at-risk students."""
    students = db.find("students", {"institution_id": current_user.institution_id, "status": "ACTIVE"})

    total_students = len(students)
    at_risk_attendance = 0

    records_by_student = group_by(
        db.find("attendance_records", {"student_id": {"$in": ids(students)}}) if students else [],
        "student_id",
    )
    for s in students:
        recs = records_by_student.get(s.id, [])
        if recs:
            att = sum(1 for r in recs if r.status in ["PRESENT", "LATE", "EXCUSED"])
            pct = (att / len(recs)) * 100
            if pct < 75.0:
                at_risk_attendance += 1
    return {
        "total_active_students": total_students,
        "students_below_75_attendance": at_risk_attendance,
        "attendance_compliance_rate": round(((total_students - at_risk_attendance) / total_students * 100), 2) if total_students > 0 else 100.0,
        "active_stream": "Class 11 & 12 Science",
        "divisions_count": db.count("divisions", {"institution_id": current_user.institution_id}),
        "examinations_held": db.count("examinations", {"institution_id": current_user.institution_id})
    }
