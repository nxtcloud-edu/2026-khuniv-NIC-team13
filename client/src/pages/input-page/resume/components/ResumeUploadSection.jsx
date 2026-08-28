import { useRef, useState } from "react";
import fileIcon from "assets/icons/File.svg";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

// 바이트 -> 사람이 읽기 쉬운 크기
const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

/**
 * ResumeUploadSection Component
 * 이력서 PDF를 업로드해 이력 항목을 자동 완성하기 위한 섹션입니다.
 * (파싱/자동완성 연동은 onFileSelect 콜백으로 상위에서 처리합니다.)
 *
 * @param {function} onFileSelect - 유효한 파일이 선택되면 호출되는 핸들러 (File)
 * @param {function} onFileRemove - 선택한 파일이 제거될 때 호출되는 핸들러
 * @param {boolean} isLoading - 업로드/분석 진행 중 여부
 */
const ResumeUploadSection = ({
  onFileSelect,
  onFileRemove,
  isLoading = false,
  className = "",
}) => {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const validateFile = (selected) => {
    const isPdf =
      selected.type === "application/pdf" ||
      selected.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) return "PDF 파일만 업로드할 수 있습니다.";
    if (selected.size > MAX_FILE_SIZE) return "파일 크기는 10MB 이하만 가능합니다.";
    return "";
  };

  const applyFile = (selected) => {
    if (!selected) return;
    const message = validateFile(selected);
    if (message) {
      setError(message);
      setFile(null);
      return;
    }
    setError("");
    setFile(selected);
    onFileSelect?.(selected);
  };

  const handleInputChange = (e) => {
    applyFile(e.target.files?.[0]);
    // 같은 파일을 다시 선택해도 onChange 가 발생하도록 초기화
    e.target.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (isLoading) return;
    applyFile(e.dataTransfer.files?.[0]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!isLoading) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleRemove = () => {
    setFile(null);
    setError("");
    onFileRemove?.();
  };

  return (
    <div className={`w-full min-[894px]:max-w-[1080px] ${className}`}>
      <div className="flex items-baseline">
        <div className="shrink-0 text-[24px] max-[893px]:text-[16px] font-normal text-[#000000] mb-[12px] max-[893px]:mb-[4px]">
          이력서
        </div>
        <span className="ml-[8px] text-[14px] max-[893px]:text-[12px] font-normal leading-[160%] text-[#717171]">
          PDF를 업로드하면 아래 항목이 자동으로 채워집니다. (선택)
        </span>
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`flex items-center justify-center gap-[20px] max-[893px]:gap-[12px] max-[893px]:flex-col rounded-[8px] border border-dashed px-[20px] py-[36px] max-[893px]:py-[24px] transition-colors duration-200 ${
          isDragging ? "border-[#09469F] bg-[#ECF1F8]" : "border-[#B5B5B5] bg-white"
        }`}
      >
        {file ? (
          <div className="flex items-center gap-[12px] max-[893px]:flex-col">
            <div className="flex items-center gap-[8px]">
              <img src={fileIcon} alt="" className="w-[24px] h-[24px]" />
              <span className="text-[16px] max-[893px]:text-[14px] font-medium text-black break-all">
                {file.name}
              </span>
              <span className="text-[14px] max-[893px]:text-[12px] text-[#717171]">
                {formatFileSize(file.size)}
              </span>
            </div>
            <button
              type="button"
              onClick={handleRemove}
              disabled={isLoading}
              className="text-[15px] max-[893px]:text-[13px] font-normal leading-[160%] text-[#717171] underline underline-offset-auto hover:text-black transition-colors disabled:text-[#B5B5B5] disabled:cursor-default"
            >
              삭제
            </button>
          </div>
        ) : (
          <>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              disabled={isLoading}
              className="inline-flex items-center justify-center gap-[8px] h-[52px] max-[893px]:h-[44px] px-[28px] max-[893px]:px-[20px] rounded-full border border-solid border-[#0D326F] text-[16px] max-[893px]:text-[14px] font-medium text-[#0D326F] hover:bg-[#ECF1F8] transition-all duration-200 cursor-pointer disabled:border-[#B5B5B5] disabled:text-[#B5B5B5] disabled:hover:bg-white disabled:cursor-default"
            >
              <img src={fileIcon} alt="" className="w-[24px] h-[24px]" />
              {isLoading ? "업로드 중..." : "PDF 업로드"}
            </button>
            <span className="text-[16px] max-[893px]:text-[13px] font-normal text-[#717171]">
              또는 여기로 파일을 끌어다 놓으세요
            </span>
          </>
        )}

        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleInputChange}
          className="hidden"
        />
      </div>

      {error && (
        <div className="text-[#E74C3C] text-[14px] max-[893px]:text-[12px] font-normal mt-[8px]">
          {error}
        </div>
      )}
    </div>
  );
};

export default ResumeUploadSection;
