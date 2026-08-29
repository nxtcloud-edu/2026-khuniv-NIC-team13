package com.example.demo.shared.web.v2.response;

import lombok.Getter;

@Getter
public enum ErrorCode {

    INVALID_EMAIL_FORMAT("INVALID_EMAIL_FORMAT", "유효하지 않은 이메일 형식입니다."),
    INVALID_REQUEST("INVALID_REQUEST", "요청이 올바르지 않습니다."),
    EMAIL_SEND_FAILED("EMAIL_SEND_FAILED", "이메일 전송에 실패했습니다."),
    INVALID_ACCESS_CODE("INVALID_ACCESS_CODE", "유효하지 않은 인증 코드입니다."),
    ACCESS_CODE_EXPIRED("ACCESS_CODE_EXPIRED", "인증 코드가 만료되었습니다."),
    NOTICE_NOT_FOUND("NOTICE_NOT_FOUND", "요청한 공지사항을 찾을 수 없습니다."),
    UNAUTHORIZED_ADMIN("UNAUTHORIZED_ADMIN", "관리자 권한이 없습니다."),
    NOT_AUTHENTICATED("NOT_AUTHENTICATED", "로그인이 필요합니다."),
    ACCESS_CODE_LIMIT_EXCEEDED("ACCESS_CODE_LIMIT_EXCEEDED", "인증 코드 요청 한도를 초과했습니다."),
    ANALYSIS_COUNT_EXCEEDED("ANALYSIS_COUNT_EXCEEDED", "분석 요청 한도를 초과했습니다."),
    SESSION_INVALID("SESSION_INVALID", "세션이 유효하지 않습니다."),
    SESSION_ALREADY_ACTIVE("SESSION_ALREADY_ACTIVE", "이미 활성 세션이 있습니다."),
    SESSION_EXPIRED("SESSION_EXPIRED", "세션이 만료되었습니다."),
    AGREEMENT_REQUIRED("AGREEMENT_REQUIRED", "모든 약관에 동의해야 합니다."),
    EMAIL_NOT_VERIFIED("EMAIL_NOT_VERIFIED", "이메일 인증을 먼저 완료해 주세요.");

    private final String code;
    private final String message;

    ErrorCode(String code, String message) {
        this.code = code;
        this.message = message;
    }
}
