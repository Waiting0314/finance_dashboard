from django.db import models

class Stock(models.Model):
    MARKET_CHOICES = [
        ('US', '美股'),
        ('TW', '台股'),
    ]
    ticker = models.CharField(max_length=15, unique=True, help_text="股票代號，例如：2330.TW")
    name = models.CharField(max_length=100, blank=True, help_text="公司名稱")
    market = models.CharField(max_length=2, choices=MARKET_CHOICES, default='US', help_text="市場別")
    description = models.TextField(blank=True, help_text="公司簡介")
    sector = models.CharField(max_length=50, blank=True, help_text="產業類別")
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="本益比")
    eps = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="每股盈餘")

    # New Financial Indicators
    short_name = models.CharField(max_length=50, blank=True, help_text="中文簡稱")
    beta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="貝塔值 (風險係數)")
    market_cap = models.BigIntegerField(null=True, blank=True, help_text="市值")
    dividend_yield = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="殖利率")
    
    # Prifitability
    roe = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="股東權益報酬率")
    roa = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="資產報酬率")
    gross_margin = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="毛利率")
    operating_margin = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="營業利益率")
    profit_margin = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="淨利率")
    
    # Solvency & Structure
    debt_to_equity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="負債權益比")
    quick_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="速動比率")
    
    # Valuation
    price_to_book = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="股價淨值比")
    
    # Cash Flow
    free_cash_flow = models.BigIntegerField(null=True, blank=True, help_text="自由現金流")
    
    # Financial Data
    last_revenue = models.BigIntegerField(null=True, blank=True, help_text="營收")
    next_earnings_date = models.DateTimeField(null=True, blank=True, help_text="下次財報日期")

    # Real-time Stats (Updated on fetch)
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="最新成交價")
    change = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="漲跌額")
    change_percent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="漲跌幅 (%)")

    def __str__(self):
        return f"{self.name} ({self.ticker})"

    class Meta:
        ordering = ['ticker']

from django.conf import settings

class StockPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='prices')
    date = models.DateField()
    open = models.DecimalField(max_digits=10, decimal_places=2)
    high = models.DecimalField(max_digits=10, decimal_places=2)
    low = models.DecimalField(max_digits=10, decimal_places=2)
    close = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField()

    def __str__(self):
        return f"{self.stock.ticker} on {self.date}"

    class Meta:
        # Ensure that for a given stock, a date can only appear once.
        unique_together = ('stock', 'date')
        ordering = ['-date']

class Watchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='watchers')

    def __str__(self):
        return f"{self.user.username}'s watchlist: {self.stock.ticker}"

    class Meta:
        unique_together = ('user', 'stock')