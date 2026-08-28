import ExplainSectionLayout from "../layouts/ExplainSectionLayout";
import { useNavigate } from "react-router-dom";

export default function Start() {
  const navigate = useNavigate();
  return (
    <ExplainSectionLayout className="flex justify-center gap-8 bg-gradient-to-b from-[#F4F6F8] to-[#C1D9FF]">
      <div className="flex flex-col items-center md:text-[24px] text-[16px]">
        <div>자기소개서를 입력하고</div>
        <div>
          <span className="font-semibold">AI 역량 분석 기반 컨설팅</span>을 지금
          바로 시작하세요
        </div>
      </div>
      <button
        className="py-4 text-[16px] px-10 rounded-[4px] text-white bg-gradient-to-r from-[#002983] to-[#2876F1]"
        onClick={() => navigate("/input-page/auth")}
      >
        자기소개서 입력하러 가기
      </button>
    </ExplainSectionLayout>
  );
}
