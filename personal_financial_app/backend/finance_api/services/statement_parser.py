"""Statement PDF parsing: extraction of transactions from bank statement PDFs."""
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException
from django.utils import timezone

from .categorization import suggest_category
from .statement_detection import detect_statement_info
from ..models.snapshots import DailyUserSnapshot


def process_statement(statement, password=None, user=None):
    """Extract transactions from a PDF and persist them for review.

    Marks the statement as failed/review_pending. Designed to be called
    without raising; errors are stored on the statement record.
    """
    try:
        transactions, detected = extract_transactions_from_pdf(statement.file.path, password, user)
    except Exception as e:
        statement.status = 'failed'
        statement.error_message = f'Failed to extract transactions: {str(e)}'
        statement.processed_at = timezone.now()
        statement.save()
        return

    # Auto-detect statement type and bank, without overriding manual choices
    if statement.statement_type == 'other' and detected['statement_type'] != 'other':
        statement.statement_type = detected['statement_type']
    if not statement.bank_name and detected['bank_name']:
        statement.bank_name = detected['bank_name']

    statement.extracted_transactions.all().delete()
    for txn_data in transactions:
        statement.extracted_transactions.create(**txn_data)

    statement.total_transactions_extracted = len(transactions)
    statement.status = 'review_pending'
    statement.processed_at = timezone.now()
    statement.save()

    return transactions


def extract_transactions_from_pdf(pdf_path, password=None, user=None):
    """Extract transaction data from PDF using pdfplumber.

    Returns (transactions, detected_info) where detected_info comes from
    detect_statement_info() over all page text.
    """
    transactions = []
    corpus_parts = []

    try:
        # Open PDF with optional password
        with pdfplumber.open(pdf_path, password=password) as pdf:
            # If password is wrong or required but not provided, this will raise
            # pdfplumber.exceptions.PdfminerException
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                corpus_parts.append(text)

                # Try to extract table data first
                tables = page.extract_tables()
                for table in tables:
                    extracted = parse_transaction_table(table, user=user)
                    transactions.extend(extracted)

                # If no tables found, try text parsing
                if not tables:
                    extracted = parse_transaction_text(text, user=user)
                    transactions.extend(extracted)
    except PdfminerException as e:
        error_str = str(e)
        wrapped = e.args[0] if e.args else None
        is_password_error = (
            (wrapped and type(wrapped).__name__ == 'PDFPasswordIncorrect') or
            'PDFPasswordIncorrect' in error_str or
            'password' in error_str.lower()
        )
        if is_password_error:
            if password:
                raise Exception('Incorrect password provided for PDF.')
            else:
                raise Exception('PDF is password protected. Please provide the password.')
        raise Exception(f'Failed to parse PDF: {error_str}')
    except Exception as e:
        raise Exception(f'Failed to process PDF: {str(e)}')

    # Deduplicate transactions
    detected = detect_statement_info('\n'.join(corpus_parts))
    return deduplicate_transactions(transactions), detected


def parse_transaction_table(table, user=None):
    """Parse transactions from extracted table."""
    transactions = []

    # Find header row
    header_keywords = ['date', 'description', 'amount', 'debit', 'credit', 'balance',
                      'fecha', 'descripci', 'concepto', 'importe', 'cargo', 'abono', 'saldo',
                      'retiro', 'deposito', 'movimiento']
    header_row = None
    for i, row in enumerate(table):
        if row and any(cell and any(keyword in str(cell).lower() for keyword in
            header_keywords) for cell in row):
            header_row = i
            break

    if header_row is None:
        return transactions

    headers = [str(cell).lower().strip() if cell else '' for cell in table[header_row]]

    # Map column indices
    date_idx = find_column(headers, ['date', 'transaction date', 'trans date',
                                      'fecha', 'fecha de transacci'])
    desc_idx = find_column(headers, ['description', 'details', 'memo', 'particulars',
                                      'descripci', 'concepto', 'detalle'])
    amount_idx = find_column(headers, ['amount', 'transaction amount',
                                        'importe', 'monto', 'cantidad'])
    debit_idx = find_column(headers, ['debit', 'withdrawal', 'dr',
                                       'cargo', 'retiro', 'debito'])
    credit_idx = find_column(headers, ['credit', 'deposit', 'cr',
                                        'abono', 'deposito', 'credito'])
    balance_idx = find_column(headers, ['balance', 'running balance',
                                          'saldo'])

    for row in table[header_row + 1:]:
        if not row or len(row) <= max(filter(lambda x: x is not None,
            [date_idx, desc_idx, amount_idx, debit_idx, credit_idx, balance_idx])):
            continue

        try:
            txn = parse_table_row(row, date_idx, desc_idx, amount_idx,
                                 debit_idx, credit_idx, balance_idx, user=user)
            if txn:
                transactions.append(txn)
        except Exception:
            continue

    return transactions


def find_column(headers, keywords):
    for i, header in enumerate(headers):
        if any(kw in header for kw in keywords):
            return i
    return None


def parse_table_row(row, date_idx, desc_idx, amount_idx, debit_idx, credit_idx, balance_idx, user=None):
    """Parse a single table row into transaction data."""
    date_str = row[date_idx] if date_idx is not None else None
    desc = row[desc_idx] if desc_idx is not None else None

    if not date_str or not desc:
        return None

    # Parse date
    date = parse_date(date_str)
    if not date:
        return None

    # Parse amount
    amount = 0
    txn_type = 'unknown'

    if amount_idx is not None and row[amount_idx]:
        amount = parse_amount(row[amount_idx])
        # Determine type from separate debit/credit columns
        if debit_idx is not None and row[debit_idx] and parse_amount(row[debit_idx]) > 0:
            txn_type = 'expense'
        elif credit_idx is not None and row[credit_idx] and parse_amount(row[credit_idx]) > 0:
            txn_type = 'income'
    elif debit_idx is not None and row[debit_idx]:
        amount = parse_amount(row[debit_idx])
        txn_type = 'expense'
    elif credit_idx is not None and row[credit_idx]:
        amount = parse_amount(row[credit_idx])
        txn_type = 'income'

    if amount == 0:
        return None

    # Determine type from amount sign if not determined
    if txn_type == 'unknown':
        txn_type = 'income' if amount > 0 else 'expense'
        amount = abs(amount)

    # Calculate usd_amount using user's active DailyUserSnapshot rates
    usd_amount = Decimal('0')
    if user is not None:
        try:
            snapshot = DailyUserSnapshot.objects.filter(
                user=user,
                snapshot_date__lte=timezone.now().date()
            ).latest('snapshot_date')
            # rates are USD-relative: rate["COP"] = how many COP per 1 USD
            rates = snapshot.rates
        except DailyUserSnapshot.DoesNotExist:
            rates = {}

    return {
        'raw_description': str(desc).strip(),
        'cleaned_description': clean_description(str(desc).strip()),
        'amount': Decimal(str(amount)),
        'date': date,
        'transaction_type': txn_type,
        'suggested_category': suggest_category(str(desc).strip()),
        'confidence_score': 0.5,
        'needs_review': True,
        'usd_amount': usd_amount,
    }


def parse_transaction_text(text, user=None):
    """Parse transactions from raw text (fallback)."""
    transactions = []
    lines = text.split('\n')

    # Common patterns for bank statements
    patterns = [
        # Date - Description - Amount pattern
        r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s+(.+?)\s+([\-\+]?\$?[\d.,]+)',
        # Description - Date - Amount
        r'(.+?)\s+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s+([\-\+]?\$?[\d.,]+)',
        # Spanish DD mmm Description +-$amount (no year on line)
        r'(\d{1,2})\s+(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\s+(.+?)\s+([\-\+]?\$?[\d.,]+)',
    ]

    for line in lines:
        line = line.strip()
        if len(line) < 10:
            continue

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) == 4:
                    date_str = f"{groups[0]} {groups[1]}"
                    desc = groups[2]
                    amount_str = groups[3]
                elif len(groups) >= 3:
                    date_str, desc, amount_str = groups[0], groups[1], groups[2]
                else:
                    continue

                date = parse_date(date_str)
                amount = parse_amount(amount_str)

                if date and amount != 0:
                    txn_type = 'income' if amount > 0 else 'expense'
                    usd_amount = Decimal('0')
                    if user is not None:
                        try:
                            snapshot = DailyUserSnapshot.objects.filter(
                                user=user,
                                snapshot_date__lte=timezone.now().date()
                            ).latest('snapshot_date')
                            rates = snapshot.rates
                        except DailyUserSnapshot.DoesNotExist:
                            rates = {}

                    transactions.append({
                        'raw_description': desc.strip(),
                        'cleaned_description': clean_description(desc.strip()),
                        'amount': Decimal(str(abs(amount))),
                        'date': date,
                        'transaction_type': txn_type,
                        'suggested_category': suggest_category(desc.strip()),
                        'confidence_score': 0.4,
                        'needs_review': True,
                        'usd_amount': usd_amount,
                    })
                    break

    return transactions


def parse_date(date_str):
    """Parse date from various formats."""
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # Map Spanish month names to English for strptime compatibility
    spanish_months = {
        'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr',
        'may': 'May', 'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug',
        'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dic': 'Dec',
        'enero': 'January', 'febrero': 'February', 'marzo': 'March',
        'abril': 'April', 'mayo': 'May', 'junio': 'June',
        'julio': 'July', 'agosto': 'August', 'septiembre': 'September',
        'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December',
    }
    for es, en in spanish_months.items():
        date_str = re.sub(rf'\b{es}\b', en, date_str, flags=re.IGNORECASE)

    formats = [
        '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y',
        '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y',
        '%b %d, %Y', '%B %d, %Y', '%d %b %Y', '%d %B %Y',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # Try day + month abbreviation without year (e.g. "1 Jan"), default to current year
    try:
        dt = datetime.strptime(date_str, '%d %b')
        return dt.date().replace(year=datetime.now().year)
    except ValueError:
        pass

    try:
        dt = datetime.strptime(date_str, '%b %d')
        return dt.date().replace(year=datetime.now().year)
    except ValueError:
        pass

    return None


def parse_amount(amount_str):
    """Parse amount from string, handling US and Latin American formats."""
    if not amount_str:
        return 0

    amount_str = str(amount_str).strip()
    amount_str = amount_str.replace('$', '').replace('(', '-').replace(')', '')

    # Detect Latin American format (. thousands, , decimal) vs US format
    if ',' in amount_str:
        amount_str = amount_str.replace('.', '').replace(',', '.')
    else:
        amount_str = amount_str.replace(',', '')

    try:
        return float(amount_str)
    except ValueError:
        return 0


def clean_description(desc):
    """Clean and normalize transaction description."""
    # Remove extra whitespace
    desc = re.sub(r'\s+', ' ', desc)
    # Remove common noise
    desc = re.sub(r'\b(DEBIT|CREDIT|CARD|PURCHASE|PAYMENT|WITHDRAWAL|DEPOSIT)\b', '', desc, flags=re.IGNORECASE)
    # Remove trailing/leading special chars
    desc = desc.strip(' -*.')
    return desc[:255]


def deduplicate_transactions(transactions):
    """Remove duplicate transactions based on date, amount, and description."""
    seen = set()
    unique = []

    for txn in transactions:
        key = (txn['date'], txn['amount'], txn['cleaned_description'][:50])
        if key not in seen:
            seen.add(key)
            unique.append(txn)

    return unique