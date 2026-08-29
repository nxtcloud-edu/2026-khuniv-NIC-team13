package com.example.demo.email.app;

import com.example.demo.email.EmailVerificationConstants;
import com.example.demo.email.domain.Email;
import com.example.demo.email.exception.AccessCodeCountException;
import com.example.demo.email.infra.EmailRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class EmailVerificationThrottle {

    private final EmailRepository emailRepository;

    public void requireUnderThreshold(String email) {
        if (email == null) {
            throw new IllegalArgumentException("이메일이 필요합니다.");
        }

        Email emailEntity = emailRepository.findByEmail(email);
        if (emailEntity != null && emailEntity.getVerificationSuccessCount() > EmailVerificationConstants.MAX_VERIFICATION_SENDS_PER_DAY) {
            log.info("{\"code\" : \"{}\", \"email\" : \"{}\"}", "UnderThreshold", email);
            throw new AccessCodeCountException("비정상적인 이메일 인증 요청 횟수가 감지되어 금일 자정까지 이용이 제한됩니다.");
        }
    }
}
