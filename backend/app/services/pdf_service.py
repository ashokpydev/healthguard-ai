from textwrap import wrap


class PdfService:
    def build_report_pdf(self, report_record: dict) -> bytes:
        report = report_record["report"]
        patient = report.get("patient_summary", {})
        review_lines = [
            f"Review status: {report_record.get('doctor_review_status', 'pending')}",
            f"Priority: {report_record.get('review_priority', 'routine')}",
            f"Assigned reviewer ID: {report_record.get('assigned_reviewer_id') or 'Unassigned'}",
            f"Reviewed at: {report_record.get('reviewed_at') or 'Pending'}",
            f"Clinician signature: {report_record.get('clinician_signature') or 'Pending'}",
        ]
        if report_record.get("doctor_comments"):
            review_lines.append(f"Doctor comments: {report_record['doctor_comments']}")
        if report_record.get("final_clinical_notes"):
            review_lines.append(f"Clinical notes: {report_record['final_clinical_notes']}")
        if report_record.get("escalation_reason"):
            review_lines.append(f"Escalation reason: {report_record['escalation_reason']}")

        sections = [
            (
                "Report Overview",
                [
                    f"Report ID: {report_record['id']}",
                    "Brand: HealthGuard AI clinical safety workspace",
                    f"Generated: {report_record.get('created_at')}",
                    report["disclaimer"],
                ],
            ),
            (
                "Patient Snapshot",
                [
                    f"Age: {patient.get('age')}",
                    f"Gender: {patient.get('gender')}",
                    f"Location: {patient.get('location')}",
                    f"Climate: {patient.get('climate')}",
                    f"Occupation: {patient.get('occupation')}",
                    f"BMI: {patient.get('bmi')}",
                ],
            ),
            (
                "Risk Summary",
                [
                    f"Overall risk level: {report['risk_summary']['overall_risk_level']}",
                    f"Risk score: {report['risk_summary']['risk_score']} / 100",
                    "Risk score chart:",
                    self._risk_bar(report["risk_summary"]["risk_score"]),
                ],
            ),
            ("Key Risk Factors", [f"- {item}" for item in report["risk_summary"]["key_risk_factors"]]),
            (
                "Concerns To Discuss With A Doctor",
                [f"- {item}" for item in report.get("possible_health_concerns_to_discuss_with_doctor", [])],
            ),
            ("Precautions", [f"- {item}" for item in report["precautions"]]),
            ("Diet Plan", [f"- {item}" for item in report.get("diet_plan", [])]),
            ("Feel-Better Precautions", [f"- {item}" for item in report.get("wellness_recommendations", [])]),
            ("Physical Activity Plan", [f"- {item}" for item in report.get("physical_activity_plan", [])]),
            ("Which Doctor To Consult", [f"- {item}" for item in report.get("doctor_department_guidance", [])]),
            ("Follow-Up Reminders", [f"- {item}" for item in report.get("follow_up_reminders", [])]),
            ("Doctor Review Metadata", review_lines),
            ("Questions For Doctor", [f"- {item}" for item in report["suggested_questions_to_ask_doctor"]]),
            (
                "Evidence Sources",
                [f"- {source.get('title')} ({source.get('source_type')}): {source.get('excerpt')}" for source in report.get("sources", [])],
            ),
        ]
        return self._sectioned_pdf(sections, report_record["id"])

    def _risk_bar(self, score: int) -> str:
        filled = max(0, min(20, round(score / 5)))
        return "[" + ("#" * filled).ljust(20, ".") + "]"

    def _sectioned_pdf(self, sections: list[tuple[str, list[str]]], report_id: int) -> bytes:
        pages: list[list[tuple[str, str]]] = [[]]
        line_count = 0
        for title, lines in sections:
            needed = 2 + sum(max(1, len(wrap(str(line), width=82))) for line in lines)
            if line_count and line_count + needed > 42:
                pages.append([])
                line_count = 0
            pages[-1].append(("section", title))
            line_count += 2
            for line in lines:
                wrapped = wrap(str(line), width=82) or [""]
                for wrapped_line in wrapped:
                    if line_count >= 46:
                        pages.append([])
                        line_count = 0
                    pages[-1].append(("text", wrapped_line))
                    line_count += 1

        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]
        page_refs: list[str] = []
        for page_index, page in enumerate(pages, start=1):
            stream = self._page_stream(page, report_id, page_index, len(pages))
            content_id = len(objects) + 2
            page_id = len(objects) + 1
            page_refs.append(f"{page_id} 0 R")
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>".encode(
                    "ascii"
                )
            )
            objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(pages)} >>".encode("ascii")

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{index} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref_start = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
        )
        return bytes(pdf)

    def _escape(self, text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _page_stream(self, page: list[tuple[str, str]], report_id: int, page_number: int, page_count: int) -> bytes:
        lines = [
            "0.93 0.98 1 rg 0 794 612 48 re f",
            "0.02 0.18 0.38 rg",
            "BT /F2 18 Tf 44 810 Td (HealthGuard AI) Tj ET",
            f"BT /F1 9 Tf 430 812 Td (Report #{report_id}) Tj ET",
            "0.04 0.53 0.50 rg 44 790 524 2 re f",
        ]
        y = 764
        for kind, text in page:
            if kind == "section":
                y -= 8
                lines.append("0.33 0.19 0.78 rg")
                lines.append(f"BT /F2 12 Tf 44 {y} Td ({self._escape(text.upper())}) Tj ET")
                lines.append("0.78 0.83 0.88 rg")
                lines.append(f"44 {y - 6} 524 1 re f")
                y -= 20
                continue
            lines.append("0.06 0.10 0.20 rg")
            lines.append(f"BT /F1 10 Tf 58 {y} Td ({self._escape(text)}) Tj ET")
            y -= 15
        lines.extend(
            [
                "0.78 0.83 0.88 rg 44 42 524 1 re f",
                "0.32 0.36 0.42 rg",
                f"BT /F1 8 Tf 44 26 Td (Educational report. Not a diagnosis. Page {page_number} of {page_count}.) Tj ET",
            ]
        )
        return "\n".join(lines).encode("latin-1", errors="replace")
