package com.example.demo.notice.api.v2.domain;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class NoticeV2 {

    private Long id;
    private String title;
    private String content;
    private LocalDateTime createdAt;
    private LocalDateTime modifiedAt;
}
