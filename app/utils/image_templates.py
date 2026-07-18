from dataclasses import dataclass

from app.schemas.image import ImageTemplate


@dataclass(frozen=True)
class TemplateStyle:
    background_start: tuple[int, int, int]
    background_end: tuple[int, int, int]
    accent: tuple[int, int, int]
    text_primary: tuple[int, int, int]
    text_secondary: tuple[int, int, int]


TEMPLATE_STYLES: dict[ImageTemplate, TemplateStyle] = {
    ImageTemplate.CLASSIC: TemplateStyle(
        background_start=(18, 32, 56),
        background_end=(32, 57, 92),
        accent=(255, 170, 0),
        text_primary=(255, 255, 255),
        text_secondary=(210, 221, 238),
    ),
    ImageTemplate.BOLD: TemplateStyle(
        background_start=(74, 10, 10),
        background_end=(148, 24, 24),
        accent=(255, 214, 10),
        text_primary=(255, 255, 255),
        text_secondary=(255, 232, 200),
    ),
    ImageTemplate.MINIMAL: TemplateStyle(
        background_start=(238, 242, 247),
        background_end=(223, 231, 241),
        accent=(20, 100, 180),
        text_primary=(24, 32, 42),
        text_secondary=(74, 88, 104),
    ),
}
