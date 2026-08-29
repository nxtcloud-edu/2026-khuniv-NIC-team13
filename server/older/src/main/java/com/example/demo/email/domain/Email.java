package com.example.demo.email.domain;

import lombok.Data;

@Data
public class Email {
    private Long id;

    private String email;

    private Integer count;
    private Integer verificationSuccessCount = 0;

    private Boolean valid;
}
