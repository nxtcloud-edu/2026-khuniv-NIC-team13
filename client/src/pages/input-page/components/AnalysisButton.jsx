import cn from "utils/cn";
import Button from "./Button";
import { useNumOfAnalysis } from "api/analysisApi";

const AnalysisButton = ({ total = 3, status = "default", ...props }) => {
  const { data } = useNumOfAnalysis();
  const remainCount = data?.data.remainCount ?? total;
  const unavailable = remainCount <= 0;

  return (
    <Button
      size="M"
      variant="primary"
      status={unavailable ? "disabled" : status}
      className="gap-[10px]"
      disabled={unavailable || status === "disabled"}
      {...props}
    >
      <span>분석하기</span>
      <span
        className={cn(
          unavailable || status === "disabled"
            ? "text-[#EEEEEE]"
            : "text-[#C1D9FF]",
        )}
      >
        {remainCount}/{total}
      </span>
    </Button>
  );
};

export default AnalysisButton;
