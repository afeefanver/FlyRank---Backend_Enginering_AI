from pydantic import BaseModel, Field, field_validator

VALID_RATINGS = {"One", "Two", "Three", "Four", "Five"}


class Book(BaseModel):
    title: str = Field(min_length=1)
    product_url: str
    price_text: str
    price_gbp: float = Field(gt=0)
    availability_text: str
    rating_text: str
    description: str | None = None        # the only optional field
    source_page: str
    fetched_at: str

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("URL must start with https://")
        return value

    @field_validator("rating_text")
    @classmethod
    def must_be_known_rating(cls, value: str) -> str:
        if value not in VALID_RATINGS:
            raise ValueError(f"unknown rating: {value}")
        return value
