from pydantic import BaseModel, Field, HttpUrl


class AsoRequest(BaseModel):
    app_link: HttpUrl
    app_name: str = Field(min_length=2)
    category: str = Field(min_length=2)
    primary_keyword: str = Field(min_length=2)
    secondary_keywords: list[str] = Field(default_factory=list)
    locales: list[str] = Field(default_factory=lambda: ["en-US"])


class LocaleMetadata(BaseModel):
    locale: str
    title_variants: list[str] = Field(default_factory=list)
    subtitle: str
    keyword_field: str
    short_description: str


class ReviewResponseTemplate(BaseModel):
    sentiment: str
    response_template: str


class AsoResponse(BaseModel):
    platform: str
    metadata: list[LocaleMetadata]
    review_response_playbook: list[ReviewResponseTemplate]
    optimization_notes: list[str]
