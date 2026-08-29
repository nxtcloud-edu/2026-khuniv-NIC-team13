package com.example.demo.session.api.v2.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;

@Getter
public class SessionStartRequest {

    @Email
    @NotNull
    private String email;

    @Valid
    @NotNull
    private Agreements agreements;

    @Getter
    public static class Agreements {
        @NotNull
        private Boolean termsOfServiceAgreed;
        @NotNull
        private Boolean privacyCollectionAgreed;
        @NotNull
        private Boolean privacyPolicyAgreed;
        @NotNull
        private Boolean thirdPartySharingAgreed;
    }
}
