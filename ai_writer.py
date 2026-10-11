"""Optional OpenAI-powered application-document generation.

The user's resume text and the selected job description are sent to the configured
OpenAI API only after the user explicitly clicks the generation button.
"""
from __future__ import annotations

import os


def is_ai_writer_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def generate_application_pack(profile: dict, job: dict) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in your local .env file to use AI document generation.")

    # Import only when the user requests this optional feature.
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    resume_text = (profile.get("resume_text") or "").strip()
    skills = profile.get("skills", "")
    if not resume_text and not skills:
        raise RuntimeError("Upload a resume or add skills in My Profile first.")

    prompt = f"""
Create a truthful, role-specific application pack using only the candidate facts below.
Do not invent employers, job titles, dates, degrees, certifications, metrics, skills,
responsibilities, achievements, work authorization, or project outcomes. If information
is missing, omit it or mark it [ADD VERIFIED DETAIL]. Do not claim the candidate has
experience that is mentioned only in the job description.

Return these sections in plain text:
1. ROLE FIT SUMMARY (brief, including gaps worth reviewing)
2. TAILORED RESUME DRAFT (reorder and clarify existing facts, preserve factual meaning)
3. COVER LETTER (professional, concise, role-specific)
4. APPLICATION QUESTIONS TO VERIFY (list only questions that need candidate confirmation)

CANDIDATE PROFILE
Name: {profile.get('full_name', '')}
Education: {profile.get('education', '')}
Skills entered by candidate: {skills}
Relevant years of experience: {profile.get('experience_years', 0)}
Preferred roles: {profile.get('target_roles', '')}
Resume text (treat as factual source; never add unsupported claims):
{resume_text[:14000]}

JOB LISTING
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Salary: {job.get('salary', '')}
Source: {job.get('source', '')}
Original URL: {job.get('url', '')}
Description:
{(job.get('description') or '')[:7000]}

Keep the document useful and readable. Do not include private contact information unless it
appears in the candidate resume/profile. The user must review this output before using it.
""".strip()

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "You help candidates prepare truthful job applications. Follow the user's facts and never fabricate credentials."},
            {"role": "user", "content": prompt},
        ],
    )
    output = getattr(response, "output_text", "")
    if not output:
        raise RuntimeError("The AI provider returned no text. Try again or choose a supported model in .env.")
    return output.strip()
