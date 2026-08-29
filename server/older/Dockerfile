# 1. 빌드 스테이지 - 레이어 캐싱 최적화
FROM gradle:9.3.1-jdk21-alpine AS build
WORKDIR /app

# Gradle 의존성만 먼저 복사 (의존성 변경 시에만 재빌드)
COPY build.gradle settings.gradle gradlew ./
COPY gradle ./gradle

# 의존성 다운로드 (캐시 활용)
RUN ./gradlew dependencies --no-daemon || true

# 소스 코드 복사
COPY src ./src

# 빌드 실행
RUN chmod +x ./gradlew
RUN ./gradlew build -x test --no-daemon && \
    find . -name "*.jar" -not -path "./build/libs/*" -delete

# 2. 실행 스테이지 - 최소 크기 이미지
FROM amazoncorretto:21-alpine
WORKDIR /app

# 시간대 설정 (한국 시간)
ENV TZ=Asia/Seoul
RUN apk add --no-cache tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    rm -rf /var/cache/apk/*

# JAR 파일 복사
COPY --from=build /app/build/libs/*.jar app.jar

# 비root 사용자로 실행 (보안)
RUN addgroup -S spring && adduser -S spring -G spring
USER spring:spring

ENTRYPOINT ["java", "-jar", "app.jar"]
