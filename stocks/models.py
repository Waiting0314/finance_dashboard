from django.db import models

class Stock(models.Model):
    ticker = models.CharField(max_length=10, unique=True, help_text="股票代號，例如：2330.TW")
    name = models.CharField(max_length=50, blank=True, help_text="公司名稱")

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