package com.example.demo.shared.web.v2.response;

import lombok.Getter;

@Getter
public enum SuccessCode {

    SUCCESS("SUCCESS", "요청이 성공적으로 처리되었습니다."),
    CREATED("CREATED", "리소스가 성공적으로 생성되었습니다.");

    private final String code;
    private final String message;

    SuccessCode(String code, String message) {
        this.code = code;
        this.message = message;
    }
}
