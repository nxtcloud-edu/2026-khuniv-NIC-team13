package com.example.demo.email.api.v2.auth.dto;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public class EmailVerifyResponseData {

    private final String email;
    private final Integer dailyLimit;
    private final Integer count;
    private final Boolean valid;
}
