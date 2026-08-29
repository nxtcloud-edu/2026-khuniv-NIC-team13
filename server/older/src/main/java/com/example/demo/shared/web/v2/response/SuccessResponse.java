package com.example.demo.shared.web.v2.response;

import lombok.Getter;

@Getter
public class SuccessResponse<T> extends BaseResponse<T> {

    private SuccessResponse(SuccessCode successCode, T data) {
        super(true, successCode.getCode(), successCode.getMessage(), data);
    }

    private SuccessResponse(SuccessCode successCode, String message, T data) {
        super(true, successCode.getCode(), message, data);
    }

    public static <T> SuccessResponse<T> of(T data) {
        return new SuccessResponse<>(SuccessCode.SUCCESS, data);
    }

    public static <T> SuccessResponse<T> of(SuccessCode code, T data) {
        return new SuccessResponse<>(code, data);
    }

    public static <T> SuccessResponse<T> of(SuccessCode code, String message, T data) {
        return new SuccessResponse<>(code, message, data);
    }
}
