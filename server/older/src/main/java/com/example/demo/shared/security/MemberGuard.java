package com.example.demo.shared.security;

import com.example.demo.shared.exception.NotMemberException;
import com.example.demo.shared.properties.PertineoServiceProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class MemberGuard {

    private final PertineoServiceProperties properties;

    public void requireMember(String email) {
        if (email == null) {
            throw new NotMemberException("경희대학교 구성원이 아니거나 허용된 사용자가 아닙니다.");
        }

        String normalized = email.trim().toLowerCase();
        if (!(normalized.endsWith("khu.ac.kr") || properties.getWhiteList().contains(normalized))) {
            log.info("{\"code\" : \"{}\", \"email\" : \"{}\"}", "NotMember", email);
            throw new NotMemberException("경희대학교 구성원이 아니거나 허용된 사용자가 아닙니다.");
        }
    }
}
