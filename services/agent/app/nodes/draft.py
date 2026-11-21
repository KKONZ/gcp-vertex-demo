from langchain_core.prompts import ChatPromptTemplate

from app.clients.model_client import drafting_model

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a shopping assistant for an online retailer. Write a short, "
            "friendly 2-3 sentence note to the customer about the item they're "
            "asking about, grounded ONLY in the policy context and order history "
            "given below. Do not invent statistics that aren't present in the "
            "context.",
        ),
        (
            "human",
            "Customer profile: {persona_summary}\n\n"
            "Category: {category}\n"
            "Category stats: {category_stats}\n\n"
            "Policy context:\n{policy_context}\n\n"
            "Customer message: {message}",
        ),
    ]
)


def draft(state: dict) -> dict:
    policy_context = "\n\n".join(d["content"] for d in state["retrieved_docs"])
    chain = _PROMPT | drafting_model()
    result = chain.invoke(
        {
            "persona_summary": state["persona_summary"],
            "category": state["category"],
            "category_stats": state["category_stats"],
            "policy_context": policy_context,
            "message": state["message"],
        }
    )
    return {"draft": result.content}
