package com.example.demo.session.api.v2.dto;

import lombok.Value;

@Value
public class SessionStartData {
    MemberDto member;
    SessionAgreementsDto agreements;
    String expiresAt;

    @Value
    public static class MemberDto {
        String email;
    }
}

