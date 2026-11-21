from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.clients.model_client import decision_model


class RiskAssessment(BaseModel):
    keep_confidence_pct: int = Field(
        ge=0, le=100,
        description="Estimated probability (0-100) the customer keeps this purchase "
        "rather than returning it.",
    )
    risk_category: str = Field(description="One of: low, medium, high")
    rationale: str = Field(
        description="One sentence citing the specific policy/history signal driving this score."
    )


_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a return-risk model for an online retailer. Score the "
            "likelihood this customer keeps (does not return) the item they're "
            "asking about, using ONLY the customer profile, category statistics, "
            "and policy context given. Cite the specific signal driving your "
            "score in the rationale.",
        ),
        (
            "human",
            "Customer profile: {persona_summary}\n"
            "Category stats: {category_stats}\n"
            "Policy context:\n{policy_context}\n"
            "Customer message: {message}\n"
            "Note already drafted for the customer: {draft}",
        ),
    ]
)


def decide(state: dict) -> dict:
    policy_context = "\n\n".join(d["content"] for d in state["retrieved_docs"])
    chain = _PROMPT | decision_model(RiskAssessment)
    result: RiskAssessment = chain.invoke(
        {
            "persona_summary": state["persona_summary"],
            "category_stats": state["category_stats"],
            "policy_context": policy_context,
            "message": state["message"],
            "draft": state["draft"],
        }
    )
    return {"decision": result.model_dump()}
