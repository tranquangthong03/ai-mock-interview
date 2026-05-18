// -----------------------------------------------------------------------
// TypeScript types for AI Mock Interviewer frontend
// -----------------------------------------------------------------------

export interface DocumentItem {
  id: number;
  document_type: "CV" | "JD";
  filename: string;
  text_length: number;
  created_at: string;
}

export interface DocumentUploadResponse {
  id: number;
  document_type: string;
  filename: string;
  extracted_text_preview: string;
  text_length: number;
  message: string;
}

export interface ParsedDocument {
  id: number;
  document_type: string;
  filename: string;
  parsed_json: Record<string, unknown>;
  message: string;
}

export interface IndexDocumentResponse {
  document_id: number;
  document_type: string;
  chunks_indexed: number;
  collection: string;
  message: string;
}

export interface StartInterviewResponse {
  session_id: number;
  status: string;
  first_question: string;
  round_number: number;
}

export interface InterviewMessage {
  id: number;
  role: "interviewer" | "candidate" | "system";
  content: string;
  round_number: number;
  created_at: string;
}

export interface EvaluationScores {
  relevance: number;
  clarity: number;
  specificity: number;
  technical_accuracy: number;
  jd_alignment: number;
  communication: number;
}

export interface Evaluation {
  score_overall: number;
  scores: EvaluationScores;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  improved_answer_suggestion: string;
  short_feedback: string;
}

export interface SubmitAnswerResponse {
  session_id: number;
  round_number: number;
  candidate_answer: string;
  evaluation: Evaluation | null;
  next_question: string;
  status: string;
}

export interface InterviewHistory {
  session_id: number;
  cv_document_id: number;
  jd_document_id: number;
  interview_type: string;
  status: string;
  current_round: number;
  created_at: string;
  completed_at: string | null;
  messages: InterviewMessage[];
}

export interface EndInterviewResponse {
  session_id: number;
  status: string;
  total_rounds: number;
  message: string;
}

export interface InterviewReport {
  session_id: number;
  overall_score: number;
  criterion_scores: EvaluationScores;
  summary: string;
  strengths_summary: string[];
  weaknesses_summary: string[];
  skill_gap_summary: string[];
  improvement_plan: string[];
  recommended_topics: string[];
  final_advice: string;
  message?: string;
  created_at?: string;
  updated_at?: string | null;
}

export interface InterviewSummary {
  session_id: number;
  total_answers: number;
  average_score: number;
  criterion_averages: EvaluationScores;
  best_criterion: string;
  weakest_criterion: string;
}

export interface EvaluationListItem {
  round_number: number;
  question: string;
  answer: string;
  score_overall: number;
  scores: EvaluationScores;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  improved_answer_suggestion: string;
  short_feedback: string;
  created_at: string;
}

export interface SessionEvaluations {
  session_id: number;
  evaluations: EvaluationListItem[];
}

export interface SpeechMetrics {
  duration_seconds: number;
  word_count: number;
  speech_rate_wpm: number;
  filler_words: string[];
  filler_word_count: number;
  estimated_pause_count: number;
  notes: string[];
}

export interface SubmitAudioAnswerResponse {
  session_id: number;
  round_number: number;
  transcript: string;
  speech_metrics: SpeechMetrics;
  evaluation: Evaluation | null;
  next_question: string;
  status: string;
}

export interface TranscribeAudioResponse {
  session_id: number;
  transcript: string;
  speech_metrics: SpeechMetrics;
  audio_file_path: string;
}

export interface ApiError {
  detail: string;
}
