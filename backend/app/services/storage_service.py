from backend.app.db.store import connect, init_db, json_dumps, json_loads, now_iso, row_to_dict
from backend.app.schemas.health import AssessmentRequest, HealthProfile


class StorageService:
    def __init__(self) -> None:
        init_db()

    def save_profile(self, profile: HealthProfile, user_id: int | None = None) -> dict:
        payload = profile.model_dump()
        timestamp = now_iso()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO patient_profiles (user_id, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, json_dumps(payload), timestamp, timestamp),
            )
            profile_id = cursor.lastrowid
        return {"id": profile_id, "profile": payload, "created_at": timestamp, "updated_at": timestamp}

    def save_assessment_and_report(self, request: AssessmentRequest, report: dict, patient_id: int | None = None, user_id: int | None = None) -> dict:
        if patient_id is None:
            patient = self.save_profile(request.profile, user_id)
            patient_id = patient["id"]
        timestamp = now_iso()
        risk = report["risk_summary"]
        with connect() as conn:
            assessment_cursor = conn.execute(
                """
                INSERT INTO assessments (patient_id, input_json, risk_score, risk_level, red_flags_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    json_dumps(request.model_dump()),
                    risk["risk_score"],
                    risk["overall_risk_level"],
                    json_dumps(report["red_flags"]),
                    timestamp,
                ),
            )
            assessment_id = assessment_cursor.lastrowid
            report_cursor = conn.execute(
                """
                INSERT INTO reports (patient_id, assessment_id, report_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (patient_id, assessment_id, json_dumps(report), timestamp),
            )
        return {"patient_id": patient_id, "assessment_id": assessment_id, "report_id": report_cursor.lastrowid}

    def get_report(self, report_id: int, user: dict | None = None) -> dict | None:
        with connect() as conn:
            if self._can_view_all_reports(user):
                row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
            elif user:
                row = conn.execute(
                    """
                    SELECT reports.*
                    FROM reports
                    JOIN patient_profiles ON patient_profiles.id = reports.patient_id
                    WHERE reports.id = ? AND patient_profiles.user_id = ?
                    """,
                    (report_id, user["id"]),
                ).fetchone()
            else:
                row = None
        item = row_to_dict(row)
        if not item:
            return None
        item["report"] = json_loads(item.pop("report_json"))
        return item

    def list_reports(self, user: dict | None = None) -> list[dict]:
        with connect() as conn:
            if self._can_view_all_reports(user):
                rows = conn.execute(
                    """
                    SELECT reports.id, reports.patient_id, reports.assessment_id, reports.doctor_review_status,
                           reports.doctor_comments, reports.final_clinical_notes, reports.created_at,
                           reports.reviewed_at, reports.report_json, patient_profiles.user_id
                    FROM reports
                    LEFT JOIN patient_profiles ON patient_profiles.id = reports.patient_id
                    ORDER BY reports.id DESC
                    LIMIT 50
                    """
                ).fetchall()
            elif user:
                rows = conn.execute(
                    """
                    SELECT reports.id, reports.patient_id, reports.assessment_id, reports.doctor_review_status,
                           reports.doctor_comments, reports.final_clinical_notes, reports.created_at,
                           reports.reviewed_at, reports.report_json, patient_profiles.user_id
                    FROM reports
                    JOIN patient_profiles ON patient_profiles.id = reports.patient_id
                    WHERE patient_profiles.user_id = ?
                    ORDER BY reports.id DESC
                    LIMIT 50
                    """,
                    (user["id"],),
                ).fetchall()
            else:
                rows = []
        reports: list[dict] = []
        for row in rows:
            item = dict(row)
            payload = json_loads(item.pop("report_json"))
            item["risk_level"] = payload["risk_summary"]["overall_risk_level"]
            item["risk_score"] = payload["risk_summary"]["risk_score"]
            item["patient_summary"] = payload["patient_summary"]
            reports.append(item)
        return reports

    def list_patient_report_folders(self, user: dict) -> list[dict]:
        folders: dict[int, dict] = {}
        for item in self.list_reports(user):
            patient_id = item["patient_id"]
            folder = folders.setdefault(
                patient_id,
                {
                    "patient_id": patient_id,
                    "patient_user_id": item.get("user_id"),
                    "patient_summary": item["patient_summary"],
                    "reports": [],
                    "pending_count": 0,
                    "total_count": 0,
                },
            )
            folder["reports"].append(item)
            folder["total_count"] += 1
            if item["doctor_review_status"] == "pending":
                folder["pending_count"] += 1
        return list(folders.values())

    def review_report(self, report_id: int, status: str, comments: str | None, notes: str | None, user: dict | None = None) -> dict | None:
        reviewed_at = now_iso()
        with connect() as conn:
            cursor = conn.execute(
                """
                UPDATE reports
                SET doctor_review_status = ?, doctor_comments = ?, final_clinical_notes = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (status, comments, notes, reviewed_at, report_id),
            )
        if cursor.rowcount == 0:
            return None
        return self.get_report(report_id, user)

    def _can_view_all_reports(self, user: dict | None) -> bool:
        return bool(user and user.get("role") in {"doctor", "dietician", "admin", "compliance"})

    def add_knowledge(self, title: str, content: str, source_type: str = "admin_upload") -> dict:
        timestamp = now_iso()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO knowledge_documents (title, source_type, content, status, created_at)
                VALUES (?, ?, ?, 'approved', ?)
                """,
                (title, source_type, content, timestamp),
            )
        return {"id": cursor.lastrowid, "title": title, "source_type": source_type, "status": "approved", "created_at": timestamp}

    def list_knowledge(self) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id, title, source_type, status, created_at FROM knowledge_documents ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def save_audit(self, action: str, input_summary: str, output_summary: str, risk_flags: list[str] | None = None) -> None:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (action, input_summary, output_summary, risk_flags, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (action, input_summary[:500], output_summary[:500], ",".join(risk_flags or []), now_iso()),
            )

    def list_audit_logs(self) -> list[dict]:
        with connect() as conn:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(row) for row in rows]
