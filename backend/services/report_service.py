"""Report service for PDF generation."""

import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from sqlalchemy.orm import Session

from backend.repositories.report_repo import ReportRepository
from backend.utils.file_storage import ensure_directory


class ReportService:
    """Service for report generation."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ReportRepository(db)

    def generate_report(
        self,
        case_id: int,
        report_type: str = "full",
        include_evidence: bool = True,
        include_timeline: bool = True,
        include_deleted: bool = True,
        include_correlations: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a PDF report.

        Args:
            case_id: The case ID
            report_type: Type of report (full, evidence, timeline, deleted, summary)
            include_evidence: Include evidence section
            include_timeline: Include timeline section
            include_deleted: Include deleted messages section
            include_correlations: Include correlation section

        Returns:
            Dict with report_id, status, and file_path
        """
        report_id = str(uuid.uuid4())

        # Get case info
        from backend.models.models import Case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"error": "Case not found", "status": "failed"}

        # Create reports directory
        reports_dir = os.path.join(os.getcwd(), "reports", str(case_id))
        ensure_directory(reports_dir)

        filename = f"report_{case_id}_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(reports_dir, filename)

        try:
            # Generate PDF
            self._create_pdf(
                filepath=filepath,
                case_id=case_id,
                case_name=case.name,
                case_description=case.description or "",
                report_type=report_type,
                include_evidence=include_evidence,
                include_timeline=include_timeline,
                include_deleted=include_deleted,
                include_correlations=include_correlations,
            )

            from backend.services.log_service import get_log_service
            log_service = get_log_service(self.db)
            log_service.log_activity(
                case_id=case_id,
                action="export_report",
                description=f"Generated court-ready PDF report ({report_type}): {filename}"
            )
            self.db.commit()

            return {
                "report_id": report_id,
                "case_id": case_id,
                "status": "completed",
                "file_path": filepath,
                "filename": filename,
            }
        except Exception as e:
            return {
                "report_id": report_id,
                "status": "failed",
                "error": str(e),
            }

    def _create_pdf(
        self,
        filepath: str,
        case_id: int,
        case_name: str,
        case_description: str,
        report_type: str,
        include_evidence: bool,
        include_timeline: bool,
        include_deleted: bool,
        include_correlations: bool,
    ) -> None:
        """Create the PDF document."""
        doc = SimpleDocTemplate(filepath, pagesize=letter,
                               rightMargin=0.75*inch, leftMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
        )
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=12,
        )

        elements = []

        # Title Page
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("Forensic Analysis Report", title_style))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"<b>Case:</b> {case_name}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"<b>Case ID:</b> {case_id}", styles['Normal']))
        if case_description:
            elements.append(Paragraph(f"<b>Description:</b> {case_description}", styles['Normal']))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"<b>Report Type:</b> {report_type.title()}", styles['Normal']))
        elements.append(PageBreak())

        # Executive Summary
        elements.append(Paragraph("Executive Summary", heading_style))
        summary = self._get_executive_summary(case_id)
        elements.append(Paragraph(f"This report contains the analysis of case <b>{case_name}</b>.", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # Summary statistics table
        if summary:
            summary_data = [
                ["Metric", "Count"],
                ["Total Messages", str(summary.get("total_messages", 0))],
                ["Total Contacts", str(summary.get("total_contacts", 0))],
                ["Total Media Files", str(summary.get("total_media", 0))],
                ["Total Groups", str(summary.get("total_groups", 0))],
            ]
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(summary_table)
        elements.append(PageBreak())

        # Evidence Section
        if include_evidence and report_type in ["full", "evidence"]:
            elements.append(Paragraph("Evidence Analysis", heading_style))
            evidence_data = self.repo.get_evidence_data(case_id)

            elements.append(Paragraph(f"Total Evidence Files: {evidence_data.get('total_evidence_files', 0)}", styles['Normal']))
            elements.append(Paragraph(f"Total Extracted Files: {evidence_data.get('total_extracted_files', 0)}", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

            # Evidence breakdown
            breakdown = evidence_data.get("evidence_breakdown", {})
            if breakdown:
                elements.append(Paragraph("Evidence Breakdown:", subheading_style))
                for ev_type, count in breakdown.items():
                    elements.append(Paragraph(f"• {ev_type}: {count}", styles['Normal']))

            # Media summary
            media = evidence_data.get("media_summary", {})
            if media:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph("Media Summary:", subheading_style))
                elements.append(Paragraph(f"• Total Media: {media.get('total', 0)}", styles['Normal']))
                elements.append(Paragraph(f"  - Images: {media.get('images', 0)}", styles['Normal']))
                elements.append(Paragraph(f"  - Videos: {media.get('videos', 0)}", styles['Normal']))
                elements.append(Paragraph(f"  - Audio: {media.get('audio', 0)}", styles['Normal']))
                elements.append(Paragraph(f"  - Documents: {media.get('documents', 0)}", styles['Normal']))

            # Apps found
            apps = evidence_data.get("apps_found", [])
            if apps:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph(f"Applications Analyzed: {', '.join(apps)}", styles['Normal']))

            elements.append(PageBreak())

        # Timeline Section
        if include_timeline and report_type in ["full", "timeline"]:
            elements.append(Paragraph("Timeline Analysis", heading_style))
            timeline_data = self.repo.get_timeline_data(case_id)

            elements.append(Paragraph(f"Total Timeline Events: {timeline_data.get('total_events', 0)}", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

            # Events by app
            by_app = timeline_data.get("events_by_app", {})
            if by_app:
                elements.append(Paragraph("Events by Application:", subheading_style))
                for app, count in by_app.items():
                    elements.append(Paragraph(f"• {app.title()}: {count}", styles['Normal']))

            # Events by type
            by_type = timeline_data.get("events_by_type", {})
            if by_type:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph("Events by Type:", subheading_style))
                for event_type, count in list(by_type.items())[:10]:
                    elements.append(Paragraph(f"• {event_type}: {count}", styles['Normal']))

            elements.append(PageBreak())

        # Deleted Messages Section
        if include_deleted and report_type in ["full", "deleted"]:
            elements.append(Paragraph("Deleted Message Analysis", heading_style))
            deleted_data = self.repo.get_deleted_data(case_id)

            elements.append(Paragraph(f"Total Detected Deletions: {deleted_data.get('total_deletions', 0)}", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

            elements.append(Paragraph("Deletions by Application:", subheading_style))
            elements.append(Paragraph(f"• WhatsApp: {deleted_data.get('whatsapp_deletions', 0)}", styles['Normal']))
            elements.append(Paragraph(f"• Telegram: {deleted_data.get('telegram_deletions', 0)}", styles['Normal']))

            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("Confidence Levels:", subheading_style))
            elements.append(Paragraph(f"• High Confidence (≥80%): {deleted_data.get('high_confidence_count', 0)}", styles['Normal']))
            elements.append(Paragraph(f"• Medium Confidence (50-80%): {deleted_data.get('medium_confidence_count', 0)}", styles['Normal']))
            elements.append(Paragraph(f"• Low Confidence (<50%): {deleted_data.get('low_confidence_count', 0)}", styles['Normal']))

            elements.append(PageBreak())

        # Correlation Section
        if include_correlations and report_type in ["full", "summary"]:
            elements.append(Paragraph("Evidence Correlation", heading_style))
            corr_data = self.repo.get_correlation_data(case_id)

            elements.append(Paragraph(f"Total Correlation Links: {corr_data.get('total_edges', 0)}", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("Correlation Breakdown:", subheading_style))
            elements.append(Paragraph(f"• Message → Contact Links: {corr_data.get('message_contact_links', 0)}", styles['Normal']))
            elements.append(Paragraph(f"• Message → Media Links: {corr_data.get('message_media_links', 0)}", styles['Normal']))
            elements.append(Paragraph(f"• Cross-App Links: {corr_data.get('cross_app_links', 0)}", styles['Normal']))

        # Build PDF
        doc.build(elements)

    def _get_executive_summary(self, case_id: int) -> Dict[str, Any]:
        """Get executive summary data."""
        stats = self.repo.get_case_statistics(case_id)
        corr = self.repo.get_correlation_data(case_id)
        return stats

    def get_evidence_summary(self, case_id: int) -> Dict[str, Any]:
        """Get evidence summary without PDF."""
        return self.repo.get_evidence_summary(case_id)

    def get_timeline_summary(self, case_id: int) -> Dict[str, Any]:
        """Get timeline summary without PDF."""
        return self.repo.get_timeline_summary(case_id)

    def get_deleted_summary(self, case_id: int) -> Dict[str, Any]:
        """Get deleted messages summary without PDF."""
        return self.repo.get_deleted_summary(case_id)


def get_report_service(db: Session) -> ReportService:
    """Factory function to create ReportService."""
    return ReportService(db)