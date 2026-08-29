package com.example.demo.notice.domain;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class Notice {

    private Long id;
    private String title;
    private String content;
    private LocalDateTime createdAt;
    private LocalDateTime modifiedAt;

}