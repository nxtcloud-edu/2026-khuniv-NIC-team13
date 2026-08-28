import { useState, useEffect } from "react";
import { useAnalysisStore } from "stores/analysisStore";
import AnalysisNavBar from "pages/analysis-page/components/AnalysisNavBar";
import AnalsisSummary from "pages/analysis-page/components/AnalsisSummary";
import AnalysisDiagnosis from "pages/analysis-page/components/AnalysisDiagnosis";
import ImproveStrategy from "pages/analysis-page/components/ImproveStrategy";
import Apply from "pages/analysis-page/components/Apply";
import { DEMO_FINAL_STATE, DEMO_PASS_SCORE } from "./demoData";

const SECTION_IDS = ["분석 요약", "역량 진단", "개선 전략", "적용 · 재평가"];
const SECTION_COMPONENTS = {
  "분석 요약": AnalsisSummary,
  "역량 진단": AnalysisDiagnosis,
  "개선 전략": ImproveStrategy,
  "적용 · 재평가": Apply,
};

interface DemoReportModalProps {
  onClose: () => void;
}

export default function DemoReportModal({ onClose }: DemoReportModalProps) {
  const [activeNav, setActiveNav] = useState(SECTION_IDS[0]);
  const {
    setFinalData,
    setPassScoreData,
    reset,
    normalData,
    evaluationResult,
    revisedResult,
    passScoreData,
    status,
  } = useAnalysisStore();

  useEffect(() => {
    // 예시레포트 사용 시 기존 store 데이터 백업
    const backup = {
      normalData,
      evaluationResult,
      revisedResult,
      passScoreData,
      status,
    };

    setFinalData(DEMO_FINAL_STATE);
    setPassScoreData(DEMO_PASS_SCORE);

    return () => {
      // 모달 닫힐 때 백업 데이터 복원
      if (backup.evaluationResult) {
        setFinalData({
          ...DEMO_FINAL_STATE,
          evaluationResult: backup.evaluationResult,
          revisedResult: backup.revisedResult!,
          ...backup.normalData,
        });
        setPassScoreData(backup.passScoreData!);
      } else {
        reset();
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleNext = () => {
    const idx = SECTION_IDS.indexOf(activeNav);
    if (idx < SECTION_IDS.length - 1) setActiveNav(SECTION_IDS[idx + 1]);
  };

  const handlePrev = () => {
    const idx = SECTION_IDS.indexOf(activeNav);
    if (idx > 0) setActiveNav(SECTION_IDS[idx - 1]);
  };

  const C = SECTION_COMPONENTS[activeNav as keyof typeof SECTION_COMPONENTS];

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60"
      style={{ top: "clamp(52px, calc(2.5vw + 28px), 64px)" }}
      onClick={onClose}
    >
      <div
        className="relative bg-[#F9FAFB] w-[90vw] h-[75%] min-[894px]:w-[65vw] min-[894px]:max-w-[1100px] min-[894px]:h-[85%] rounded-[12px] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 상단 헤더 */}
        <div className="bg-white px-[40px] pt-[24px] shrink-0">
          <div className="flex items-center justify-between">
            <h2 className="text-[20px] font-medium text-[#111] font-['Pretendard']">
              자기소개서 역량 평가 리포트{" "}
              <span className="text-[14px] text-[#2876F1] ml-2">예시</span>
            </h2>
            <button
              onClick={onClose}
              className="w-[32px] h-[32px] flex items-center justify-center text-[#717171] hover:text-[#111] transition-colors text-[24px]"
            >
              ×
            </button>
          </div>
          <div className="[&>nav]:mt-[0px]">
            <AnalysisNavBar active={activeNav} onChange={setActiveNav} />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="px-[40px] mt-[40px] pb-[40px]">
            <C onNext={handleNext} onPrev={handlePrev} />
          </div>
        </div>
      </div>
    </div>
  );
}
