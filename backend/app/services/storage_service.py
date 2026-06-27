import json

from backend.app.db.store import connect, init_db, json_dumps, json_loads, now_iso, row_to_dict
from backend.app.schemas.health import AssessmentRequest, HealthProfile
from backend.app.services.privacy_service import PrivacyService
from backend.app.services.security_service import canonical_event_hash, mask_pii, retention_until


class StorageService:
    def __init__(self) -> None:
        init_db()
        self.privacy = PrivacyService()

    def _secure_dump(self, value: object) -> str:
        return self.privacy.encrypt_text(json_dumps(value))

    def _secure_load(self, value: str) -> object:
        return json_loads(self.privacy.decrypt_text(value))

    def save_profile(self, profile: HealthProfile, user_id: int | None = None) -> dict:
        payload = profile.model_dump()
        timestamp = now_iso()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO patient_profiles (user_id, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, self._secure_dump(payload), timestamp, timestamp),
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
                    self._secure_dump(request.model_dump()),
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
                (patient_id, assessment_id, self._secure_dump(report), timestamp),
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
        item["report"] = self._secure_load(item.pop("report_json"))
        item["review_history"] = json_loads(item.get("review_history_json") or "[]")
        return item

    def list_reports(self, user: dict | None = None, include_role_scope: bool = True) -> list[dict]:
        with connect() as conn:
            if include_role_scope and self._can_view_all_reports(user):
                rows = conn.execute(
                    """
                    SELECT reports.id, reports.patient_id, reports.assessment_id, reports.doctor_review_status,
                           reports.doctor_comments, reports.final_clinical_notes, reports.assigned_reviewer_id,
                           reports.review_priority, reports.clinician_signature, reports.escalation_reason,
                           reports.review_history_json, reports.created_at, reports.reviewed_at,
                           reports.report_json, patient_profiles.user_id
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
                           reports.doctor_comments, reports.final_clinical_notes, reports.assigned_reviewer_id,
                           reports.review_priority, reports.clinician_signature, reports.escalation_reason,
                           reports.review_history_json, reports.created_at, reports.reviewed_at,
                           reports.report_json, patient_profiles.user_id
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
            payload = self._secure_load(item.pop("report_json"))
            item["risk_level"] = payload["risk_summary"]["overall_risk_level"]
            item["risk_score"] = payload["risk_summary"]["risk_score"]
            item["patient_summary"] = payload["patient_summary"]
            item["problem_summary"] = self._report_problem_summary(payload)
            item["risk_factors"] = (payload.get("risk_summary") or {}).get("key_risk_factors", [])[:4]
            item["doctor_questions"] = payload.get("suggested_questions_to_ask_doctor", [])[:3]
            item["uses_uploaded_document"] = any(
                source.get("source_type") == "user_upload_rag_context"
                for source in payload.get("sources", [])
                if isinstance(source, dict)
            )
            item["review_history"] = json_loads(item.get("review_history_json") or "[]")
            reports.append(item)
        return reports

    def _report_problem_summary(self, payload: dict) -> str:
        concerns = payload.get("possible_health_concerns_to_discuss_with_doctor") or []
        if concerns:
            return str(concerns[0])
        risk_summary = payload.get("risk_summary") or {}
        factors = risk_summary.get("key_risk_factors") or []
        if factors:
            return str(factors[0])
        return "Preventive health review requires clinician review."

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

    def assign_report(self, report_id: int, reviewer_id: int, priority: str, user: dict) -> dict | None:
        current = self.get_report(report_id, user)
        if not current:
            return None
        timestamp = now_iso()
        history = current.get("review_history") or []
        previous_status = current.get("doctor_review_status") or "pending"
        status = "assigned" if previous_status == "pending" else previous_status
        history.append(
            {
                "at": timestamp,
                "actor_user_id": user["id"],
                "actor_role": user["role"],
                "action": "assigned",
                "from_status": previous_status,
                "to_status": status,
                "assigned_reviewer_id": reviewer_id,
                "priority": priority,
            }
        )
        with connect() as conn:
            conn.execute(
                """
                UPDATE reports
                SET assigned_reviewer_id = ?, review_priority = ?, doctor_review_status = ?, review_history_json = ?
                WHERE id = ?
                """,
                (reviewer_id, priority, status, json_dumps(history), report_id),
            )
        return self.get_report(report_id, user)

    def review_report(
        self,
        report_id: int,
        status: str,
        comments: str | None,
        notes: str | None,
        user: dict | None = None,
        clinician_signature: str | None = None,
        priority: str | None = None,
        escalation_reason: str | None = None,
    ) -> dict | None:
        reviewed_at = now_iso()
        current = self.get_report(report_id, user)
        if not current:
            return None
        history = current.get("review_history") or []
        previous_status = current.get("doctor_review_status") or "pending"
        history.append(
            {
                "at": reviewed_at,
                "actor_user_id": user.get("id") if user else None,
                "actor_role": user.get("role") if user else None,
                "action": "review_updated",
                "from_status": previous_status,
                "to_status": status,
                "comments": comments,
                "signature": clinician_signature,
                "escalation_reason": escalation_reason,
            }
        )
        with connect() as conn:
            cursor = conn.execute(
                """
                UPDATE reports
                SET doctor_review_status = ?, doctor_comments = ?, final_clinical_notes = ?, reviewed_at = ?,
                    clinician_signature = ?, review_priority = COALESCE(?, review_priority),
                    escalation_reason = ?, review_history_json = ?
                WHERE id = ?
                """,
                (
                    status,
                    comments,
                    notes,
                    reviewed_at,
                    clinician_signature,
                    priority,
                    escalation_reason,
                    json_dumps(history),
                    report_id,
                ),
            )
        if cursor.rowcount == 0:
            return None
        return self.get_report(report_id, user)

    def report_review_history(self, report_id: int, user: dict) -> list[dict] | None:
        item = self.get_report(report_id, user)
        if not item:
            return None
        return item.get("review_history") or []

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

    def save_audit(
        self,
        action: str,
        input_summary: str,
        output_summary: str,
        risk_flags: list[str] | None = None,
        user_id: int | None = None,
        metadata: dict | None = None,
    ) -> None:
        created_at = now_iso()
        metadata = metadata or {}
        safe_input = mask_pii(input_summary)
        safe_output = mask_pii(output_summary)
        with connect() as conn:
            previous = conn.execute("SELECT event_hash FROM audit_logs ORDER BY id DESC LIMIT 1").fetchone()
            previous_hash = previous["event_hash"] if previous else None
            event_payload = {
                "user_id": user_id or metadata.get("user_id"),
                "action": action,
                "input_summary": safe_input,
                "output_summary": safe_output,
                "risk_flags": risk_flags or [],
                "created_at": created_at,
                "previous_hash": previous_hash,
            }
            event_hash = canonical_event_hash(event_payload)
            conn.execute(
                """
                INSERT INTO audit_logs (
                    user_id, action, input_summary, output_summary, risk_flags, ip_address, user_agent,
                    metadata_json, event_hash, previous_hash, retention_until, immutable, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    user_id or metadata.get("user_id"),
                    action,
                    safe_input,
                    safe_output,
                    ",".join(risk_flags or []),
                    metadata.get("ip_address"),
                    metadata.get("user_agent"),
                    json_dumps(metadata),
                    event_hash,
                    previous_hash,
                    retention_until(),
                    created_at,
                ),
            )

    def list_audit_logs(
        self,
        action: str | None = None,
        user_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        filters: list[str] = []
        params: list[object] = []
        if action:
            filters.append("action = ?")
            params.append(action)
        if user_id is not None:
            filters.append("user_id = ?")
            params.append(user_id)
        if date_from:
            filters.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            filters.append("created_at <= ?")
            params.append(date_to)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        params.append(limit)
        with connect() as conn:
            rows = conn.execute(f"SELECT * FROM audit_logs {where_clause} ORDER BY id DESC LIMIT ?", tuple(params)).fetchall()
        return [dict(row) for row in rows]
