package com.example.demo.analysis.app;

import com.example.demo.admin.AdminData;
import com.example.demo.analysis.exception.AnalysisCountExceedException;
import com.example.demo.email.app.EmailEntityServicePort;
import com.example.demo.email.domain.Email;
import com.example.demo.shared.properties.PertineoServiceProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class CreditGuard {

    private final EmailEntityServicePort emailEntityPort;
    private final PertineoServiceProperties properties;

    public void requireCredit(String email) {
        if (email == null) {
            return;
        }

        if (AdminData.whiteList.contains(email)) {
            return;
        }

        if (properties.getAdminList().contains(email)) {
            return;
        }

        Email emailEntity = emailEntityPort.getEmailEntity(email);

        if (emailEntity == null) {
            return;
        }

        if (emailEntity.getCount() > 3) {
            log.info("{\"code\" : \"{}\", \"email\" : \"{}\"}", "NoCredit", email);
            throw new AnalysisCountExceedException("허용 횟수를 초과했습니다.");
        }
    }
}
