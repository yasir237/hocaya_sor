from enum import Enum


class FeedbackTypeEnum(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"