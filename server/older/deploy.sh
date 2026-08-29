#!/bin/bash

# 실행 중인 JAR 프로세스 찾기
CURRENT_PID=$(pgrep -f 'java -jar')

if [ -z "$CURRENT_PID" ]; then
    echo "✅ No running application found."
else
    echo "🛑 Stopping application (PID: $CURRENT_PID)..."
    kill -15 "$CURRENT_PID"
    sleep 5

    # 정상 종료되지 않은 경우 강제 종료
    if ps -p "$CURRENT_PID" > /dev/null; then
        echo "⚠️ Process still running. Force killing..."
        kill -9 "$CURRENT_PID"
        sleep 3
    fi
fi

# 실행할 JAR 파일 찾기 (plain 제외)
JAR_PATH=$(ls -t /home/ubuntu/cicd/*.jar | grep -v 'plain' | head -n 1)

if [ -z "$JAR_PATH" ]; then
    echo "❌ No valid JAR file found in /home/ubuntu/cicd/"
    exit 1
fi

echo "🚀 Deploying $JAR_PATH..."

# 애플리케이션 실행 (백그라운드 실행 및 로그 저장)
nohup java -jar "$JAR_PATH" > /home/ubuntu/nohup.out 2>&1 &

NEW_PID=$!
echo "✅ Deployment successful! New PID: $NEW_PID"
