from textwrap import wrap


class PdfService:
    def build_report_pdf(self, report_record: dict) -> bytes:
        report = report_record["report"]
        lines = [
            "HealthGuard AI - Personalized Health Awareness Report",
            f"Report ID: {report_record['id']}",
            "",
            "Safety statement:",
            report["disclaimer"],
            "",
            "Patient summary:",
            f"Age: {report['patient_summary'].get('age')}",
            f"Location: {report['patient_summary'].get('location')}",
            f"Occupation: {report['patient_summary'].get('occupation')}",
            f"BMI: {report['patient_summary'].get('bmi')}",
            "",
            "Risk summary:",
            f"Risk level: {report['risk_summary']['overall_risk_level']}",
            f"Risk score: {report['risk_summary']['risk_score']}",
            "",
            "Key risk factors:",
            *[f"- {item}" for item in report["risk_summary"]["key_risk_factors"]],
            "",
            "Precautions:",
            *[f"- {item}" for item in report["precautions"]],
            "",
            "Questions to ask doctor:",
            *[f"- {item}" for item in report["suggested_questions_to_ask_doctor"]],
        ]
        return self._simple_pdf(lines)

    def _simple_pdf(self, lines: list[str]) -> bytes:
        wrapped: list[str] = []
        for line in lines:
            if not line:
                wrapped.append("")
                continue
            wrapped.extend(wrap(str(line), width=86) or [""])

        content_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
        for line in wrapped[:52]:
            content_lines.append(f"({self._escape(line)}) Tj")
            content_lines.append("T*")
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1", errors="replace")

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        ]

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
