from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# xAPI Statement Models
class ActorAccount(BaseModel):
    name: str
    homePage: Optional[str] = None


class Actor(BaseModel):
    account: Optional[ActorAccount] = None
    name: Optional[str] = None


class VerbDisplay(BaseModel):
    en: Optional[str] = None


class Verb(BaseModel):
    id: str
    display: Optional[VerbDisplay] = None


class ActivityDefinition(BaseModel):
    name: Optional[Dict[str, str]] = None
    type: Optional[str] = None
    correctResponsesPattern: Optional[List[str]] = None


class ActivityObject(BaseModel):
    id: str
    objectType: Optional[str] = None
    definition: Optional[ActivityDefinition] = None


class Score(BaseModel):
    raw: Optional[float] = None
    scaled: Optional[float] = None


class Result(BaseModel):
    score: Optional[Score] = None
    success: Optional[bool] = None
    completion: Optional[bool] = None
    duration: Optional[str] = None
    response: Optional[str] = None


class ContextActivity(BaseModel):
    id: str
    objectType: Optional[str] = None
    definition: Optional[ActivityDefinition] = None


class ContextActivities(BaseModel):
    parent: Optional[List[ContextActivity]] = None
    category: Optional[List[ContextActivity]] = None
    grouping: Optional[List[ContextActivity]] = None
    other: Optional[List[ContextActivity]] = None


class Context(BaseModel):
    registration: Optional[str] = None
    contextActivities: Optional[ContextActivities] = None
    extensions: Optional[Dict[str, Any]] = None


class Statement(BaseModel):
    id: Optional[str] = None
    actor: Actor
    verb: Verb
    object: ActivityObject
    result: Optional[Result] = None
    context: Optional[Context] = None
    timestamp: Optional[str] = None
    stored: Optional[str] = None