from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ai_writer import generate_application_pack, is_ai_writer_configured
from jobpilot import (
    APPLICATION_STATUSES,
    add_application,
    clean_html,
    count_jobs,
    create_daily_report,
    extract_skill_keywords,
    get_applications,
    get_jobs,
    get_profile,
    get_recent_reports,
    get_status_history,
    get_setting,
    init_db,
    parse_resume_bytes,
    refresh_sources,
    save_profile,
    save_resume_file,
    send_email,
    set_setting,
    update_application,
)

load_dotenv()
init_db()
st.set_page_config(page_title="JobPilot AI", page_icon="🧭", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.7rem; padding-bottom: 2.5rem; }
      div[data-testid="stMetric"] { border: 1px solid rgba(128,128,128,.22); padding: 12px 14px; border-radius: 12px; }
      .jobpilot-subtle { color: #6b7280; font-size: .9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

profile = get_profile()
with st.sidebar:
    st.title("🧭 JobPilot AI")
    st.caption("Your personal job discovery and application tracker")
    page = st.radio(
        "Navigation",
        ["Dashboard", "My Profile", "Discover Jobs", "Application Tracker", "Daily Report", "Settings"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Local-first starter • your resume stays on this machine unless you deploy or sync it yourself.")


def show_job_card(job: dict, key_prefix: str = "job") -> None:
    st.markdown(f"### {job['title']} — {job['company']}")
    meta = f"{job.get('location') or 'Location not specified'} · {job.get('source')} · {job.get('category', job.get('score', 0))}"
    st.caption(meta)
    score = job.get("score", 0)
    st.write(f"**Match: {score}/100 — {job.get('category', 'Unscored')}**")
    if job.get("salary"):
        st.write(f"**Salary:** {job['salary']}")
    if job.get("published_at"):
        st.caption(f"Published: {job['published_at']}")
    matched = job.get("matched_skills", [])
    if matched:
        st.write("**Matching skills:** " + ", ".join(matched[:12]))
    reasons = job.get("reasons", [])
    if reasons:
        with st.expander("Why this match? / Match breakdown"):
            st.write(" · ".join(reasons))
            if job.get("breakdown"):
                st.json(job["breakdown"])
            if job.get("missing_skills"):
                st.write("**Profile skills not seen in this listing:** " + ", ".join(job["missing_skills"][:15]))
    description = job.get("description", "")
    if description:
        st.write(description[:900] + ("…" if len(description) > 900 else ""))
    if job.get("url"):
        st.link_button("Open original job listing", job["url"])
    st.caption(f"Source: {job.get('source_attribution') or job.get('source', 'Unknown')}")

    pack_key = f"application_pack_{job.get('id', 'unknown')}"
    if is_ai_writer_configured():
        if st.button("Generate AI application pack", key=f"{key_prefix}_ai_{job.get('id')}"):
            try:
                with st.spinner("Generating a truthful role-specific draft…"):
                    st.session_state[pack_key] = generate_application_pack(get_profile(), job)
            except Exception as exc:
                st.error(f"Could not generate the application pack: {exc}")
        if st.session_state.get(pack_key):
            pack_text = st.session_state[pack_key]
            with st.expander("Review AI-generated application pack", expanded=True):
                st.warning("Review every statement before using it. This action sends the resume text and job description to the configured OpenAI API.")
                st.text_area("Application pack", value=pack_text, height=420, key=f"pack_text_{job.get('id')}")
                st.download_button(
                    "Download application pack",
                    data=pack_text,
                    file_name=f"jobpilot_application_pack_{job.get('id', 'job')}.txt",
                    mime="text/plain",
                    key=f"download_pack_{job.get('id')}",
                )
    elif job.get("id"):
        st.caption("Optional AI resume/cover-letter generation is available after configuring OPENAI_API_KEY.")

    if job.get("id"):
        from jobpilot import get_applications
        already = any(a.get("job_id") == job.get("id") for a in get_applications())
        if already:
            st.info("This job is already in your application tracker.")
        else:
            default_status = "Awaiting Approval" if get_setting("application_mode", "Manual Review") == "Approval Required" else "Shortlisted"
            if st.button("Add to application tracker", key=f"{key_prefix}_track_{job['id']}", type="primary"):
                created = add_application(int(job["id"]), default_status)
                if created:
                    st.success(f"Added to tracker as {default_status}.")
                    st.rerun()
                else:
                    st.info("This job is already being tracked.")


if page == "Dashboard":
    st.title("Good day" + (f", {profile.get('full_name').split()[0]}" if profile.get("full_name") else "") + " 👋")
    st.write("Your job search overview, based on data recorded in JobPilot AI.")
    applications = get_applications()
    statuses = [a["status"] for a in applications]
    today = datetime.now().date().isoformat()
    todays_history = [h for h in get_status_history() if h.get("changed_at", "")[:10] == today]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Saved job listings", count_jobs())
    c2.metric("Tracked applications", len(applications))
    c3.metric("Submitted", statuses.count("Submitted"))
    c4.metric("Status changes today", len(todays_history))
    st.divider()
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Application pipeline")
        if applications:
            summary = pd.DataFrame({"Status": APPLICATION_STATUSES})
            counts = pd.Series(statuses).value_counts()
            summary["Count"] = summary["Status"].map(counts).fillna(0).astype(int)
            summary = summary[summary["Count"] > 0]
            st.bar_chart(summary.set_index("Status"))
        else:
            st.info("Start by completing your profile, then discover jobs and add relevant roles to your tracker.")
    with right:
        st.subheader("Quick actions")
        if st.button("Refresh public job feeds", use_container_width=True):
            with st.spinner("Checking job sources…"):
                outcomes = refresh_sources()
            for source, result in outcomes.items():
                (st.success if result.get("ok") else st.warning)(f"{source}: {result['message']}")
        if st.button("Generate today's report", use_container_width=True):
            report = create_daily_report()
            st.session_state["latest_report"] = report["content"]
            st.success("Daily report generated from saved records.")
        st.caption("Public-feed refreshes are rate-limited and use cached listings when possible.")
    st.subheader("Recent applications")
    if applications:
        df = pd.DataFrame(applications[:8])
        cols = [c for c in ["company", "title", "location", "match_score", "status", "updated_at"] if c in df.columns]
        st.dataframe(df[cols].rename(columns={"company": "Company", "title": "Role", "location": "Location", "match_score": "Match", "status": "Status", "updated_at": "Last updated"}), use_container_width=True, hide_index=True)
    else:
        st.caption("No applications tracked yet.")

elif page == "My Profile":
    st.title("My Profile & Resume")
    st.write("Add accurate profile information. Match scores depend on the information you save here.")
    with st.form("profile_form"):
        name = st.text_input("Full name", value=profile.get("full_name", ""))
        email = st.text_input("Email", value=profile.get("email", ""))
        phone = st.text_input("Phone (optional)", value=profile.get("phone", ""))
        skills = st.text_area("Skills (comma-separated)", value=profile.get("skills", ""), help="Example: Python, SQL, PostgreSQL, Azure, troubleshooting")
        experience = st.number_input("Total relevant experience (years)", min_value=0.0, max_value=60.0, value=float(profile.get("experience_years") or 0), step=0.5)
        education = st.text_area("Education / qualifications", value=profile.get("education", ""))
        roles = st.text_area("Target job titles (comma-separated)", value=profile.get("target_roles", ""), help="Example: Python Developer, Data Analyst, Azure Database Support Engineer")
        location = st.text_input("Preferred location", value=profile.get("preferred_location", "Hyderabad, India"))
        remote_only = st.checkbox("Remote jobs only", value=bool(profile.get("remote_only")))
        employment_types = st.text_input("Employment types", value=profile.get("employment_types", "Full-time"))
        uploaded_resume = st.file_uploader("Upload resume (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])
        st.caption("Resume text is extracted locally. This starter does not send your resume to an LLM service.")
        submitted = st.form_submit_button("Save profile", type="primary")
    if submitted:
        resume_text = profile.get("resume_text", "")
        resume_path = profile.get("resume_path", "")
        if uploaded_resume is not None:
            try:
                file_bytes = uploaded_resume.getvalue()
                resume_text = parse_resume_bytes(uploaded_resume.name, file_bytes)
                resume_path = save_resume_file(uploaded_resume.name, file_bytes)
            except Exception as exc:
                st.error(f"Could not read the resume: {exc}")
                st.stop()
        new_profile = {
            "full_name": name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "experience_years": experience,
            "education": education,
            "target_roles": roles,
            "preferred_location": location,
            "remote_only": remote_only,
            "employment_types": employment_types,
            "resume_text": resume_text,
            "resume_path": resume_path,
        }
        save_profile(new_profile)
        st.success("Profile saved.")
        st.rerun()
    current_profile = get_profile()
    if current_profile.get("resume_text"):
        with st.expander("View extracted resume text"):
            st.text(current_profile["resume_text"][:15000])
            if len(current_profile["resume_text"]) > 15000:
                st.caption("Text display truncated; the saved text remains intact.")
        inferred = extract_skill_keywords(current_profile["resume_text"])
        st.write("**Skill keywords detected in resume:** " + (", ".join(inferred) if inferred else "No known keywords detected. Add skills manually to improve matching."))

elif page == "Discover Jobs":
    st.title("Discover Jobs")
    st.write("Search saved listings and refresh supported public feeds. Every card links to the original source.")
    with st.expander("Search sources and limitations", expanded=True):
        col1, col2 = st.columns(2)
        use_remotive = col1.checkbox("Remotive (remote roles)", value=True)
        use_arbeitnow = col2.checkbox("Arbeitnow (international listings)", value=True)
        st.caption("This MVP does not scrape LinkedIn, Naukri, Indeed, or Glassdoor. Add authorized APIs/connectors for those platforms.")
        if st.button("Refresh selected job sources", type="primary"):
            selected = (["Remotive"] if use_remotive else []) + (["Arbeitnow"] if use_arbeitnow else [])
            if not selected:
                st.warning("Select at least one source.")
            else:
                with st.spinner("Fetching public job listings…"):
                    outcomes = refresh_sources(selected)
                for source, result in outcomes.items():
                    (st.success if result.get("ok") else st.warning)(f"{source}: {result['message']}")
    default_query = ", ".join([x.strip() for x in profile.get("target_roles", "").split(",")[:1] if x.strip()])
    col1, col2, col3 = st.columns([2, 1, 1])
    query = col1.text_input("Filter listings by keyword", value=default_query, placeholder="Python, SQL, support engineer…")
    min_score = col2.slider("Minimum match score", min_value=0, max_value=100, value=int(get_setting("min_match_score", "60")), step=5)
    source_filter = col3.selectbox("Source", ["All", "Remotive", "Arbeitnow"])
    sources = None if source_filter == "All" else [source_filter]
    jobs = get_jobs(search=query, min_score=min_score, sources=sources)
    st.caption(f"Showing {len(jobs)} matching saved listings out of {count_jobs()} stored listings.")
    if not profile.get("skills") and not profile.get("resume_text"):
        st.warning("Complete your profile and add skills to improve job matching.")
    if not jobs:
        st.info("No matching stored jobs. Refresh a source above, or broaden your keyword/score filters.")
    for job in jobs[:100]:
        with st.container(border=True):
            show_job_card(job, "discover")

elif page == "Application Tracker":
    st.title("Application Tracker")
    st.write("Track the application lifecycle, notes, evidence, and follow-up dates in one place.")
    col1, col2 = st.columns([1, 2])
    status_filter = col1.selectbox("Filter by status", ["All"] + APPLICATION_STATUSES)
    search = col2.text_input("Search company, role, or location")
    applications = get_applications(status_filter=status_filter, search=search)
    st.caption(f"{len(applications)} tracked application(s)")
    if applications:
        table = pd.DataFrame(applications)
        view_cols = [c for c in ["company", "title", "location", "match_score", "status", "created_at", "updated_at"] if c in table.columns]
        st.dataframe(table[view_cols].rename(columns={"company": "Company", "title": "Role", "location": "Location", "match_score": "Match", "status": "Status", "created_at": "Added", "updated_at": "Last updated"}), use_container_width=True, hide_index=True)
        st.divider()
        for app in applications:
            with st.expander(f"{app['company']} — {app['title']} · {app['status']}"):
                st.caption(f"Match score: {app['match_score']}/100 · Source: {app['source']}")
                st.link_button("Open original application page", app["url"])
                st.caption("Open the site, complete/submit its form yourself, then update the status here. This MVP does not falsely report a submission.")
                with st.form(f"app_form_{app['id']}"):
                    status = st.selectbox("Status", APPLICATION_STATUSES, index=APPLICATION_STATUSES.index(app["status"]), key=f"status_{app['id']}")
                    notes = st.text_area("Notes", value=app.get("notes", ""), key=f"notes_{app['id']}")
                    next_action = st.text_input("Next action", value=app.get("next_action", ""), key=f"next_{app['id']}")
                    follow_up = st.text_input("Follow-up date (YYYY-MM-DD)", value=app.get("follow_up_date", ""), key=f"follow_{app['id']}")
                    evidence = st.text_input("Confirmation evidence / reference", value=app.get("confirmation_evidence", ""), key=f"evidence_{app['id']}", help="Optional: confirmation number or a note about the email/portal evidence.")
                    save = st.form_submit_button("Save application update", type="primary")
                if save:
                    if status == "Submitted" and not evidence.strip():
                        st.warning("Add a confirmation reference or a brief note about how you confirmed submission. Save again to proceed.")
                        st.stop()
                    update_application(app["id"], status, notes, next_action, follow_up, evidence)
                    st.success("Application record updated; status history saved.")
                    st.rerun()
    else:
        st.info("No applications match the selected filters. Add jobs from Discover Jobs to get started.")
    with st.expander("Recent status history"):
        history = get_status_history()
        if history:
            history_df = pd.DataFrame(history[:50])
            columns = [c for c in ["changed_at", "company", "title", "previous_status", "new_status", "source", "evidence"] if c in history_df.columns]
            st.dataframe(history_df[columns], use_container_width=True, hide_index=True)
        else:
            st.caption("No status history available yet.")

elif page == "Daily Report":
    st.title("Daily Job Search Report")
    st.write("Reports summarize records in this app. They do not infer unseen employer-side status changes.")
    if st.button("Generate report now", type="primary"):
        report = create_daily_report()
        st.session_state["latest_report"] = report["content"]
    latest = st.session_state.get("latest_report")
    if latest:
        st.text_area("Generated report", value=latest, height=450)
        st.download_button("Download report as TXT", data=latest, file_name=f"jobpilot_report_{datetime.now().date()}.txt", mime="text/plain")
        if st.button("Email this report using .env SMTP settings"):
            try:
                send_email(f"JobPilot AI Daily Report — {datetime.now().date()}", latest)
                st.success("Report email sent.")
            except Exception as exc:
                st.error(str(exc))
    st.subheader("Previous reports")
    reports = get_recent_reports()
    if reports:
        for report in reports:
            with st.expander(f"{report['report_date']} · created {report['created_at']} · {'emailed' if report.get('sent_at') else 'not marked sent'}"):
                st.text(report["content"])
    else:
        st.caption("No reports generated yet.")

elif page == "Settings":
    st.title("Settings & Integrations")
    st.subheader("Matching preferences")
    with st.form("settings_form"):
        current_min = int(get_setting("min_match_score", "60"))
        minimum = st.slider("Default minimum match score", min_value=0, max_value=100, value=current_min, step=5)
        mode = st.selectbox("Application workflow", ["Manual Review", "Approval Required"], index=0 if get_setting("application_mode", "Manual Review") == "Manual Review" else 1)
        daily_limit = st.number_input("Daily application planning limit", min_value=1, max_value=100, value=int(get_setting("daily_limit", "10")))
        save_settings = st.form_submit_button("Save settings", type="primary")
    if save_settings:
        set_setting("min_match_score", str(minimum))
        set_setting("application_mode", mode)
        set_setting("daily_limit", str(daily_limit))
        st.success("Settings saved.")
    st.info("Auto-Apply is not enabled in this starter. Applying automatically requires platform-specific, permitted integrations and verified submission evidence. Manual Review and Approval Required are supported as tracking workflows.")
    st.subheader("Configured public job feeds")
    st.markdown("- **Remotive:** public remote-job feed; listings must retain their original Remotive link and attribution. The feed may be delayed and should not be polled too frequently. [Source documentation](https://github.com/remotive-io/remote-jobs-api)")
    st.markdown("- **Arbeitnow:** public job-board feed; this app filters saved results locally. [Job board API](https://www.arbeitnow.com/api/job-board-api)")
    st.subheader("Optional AI document generation")
    ai_ready = bool(os.getenv("OPENAI_API_KEY", ""))
    st.write("AI document generation: " + ("configured" if ai_ready else "not configured"))
    st.caption("When you explicitly click Generate AI application pack, your resume text and selected job description are sent to the OpenAI API. Review generated materials for accuracy.")
    st.code("OPENAI_API_KEY=your-api-key\nOPENAI_MODEL=gpt-4.1-mini", language="dotenv")
    st.subheader("Email configuration")
    st.write("Configure SMTP settings in a local `.env` file; do not paste passwords into this page.")
    email_ready = all(os.getenv(name) for name in ["SMTP_HOST", "SMTP_FROM", "REPORT_EMAIL_TO"])
    st.write("Email readiness: " + ("configured" if email_ready else "not configured"))
    st.code("""SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@example.com
REPORT_EMAIL_TO=you@example.com""", language="dotenv")
    st.caption("The app is a single-user local MVP. Before public deployment, add authentication, authorization, encrypted private storage, secrets management, and tenant isolation.")
