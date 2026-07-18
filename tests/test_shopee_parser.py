from decimal import Decimal

from app.utils.shopee_parser import ShopeeProductParser


def test_parse_shopee_product_from_state_blob() -> None:
    html = """
    <html><head></head><body>
      <script>
        window.__INITIAL_STATE__ = {
          "item": {
            "name": "Wireless Mouse",
            "price": 12990000,
            "price_before_discount": 19990000,
            "discount": "35%",
            "historical_sold": 120,
            "item_rating": {"rating_star": 4.8},
            "images": ["abc123", "def456"],
            "shop": {"name": "Mouse Hub"},
            "category": "Computer Accessories"
          }
        };
      </script>
    </body></html>
    """

    parser = ShopeeProductParser(timeout_seconds=1.0, html_fetcher=lambda _: html)

    payload = parser.parse("https://shopee.co.id/wireless-mouse")

    assert payload.title == "Wireless Mouse"
    assert payload.price == Decimal("129.90")
    assert payload.original_price == Decimal("199.90")
    assert payload.discount == "35%"
    assert payload.rating == 4.8
    assert payload.sold_count == 120
    assert payload.shop_name == "Mouse Hub"
    assert payload.category == "Computer Accessories"
    assert len(payload.images) == 2
    assert payload.affiliate_url == "https://shopee.co.id/wireless-mouse"
