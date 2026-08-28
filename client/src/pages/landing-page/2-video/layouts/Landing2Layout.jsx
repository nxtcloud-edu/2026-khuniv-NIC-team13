function Landing2Layout() {
  return (
    <section className="flex h-full w-screen items-center justify-center bg-[#05091d] px-6 pt-[clamp(52px,calc(2.5vw+28px),64px)] text-center text-white">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#75ABFF]">
          Pertineo
        </p>
        <h2 className="mt-5 text-4xl font-bold leading-tight md:text-6xl">
          막막한 자기소개서를<br />명확한 전략으로
        </h2>
        <p className="mt-6 text-base text-white/70 md:text-xl">
          지원 직무와 경험을 연결해 나만의 강점을 발견하세요.
        </p>
      </div>
    </section>
  );
}

export default Landing2Layout;
