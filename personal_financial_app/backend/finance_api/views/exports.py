"""API views for CSV/PDF export of financial records."""
import csv

from django.db.models import Sum
from django.http import HttpResponse
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiTypes

from ..models import FinancialRecord
from ..services.filters import apply_filters_to_queryset

# PDF Report Generation Imports (ReportLab)
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


@extend_schema(
    responses={200: OpenApiTypes.OBJECT},
    description='Generates a downloadable CSV extract of the filtered financial records.',
)
class ExportCSVView(APIView):
    """
    API endpoint that generates a downloadable CSV extract.
    Adheres to the active user filters to allow exporting custom views.
    """
    def get(self, request, *args, **kwargs):
        # Query this user's records and apply current active filters
        records = FinancialRecord.objects.filter(owner=request.user)
        records = apply_filters_to_queryset(request, records)

        # Construct CSV HTTP response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="financial_bank_extract.csv"'

        writer = csv.writer(response)
        # Write headers
        writer.writerow(['ID', 'Type', 'Category', 'Amount', 'Date', 'Bank Account', 'Description', 'Created At'])

        # Write record values
        for record in records:
            writer.writerow([
                record.id,
                record.type.capitalize(),
                record.category,
                record.amount,
                record.date,
                record.account_bank,
                record.description or '',
                record.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

        return response


@extend_schema(
    responses={200: OpenApiTypes.OBJECT},
    description='Generates a downloadable PDF statement of the filtered financial records (totals + ledger table).',
)
class ExportPDFView(APIView):
    """
    API endpoint that builds a beautiful PDF extract statement.
    Features detailed summaries (Total Incomes, Total Expenses, Balance)
    and a clean, structured ledger table utilizing ReportLab.
    """
    def get(self, request, *args, **kwargs):
        # Retrieve and filter this user's record queryset
        records = FinancialRecord.objects.filter(owner=request.user)
        records = apply_filters_to_queryset(request, records)

        # Calculate totals for the summary box
        total_income = records.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0.00
        total_expense = records.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0.00
        net_balance = total_income - total_expense

        # Set up PDF Response headers
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="financial_bank_extract.pdf"'

        # Build Document
        doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        # Styles Setup
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor('#1e293b'), # Dark Slate
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#64748b'), # Cool Grey
            spaceAfter=20
        )
        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.HexColor('#334155'),
            spaceAfter=8,
            spaceBefore=15
        )
        summary_text_style = ParagraphStyle(
            'SummaryText',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.HexColor('#1e293b')
        )
        cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#334155')
        )

        # Title and Subtitle Header
        story.append(Paragraph("Personal Financial Statement", title_style))
        story.append(Paragraph("Official Bank Account Extract & Transaction Ledger", subtitle_style))
        story.append(Spacer(1, 10))

        # Financial Summary Section Box
        balance_color = '#10b981' if net_balance >= 0 else '#ef4444' # Green or Red
        summary_data = [
            [
                Paragraph(f"<b>Total Incomes:</b> <font color='#10b981'>${total_income:,.2f}</font>", summary_text_style),
                Paragraph(f"<b>Total Expenses:</b> <font color='#ef4444'>${total_expense:,.2f}</font>", summary_text_style),
                Paragraph(f"<b>Net Balance:</b> <font color='{balance_color}'>${net_balance:,.2f}</font>", summary_text_style)
            ]
        ]

        summary_table = Table(summary_data, colWidths=[180, 180, 180])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')), # Light background slate
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 12),
            ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1'))
        ]))
        story.append(Paragraph("Statement Summary", heading_style))
        story.append(summary_table)
        story.append(Spacer(1, 15))

        # Detailed Transaction Ledger Table
        story.append(Paragraph("Detailed Transaction Ledger", heading_style))

        table_headers = ['Date', 'Type', 'Category', 'Bank Account', 'Description', 'Amount']
        table_data = [table_headers]

        for record in records:
            amt_prefix = "+" if record.type == 'income' else "-"
            amt_color = '#10b981' if record.type == 'income' else '#ef4444'

            table_data.append([
                record.date.strftime('%Y-%m-%d'),
                record.type.capitalize(),
                record.category,
                record.account_bank,
                record.description or '-',
                Paragraph(f"<font color='{amt_color}'><b>{amt_prefix}${record.amount:,.2f}</b></font>", cell_style)
            ])

        # Table Layout Config
        col_widths = [75, 55, 100, 105, 125, 80]
        ledger_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Grid, padding, and text-styling config
        ledger_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')), # Slate header
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ALIGN', (-1,1), (-1,-1), 'RIGHT'), # Align amounts to right
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ]

        # Alternating background colors for rows
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                ledger_style.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#f8fafc')))

        ledger_table.setStyle(TableStyle(ledger_style))
        story.append(ledger_table)

        # Build PDF
        doc.build(story)
        return response