package com.example.demo.shared.web.v2.response;

import lombok.Getter;

@Getter
public class ErrorResponse extends BaseResponse<Object> {

    private ErrorResponse(ErrorCode errorCode) {
        super(false, errorCode.getCode(), errorCode.getMessage(), null);
    }

    private ErrorResponse(ErrorCode errorCode, String message) {
        super(false, errorCode.getCode(), message, null);
    }

    public static ErrorResponse of(ErrorCode code) {
        return new ErrorResponse(code);
    }

    public static ErrorResponse of(ErrorCode code, String message) {
        return new ErrorResponse(code, message);
    }
}
