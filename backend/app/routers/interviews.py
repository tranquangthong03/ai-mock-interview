"""
Interview Router

Endpoints:
  POST /interviews/start              – Start a new interview session
  POST /interviews/{session_id}/answer – Submit a text answer
  POST /interviews/{session_id}/answer-audio – Submit a voice answer
  GET  /interviews/{session_id}        – Get interview history
  GET  /interviews/{session_id}/evaluations – Get all evaluations
  POST /interviews/{session_id}/end    – End an interview session
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, InterviewSession, InterviewMessage, AnswerEvaluation
from app.schemas import (
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    SubmitAudioAnswerResponse,
    TranscribeAudioResponse,
    SpeechMetrics,
    InterviewHistoryResponse,
    InterviewMessageItem,
    EndInterviewResponse,
    EvaluationResult,
    EvaluationScores,
    EvaluationListItem,
    SessionEvaluationsResponse,
)
from app.services.interview_orchestrator_service import (
    generate_first_question,
    generate_followup_question,
    generate_retry_question,
    build_interview_context,
    build_history_text,
)
from app.services.answer_evaluation_service import evaluate_answer
from app.services.rag_service import retrieve_context
from app.services.audio_processing_service import AudioProcessingError, process_audio_answer

router = APIRouter(prefix="/interviews", tags=["Interviews"])
logger = logging.getLogger(__name__)

# Relevance score threshold below which a retry question is generated
RELEVANCE_RETRY_THRESHOLD = 4.0


# ---------------------------------------------------------------------------
# POST /interviews/start
# ---------------------------------------------------------------------------

@router.post("/start", response_model=StartInterviewResponse)
def start_interview(
    body: StartInterviewRequest,
    db: Session = Depends(get_db),
):
    """
    Start a new interview session.

    - Validates that CV and JD documents exist and have parsed_json
    - Creates a session and generates the first personalised question
    """
    # --- Validate CV document ---
    cv_doc = db.query(Document).filter(Document.id == body.cv_document_id).first()
    if not cv_doc:
        raise HTTPException(
            status_code=404,
            detail=f"CV document with id={body.cv_document_id} not found.",
        )
    if cv_doc.document_type != "CV":
        raise HTTPException(
            status_code=400,
            detail=f"Document id={body.cv_document_id} is not a CV (type={cv_doc.document_type}).",
        )
    if not cv_doc.parsed_json:
        raise HTTPException(
            status_code=400,
            detail=f"CV document id={body.cv_document_id} has not been parsed yet. "
                   "Please call POST /documents/{id}/parse first.",
        )

    # --- Validate JD document ---
    jd_doc = db.query(Document).filter(Document.id == body.jd_document_id).first()
    if not jd_doc:
        raise HTTPException(
            status_code=404,
            detail=f"JD document with id={body.jd_document_id} not found.",
        )
    if jd_doc.document_type != "JD":
        raise HTTPException(
            status_code=400,
            detail=f"Document id={body.jd_document_id} is not a JD (type={jd_doc.document_type}).",
        )
    if not jd_doc.parsed_json:
        raise HTTPException(
            status_code=400,
            detail=f"JD document id={body.jd_document_id} has not been parsed yet. "
                   "Please call POST /documents/{id}/parse first.",
        )

    # --- Create session ---
    session = InterviewSession(
        cv_document_id=cv_doc.id,
        jd_document_id=jd_doc.id,
        interview_type=body.interview_type,
        target_language=body.target_language,
        status="active",
        current_round=1,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # --- Generate first question ---
    try:
        first_question = generate_first_question(
            cv_document=cv_doc,
            jd_document=jd_doc,
            interview_type=body.interview_type,
        )
    except Exception as e:
        # Roll back the session if question generation fails
        db.delete(session)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating first question: {str(e)}",
        )

    # --- Save interviewer message ---
    msg = InterviewMessage(
        session_id=session.id,
        role="interviewer",
        content=first_question,
        round_number=1,
    )
    db.add(msg)
    db.commit()

    return StartInterviewResponse(
        session_id=session.id,
        status=session.status,
        first_question=first_question,
        round_number=1,
    )


# ---------------------------------------------------------------------------
# Shared answer processing logic
# ---------------------------------------------------------------------------

def _process_answer_core(
    session: InterviewSession,
    answer_text: str,
    answer_msg: InterviewMessage,
    last_question_msg: InterviewMessage,
    db: Session,
) -> tuple:
    """
    Shared logic for evaluating an answer and generating the follow-up question.
    Returns (evaluation_result, evaluation_dict, next_question).
    """
    # Load documents
    cv_doc = db.query(Document).filter(Document.id == session.cv_document_id).first()
    jd_doc = db.query(Document).filter(Document.id == session.jd_document_id).first()

    # Load full message history
    all_messages = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.session_id == session.id)
        .order_by(InterviewMessage.created_at)
        .all()
    )

    # Build RAG context
    context = build_interview_context(cv_doc, jd_doc)
    eval_query_parts = [
        last_question_msg.content[:300],
        answer_text[:300],
    ]
    if context.get("target_role"):
        eval_query_parts.append(context["target_role"])
    if context.get("required_skills"):
        eval_query_parts.append(", ".join(context["required_skills"][:5]))
    eval_query = " | ".join(eval_query_parts)

    try:
        rag_results = retrieve_context(
            query=eval_query,
            top_k=5,
            document_ids=[session.cv_document_id, session.jd_document_id],
        )
    except Exception:
        rag_results = []

    # Evaluate answer
    history_text = build_history_text(all_messages)
    evaluation_dict = None
    evaluation_result = None

    try:
        evaluation_dict = evaluate_answer(
            question=last_question_msg.content,
            answer=answer_text,
            cv_document=cv_doc,
            jd_document=jd_doc,
            rag_context=rag_results,
            interview_history=history_text,
        )
    except Exception as e:
        print(f"[WARNING] Answer evaluation failed: {e}")

    # Save evaluation to database
    if evaluation_dict:
        eval_record = AnswerEvaluation(
            session_id=session.id,
            question_message_id=last_question_msg.id,
            answer_message_id=answer_msg.id,
            round_number=session.current_round,
            score_overall=evaluation_dict.get("score_overall", 0),
            relevance_score=evaluation_dict.get("scores", {}).get("relevance", 0),
            clarity_score=evaluation_dict.get("scores", {}).get("clarity", 0),
            specificity_score=evaluation_dict.get("scores", {}).get("specificity", 0),
            technical_accuracy_score=evaluation_dict.get("scores", {}).get("technical_accuracy", 0),
            jd_alignment_score=evaluation_dict.get("scores", {}).get("jd_alignment", 0),
            communication_score=evaluation_dict.get("scores", {}).get("communication", 0),
            strengths=json.dumps(evaluation_dict.get("strengths", []), ensure_ascii=False),
            weaknesses=json.dumps(evaluation_dict.get("weaknesses", []), ensure_ascii=False),
            suggestions=json.dumps(evaluation_dict.get("suggestions", []), ensure_ascii=False),
            improved_answer_suggestion=evaluation_dict.get("improved_answer_suggestion", ""),
            short_feedback=evaluation_dict.get("short_feedback", ""),
            raw_evaluation_json=json.dumps(evaluation_dict, ensure_ascii=False),
        )
        db.add(eval_record)
        db.commit()

        evaluation_result = EvaluationResult(
            score_overall=evaluation_dict.get("score_overall", 0),
            scores=EvaluationScores(**evaluation_dict.get("scores", {})),
            strengths=evaluation_dict.get("strengths", []),
            weaknesses=evaluation_dict.get("weaknesses", []),
            suggestions=evaluation_dict.get("suggestions", []),
            improved_answer_suggestion=evaluation_dict.get("improved_answer_suggestion", ""),
            short_feedback=evaluation_dict.get("short_feedback", ""),
        )

    # Determine if we should retry (low relevance) or generate follow-up
    relevance_score = 10.0  # default: assume on-topic
    short_feedback = ""
    if evaluation_dict:
        relevance_score = evaluation_dict.get("scores", {}).get("relevance", 10.0)
        short_feedback = evaluation_dict.get("short_feedback", "")

    if relevance_score < RELEVANCE_RETRY_THRESHOLD:
        # Low relevance → retry question (redirect to original topic)
        try:
            next_question = generate_retry_question(
                original_question=last_question_msg.content,
                candidate_answer=answer_text,
                short_feedback=short_feedback,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating retry question: {str(e)}",
            )
    else:
        # Normal flow → follow-up question
        try:
            next_question = generate_followup_question(
                session=session,
                messages=all_messages,
                latest_answer=answer_text,
                cv_document=cv_doc,
                jd_document=jd_doc,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating follow-up question: {str(e)}",
            )

    # Advance round
    session.current_round += 1
    db.commit()

    # Save interviewer follow-up message
    followup_msg = InterviewMessage(
        session_id=session.id,
        role="interviewer",
        content=next_question,
        round_number=session.current_round,
    )
    db.add(followup_msg)
    db.commit()

    return evaluation_result, evaluation_dict, next_question


# ---------------------------------------------------------------------------
# POST /interviews/{session_id}/answer
# ---------------------------------------------------------------------------

@router.post("/{session_id}/answer", response_model=SubmitAnswerResponse)
def submit_answer(
    session_id: int,
    body: SubmitAnswerRequest,
    db: Session = Depends(get_db),
):
    """
    Submit a candidate text answer, evaluate it, and receive the next follow-up question.
    """
    # --- 1. Find session ---
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    if session.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="This interview session is already completed.",
        )

    if not body.answer or not body.answer.strip():
        raise HTTPException(
            status_code=400,
            detail="Answer cannot be empty.",
        )

    # --- 2. Find last interviewer question ---
    last_question_msg = (
        db.query(InterviewMessage)
        .filter(
            InterviewMessage.session_id == session.id,
            InterviewMessage.role == "interviewer",
        )
        .order_by(InterviewMessage.created_at.desc())
        .first()
    )
    if not last_question_msg:
        raise HTTPException(
            status_code=400,
            detail="No interviewer question found for this session.",
        )

    # --- 3. Save candidate answer ---
    answer_msg = InterviewMessage(
        session_id=session.id,
        role="candidate",
        content=body.answer.strip(),
        round_number=session.current_round,
    )
    db.add(answer_msg)
    db.commit()
    db.refresh(answer_msg)

    # --- 4. Evaluate + follow-up (shared logic) ---
    evaluation_result, _, next_question = _process_answer_core(
        session=session,
        answer_text=body.answer.strip(),
        answer_msg=answer_msg,
        last_question_msg=last_question_msg,
        db=db,
    )

    return SubmitAnswerResponse(
        session_id=session.id,
        round_number=session.current_round,
        candidate_answer=body.answer.strip(),
        evaluation=evaluation_result,
        next_question=next_question,
        status=session.status,
    )


# ---------------------------------------------------------------------------
# POST /interviews/{session_id}/answer-audio
# ---------------------------------------------------------------------------

@router.post("/{session_id}/answer-audio", response_model=SubmitAudioAnswerResponse)
def submit_audio_answer(
    session_id: int,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Submit a voice answer: saves audio, transcribes, evaluates, returns next question.
    """
    # --- 1. Find session ---
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    if session.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="This interview session is already completed.",
        )

    # --- 2. Find last interviewer question ---
    last_question_msg = (
        db.query(InterviewMessage)
        .filter(
            InterviewMessage.session_id == session.id,
            InterviewMessage.role == "interviewer",
        )
        .order_by(InterviewMessage.created_at.desc())
        .first()
    )
    if not last_question_msg:
        raise HTTPException(
            status_code=400,
            detail="No interviewer question found for this session.",
        )

    # --- 3. Process audio: save + transcribe + metrics ---
    try:
        audio_result = process_audio_answer(audio_file, session.id)
    except AudioProcessingError as e:
        logger.warning("[Audio/STT] Expected audio processing failure: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValueError as e:
        logger.warning("[Audio/STT] Audio validation failure: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("[Audio/STT] Unexpected audio processing error.")
        raise HTTPException(status_code=500, detail=f"Unexpected audio processing error: {str(e)}")

    transcript = audio_result["transcript"]
    speech_metrics = audio_result["speech_metrics"]
    audio_path = audio_result["audio_file_path"]

    # --- 4. Save candidate answer with audio metadata ---
    answer_msg = InterviewMessage(
        session_id=session.id,
        role="candidate",
        content=transcript,
        round_number=session.current_round,
        audio_file_path=audio_path,
        speech_metrics_json=json.dumps(speech_metrics, ensure_ascii=False),
    )
    db.add(answer_msg)
    db.commit()
    db.refresh(answer_msg)

    # --- 5. Evaluate + follow-up (shared logic) ---
    evaluation_result, _, next_question = _process_answer_core(
        session=session,
        answer_text=transcript,
        answer_msg=answer_msg,
        last_question_msg=last_question_msg,
        db=db,
    )

    return SubmitAudioAnswerResponse(
        session_id=session.id,
        round_number=session.current_round,
        transcript=transcript,
        speech_metrics=SpeechMetrics(**speech_metrics),
        evaluation=evaluation_result,
        next_question=next_question,
        status=session.status,
    )


# ---------------------------------------------------------------------------
# POST /interviews/{session_id}/transcribe-audio
# ---------------------------------------------------------------------------

@router.post("/{session_id}/transcribe-audio", response_model=TranscribeAudioResponse)
def transcribe_audio_only(
    session_id: int,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Transcribe audio without submitting as an answer.

    This enables a 2-step voice flow:
      1. POST /transcribe-audio → get transcript + speech metrics
      2. User reviews/edits transcript in the UI
      3. POST /answer → submit the confirmed text

    Does NOT save a candidate message, does NOT evaluate, does NOT generate
    a follow-up question.
    """
    # Validate session exists
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    if session.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="This interview session is already completed.",
        )

    # Process audio: save + transcribe + compute metrics
    try:
        audio_result = process_audio_answer(audio_file, session.id)
    except AudioProcessingError as e:
        logger.warning("[Audio/STT] Expected audio processing failure: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValueError as e:
        logger.warning("[Audio/STT] Audio validation failure: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("[Audio/STT] Unexpected audio processing error.")
        raise HTTPException(status_code=500, detail=f"Unexpected audio processing error: {str(e)}")

    return TranscribeAudioResponse(
        session_id=session.id,
        transcript=audio_result["transcript"],
        speech_metrics=SpeechMetrics(**audio_result["speech_metrics"]),
        audio_file_path=audio_result["audio_file_path"],
    )


# ---------------------------------------------------------------------------
# GET /interviews/{session_id}/evaluations
# ---------------------------------------------------------------------------

@router.get("/{session_id}/evaluations", response_model=SessionEvaluationsResponse)
def get_session_evaluations(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all answer evaluations for an interview session.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    evaluations = (
        db.query(AnswerEvaluation)
        .filter(AnswerEvaluation.session_id == session.id)
        .order_by(AnswerEvaluation.created_at)
        .all()
    )

    items = []
    for ev in evaluations:
        # Load question and answer text from messages
        q_msg = db.query(InterviewMessage).filter(
            InterviewMessage.id == ev.question_message_id
        ).first()
        a_msg = db.query(InterviewMessage).filter(
            InterviewMessage.id == ev.answer_message_id
        ).first()

        # Parse JSON list fields
        try:
            strengths = json.loads(ev.strengths) if ev.strengths else []
        except (json.JSONDecodeError, TypeError):
            strengths = []
        try:
            weaknesses = json.loads(ev.weaknesses) if ev.weaknesses else []
        except (json.JSONDecodeError, TypeError):
            weaknesses = []
        try:
            suggestions = json.loads(ev.suggestions) if ev.suggestions else []
        except (json.JSONDecodeError, TypeError):
            suggestions = []

        items.append(EvaluationListItem(
            id=ev.id,
            round_number=ev.round_number,
            question=q_msg.content if q_msg else "",
            answer=a_msg.content if a_msg else "",
            score_overall=ev.score_overall,
            scores=EvaluationScores(
                relevance=ev.relevance_score,
                clarity=ev.clarity_score,
                specificity=ev.specificity_score,
                technical_accuracy=ev.technical_accuracy_score,
                jd_alignment=ev.jd_alignment_score,
                communication=ev.communication_score,
            ),
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            improved_answer_suggestion=ev.improved_answer_suggestion or "",
            short_feedback=ev.short_feedback or "",
            created_at=ev.created_at,
        ))

    return SessionEvaluationsResponse(
        session_id=session.id,
        evaluations=items,
    )


# ---------------------------------------------------------------------------
# GET /interviews/{session_id}
# ---------------------------------------------------------------------------

@router.get("/{session_id}", response_model=InterviewHistoryResponse)
def get_interview_history(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the full interview session history including all messages.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    messages = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.session_id == session.id)
        .order_by(InterviewMessage.created_at)
        .all()
    )

    return InterviewHistoryResponse(
        session_id=session.id,
        cv_document_id=session.cv_document_id,
        jd_document_id=session.jd_document_id,
        interview_type=session.interview_type,
        status=session.status,
        current_round=session.current_round,
        created_at=session.created_at,
        completed_at=session.completed_at,
        messages=[InterviewMessageItem.model_validate(m) for m in messages],
    )


# ---------------------------------------------------------------------------
# POST /interviews/{session_id}/end
# ---------------------------------------------------------------------------

@router.post("/{session_id}/end", response_model=EndInterviewResponse)
def end_interview(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    End an active interview session.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    if session.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="This interview session is already completed.",
        )

    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    return EndInterviewResponse(
        session_id=session.id,
        status=session.status,
        total_rounds=session.current_round,
        message="Interview completed successfully",
    )
