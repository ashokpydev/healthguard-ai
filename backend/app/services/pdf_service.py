from textwrap import wrap


class PdfService:
    def build_report_pdf(self, report_record: dict) -> bytes:
        report = report_record["report"]
        patient = report.get("patient_summary", {})
        risk_score = int(report["risk_summary"]["risk_score"])
        bmi = patient.get("bmi")
        sleep_hours = patient.get("sleep_hours") or patient.get("sleep")
        lifestyle_score = self._lifestyle_score(report)
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

        version_lines = [
            f"Current report version: v{report_record.get('current_version', 1)}",
        ]
        for version in report_record.get("version_history", []):
            version_lines.append(
                f"v{version.get('version_number')}: {version.get('change_type')} - {version.get('summary')} ({version.get('created_at')})"
            )
        chat_lines: list[str] = []
        for conversation in report_record.get("chat_conversations", [])[:3]:
            chat_lines.append(f"Conversation #{conversation.get('id')}: {conversation.get('title')} ({conversation.get('updated_at')})")
            for message in (conversation.get("messages") or [])[-6:]:
                prefix = "Patient" if message.get("role") == "user" else "HealthGuard"
                chat_lines.append(f"- {prefix}: {message.get('content')}")
        if not chat_lines:
            chat_lines = ["No chatbot conversation was linked to this report."]

        sections = [
            (
                "HealthGuard AI Branded Report",
                [
                    f"Report ID: {report_record['id']}",
                    f"Report version: v{report_record.get('current_version', 1)}",
                    "Prepared by: HealthGuard AI clinical safety workspace",
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
                    f"Sleep hours: {patient.get('sleep_hours', 'Not captured')}",
                ],
            ),
            (
                "Metric Charts",
                [
                    f"Overall risk level: {report['risk_summary']['overall_risk_level']}",
                    ("chart", "Risk score", risk_score, 100, self._chart_color(risk_score)),
                    ("chart", "BMI position", self._bmi_chart_value(bmi), 40, "amber"),
                    ("chart", "Sleep balance", self._sleep_chart_value(sleep_hours), 10, "teal"),
                    ("chart", "Lifestyle risk", lifestyle_score, 100, self._chart_color(lifestyle_score)),
                ],
            ),
            ("Symptoms", [f"- {item}" for item in self._symptom_lines(report)]),
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
            ("Linked Chatbot Conversation", chat_lines),
            ("Questions For Doctor", [f"- {item}" for item in report["suggested_questions_to_ask_doctor"]]),
            (
                "RAG References",
                [
                    f"- [{source.get('citation') or 'S?'}] {source.get('title')} ({source.get('source_type')}, score {source.get('similarity_score') or 'n/a'}): {source.get('excerpt')}"
                    for source in report.get("sources", [])
                ],
            ),
            ("Report Version History", version_lines),
        ]
        return self._sectioned_pdf(sections, report_record["id"])

    def _lifestyle_score(self, report: dict) -> int:
        factors = " ".join(report.get("risk_summary", {}).get("key_risk_factors", [])).lower()
        score = 10
        for marker in ["sedentary", "sleep", "sugar", "processed", "smoking", "alcohol", "low water", "overweight"]:
            if marker in factors:
                score += 10
        return min(score, 100)

    def _chart_color(self, score: int) -> str:
        if score >= 70:
            return "red"
        if score >= 40:
            return "amber"
        return "teal"

    def _bmi_chart_value(self, bmi: object) -> int:
        try:
            return max(0, min(40, round(float(bmi or 0))))
        except (TypeError, ValueError):
            return 0

    def _sleep_chart_value(self, sleep_hours: object) -> int:
        try:
            return max(0, min(10, round(float(sleep_hours or 0))))
        except (TypeError, ValueError):
            return 0

    def _symptom_lines(self, report: dict) -> list[str]:
        questions = report.get("follow_up_reminders") or []
        red_flags = report.get("red_flags") or []
        if red_flags:
            return [*red_flags, *questions[:2]]
        concerns = report.get("possible_health_concerns_to_discuss_with_doctor") or []
        return concerns[:4] or ["No emergency symptoms detected in the submitted assessment."]

    def _sectioned_pdf(self, sections: list[tuple[str, list[object]]], report_id: int) -> bytes:
        pages: list[list[tuple[str, object]]] = [[]]
        line_count = 0
        for title, lines in sections:
            needed = 2 + sum(3 if isinstance(line, tuple) and line and line[0] == "chart" else max(1, len(wrap(str(line), width=82))) for line in lines)
            if line_count and line_count + needed > 42:
                pages.append([])
                line_count = 0
            pages[-1].append(("section", title))
            line_count += 2
            for line in lines:
                if isinstance(line, tuple) and line and line[0] == "chart":
                    if line_count >= 43:
                        pages.append([])
                        line_count = 0
                    pages[-1].append(("chart", line))
                    line_count += 3
                    continue
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

    def _page_stream(self, page: list[tuple[str, object]], report_id: int, page_number: int, page_count: int) -> bytes:
        lines = [
            "0.94 0.98 1 rg 0 0 612 842 re f",
            "0.05 0.23 0.48 rg 0 778 612 64 re f",
            "0.13 0.75 0.73 rg 0 774 612 5 re f",
            "1 1 1 rg 44 796 34 28 re f",
            "0.05 0.23 0.48 rg 50 802 22 16 re f",
            "1 1 1 rg 59 805 4 10 re f 55 808 12 4 re f",
            "1 1 1 rg",
            "BT /F2 18 Tf 90 810 Td (HealthGuard AI) Tj ET",
            "BT /F1 9 Tf 90 796 Td (Preventive health report with clinician review support) Tj ET",
            f"BT /F1 9 Tf 430 810 Td (Report #{report_id}) Tj ET",
        ]
        y = 764
        for kind, text in page:
            if kind == "section":
                y -= 8
                lines.append("0.07 0.24 0.45 rg")
                lines.append(f"BT /F2 12 Tf 44 {y} Td ({self._escape(str(text).upper())}) Tj ET")
                lines.append("0.13 0.75 0.73 rg")
                lines.append(f"44 {y - 6} 524 1 re f")
                y -= 20
                continue
            if kind == "chart":
                _, label, value, maximum, color = text
                value = max(0, min(float(maximum), float(value)))
                width = round(300 * (value / float(maximum)), 2) if maximum else 0
                lines.append("0.07 0.24 0.45 rg")
                lines.append(f"BT /F2 10 Tf 58 {y} Td ({self._escape(str(label))}: {round(value, 1)} / {maximum}) Tj ET")
                lines.append("0.86 0.91 0.96 rg")
                lines.append(f"230 {y - 2} 300 10 re f")
                lines.append(self._pdf_color(str(color)))
                lines.append(f"230 {y - 2} {width} 10 re f")
                y -= 28
                continue
            lines.append("0.06 0.10 0.20 rg")
            lines.append(f"BT /F1 10 Tf 58 {y} Td ({self._escape(str(text))}) Tj ET")
            y -= 15
        lines.extend(
            [
                "0.13 0.75 0.73 rg 44 42 524 1 re f",
                "0.32 0.36 0.42 rg",
                f"BT /F1 8 Tf 44 26 Td (Educational report. Not a diagnosis. Page {page_number} of {page_count}.) Tj ET",
            ]
        )
        return "\n".join(lines).encode("latin-1", errors="replace")

    def _pdf_color(self, color: str) -> str:
        if color == "red":
            return "0.88 0.18 0.30 rg"
        if color == "amber":
            return "0.95 0.55 0.18 rg"
        return "0.04 0.58 0.55 rg"
