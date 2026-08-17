"""Statement type and bank identification from extracted PDF text."""
import re

BANK_KEYWORDS = [
    ('Nu Colombia', ['nu colombia', 'cuenta nu', 'banco nu', 'nu s.a', 'nu s.a.']),
    ('Nequi', ['nequi']),
    ('Bancolombia', ['bancolombia']),
    ('Davivienda', ['davivienda']),
    ('Daviplata', ['daviplata']),
    ('BBVA', ['bbva']),
    ('Banco de Bogotá', ['banco de bogot']),
    ('Banco Itaú', ['itaú', 'itau']),
    ('Scotiabank', ['scotiabank', 'colpatria']),
    ('Banco Caja Social', ['caja social']),
    ('Banco AV Villas', ['av villas']),
    ('Banco Popular', ['banco popular']),
    ('Banco Agrario', ['banco agrario']),
]

_TYPE_RULES = [
    ('credit_card', [
        'estado de cuenta de tarjeta', 'estado de cuenta tarjeta',
        'cuota de manejo', 'crédito disponible', 'credito disponible',
        'pago minimo', 'pago mínimo', 'payment due date', 'credit card statement',
    ]),
    ('loan', [
        'préstamo', 'prestamo', 'hipoteca', 'mortgage', 'amortizac',
        'tabla de amortización', 'tabla de amortizacion', 'cuota del prestamo',
        'cuota del préstamo',
    ]),
    ('investment', [
        'inversi', 'portafolio', 'portfolio', 'fondo de inversión',
        'fondo de inversion', 'participaciones', 'valor de la cuota',
        'rendimiento de la inversión',
    ]),
    ('checking', [
        'cuenta corriente', 'checking', 'chequera', 'cuenta de cheques',
        'cheques', 'libreta de cheques',
    ]),
    ('savings', [
        'cuenta de ahorro', 'cuenta de ahorros', 'cuenta ahorro',
        'cuenta de ahorro nu', 'ahorr', 'savings', 'cuenta nu',
    ]),
]


def _keyword_hits(corpus, keywords):
    """Return the first keyword found, using word boundaries for short tokens."""
    for kw in keywords:
        if len(kw) >= 5:
            if kw in corpus:
                return kw
        elif re.search(rf'\b{re.escape(kw)}\b', corpus):
            return kw
    return None


def detect_statement_info(text):
    """Detect the statement type and bank name from PDF text.

    Returns {'statement_type': <one of savings/checking/credit_card/loan/
    investment/other>, 'bank_name': <canonical name or ''>}.
    """
    corpus = re.sub(r'\s+', ' ', (text or '').lower())

    bank_name = ''
    for name, keywords in BANK_KEYWORDS:
        if _keyword_hits(corpus, keywords):
            bank_name = name
            break

    statement_type = 'other'
    for stype, keywords in _TYPE_RULES:
        if _keyword_hits(corpus, keywords):
            statement_type = stype
            break

    return {'statement_type': statement_type, 'bank_name': bank_name}