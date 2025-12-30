from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any, Literal, TypedDict
from datetime import datetime


class DocumentChunk(BaseModel):
    """Represents a chunk of document content"""
    doc_id: str = Field(description="Document identifier")
    content: str = Field(description="The actual text content")
    metadata: Dict[str, Any] = Field(default_factory=lambda: dict, description="Additional metadata")
    relevance_score: float = Field(default=0.0, description="Relevance score for retrieval")


class AnswerResponse(BaseModel):
    """Structured response for Q&A tasks"""
    question: str = Field(description="Question text")
    answer: str = Field(description="The generated answer")
    sources: List[str] = Field(default_factory=lambda: list, description="List of sources")
    confidence: float = Field(le=1.0, ge=0.0, description="Confidence score of the answer")
    timestamp: datetime = Field(default_factory=datetime.now)

    @model_validator(mode='after')
    def validate_sources_with_confidence(self):
        """Enforce non-empty sources when confidence is high (>= 0.7)"""
        if self.confidence >= 0.7 and not self.sources:
            raise ValueError(
                f"Sources cannot be empty when confidence is high ({self.confidence}). "
                "Please provide at least one source to support the high confidence claim."
            )
        return self


class SummarizationResponse(BaseModel):
    """Structured response for summarization tasks"""
    original_length: int = Field(description="Length of original text")
    summary: str = Field(description="The generated summary")
    key_points: List[str] = Field(description="List of key points extracted")
    document_ids: List[str] = Field(default_factory=lambda: list, description="Documents summarized")
    timestamp: datetime = Field(default_factory=datetime.now)


class CalculationResponse(BaseModel):
    """Structured response for calculation tasks"""
    expression: str = Field(description="The mathematical expression")
    result: float = Field(description="The calculated result")
    explanation: str = Field(description="Step-by-step explanation")
    units: Optional[str] = Field(default=None, description="Units if applicable")
    timestamp: datetime = Field(default_factory=datetime.now)


class UpdateMemoryResponse(BaseModel):
    """Response after updating memory"""
    summary: str = Field(description="Summary of the conversation up to this point")
    document_ids: List[str] = Field(default_factory=lambda: list, description="List of documents ids that are relevant to the users last message")


class UserIntent(BaseModel):
    """User intent classification"""
    intent_type: Literal["qa", "summarization", "calculation", "unknown"] = Field(description="Type of user intent")
    confidence: float = Field(le=1.0, ge=0.0, description="Confidence score of the intent classification")
    reasoning: str = Field(description="Explanation of how the intent was determined")


class SessionState(BaseModel):
    """Session state"""
    session_id: str
    user_id: str
    conversation_history: List[TypedDict] = Field(default_factory=lambda: list)
    document_context: List[str] = Field(default_factory=lambda: list, description="Active document IDs")
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
