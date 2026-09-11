"""
LLM service for generating personalized outreach emails.

Uses Google's Gemini API (free tier) to generate emails based on
enriched prospect data. The prompt template is designed to produce
relevant, non-spammy outreach that references specific details
about the prospect's company.

Gemini free tier: 500 requests/day on Flash models — more than
enough for development and demos.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def _build_prompt(prospect_data: dict, tone: str, context: str | None, our_product: str) -> str:
    prospect_info_lines = [f"Company: {prospect_data.get('company_name', 'Unknown')}"]

    if prospect_data.get("domain"):
        prospect_info_lines.append(f"Website: {prospect_data['domain']}")
    if prospect_data.get("contact_name"):
        prospect_info_lines.append(f"Contact: {prospect_data['contact_name']}")
    if prospect_data.get("contact_role"):
        prospect_info_lines.append(f"Role: {prospect_data['contact_role']}")
    if prospect_data.get("company_description"):
        prospect_info_lines.append(f"About: {prospect_data['company_description']}")
    if prospect_data.get("industry"):
        prospect_info_lines.append(f"Industry: {prospect_data['industry']}")
    if prospect_data.get("employee_count"):
        prospect_info_lines.append(f"Size: {prospect_data['employee_count']} employees")
    if prospect_data.get("funding_stage"):
        prospect_info_lines.append(f"Funding: {prospect_data['funding_stage']}")
    if prospect_data.get("technologies"):
        prospect_info_lines.append(f"Tech stack: {prospect_data['technologies']}")

    prospect_info = "\n".join(prospect_info_lines)
    context_line = f"\nAdditional context: {context}" if context else ""

    prompt = f"""You are a B2B outreach specialist writing a cold email to a potential customer.

PROSPECT INFORMATION:
{prospect_info}
{context_line}

OUR PRODUCT:
{our_product}

REQUIREMENTS:
- Tone: {tone}
- The email must reference at least ONE specific detail about their company (not generic)
- Keep the subject line under 60 characters
- Keep the email body under 250 words
- Include a clear, low-friction call to action (e.g., "15-minute call" not "buy our product")
- Do NOT use clichéd openers like "I hope this email finds you well"
- Do NOT be pushy or salesy — be helpful and relevant

Respond in this exact JSON format and nothing else:
{{
    "subject": "your subject line here",
    "body": "your email body here"
}}

Return ONLY valid JSON, no markdown, no code blocks, no extra text."""

    return prompt


async def generate_email(
    prospect_data: dict,
    tone: str = "professional",
    context: str | None = None,
    our_product: str = "CodeRound AI - AI-powered technical interview platform"
) -> dict:
    prompt = _build_prompt(prospect_data, tone, context, our_product)

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or not GEMINI_AVAILABLE:
        return _mock_generate(prospect_data, tone)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        if "subject" not in result or "body" not in result:
            raise ValueError("LLM response missing 'subject' or 'body' fields")

        return result

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}")


def _mock_generate(prospect_data: dict, tone: str) -> dict:
    company = prospect_data.get("company_name", "your company")
    contact = prospect_data.get("contact_name", "there")
    industry = prospect_data.get("industry", "tech")

    first_name = contact.split()[0] if contact and contact != "there" else "Hi"

    subject = f"Cutting your {company} interview cycle from weeks to days"

    industry_mention = f" in the {industry} space" if industry else ""

    body = f"""Hi {first_name},

I noticed {company} is growing{industry_mention} — congrats on the momentum.

One challenge fast-growing teams hit: technical hiring becomes a bottleneck. Engineering managers spend 8-10 hours/week on first-round interviews that could be automated.

We built CodeRound AI to solve exactly this. Our platform runs AI-powered first-round technical interviews, and our customers are seeing a 6:1 interview-to-offer ratio with a 7-day hire cycle.

Would a 15-minute call next week make sense to see if this fits {company}'s hiring workflow?

Best,
[Your name]"""

    return {"subject": subject, "body": body}