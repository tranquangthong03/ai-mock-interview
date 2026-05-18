"""
Central language defaults for the interview flow.

The UI can stay Vietnamese, but interview content follows:
  - interviewer questions: English
  - candidate answers: English
  - evaluation feedback: Vietnamese
  - final report: Vietnamese
"""

import os


INTERVIEW_QUESTION_LANGUAGE = os.getenv("INTERVIEW_QUESTION_LANGUAGE", "en")
CANDIDATE_EXPECTED_LANGUAGE = os.getenv("CANDIDATE_EXPECTED_LANGUAGE", "en")
FEEDBACK_LANGUAGE = os.getenv("FEEDBACK_LANGUAGE", "vi")
REPORT_LANGUAGE = os.getenv("REPORT_LANGUAGE", "vi")
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en")

