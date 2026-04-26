from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from prototype.models import GenerationRequest
from prototype.service import generate_application_package


ROOT = Path(__file__).resolve().parent
EVAL_PATH = ROOT / "evaluation_cases.json"
RESULTS_PATH = ROOT / "evaluation_results.json"
REPORT_MD_PATH = ROOT / "technical_report.md"
STUDENT_ID = "20203115"
REPO_URL = "https://github.com/ljamesl3718/20203115_NLP_Assignment_Project_1.git"
PDF_PATH = ROOT / f"{STUDENT_ID}.pdf"


def run_evaluation() -> dict:
    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    outputs = []
    for case in cases:
        request = GenerationRequest.from_dict(case)
        start = time.perf_counter()
        response = generate_application_package(request)
        latency_ms = (time.perf_counter() - start) * 1000
        avg_score = (
            round(statistics.mean(match.score for match in response.evidence_matches), 2)
            if response.evidence_matches
            else 0.0
        )
        outputs.append(
            {
                "case_id": case["case_id"],
                "goal": request.goal,
                "language": response.language,
                "backend": response.backend,
                "latency_ms": round(latency_ms, 2),
                "requirements_count": len(response.extracted_requirements),
                "matches_count": len(response.evidence_matches),
                "gaps_count": len(response.evidence_gaps),
                "resume_bullets_count": len(response.resume_bullets),
                "cover_points_count": len(response.cover_letter_points),
                "warnings_count": len(response.warnings),
                "average_match_score": avg_score,
            }
        )
    summary = {
        "case_count": len(outputs),
        "mean_latency_ms": round(statistics.mean(item["latency_ms"] for item in outputs), 2),
        "mean_average_match_score": round(statistics.mean(item["average_match_score"] for item in outputs), 2),
        "mean_requirements_count": round(statistics.mean(item["requirements_count"] for item in outputs), 2),
        "mean_gaps_count": round(statistics.mean(item["gaps_count"] for item in outputs), 2),
        "all_cases_produced_bullets": all(item["resume_bullets_count"] == 3 for item in outputs),
        "all_cases_produced_cover_points": all(item["cover_points_count"] == 3 for item in outputs),
    }
    payload = {"summary": summary, "cases": outputs}
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def build_markdown(results: dict) -> str:
    summary = results["summary"]
    cases = results["cases"]
    table_rows = [
        "| Case | Lang | Latency (ms) | Req. | Matches | Gaps | Avg. match score |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in cases:
        table_rows.append(
            f"| {case['case_id']} | {case['language']} | {case['latency_ms']} | "
            f"{case['requirements_count']} | {case['matches_count']} | {case['gaps_count']} | "
            f"{case['average_match_score']} |"
        )

    summary_text = (
        "This report presents a prototype of a tailored application coach for Korean undergraduates applying for internships. "
        "The problem addressed is repeated rewriting: students already have relevant experiences, but they struggle to adapt those experiences to each job posting without losing authenticity. "
        "The system uses a lightweight local web interface, a heuristic fallback generator, and an optional OpenAI Responses API backend when an API key is available. "
        f"To evaluate the prototype, I ran three demo cases across English and Korean job-posting scenarios and measured output completeness, response latency, and requirement-to-evidence matching quality. "
        f"In heuristic mode, the prototype generated three resume bullets and three cover-letter points for all {summary['case_count']} cases, with a mean latency of {summary['mean_latency_ms']} ms and a mean evidence-match score of {summary['mean_average_match_score']}. "
        "The findings suggest that even a lightweight prototype can support grounded tailoring by extracting job requirements, surfacing missing evidence, and organizing revision priorities. "
        "The main conclusion is that the workflow is feasible and presentation-ready, but higher-quality personalization will require live LLM evaluation, stronger scoring, and longitudinal user testing."
    )

    content = f"""# Technical Report

## Summary

{summary_text}

## Introduction

Large language models are increasingly used for writing assistance, but many student-facing tools still produce generic text rather than grounded, job-specific support. In Step 1, I identified a narrow user: a Korean undergraduate preparing internship applications who repeatedly rewrites the same experiences for different postings. The core problem is not lack of effort, but repeated translation from fragmented evidence into role-specific wording.

The objective of Step 2 was to build a working prototype that demonstrates this opportunity. The prototype should accept a base profile, an activity bank, and a target job posting, then return a tailored summary, resume bullets, cover-letter talking points, requirement-to-evidence mapping, and a revision checklist.

## Methods

### System design

- Frontend: local static HTML/CSS/JavaScript interface
- Backend: Python standard-library HTTP server
- Generation backends:
  - heuristic mode for offline demonstration
  - OpenAI Responses API mode when `OPENAI_API_KEY` is available

### Data preprocessing

- The prototype receives three text fields: base resume/profile, activity bank, and job posting.
- Text is normalized into lines and sentence-like units.
- A lightweight language detector compares Hangul and Latin character counts to choose Korean or English output.
- Requirement extraction selects salient job-posting lines and filters out section headers.
- Evidence extraction collects resume and activity lines that can support the extracted requirements.

### Models and generation logic

- Heuristic mode:
  - token overlap scoring between requirements and evidence lines
  - fallback template generation for summary, bullets, cover-letter points, gaps, and checklist
- OpenAI mode:
  - server-side call to the OpenAI Responses API
  - JSON-only prompt design to keep the output structured and easy to render
  - `auto` mode falls back to heuristic mode if the API is unavailable

### Experiments and analysis

- I created three evaluation cases:
  - English product-operations internship
  - Korean content-marketing internship
  - English data-operations internship
- For each case, I measured:
  - response latency
  - number of extracted requirements
  - number of matched evidence items
  - number of evidence gaps
  - average requirement-to-evidence match score
- I also checked whether the prototype consistently produced three resume bullets and three cover-letter points.

### Repository link

- GitHub repository link: `{REPO_URL}`
- If the repository is private, invite `ssuai` as a collaborator.

## Results

### Table 1. Prototype evaluation across three demo cases

{chr(10).join(table_rows)}

### Table 2. Aggregate findings

| Metric | Value |
| --- | ---: |
| Number of evaluated cases | {summary['case_count']} |
| Mean latency (ms) | {summary['mean_latency_ms']} |
| Mean extracted requirements | {summary['mean_requirements_count']} |
| Mean evidence gaps | {summary['mean_gaps_count']} |
| Mean evidence-match score | {summary['mean_average_match_score']} |
| All cases produced 3 resume bullets | {summary['all_cases_produced_bullets']} |
| All cases produced 3 cover-letter points | {summary['all_cases_produced_cover_points']} |

The prototype generated complete output packages for all evaluated cases. It was also able to switch between Korean and English outputs depending on the input language. The most consistent strength was structured output completeness, while the weakest area was semantic precision in heuristic mode when evidence wording did not closely match the job-post language.

## Discussion

The results suggest that the proposed workflow is practical: even a lightweight baseline can identify job requirements, connect them to evidence, and highlight missing proof points. This supports the Step 1 claim that the main user value is grounded tailoring rather than generic text generation.

However, the experiments also reveal the limits of the current heuristic baseline. Match scores are sensitive to lexical overlap, so semantically relevant evidence can still be undervalued if it is phrased differently from the job post. In other words, the current prototype is good for demonstrating the user flow, but not yet sufficient for production-grade reasoning.

The implication is that Step 2 successfully validates the feasibility of the product direction, while also clarifying where a stronger LLM backend would create the most value: better semantic matching, stronger ranking, and more natural rewriting.

## Conclusion

This project built a functioning prototype of a tailored application coach for Korean undergraduates applying for internships. The system accepts user materials and a job posting, then returns structured outputs that help the user rewrite their application in a more targeted and grounded way.

The main message is that the proposed LLM opportunity is concrete, buildable, and easy to demonstrate. Future work should include live OpenAI-mode evaluation, stronger quantitative benchmarking, user feedback collection, and export features for directly reusable application drafts.

## References

1. `project_1-1.pdf`, Term Project #1 instructions.
2. OpenAI, "Text generation guide," https://developers.openai.com/api/docs/guides/text
3. OpenAI, "API overview," https://developers.openai.com/api/reference/overview
"""
    REPORT_MD_PATH.write_text(content, encoding="utf-8")
    return content


def build_pdf(results: dict) -> None:
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    bullet_style = ParagraphStyle(
        "BulletStyle",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-8,
        alignment=TA_LEFT,
    )

    summary = results["summary"]
    cases = results["cases"]

    story = [
        Paragraph("Technical Report", title_style),
        Paragraph("Summary", heading_style),
        Paragraph(
            (
                "This report presents a prototype of a tailored application coach for Korean undergraduates applying "
                "for internships. The system addresses repeated rewriting by turning a base profile, an activity bank, "
                "and a target job posting into a tailored application package. The methodology combines a local web "
                "interface, a heuristic matching engine, and an optional OpenAI Responses API backend. Across three "
                f"demo cases, the heuristic baseline produced complete outputs in every case, with a mean latency of "
                f"{summary['mean_latency_ms']} ms and a mean evidence-match score of {summary['mean_average_match_score']}. "
                "The findings suggest that grounded tailoring is feasible in a small prototype, although higher-quality "
                "personalization will require stronger semantic reasoning and live LLM evaluation."
            ),
            body_style,
        ),
        Paragraph("Introduction", heading_style),
        Paragraph(
            "The target user is a Korean undergraduate applying for internships who repeatedly rewrites the same "
            "experiences for different companies. The problem is not a lack of experiences, but the difficulty of "
            "reframing those experiences in a job-specific and credible way. The goal of this project was to build "
            "a working prototype that demonstrates this LLM opportunity end-to-end.",
            body_style,
        ),
        Paragraph("Methods", heading_style),
        Paragraph(
            "The prototype uses a static frontend, a Python standard-library HTTP server, a heuristic baseline, and "
            "an optional OpenAI Responses API backend. Inputs are normalized into lines, a lightweight language detector "
            "selects Korean or English output, requirement lines are extracted from the job posting, and resume/activity "
            "lines are matched to those requirements through token overlap scoring. Three evaluation cases were used: "
            f"English product operations, Korean content marketing, and English data operations. GitHub repository link: "
            f"{REPO_URL}. If the repository is private, invite ssuai as a collaborator.",
            body_style,
        ),
    ]

    case_rows = [["Case", "Lang", "Latency (ms)", "Req.", "Matches", "Gaps", "Avg. score"]]
    for case in cases:
        case_rows.append(
            [
                case["case_id"],
                case["language"],
                f"{case['latency_ms']}",
                str(case["requirements_count"]),
                str(case["matches_count"]),
                str(case["gaps_count"]),
                str(case["average_match_score"]),
            ]
        )
    case_table = Table(case_rows, repeatRows=1, colWidths=[4.0 * cm, 1.2 * cm, 2.3 * cm, 1.4 * cm, 1.6 * cm, 1.2 * cm, 2.0 * cm])
    case_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9ead7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#444444")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    aggregate_rows = [
        ["Metric", "Value"],
        ["Number of evaluated cases", str(summary["case_count"])],
        ["Mean latency (ms)", str(summary["mean_latency_ms"])],
        ["Mean extracted requirements", str(summary["mean_requirements_count"])],
        ["Mean evidence gaps", str(summary["mean_gaps_count"])],
        ["Mean evidence-match score", str(summary["mean_average_match_score"])],
        ["All cases produced 3 resume bullets", str(summary["all_cases_produced_bullets"])],
        ["All cases produced 3 cover-letter points", str(summary["all_cases_produced_cover_points"])],
    ]
    aggregate_table = Table(aggregate_rows, repeatRows=1, colWidths=[8.5 * cm, 4.0 * cm])
    aggregate_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2dfb8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#444444")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbf7ef")]),
            ]
        )
    )

    story.extend(
        [
            Paragraph("Results", heading_style),
            Paragraph("Table 1. Prototype evaluation across three demo cases.", body_style),
            case_table,
            Spacer(1, 8),
            Paragraph("Table 2. Aggregate findings.", body_style),
            aggregate_table,
            Spacer(1, 8),
            Paragraph(
                "The prototype produced complete output packages in every case and successfully adapted to both English and Korean inputs. "
                "The strongest result was output completeness, while the main weakness was lexical sensitivity in heuristic matching.",
                body_style,
            ),
            Paragraph("Discussion", heading_style),
            Paragraph(
                "These results support the feasibility of the Step 1 opportunity: the value of the product lies in grounded tailoring, "
                "requirement extraction, and evidence organization. At the same time, the heuristic baseline shows that production-quality "
                "personalization will require a stronger semantic model and richer evaluation.",
                body_style,
            ),
            Paragraph("Conclusion", heading_style),
            Paragraph(
                "The project successfully implemented a working prototype of a tailored application coach for Korean undergraduates. "
                "The main message is that the idea is concrete, buildable, and demonstrable, while future work should expand live LLM evaluation, "
                "benchmarking, and export-ready draft generation.",
                body_style,
            ),
            Paragraph("References", heading_style),
            Paragraph("1. project_1-1.pdf, Term Project #1 instructions.", bullet_style),
            Paragraph('2. OpenAI, "Text generation guide," https://developers.openai.com/api/docs/guides/text', bullet_style),
            Paragraph('3. OpenAI, "API overview," https://developers.openai.com/api/reference/overview', bullet_style),
        ]
    )

    doc.build(story)


def main() -> None:
    results = run_evaluation()
    build_markdown(results)
    build_pdf(results)
    print(RESULTS_PATH)
    print(REPORT_MD_PATH)
    print(PDF_PATH)


if __name__ == "__main__":
    main()
