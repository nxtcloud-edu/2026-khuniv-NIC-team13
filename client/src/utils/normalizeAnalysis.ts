import { FinalStateData } from "schema/Analysis";

type UnknownRecord = Record<string, any>;

const camelizeKey = (key: string) =>
  key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());

const camelizeObject = (value: any): any => {
  if (Array.isArray(value)) return value.map(camelizeObject);
  if (value === null || typeof value !== "object") return value;

  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [camelizeKey(key), camelizeObject(item)]),
  );
};

const read = (data: UnknownRecord, camelKey: string, snakeKey: string) =>
  data[camelKey] ?? data[snakeKey];

/** Accept both the legacy Java camelCase state and the Python AI server's snake_case state. */
export const normalizeFinalState = (data: UnknownRecord): FinalStateData => ({
  analyzerRetryCount: read(data, "analyzerRetryCount", "analyzer_retry_count"),
  answerList: read(data, "answerList", "answer_list"),
  applyUrl: read(data, "applyUrl", "apply_url"),
  backgroundCareerAward: read(
    data,
    "backgroundCareerAward",
    "background_career_award",
  ),
  certificates: data.certificates,
  company: data.company,
  contextDB: read(data, "contextDB", "context_db"),
  contextWeb: read(data, "contextWeb", "context_web"),
  division: data.division,
  education: data.education,
  evaluationResult: camelizeObject(read(data, "evaluationResult", "evaluation_result")),
  gpa: data.gpa,
  isEvaluationPassed: read(data, "isEvaluationPassed", "is_evaluation_passed"),
  jobField: read(data, "jobField", "job_field"),
  jobPosition: read(data, "jobPosition", "job_position"),
  linguisticAbility: read(data, "linguisticAbility", "linguistic_ability"),
  major: data.major,
  planResult: read(data, "planResult", "plan_result"),
  questionList: read(data, "questionList", "question_list"),
  revisedResult: read(data, "revisedResult", "revised_result"),
  schemaResult: read(data, "schemaResult", "schema_result"),
  userId: read(data, "userId", "user_id"),
});
