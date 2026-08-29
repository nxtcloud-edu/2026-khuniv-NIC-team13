package com.example.demo.session.api.v2.dto;

import lombok.Value;

@Value
public class SessionAgreementsDto {
    boolean termsOfServiceAgreed;
    boolean privacyCollectionAgreed;
    boolean privacyPolicyAgreed;
    boolean thirdPartySharingAgreed;
}

