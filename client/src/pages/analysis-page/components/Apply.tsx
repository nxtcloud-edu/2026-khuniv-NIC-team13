import { useNavigate } from "react-router-dom";
import AnalysisHeader from "./AnalysisHeader";
import { useAnalysisStore } from "stores/analysisStore";

export default function Apply({
  onPrev,
  onDownload,
  isGenerating,
}: {
  onPrev?: () => void;
  onDownload?: () => void;
  isGenerating?: boolean;
}) {
  const navigate = useNavigate();
  const { revisedResult, normalData } = useAnalysisStore();

  return (
    <div className="flex flex-col">
      <AnalysisHeader title="전략 반영 자기소개서 수정본" className="mb-2" />
      <div className="text-[14px] text-gray900 mb-10">
        *본 개선된 자기소개서는 모범적인 예시로 참고만 하시되 본인의경험을 잘
        녹여내어 작성하시길 바랍니다.
      </div>
      {revisedResult?.best_reply.map((reply, index) => (
        <div
          key={reply}
          className="pb-[70px] mb-[70px] border-dashed border-b-[1px] border-b-[#B5B5B5]"
        >
          <section>
            <h3 className="text-xl pb-[30px]">
              [ {normalData?.questionList[index]} ]
            </h3>
            <h4 className="text-xl text-gray900 pb-[10px]">내 응답</h4>
            <div className="pb-10">{normalData?.answerList[index]}</div>
            <h4 className="text-xl text-gray900 pb-[10px]">개선된 응답</h4>
            <div className="pb-10">{revisedResult?.best_reply[index]}</div>
            <h4 className="text-xl text-gray900 pb-[10px]">개선된 근거</h4>
            <div className="pb-10">{revisedResult?.reply_reason[index]}</div>
            <h4 className="text-xl text-gray900 pb-[10px]">기대 효과</h4>
            <div>{revisedResult?.expectation[index]}</div>
          </section>
        </div>
      ))}
      {/* <AnalysisHeader title="수정된 자기소개서 3D 역량평가" />
      <div className="flex flex-col gap-5">
        <div>
          <div>학습수준</div>
          <div>근거:</div>
        </div>

        <div>
          <div>학습수준</div>
          <div>근거:</div>
        </div>
        <div>
          <div>학습수준</div>
          <div>근거:</div>
        </div>
      </div> */}
      {/* 하단 버튼 */}
      <div className="flex justify-center gap-[16px] pt-[120px] pb-[120px]">
        <button
          onClick={() => navigate("/")}
          className="w-[160px] h-[44px] bg-white rounded-[6px] text-[16px] font-medium text-[#0D326F] border border-[#09469F] hover:bg-[#ECF1F8] transition-all duration-200"
        >
          메인으로
        </button>
        <button
          onClick={onDownload}
          disabled={isGenerating}
          className="w-[160px] h-[44px] bg-[#09469F] text-white text-[16px] font-medium rounded-[6px] hover:bg-[#0D326F] transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isGenerating ? (
            <>
              <svg
                className="animate-spin h-4 w-4 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              생성 중...
            </>
          ) : (
            "리포트 다운로드"
          )}
        </button>
      </div>
    </div>
  );
}
