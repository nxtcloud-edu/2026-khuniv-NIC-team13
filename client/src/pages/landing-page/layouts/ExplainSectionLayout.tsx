import cn from "utils/cn";

interface ExplainSectionLayoutProps {
  children: React.ReactNode;
  className?: string;
}
export default function ExplainSectionLayout({
  children,
  className,
}: ExplainSectionLayoutProps) {
  return (
    <section
      className={cn(
        "flex flex-col items-center px-[20px] pt-[80px] pb-[50px] bg-[#F4F6F8] h-fit",
        "lg:px-[calc((100vw-1200px)/2)] lg:pt-[120px] lg:h-screen",
        "min-[894px]:px-[40px] md:pt-[130px]",
        className,
      )}
    >
      {children}
    </section>
  );
}
