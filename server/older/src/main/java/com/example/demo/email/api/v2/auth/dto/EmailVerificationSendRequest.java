package com.example.demo.email.api.v2.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;

@Getter
public class EmailVerificationSendRequest {

    @Email
    @NotNull
    private String email;
}
