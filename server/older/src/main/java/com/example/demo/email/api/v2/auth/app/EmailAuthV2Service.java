package com.example.demo.email.api.v2.auth.app;

import com.example.demo.email.api.v2.auth.dto.EmailVerifyResponseData;
import com.example.demo.email.EmailVerificationConstants;
import com.example.demo.email.app.EmailService;
import com.example.demo.email.domain.Email;
import com.example.demo.shared.dynamodb.handler.AccessCodeHandler;
import com.example.demo.shared.exception.AccessCodeExpiredException;
import com.example.demo.shared.exception.AccessCodeMismatchException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class EmailAuthV2Service {

    private final AccessCodeHandler accessCodeHandler;
    private final EmailService emailService;

    public EmailVerifyResponseData verifyCode(String email, int code) {
        Integer stored = accessCodeHandler.getAccessCode(email)
                .orElseThrow(() -> new AccessCodeExpiredException("이메일에 대한 인증 코드가 만료되었습니다. 재시도 해주세요."));
        if (stored != code) {
            throw new AccessCodeMismatchException("인증번호가 일치하지 않습니다.");
        }
//        accessCodeHandler.deleteAccessCode(email); 여기서 삭제하니까 Analysis에서 검증을 못합니다. Analysis 시작되면 삭제하는걸로 바꿀게요.
        Email entity = emailService.getEmailEntity(email);
        return new EmailVerifyResponseData(
                entity.getEmail(),
                EmailVerificationConstants.MAX_VERIFICATION_SENDS_PER_DAY,
                entity.getCount(),
                entity.getValid()
        );
    }
}
