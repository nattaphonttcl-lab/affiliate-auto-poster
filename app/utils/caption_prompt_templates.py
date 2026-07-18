from app.schemas.caption import CaptionStyle

CAPTION_COUNT = 10

PROMPT_TEMPLATES: dict[CaptionStyle, str] = {
    CaptionStyle.FUNNY: (
        "You are a witty social media copywriter. Create short, playful Facebook captions for {title} "
        "in category {category} from {shop_name}. Keep value clear, add a light joke, and end with a direct CTA."
    ),
    CaptionStyle.REVIEW: (
        "You are a trusted reviewer voice. Create evidence-driven Facebook captions for {title}, highlighting "
        "rating {rating}, sold count {sold_count}, and practical benefits. End with a confident CTA."
    ),
    CaptionStyle.PROMOTION: (
        "You are a performance marketer. Create conversion-focused Facebook captions for {title} with price {price}, "
        "original price {original_price}, discount {discount}, and affiliate URL {affiliate_url}. End with a clear CTA."
    ),
    CaptionStyle.STORYTELLING: (
        "You are a storyteller for social commerce. Build mini story arcs around {title} and a customer challenge, "
        "then show product win and a final CTA to buy via {affiliate_url}."
    ),
    CaptionStyle.URGENCY: (
        "You are a direct-response copywriter. Create urgency-based Facebook captions for {title} using scarcity "
        "signals from sold count {sold_count}, discount {discount}, and fast action CTA."
    ),
}
