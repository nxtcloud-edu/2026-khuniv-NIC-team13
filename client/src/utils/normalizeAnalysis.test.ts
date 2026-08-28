import { normalizeFinalState } from "./normalizeAnalysis";

test("normalizes Python final state and nested evaluation keys", () => {
  const result = normalizeFinalState({
    user_id: "user@example.com",
    question_list: ["Q1"],
    answer_list: ["A1"],
    job_position: "개발자",
    evaluation_result: {
      x: { score: 4.1, compare_score: "높음" },
      role_fit: "적합",
      improve_strategy: [
        { strategy_name: "구체화", action_items: ["성과를 수치로 표현"] },
      ],
    },
    revised_result: {
      best_reply: ["개선 답변"],
      reply_reason: ["개선 이유"],
      expectation: ["기대 효과"],
    },
  });

  expect(result.userId).toBe("user@example.com");
  expect(result.questionList).toEqual(["Q1"]);
  expect(result.jobPosition).toBe("개발자");
  expect(result.evaluationResult.x.compareScore).toBe("높음");
  expect(result.evaluationResult.roleFit).toBe("적합");
  expect(result.evaluationResult.improveStrategy[0]).toEqual({
    strategyName: "구체화",
    actionItems: ["성과를 수치로 표현"],
  });
  expect(result.revisedResult.best_reply).toEqual(["개선 답변"]);
});
