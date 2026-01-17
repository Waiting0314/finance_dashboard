from django import template

register = template.Library()

@register.filter
def format_revenue(value):
    """
    Formats large numbers into abbreviated form:
    1,234,567,890,000 -> 1.2T
    1,234,567,890 -> 1.2B
    1,234,567 -> 1.2M
    """
    if value is None:
        return "--"
    try:
        num = float(value)
        abs_num = abs(num)
        sign = "-" if num < 0 else ""

        if abs_num >= 1_000_000_000_000:
            return f"{sign}{abs_num / 1_000_000_000_000:.1f}兆"
        elif abs_num >= 1_000_000_000:
            return f"{sign}{abs_num / 1_000_000_000:.0f}億"
        elif abs_num >= 1_000_000:
            return f"{sign}{abs_num / 1_000_000:.0f}百萬"
        else:
            return f"{num:.0f}"
    except (ValueError, TypeError):
        return str(value)

@register.filter
def percentage(value, decimals=2):
    """
    將小數轉換為百分比格式 (例如: 0.15 -> 15.00%)
    """
    if value is None or value == "":
        return "-"
    try:
        val = float(value)
        return f"{val * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return value
