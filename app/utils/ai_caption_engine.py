from dataclasses import dataclass
from decimal import Decimal

from app.models.product import Product
from app.schemas.caption import CaptionStyle
from app.utils.caption_prompt_templates import CAPTION_COUNT, PROMPT_TEMPLATES


@dataclass(frozen=True)
class GeneratedCaption:
    hook: str
    cta: str
    emoji: str
    hashtags: list[str]
    caption_text: str


class AICaptionEngine:
    _emojis: dict[CaptionStyle, list[str]] = {
        CaptionStyle.FUNNY: ["🤣", "😄", "😎", "🔥", "🎉"],
        CaptionStyle.REVIEW: ["⭐", "✅", "🧪", "💬", "👍"],
        CaptionStyle.PROMOTION: ["💸", "🛍️", "🎁", "📣", "💥"],
        CaptionStyle.STORYTELLING: ["📖", "✨", "💡", "🌟", "🎬"],
        CaptionStyle.URGENCY: ["⏰", "🚨", "⚡", "🔥", "🛒"],
    }

    _hooks: dict[CaptionStyle, list[str]] = {
        CaptionStyle.FUNNY: [
            "Your cart called. It wants this.",
            "This product is doing more than your group chat.",
            "Warning: friends may ask where you got this.",
            "Plot twist: this is actually affordable.",
            "One scroll, one obsession.",
        ],
        CaptionStyle.REVIEW: [
            "What buyers love most about this:",
            "Quick review before you buy:",
            "Real value in one glance:",
            "Performance check from real users:",
            "Is it worth it? Here is the verdict:",
        ],
        CaptionStyle.PROMOTION: [
            "Deal alert for smart shoppers:",
            "Best-value find today:",
            "Price dropped, quality stayed high:",
            "Promo moment you should not miss:",
            "Limited-time value unlocked:",
        ],
        CaptionStyle.STORYTELLING: [
            "It started with a small daily problem:",
            "Here is a simple before-and-after story:",
            "Someone needed an easier routine:",
            "A quick story from busy buyers:",
            "From frustration to convenience:",
        ],
        CaptionStyle.URGENCY: [
            "Fast movers are taking this now:",
            "This offer will not wait:",
            "If you are thinking about it, act now:",
            "Low hesitation, high demand:",
            "Clock is ticking on this one:",
        ],
    }

    _ctas: dict[CaptionStyle, list[str]] = {
        CaptionStyle.FUNNY: [
            "Grab yours and thank me later.",
            "Tap now before your friends do.",
            "Shop this now and enjoy the flex.",
            "Click to get yours today.",
            "Order now while it is hot.",
        ],
        CaptionStyle.REVIEW: [
            "See full details and buy here.",
            "Check it out and decide with confidence.",
            "Tap for specs, reviews, and checkout.",
            "Open the link to grab yours now.",
            "Review done. Time to shop smart.",
        ],
        CaptionStyle.PROMOTION: [
            "Claim the promo through this link now.",
            "Tap to secure this price today.",
            "Shop now while discount is active.",
            "Get yours before the deal ends.",
            "Click now and save instantly.",
        ],
        CaptionStyle.STORYTELLING: [
            "Start your own easier routine today.",
            "Tap the link and make the switch.",
            "Try it now and feel the difference.",
            "Begin your upgrade with one click.",
            "Get yours and write your own story.",
        ],
        CaptionStyle.URGENCY: [
            "Buy now before stock moves.",
            "Tap now and lock your order.",
            "Checkout now before promo closes.",
            "Act fast and secure yours today.",
            "Do not wait. Grab it now.",
        ],
    }

    _hashtags: dict[CaptionStyle, list[str]] = {
        CaptionStyle.FUNNY: ["#ShopeeFinds", "#AddToCart", "#WorthIt", "#DailyDeals", "#SmartShopping"],
        CaptionStyle.REVIEW: ["#ProductReview", "#TopRated", "#BuyerFavorite", "#ShopSmart", "#ShopeeFinds"],
        CaptionStyle.PROMOTION: ["#Promo", "#Discount", "#DealAlert", "#BestPrice", "#LimitedOffer"],
        CaptionStyle.STORYTELLING: ["#CustomerStory", "#LifestyleUpgrade", "#DailyEssential", "#ShopNow", "#Shopee"],
        CaptionStyle.URGENCY: ["#BuyNow", "#LastChance", "#HurryUp", "#FlashDeal", "#ShopeeDeals"],
    }

    def get_prompt_template(self, style: CaptionStyle) -> str:
        return PROMPT_TEMPLATES[style]

    def generate(self, product: Product, style: CaptionStyle) -> list[GeneratedCaption]:
        output: list[GeneratedCaption] = []

        for index in range(CAPTION_COUNT):
            hook = self._pick(self._hooks[style], index)
            cta = self._pick(self._ctas[style], index)
            emoji = self._pick(self._emojis[style], index)
            hashtags = self._build_hashtags(style, index)
            caption_text = self._compose_caption(product, hook, cta, emoji, hashtags)

            output.append(
                GeneratedCaption(
                    hook=hook,
                    cta=cta,
                    emoji=emoji,
                    hashtags=hashtags,
                    caption_text=caption_text,
                )
            )

        return output

    def _compose_caption(
        self,
        product: Product,
        hook: str,
        cta: str,
        emoji: str,
        hashtags: list[str],
    ) -> str:
        price = self._money(product.price)
        discount = product.discount or "Special offer"
        shop_name = product.shop_name or "trusted seller"
        core = f"{hook} {product.title} by {shop_name} now at {price} ({discount})."
        return f"{emoji} {core} {cta} {' '.join(hashtags)}"

    def _build_hashtags(self, style: CaptionStyle, index: int) -> list[str]:
        base = self._hashtags[style]
        rotated = [base[(index + shift) % len(base)] for shift in range(3)]
        return rotated

    def _pick(self, values: list[str], index: int) -> str:
        return values[index % len(values)]

    def _money(self, value: Decimal) -> str:
        return f"Rp {value:,.2f}"
