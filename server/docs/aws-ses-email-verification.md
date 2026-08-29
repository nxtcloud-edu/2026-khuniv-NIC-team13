# AWS SES 이메일 인증 배포 설정

일반 이메일 인증은 FastAPI가 AWS SES v2로 6자리 인증번호를 전송하고 기존 DynamoDB table에
인증 상태를 저장하는 구조다. DynamoDB table이나 key schema 변경은 필요하지 않다.

## 1. SES 발신자 등록

AWS Console의 `Amazon SES`에서 서울 리전(`ap-northeast-2`)을 선택한다.

1. `Configuration > Identities`에서 발신 domain 또는 email identity를 생성한다.
2. domain identity를 사용한다면 안내된 DKIM DNS record를 등록한다.
3. identity status가 `Verified`인지 확인한다.
4. SES sandbox 상태라면 production access를 요청한다. Sandbox에서는 수신자도 검증된 주소만
   사용할 수 있으므로 임의의 일반 이메일 인증이 불가능하다.

## 2. EC2 IAM role 권한

EC2 instance role `ai-rookie-pertineo-api-ec2-role`에 최소한 다음 권한을 추가한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ses:SendEmail",
      "Resource": "*"
    }
  ]
}
```

가능하면 `Resource`를 검증한 SES identity ARN으로 제한한다.

## 3. EC2 환경변수

서버 `.env`에 다음 값을 설정한다.

```dotenv
ALLOW_ALL_EMAILS=true
EMAIL_DELIVERY_BACKEND=ses
EMAIL_FROM_ADDRESS=noreply@your-verified-domain.example
EMAIL_VERIFICATION_SUBJECT=AI Rookie 이메일 인증번호
```

기존 DynamoDB 설정은 유지한다. 인증번호는 `pertineo-email-verifications`, 인증 완료와 credit은
`pertineo-emails`에 저장된다.

## 4. 재시작과 확인

배포 후 실제 systemd unit 이름에 맞춰 서버를 재시작하고 log를 확인한다.

```bash
sudo systemctl restart ai-rookie-server
sudo systemctl status ai-rookie-server --no-pager
sudo journalctl -u ai-rookie-server -n 100 --no-pager
```

공개 API로 secret을 노출하지 않고 실제 수신 가능한 email로 발송·검증·session 시작을
확인한다. SES 오류는 `502 EMAIL_SEND_FAILED`로 반환된다.
