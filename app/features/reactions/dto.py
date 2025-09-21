"""Data Transfer Objects for the reactions feature."""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ReactOnceInput:
    """Input for creating a single reaction."""

    post_id: int
    user_id: int
    reaction_type: str

    def __post_init__(self) -> None:
        """Validate input data."""
        if self.post_id <= 0:
            raise ValueError("post_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if not self.reaction_type or not self.reaction_type.strip():
            raise ValueError("reaction_type cannot be empty")


@dataclass(frozen=True)
class ReactOnceResult:
    """Result of a reaction creation attempt."""

    created: bool
    reaction_type: str
    message: Optional[str] = None

    @classmethod
    def success(cls, reaction_type: str) -> "ReactOnceResult":
        """Create a successful reaction result."""
        return cls(created=True, reaction_type=reaction_type, message="Reaction saved!")

    @classmethod
    def already_exists(cls, reaction_type: str) -> "ReactOnceResult":
        """Create a result for when user already reacted."""
        message = f"You've already reacted with {reaction_type}. Reactions are permanent and cannot be changed!"
        return cls(created=False, reaction_type=reaction_type, message=message)


@dataclass(frozen=True)
class ReactionData:
    """Data about a single reaction."""

    post_id: int
    user_id: int
    reaction_type: str
    created_at: datetime


@dataclass(frozen=True)
class ReactionCount:
    """Count of reactions by type for a post."""

    reaction_type: str
    count: int


@dataclass(frozen=True)
class PostReactionsData:
    """All reaction data for a post."""

    post_id: int
    reaction_counts: List[ReactionCount]
    user_reaction: Optional[str] = None  # Current user's reaction type, if any
    total_reactions: int = 0

    def __post_init__(self) -> None:
        """Calculate total reactions from counts."""
        if self.total_reactions == 0:
            # Calculate total from counts if not provided
            object.__setattr__(self, "total_reactions", sum(rc.count for rc in self.reaction_counts))


@dataclass(frozen=True)
class GetReactionsInput:
    """Input for getting reactions for posts."""

    post_ids: List[int]
    user_id: Optional[int] = None  # If provided, include user's reactions

    def __post_init__(self) -> None:
        """Validate input data."""
        if not self.post_ids:
            raise ValueError("post_ids cannot be empty")
        if any(pid <= 0 for pid in self.post_ids):
            raise ValueError("All post_ids must be positive")


@dataclass(frozen=True)
class GetReactionsResult:
    """Result of getting reactions for multiple posts."""

    reactions_by_post: Dict[int, PostReactionsData]

    def get_post_reactions(self, post_id: int) -> PostReactionsData:
        """Get reactions for a specific post."""
        return self.reactions_by_post.get(
            post_id, PostReactionsData(post_id=post_id, reaction_counts=[], total_reactions=0)
        )