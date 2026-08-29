package com.example.demo.session.api.v2.app;

import com.example.demo.session.api.v2.dto.SessionAgreementsDto;
import com.example.demo.session.api.v2.dto.SessionExtendData;
import com.example.demo.session.api.v2.dto.SessionStartData;
import com.example.demo.session.api.v2.dto.SessionStartRequest;
import com.example.demo.session.api.v2.exception.AgreementRequiredException;
import com.example.demo.session.api.v2.exception.InvalidSessionException;
import com.example.demo.session.api.v2.exception.SessionExpiredException;
import com.example.demo.config.PertineoLegalProperties;
import com.example.demo.config.PertineoSessionProperties;
import com.example.demo.email.app.EmailService;
import com.example.demo.shared.dynamodb.handler.MemberTermsDocumentHandler;
import com.example.demo.shared.dynamodb.handler.SessionDynamoHandler;
import com.example.demo.shared.exception.NotMemberException;
import com.example.demo.shared.properties.PertineoServiceProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Slf4j
@Service
@RequiredArgsConstructor
public class V2SessionService {

    private final PertineoServiceProperties pertineoServiceProperties;
    private final EmailService emailService;
    private final SessionDynamoHandler sessionDynamoHandler;
    private final MemberTermsDocumentHandler memberTermsDocumentHandler;
    private final PertineoSessionProperties sessionProperties;
    private final PertineoLegalProperties legalProperties;

    public StartResult start(SessionStartRequest request) {
        String email = normalizeEmail(request.getEmail());
        validateMemberEmail(email);

        SessionStartRequest.Agreements a = request.getAgreements();
        if (!Boolean.TRUE.equals(a.getTermsOfServiceAgreed())
                || !Boolean.TRUE.equals(a.getPrivacyCollectionAgreed())
                || !Boolean.TRUE.equals(a.getPrivacyPolicyAgreed())
                || !Boolean.TRUE.equals(a.getThirdPartySharingAgreed())) {
            throw new AgreementRequiredException("모든 약관에 동의해야 합니다.");
        }

        emailService.requireEmailVerified(email);

        Instant now = Instant.now();
        MemberTermsDocumentHandler.Agreements agreements = new MemberTermsDocumentHandler.Agreements(
                a.getTermsOfServiceAgreed(),
                a.getPrivacyCollectionAgreed(),
                a.getPrivacyPolicyAgreed(),
                a.getThirdPartySharingAgreed()
        );
        MemberTermsDocumentHandler.TermsVersions versions = new MemberTermsDocumentHandler.TermsVersions(
                legalProperties.getTermsVersion(),
                legalProperties.getPrivacyCollectionVersion(),
                legalProperties.getPrivacyPolicyVersion(),
                legalProperties.getThirdPartyVersion()
        );
        memberTermsDocumentHandler.upsertTerms(email, agreements, now, versions);

        SessionDynamoHandler.UpsertActiveSessionResult upsert = sessionDynamoHandler.upsertActiveSessionForEmail(email);
        SessionDynamoHandler.SessionRecord session = upsert.session();

        SessionAgreementsDto agreementsDto = new SessionAgreementsDto(
                a.getTermsOfServiceAgreed(),
                a.getPrivacyCollectionAgreed(),
                a.getPrivacyPolicyAgreed(),
                a.getThirdPartySharingAgreed()
        );
        SessionStartData data = new SessionStartData(
                new SessionStartData.MemberDto(email),
                agreementsDto,
                session.expiresAt().toString()
        );
        log.info("session.start.ok email={} sessionRef={} refreshedExisting={}",
                maskEmail(email), shortSessionRef(session.getSessionId()), upsert.refreshedExisting());
        return new StartResult(session.getSessionId(), data);
    }

    public ExtendResult extend(String sessionId) {
        if (sessionId == null || sessionId.isBlank()) {
            throw new InvalidSessionException("세션이 유효하지 않습니다.");
        }

        SessionDynamoHandler.SessionRecord existing = sessionDynamoHandler.get(sessionId)
                .orElseThrow(() -> new InvalidSessionException("세션이 유효하지 않습니다."));

        Instant now = Instant.now();
        if (existing.isExpired(now)) {
            throw new SessionExpiredException("세션이 만료되었습니다.");
        }

        int fixedMinutes = sessionProperties.getExtendFixedMinutes();
        if (fixedMinutes < 1) {
            throw new IllegalStateException("extendFixedMinutes 설정이 올바르지 않습니다.");
        }

        SessionDynamoHandler.SessionRecord extended = sessionDynamoHandler.extendFixedFromNow(sessionId, fixedMinutes, now)
                .orElseThrow(() -> new InvalidSessionException("세션이 유효하지 않습니다."));

        SessionExtendData data = new SessionExtendData("ACTIVE", extended.expiresAt().toString());
        log.info("session.extend.ok sessionRef={} fixedMinutes={} expiresAt={}",
                shortSessionRef(sessionId), fixedMinutes, extended.expiresAt());
        return new ExtendResult(data, extended.expiresAt());
    }

    private void validateMemberEmail(String email) {
        boolean allowed = email.endsWith("khu.ac.kr") || pertineoServiceProperties.getWhiteList().contains(email);
        if (!allowed) {
            throw new NotMemberException("경희대학교 구성원이 아니거나 허용된 사용자가 아닙니다.");
        }
    }

    private static String normalizeEmail(String email) {
        return email == null ? null : email.trim().toLowerCase();
    }

    /** 로그용: 로컬파트 일부만 남기고 마스킹 */
    private static String maskEmail(String email) {
        if (email == null || !email.contains("@")) {
            return "***";
        }
        int at = email.indexOf('@');
        String local = email.substring(0, at);
        String domain = email.substring(at);
        if (local.length() <= 1) {
            return "*" + domain;
        }
        return local.charAt(0) + "***" + domain;
    }

    private static String shortSessionRef(String sessionId) {
        if (sessionId == null || sessionId.length() <= 8) {
            return sessionId == null ? "null" : "***";
        }
        return "…" + sessionId.substring(sessionId.length() - 8);
    }

    public record StartResult(String sessionId, SessionStartData data) {
    }

    public record ExtendResult(SessionExtendData data, Instant expiresAt) {
    }
}

