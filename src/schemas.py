from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field



#__________________________________Idea Parsing_________________________________


class Constraints(BaseModel):
    budget: Optional[str] = Field(
        default=None, description="Budget constraint, e.g. 'bootstrapped', '$5k', 'unlimited'"
    )
    timeline: Optional[str] = Field(
        default=None, description="Timeline constraint, e.g. '3 months', 'ASAP'"
    )
    team_size: Optional[int] = Field(
        default=None, description="Number of people available to build this"
    )


class TechnicalMaturity(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ParsedIdea(BaseModel):
    raw_text: str = Field(description="The original idea text as submitted by the user")
    domain: str = Field(description="Primary domain/industry, e.g. 'healthtech', 'e-commerce'")
    scale: str = Field(description="Intended scale, e.g. 'personal project', 'startup MVP', 'enterprise'")
    constraints: Constraints = Field(default_factory=Constraints)
    technical_maturity: TechnicalMaturity = Field(
        description="Estimated technical maturity required or assumed by the idea"
    )
    summary: str = Field(description="One or two sentence normalized summary of the idea")



#__________________________________Plan_________________________________________


class PlanPhase(BaseModel):
    name: str = Field(description="Phase name, e.g. 'Discovery', 'MVP Build'")
    description: str = Field(description="What happens in this phase")
    steps: list[str] = Field(description="High-level implementation steps within this phase")


class ProjectPlan(BaseModel):
    overview: str = Field(description="High-level summary of the overall approach")
    phases: list[PlanPhase] = Field(description="Ordered list of project phases")
    reasoning: Optional[str] = Field(
        default=None, description="Chain-of-thought / rationale behind the plan structure"
    )


#______________________________Tools (RAG)______________________________________


class ToolRecommendation(BaseModel):
    name: str = Field(description="Tool or library name")
    description: str = Field(description="Short description of what the tool does")
    justification: str = Field(description="Why this tool fits the parsed idea")
    rank: int = Field(description="1 = most recommended, higher numbers = lower priority")



#_________________________________Risks_________________________________________

class RiskCategory(str, Enum):
    TECHNICAL = "technical"
    DATA = "data"
    SCOPE = "scope"
    TIMELINE = "timeline"
    TEAM = "team"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskAssessment(BaseModel):
    category: RiskCategory
    description: str = Field(description="What the risk is")
    severity: RiskSeverity
    mitigation: str = Field(description="Suggested mitigation strategy")



#_______________________________ Roadmap________________________________________


class Milestone(BaseModel):
    label: str = Field(description="Milestone name, e.g. 'MVP Launch'")
    timeframe: str = Field(description="e.g. 'Week 2', 'Month 1'")
    deliverables: list[str] = Field(description="What's done by this milestone")


class Roadmap(BaseModel):
    milestones: list[Milestone]



# ___________________________Bundled Output_____________________________________


class ConsultantOutput(BaseModel):
    parsed_idea: ParsedIdea
    plan: ProjectPlan
    tools: list[ToolRecommendation]
    risks: list[RiskAssessment]
    roadmap: Roadmap
