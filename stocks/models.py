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
    
    # 財務警示訊息
    alert_message = models.TextField(blank=True, help_text="財務指標異常警示訊息")

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

class StockNews(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='news')
    title = models.CharField(max_length=500)
    link = models.URLField(max_length=1000)
    publisher = models.CharField(max_length=100, blank=True, null=True)
    pub_date = models.DateTimeField(db_index=True)
    sentiment = models.CharField(max_length=20, default='neutral') # positive, negative, neutral
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pub_date']
        indexes = [
            models.Index(fields=['stock', '-pub_date']),
        ]

    def __str__(self):
        return f"{self.stock.ticker} - {self.title[:30]}"


class StockRevenue(models.Model):
    """
    月營收資料（主要用於台股）
    支援多資料來源驗證
    """
    DATA_SOURCE_CHOICES = [
        ('finmind', 'FinMind'),
        ('mops', 'MOPS 公開資訊站'),
        ('twse', 'TWSE 證交所'),
    ]
    
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='revenues')
    date = models.DateField(help_text="資料日期")
    year = models.IntegerField(help_text="營收年份")
    month = models.IntegerField(help_text="營收月份")
    revenue = models.BigIntegerField(help_text="營收金額（元）")
    yoy_growth = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="年增率")
    mom_growth = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="月增率")
    data_source = models.CharField(max_length=20, choices=DATA_SOURCE_CHOICES, default='finmind')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('stock', 'year', 'month', 'data_source')
        ordering = ['-year', '-month']
        indexes = [
            models.Index(fields=['stock', '-year', '-month']),
        ]

    def __str__(self):
        return f"{self.stock.ticker} {self.year}/{self.month} 營收: {self.revenue}"


class FinancialStatement(models.Model):
    """
    財務報表資料（損益表、資產負債表等）
    """
    PERIOD_CHOICES = [
        ('Q1', '第一季'),
        ('Q2', '第二季'),
        ('Q3', '第三季'),
        ('Q4', '第四季'),
        ('FY', '全年'),
    ]
    
    DATA_SOURCE_CHOICES = [
        ('finmind', 'FinMind'),
        ('mops', 'MOPS 公開資訊站'),
        ('yfinance', 'Yahoo Finance'),
        ('sec_edgar', 'SEC EDGAR'),
        ('alpha_vantage', 'Alpha Vantage'),
    ]
    
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='financial_statements')
    date = models.DateField(help_text="報表期間結束日")
    year = models.IntegerField(help_text="報表年份")
    period = models.CharField(max_length=2, choices=PERIOD_CHOICES, help_text="報表期間")
    
    # 損益表項目
    revenue = models.BigIntegerField(null=True, blank=True, help_text="營業收入")
    gross_profit = models.BigIntegerField(null=True, blank=True, help_text="營業毛利")
    operating_income = models.BigIntegerField(null=True, blank=True, help_text="營業利益")
    net_income = models.BigIntegerField(null=True, blank=True, help_text="本期淨利")
    eps = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="每股盈餘")
    
    data_source = models.CharField(max_length=20, choices=DATA_SOURCE_CHOICES, default='finmind')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('stock', 'year', 'period', 'data_source')
        ordering = ['-year', '-period']
        indexes = [
            models.Index(fields=['stock', '-year', '-period']),
        ]

    def __str__(self):
        return f"{self.stock.ticker} {self.year} {self.period}"


class StockIndicator(models.Model):
    """
    股票指標資料（領先/落後指標）
    用於儲存時間序列指標數據
    """
    INDICATOR_TYPE_CHOICES = [
        ('leading', '領先指標'),
        ('lagging', '落後指標'),
    ]
    
    DATA_SOURCE_CHOICES = [
        ('finmind', 'FinMind'),
        ('twse', 'TWSE 證交所'),
        ('yfinance', 'Yahoo Finance'),
        ('sec_edgar', 'SEC EDGAR'),
        ('alpha_vantage', 'Alpha Vantage'),
    ]
    
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='indicators')
    date = models.DateField(help_text="資料日期")
    indicator_type = models.CharField(max_length=10, choices=INDICATOR_TYPE_CHOICES, help_text="指標類型")
    name = models.CharField(max_length=50, help_text="指標名稱（如 PE, PB, 融資餘額）")
    value = models.DecimalField(max_digits=20, decimal_places=4, help_text="指標數值")
    data_source = models.CharField(max_length=20, choices=DATA_SOURCE_CHOICES, default='finmind')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('stock', 'date', 'name', 'data_source')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['stock', 'name', '-date']),
        ]

    def __str__(self):
        return f"{self.stock.ticker} {self.date} {self.name}: {self.value}"