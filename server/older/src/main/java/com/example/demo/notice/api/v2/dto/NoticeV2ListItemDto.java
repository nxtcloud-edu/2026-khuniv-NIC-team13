package com.example.demo.notice.api.v2.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class NoticeV2ListItemDto {

    private Long id;
    private String title;
    private LocalDateTime modifiedAt;
}
