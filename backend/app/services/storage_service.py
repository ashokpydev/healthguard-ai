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
                INSERT INTO reports (patient_id, assessment_id, report_json, doctor_review_status, created_at)
                VALUES (?, ?, ?, 'submitted', ?)
                """,
                (patient_id, assessment_id, self._secure_dump(report), timestamp),
            )
            report_id = report_cursor.lastrowid
            self._insert_report_version(
                conn,
                report_id,
                1,
                "generated",
                "Initial LLM-enhanced preventive health report generated from patient assessment.",
                report,
                user_id,
                timestamp,
            )
        return {"patient_id": patient_id, "assessment_id": assessment_id, "report_id": report_id, "report_version": 1}

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
        item["version_history"] = self.list_report_versions(report_id, user)
        item["chat_conversations"] = self.list_chat_conversations(user, report_id=report_id) if user else []
        return item

    def list_reports(self, user: dict | None = None, include_role_scope: bool = True) -> list[dict]:
        with connect() as conn:
            if include_role_scope and self._can_view_all_reports(user):
                rows = conn.execute(
                    """
                    SELECT reports.id, reports.patient_id, reports.assessment_id, reports.doctor_review_status,
                           reports.doctor_comments, reports.final_clinical_notes, reports.assigned_reviewer_id,
                           reports.review_priority, reports.clinician_signature, reports.escalation_reason,
                           reports.review_history_json, reports.current_version, reports.created_at, reports.reviewed_at,
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
                           reports.review_history_json, reports.current_version, reports.created_at, reports.reviewed_at,
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
            item["version_history"] = self.list_report_versions(item["id"], user)
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
            if item["doctor_review_status"] in {"submitted", "pending"}:
                folder["pending_count"] += 1
        return list(folders.values())

    def list_doctor_queue(self, user: dict, status: str = "pending", priority: str | None = None) -> dict:
        reports = self.list_reports(user)
        filtered: list[dict] = []
        for item in reports:
            review_status = item["doctor_review_status"]
            include = (
                status == "all"
                or (status == "pending" and review_status in {"submitted", "pending", "assigned", "in_review"})
                or (status == "reviewed" and review_status in {"reviewed", "approved", "closed", "modified", "rejected"})
                or (status == "urgent" and (item.get("review_priority") == "urgent" or review_status == "escalated"))
                or review_status == status
            )
            if include and (not priority or item.get("review_priority") == priority):
                filtered.append(item)
        folders = self._folders_from_reports(filtered)
        return {
            "items": filtered,
            "patient_folders": folders,
            "counts": {
                "all": len(reports),
                "pending": sum(1 for item in reports if item["doctor_review_status"] in {"submitted", "pending", "assigned", "in_review"}),
                "reviewed": sum(1 for item in reports if item["doctor_review_status"] in {"reviewed", "approved", "closed", "modified", "rejected"}),
                "urgent": sum(1 for item in reports if item.get("review_priority") == "urgent" or item["doctor_review_status"] == "escalated"),
            },
        }

    def _folders_from_reports(self, reports: list[dict]) -> list[dict]:
        folders: dict[int, dict] = {}
        for item in reports:
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
            if item["doctor_review_status"] in {"submitted", "pending", "assigned", "in_review"}:
                folder["pending_count"] += 1
        return list(folders.values())

    def assign_report(self, report_id: int, reviewer_id: int, priority: str, user: dict) -> dict | None:
        current = self.get_report(report_id, user)
        if not current:
            return None
        timestamp = now_iso()
        history = current.get("review_history") or []
        previous_status = current.get("doctor_review_status") or "pending"
        status = "assigned" if previous_status in {"submitted", "pending"} else previous_status
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
                    escalation_reason = ?, review_history_json = ?, current_version = current_version + 1
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
            if cursor.rowcount:
                next_version = int(current.get("current_version") or 1) + 1
                snapshot = dict(current["report"])
                snapshot["doctor_review_metadata"] = {
                    "status": status,
                    "comments": comments,
                    "final_clinical_notes": notes,
                    "clinician_signature": clinician_signature,
                    "review_priority": priority or current.get("review_priority", "routine"),
                    "escalation_reason": escalation_reason,
                    "reviewed_at": reviewed_at,
                }
                self._insert_report_version(
                    conn,
                    report_id,
                    next_version,
                    "doctor_review",
                    f"Doctor review updated to {status.replace('_', ' ')}.",
                    snapshot,
                    user.get("id") if user else None,
                    reviewed_at,
                )
        if cursor.rowcount:
            self._notify_patient_after_review(current, status, comments, notes)
        if cursor.rowcount == 0:
            return None
        return self.get_report(report_id, user)

    def _notify_patient_after_review(self, current: dict, status: str, comments: str | None, notes: str | None) -> None:
        patient_user_id = current.get("user_id")
        if not patient_user_id:
            with connect() as conn:
                row = conn.execute(
                    """
                    SELECT patient_profiles.user_id
                    FROM reports
                    JOIN patient_profiles ON patient_profiles.id = reports.patient_id
                    WHERE reports.id = ?
                    """,
                    (current["id"],),
                ).fetchone()
            patient_user_id = row["user_id"] if row else None
        if not patient_user_id:
            return
        status_label = status.replace("_", " ")
        message = f"Your report #{current['id']} review status is now {status_label}."
        if comments:
            message = f"{message} Doctor comments: {comments}"
        if notes:
            message = f"{message} Clinical notes: {notes}"
        self.create_notification(
            patient_user_id,
            current["id"],
            "Doctor review updated",
            message,
        )

    def create_notification(self, user_id: int, report_id: int | None, title: str, message: str) -> dict:
        timestamp = now_iso()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notifications (user_id, report_id, title, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, report_id, title, message, timestamp),
            )
        return {"id": cursor.lastrowid, "user_id": user_id, "report_id": report_id, "title": title, "message": message, "status": "unread", "created_at": timestamp}

    def list_notifications(self, user: dict) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, report_id, title, message, status, created_at, read_at
                FROM notifications
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 25
                """,
                (user["id"],),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_notification_read(self, notification_id: int, user: dict) -> dict | None:
        timestamp = now_iso()
        with connect() as conn:
            cursor = conn.execute(
                """
                UPDATE notifications
                SET status = 'read', read_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (timestamp, notification_id, user["id"]),
            )
        if cursor.rowcount == 0:
            return None
        return {"id": notification_id, "status": "read", "read_at": timestamp}

    def record_consent(self, user: dict, action: str, metadata: dict | None = None) -> dict:
        timestamp = now_iso()
        metadata = metadata or {}
        consent_text = "I consent to process my health information for educational HealthGuard AI features."
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO consent_records (
                    user_id, action, consent_text, consent_version, ip_address, user_agent, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    action,
                    consent_text,
                    "2026-06-27.v1",
                    metadata.get("ip_address"),
                    metadata.get("user_agent"),
                    timestamp,
                ),
            )
        return {"id": cursor.lastrowid, "action": action, "consent_version": "2026-06-27.v1", "created_at": timestamp}

    def export_user_health_data(self, user: dict) -> dict:
        with connect() as conn:
            profile_rows = conn.execute(
                "SELECT id, profile_json, created_at, updated_at FROM patient_profiles WHERE user_id = ? ORDER BY id",
                (user["id"],),
            ).fetchall()
            patient_ids = [row["id"] for row in profile_rows]
            assessment_rows = []
            report_rows = []
            for patient_id in patient_ids:
                assessment_rows.extend(
                    conn.execute(
                        "SELECT id, patient_id, input_json, risk_score, risk_level, red_flags_json, created_at FROM assessments WHERE patient_id = ? ORDER BY id",
                        (patient_id,),
                    ).fetchall()
                )
                report_rows.extend(
                    conn.execute(
                        """
                        SELECT id, patient_id, assessment_id, report_json, doctor_review_status, doctor_comments,
                               final_clinical_notes, review_priority, clinician_signature, reviewed_at, created_at
                        FROM reports
                        WHERE patient_id = ?
                        ORDER BY id
                        """,
                        (patient_id,),
                    ).fetchall()
                )
            rag_docs = conn.execute(
                "SELECT id, title, source_type, filename, status, created_at FROM rag_documents WHERE user_id = ? ORDER BY id",
                (user["id"],),
            ).fetchall()
            consents = conn.execute(
                "SELECT id, action, consent_text, consent_version, created_at FROM consent_records WHERE user_id = ? ORDER BY id",
                (user["id"],),
            ).fetchall()
        return {
            "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]},
            "patient_profiles": [
                {**dict(row), "profile": self._secure_load(row["profile_json"])} for row in profile_rows
            ],
            "assessments": [
                {**dict(row), "input": self._secure_load(row["input_json"])} for row in assessment_rows
            ],
            "reports": [
                {**dict(row), "report": self._secure_load(row["report_json"])} for row in report_rows
            ],
            "rag_documents": [dict(row) for row in rag_docs],
            "consent_records": [dict(row) for row in consents],
            "exported_at": now_iso(),
        }

    def delete_user_health_data(self, user: dict, metadata: dict | None = None) -> dict:
        timestamp = now_iso()
        deleted = {"reports": 0, "assessments": 0, "patient_profiles": 0, "rag_documents": 0, "rag_chunks": 0, "notifications": 0, "chat_conversations": 0, "chat_messages": 0, "chat_feedback": 0}
        with connect() as conn:
            profile_rows = conn.execute("SELECT id FROM patient_profiles WHERE user_id = ?", (user["id"],)).fetchall()
            patient_ids = [row["id"] for row in profile_rows]
            report_ids: list[int] = []
            for patient_id in patient_ids:
                report_rows = conn.execute("SELECT id FROM reports WHERE patient_id = ?", (patient_id,)).fetchall()
                report_ids.extend(row["id"] for row in report_rows)
                for report_id in report_ids:
                    conn.execute("DELETE FROM report_versions WHERE report_id = ?", (report_id,))
                deleted["reports"] += conn.execute("DELETE FROM reports WHERE patient_id = ?", (patient_id,)).rowcount
                deleted["assessments"] += conn.execute("DELETE FROM assessments WHERE patient_id = ?", (patient_id,)).rowcount
            deleted["patient_profiles"] = conn.execute("DELETE FROM patient_profiles WHERE user_id = ?", (user["id"],)).rowcount
            doc_rows = conn.execute("SELECT id FROM rag_documents WHERE user_id = ?", (user["id"],)).fetchall()
            for row in doc_rows:
                deleted["rag_chunks"] += conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (row["id"],)).rowcount
            deleted["rag_documents"] = conn.execute("DELETE FROM rag_documents WHERE user_id = ?", (user["id"],)).rowcount
            deleted["notifications"] = conn.execute("DELETE FROM notifications WHERE user_id = ?", (user["id"],)).rowcount
            conversation_rows = conn.execute("SELECT id FROM chat_conversations WHERE user_id = ?", (user["id"],)).fetchall()
            message_ids: list[int] = []
            for row in conversation_rows:
                message_ids.extend(item["id"] for item in conn.execute("SELECT id FROM chat_messages WHERE conversation_id = ?", (row["id"],)).fetchall())
            for message_id in message_ids:
                deleted["chat_feedback"] += conn.execute("DELETE FROM chat_feedback WHERE message_id = ?", (message_id,)).rowcount
            for row in conversation_rows:
                deleted["chat_messages"] += conn.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (row["id"],)).rowcount
            deleted["chat_conversations"] = conn.execute("DELETE FROM chat_conversations WHERE user_id = ?", (user["id"],)).rowcount
            cursor = conn.execute(
                """
                INSERT INTO privacy_requests (user_id, request_type, status, details_json, created_at, completed_at)
                VALUES (?, 'delete_health_data', 'completed', ?, ?, ?)
                """,
                (user["id"], json_dumps({"deleted": deleted, **(metadata or {})}), timestamp, timestamp),
            )
        return {"request_id": cursor.lastrowid, "status": "completed", "deleted": deleted, "completed_at": timestamp}

    def report_review_history(self, report_id: int, user: dict) -> list[dict] | None:
        item = self.get_report(report_id, user)
        if not item:
            return None
        return item.get("review_history") or []

    def list_report_versions(self, report_id: int, user: dict | None = None) -> list[dict]:
        with connect() as conn:
            if self._can_view_all_reports(user):
                allowed = conn.execute("SELECT id FROM reports WHERE id = ?", (report_id,)).fetchone()
            elif user:
                allowed = conn.execute(
                    """
                    SELECT reports.id
                    FROM reports
                    JOIN patient_profiles ON patient_profiles.id = reports.patient_id
                    WHERE reports.id = ? AND patient_profiles.user_id = ?
                    """,
                    (report_id, user["id"]),
                ).fetchone()
            else:
                allowed = None
            if not allowed:
                return []
            rows = conn.execute(
                """
                SELECT id, report_id, version_number, change_type, summary, actor_user_id, created_at
                FROM report_versions
                WHERE report_id = ?
                ORDER BY version_number ASC, id ASC
                """,
                (report_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _insert_report_version(
        self,
        conn,
        report_id: int,
        version_number: int,
        change_type: str,
        summary: str,
        report_snapshot: dict,
        actor_user_id: int | None,
        created_at: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO report_versions (
                report_id, version_number, change_type, summary, report_json_snapshot, actor_user_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                version_number,
                change_type,
                summary,
                self._secure_dump(report_snapshot),
                actor_user_id,
                created_at,
            ),
        )

    def _can_view_all_reports(self, user: dict | None) -> bool:
        return bool(user and user.get("role") in {"doctor", "dietician", "admin", "compliance"})

    def add_knowledge(self, title: str, content: str, source_type: str = "admin_upload", category: str = "General", citation: str | None = None) -> dict:
        timestamp = now_iso()
        category = (category or "General").strip() or "General"
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO knowledge_documents (title, source_type, category, citation, content, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'approved', ?)
                """,
                (title, source_type, category, citation, content, timestamp),
            )
        self.upsert_knowledge_category(category)
        return {"id": cursor.lastrowid, "title": title, "source_type": source_type, "category": category, "citation": citation, "status": "approved", "created_at": timestamp}

    def list_knowledge(self) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id, title, source_type, category, citation, status, created_at FROM knowledge_documents ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_knowledge_category(self, name: str, description: str | None = None) -> dict:
        timestamp = now_iso()
        clean = (name or "General").strip() or "General"
        with connect() as conn:
            existing = conn.execute("SELECT id, name, description, created_at FROM knowledge_categories WHERE name = ?", (clean,)).fetchone()
            if existing:
                if description:
                    conn.execute("UPDATE knowledge_categories SET description = ? WHERE id = ?", (description, existing["id"]))
                    existing = {**dict(existing), "description": description}
                return dict(existing)
            cursor = conn.execute(
                "INSERT INTO knowledge_categories (name, description, created_at) VALUES (?, ?, ?)",
                (clean, description, timestamp),
            )
        return {"id": cursor.lastrowid, "name": clean, "description": description, "created_at": timestamp}

    def list_knowledge_categories(self) -> list[dict]:
        with connect() as conn:
            rows = conn.execute("SELECT id, name, description, created_at FROM knowledge_categories ORDER BY name ASC").fetchall()
        base = [dict(row) for row in rows]
        if not any(item["name"] == "General" for item in base):
            base.insert(0, {"id": None, "name": "General", "description": "Default chatbot guidance category.", "created_at": None})
        return base

    def _owns_report(self, conn, report_id: int | None, user: dict) -> bool:
        if report_id is None:
            return True
        if self._can_view_all_reports(user):
            return bool(conn.execute("SELECT id FROM reports WHERE id = ?", (report_id,)).fetchone())
        row = conn.execute(
            """
            SELECT reports.id
            FROM reports
            JOIN patient_profiles ON patient_profiles.id = reports.patient_id
            WHERE reports.id = ? AND patient_profiles.user_id = ?
            """,
            (report_id, user["id"]),
        ).fetchone()
        return bool(row)

    def ensure_chat_conversation(self, user: dict, conversation_id: int | None = None, report_id: int | None = None, title: str | None = None) -> dict | None:
        timestamp = now_iso()
        with connect() as conn:
            if conversation_id:
                row = conn.execute(
                    "SELECT * FROM chat_conversations WHERE id = ? AND user_id = ?",
                    (conversation_id, user["id"]),
                ).fetchone()
                if row:
                    return dict(row)
                return None
            if not self._owns_report(conn, report_id, user):
                report_id = None
            cursor = conn.execute(
                """
                INSERT INTO chat_conversations (user_id, report_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user["id"], report_id, (title or "HealthGuard chat")[:120], timestamp, timestamp),
            )
        return {"id": cursor.lastrowid, "user_id": user["id"], "report_id": report_id, "title": (title or "HealthGuard chat")[:120], "status": "open", "created_at": timestamp, "updated_at": timestamp}

    def save_chat_message(
        self,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        red_flags: list[str] | None = None,
        sources: list[dict] | None = None,
        doctor_consultation_required: bool = False,
        prompt_version: str | None = None,
        answer_source: str | None = None,
        generation_engine: str | None = None,
        rag_used: bool = False,
    ) -> dict:
        timestamp = now_iso()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chat_messages (
                    conversation_id, user_id, role, content, red_flags_json, sources_json,
                    doctor_consultation_required, prompt_version, answer_source, generation_engine,
                    rag_used, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    user_id,
                    role,
                    content,
                    json_dumps(red_flags or []),
                    json_dumps(sources or []),
                    1 if doctor_consultation_required else 0,
                    prompt_version,
                    answer_source,
                    generation_engine,
                    1 if rag_used else 0,
                    timestamp,
                ),
            )
            conn.execute("UPDATE chat_conversations SET updated_at = ? WHERE id = ?", (timestamp, conversation_id))
        return {"id": cursor.lastrowid, "conversation_id": conversation_id, "role": role, "content": content, "created_at": timestamp}

    def list_chat_conversations(self, user: dict, report_id: int | None = None) -> list[dict]:
        params: list[object] = [user["id"]]
        where = "WHERE user_id = ?"
        if report_id is not None:
            where += " AND report_id = ?"
            params.append(report_id)
        with connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM chat_conversations {where} ORDER BY updated_at DESC, id DESC LIMIT 20",
                tuple(params),
            ).fetchall()
        conversations = [dict(row) for row in rows]
        for item in conversations:
            item["messages"] = self.list_chat_messages(user, item["id"], limit=12)
        return conversations

    def list_chat_messages(self, user: dict, conversation_id: int, limit: int = 50) -> list[dict]:
        with connect() as conn:
            allowed = conn.execute("SELECT id FROM chat_conversations WHERE id = ? AND user_id = ?", (conversation_id, user["id"])).fetchone()
            if not allowed:
                return []
            rows = conn.execute(
                """
                SELECT id, conversation_id, role, content, red_flags_json, sources_json, doctor_consultation_required,
                    prompt_version, answer_source, generation_engine, rag_used, created_at
                FROM chat_messages
                WHERE conversation_id = ? AND user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, user["id"], limit),
            ).fetchall()
        items: list[dict] = []
        for row in reversed(rows):
            item = dict(row)
            item["red_flags"] = json_loads(item.pop("red_flags_json") or "[]")
            item["sources"] = json_loads(item.pop("sources_json") or "[]")
            item["doctor_consultation_required"] = bool(item["doctor_consultation_required"])
            item["rag_used"] = bool(item.get("rag_used"))
            items.append(item)
        return items

    def export_chat_conversation(self, user: dict, conversation_id: int) -> dict | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM chat_conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user["id"]),
            ).fetchone()
            if not row:
                return None
        item = dict(row)
        item["messages"] = self.list_chat_messages(user, conversation_id, limit=200)
        return item

    def save_chat_analytics(
        self,
        user: dict,
        conversation_id: int,
        question_text: str,
        intent: str | None,
        answer_source: str,
        prompt_version: str | None,
        latency_ms: int,
        rag_used: bool,
        unresolved: bool,
    ) -> dict:
        timestamp = now_iso()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chat_analytics (
                    user_id, conversation_id, question_text, intent, answer_source,
                    prompt_version, latency_ms, rag_used, unresolved, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    conversation_id,
                    mask_pii(question_text)[:500],
                    intent,
                    answer_source,
                    prompt_version,
                    latency_ms,
                    1 if rag_used else 0,
                    1 if unresolved else 0,
                    timestamp,
                ),
            )
        return {"id": cursor.lastrowid, "created_at": timestamp}

    def chat_analytics_summary(self, user: dict) -> dict:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT answer_source, COUNT(*) AS count
                FROM chat_analytics
                WHERE user_id = ?
                GROUP BY answer_source
                ORDER BY count DESC
                """,
                (user["id"],),
            ).fetchall()
            slow = conn.execute(
                "SELECT COUNT(*) AS count FROM chat_analytics WHERE user_id = ? AND latency_ms >= 3000",
                (user["id"],),
            ).fetchone()
            unresolved = conn.execute(
                "SELECT COUNT(*) AS count FROM chat_analytics WHERE user_id = ? AND unresolved = 1",
                (user["id"],),
            ).fetchone()
        return {
            "by_answer_source": [dict(row) for row in rows],
            "slow_responses": slow["count"] if slow else 0,
            "unresolved": unresolved["count"] if unresolved else 0,
        }

    def save_chat_feedback(self, user: dict, message_id: int, rating: str, reason: str | None = None) -> dict | None:
        timestamp = now_iso()
        with connect() as conn:
            allowed = conn.execute(
                """
                SELECT chat_messages.id
                FROM chat_messages
                JOIN chat_conversations ON chat_conversations.id = chat_messages.conversation_id
                WHERE chat_messages.id = ? AND chat_conversations.user_id = ?
                """,
                (message_id, user["id"]),
            ).fetchone()
            if not allowed:
                return None
            cursor = conn.execute(
                "INSERT INTO chat_feedback (message_id, user_id, rating, reason, created_at) VALUES (?, ?, ?, ?, ?)",
                (message_id, user["id"], rating, reason, timestamp),
            )
        return {"id": cursor.lastrowid, "message_id": message_id, "rating": rating, "reason": reason, "created_at": timestamp}

    def chat_starter_questions(self, user: dict) -> list[str]:
        starters: list[str] = [
            "What symptoms should I track before seeing a doctor?",
            "Which lifestyle risks should I prioritize this week?",
            "What questions should I ask my clinician?",
        ]
        with connect() as conn:
            doc = conn.execute(
                "SELECT title FROM rag_documents WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user["id"],),
            ).fetchone()
            report_row = conn.execute(
                """
                SELECT reports.report_json
                FROM reports
                JOIN patient_profiles ON patient_profiles.id = reports.patient_id
                WHERE patient_profiles.user_id = ?
                ORDER BY reports.id DESC
                LIMIT 1
                """,
                (user["id"],),
            ).fetchone()
        if doc:
            starters.insert(0, f"What should I understand from my uploaded document: {doc['title']}?")
        if report_row:
            report = self._secure_load(report_row["report_json"])
            for question in (report.get("suggested_questions_to_ask_doctor") or [])[:3]:
                if question not in starters:
                    starters.append(question)
        return starters[:6]

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
