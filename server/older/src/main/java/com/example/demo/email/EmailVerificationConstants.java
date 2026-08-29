package com.example.demo.email;

/**
 * 이메일 인증번호 발송 빈도 제한(일일)에 사용하는 상한.
 */
public final class EmailVerificationConstants {

    /** 자정 초기화 전까지 허용하는 발송(성공) 횟수 상한. 초과 시 {@link com.example.demo.email.exception.AccessCodeCountException}. */
    public static final int MAX_VERIFICATION_SENDS_PER_DAY = 10;

    private EmailVerificationConstants() {
    }
}
